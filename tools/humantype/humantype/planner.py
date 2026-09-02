"""The pure core: text in, timed keystrokes out.

No clipboard, no display, no sleeping. `plan()` is deterministic for a given
seed, which is what makes the rhythm testable instead of a thing you can only
eyeball.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator, Literal

from .profile import IndentMode, TypingProfile

KeyName = Literal["enter", "backspace", "shift+home"]

#: Characters that require Shift or a stretch to the number row. Typing these
#: measurably slows people down, which is most of what makes replayed code
#: read as typed rather than injected.
AWKWARD = set("~!@#$%^&*()_+{}|:\"<>?" + "1234567890-=[]\;',./`")

#: QWERTY neighbours, used only to make a simulated typo land on a key that a
#: hand could plausibly have hit instead.
_NEIGHBOURS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop;", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol;[", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}


@dataclass(frozen=True)
class Keystroke:
    """One thing to send, and how long to wait before sending it.

    `delay` is charged *before* the keystroke, so a plan can open with a
    pause and the runner never needs a special case for the first key.
    """

    kind: Literal["char", "key"]
    value: str
    delay: float

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        shown = repr(self.value) if self.kind == "char" else f"<{self.value}>"
        return f"{self.delay * 1000:6.1f}ms {shown}"


def _char_delay(
    ch: str,
    previous: str | None,
    profile: TypingProfile,
    rng: random.Random,
    *,
    in_indent: bool,
) -> float:
    """How long a hand would take to get to this character."""
    delay = profile.base_delay()

    if in_indent and ch == " ":
        delay *= profile.indent_factor
    elif ch in AWKWARD:
        delay *= profile.symbol_factor

    if previous is not None and ch == previous:
        delay *= profile.repeat_factor

    if profile.jitter > 0:
        # Log-normal, so delays can spike long but never go negative -- the
        # shape real keystroke intervals actually have.
        delay *= rng.lognormvariate(0.0, profile.jitter)

    return max(delay, profile.min_delay)


def _maybe_think(profile: TypingProfile, rng: random.Random) -> float:
    """Occasionally, a person stops mid-line and looks at what they wrote."""
    if profile.thinking_rate <= 0:
        return 0.0
    if rng.random() >= profile.thinking_rate:
        return 0.0
    return rng.uniform(profile.thinking_min, profile.thinking_max)


def _typo_for(ch: str, rng: random.Random) -> str | None:
    """A neighbouring key, if this character has plausible neighbours."""
    neighbours = _NEIGHBOURS.get(ch.lower())
    if not neighbours:
        return None
    wrong = rng.choice(neighbours)
    return wrong.upper() if ch.isupper() else wrong


def _opens_or_closes_block(line: str) -> bool:
    """Whether a line ends a logical chunk, earning a slightly longer breath."""
    stripped = line.strip()
    if not stripped:
        return False
    return stripped[-1] in "{}:;" or stripped in ("}", "});", "};")


def _type_line(
    line: str,
    profile: TypingProfile,
    rng: random.Random,
    *,
    lead_delay: float,
) -> Iterator[Keystroke]:
    """Emit the keystrokes for one line's worth of characters."""
    indent_len = len(line) - len(line.lstrip(" "))
    previous: str | None = None
    pending = lead_delay

    for index, ch in enumerate(line):
        delay = pending + _char_delay(
            ch, previous, profile, rng, in_indent=index < indent_len
        )
        pending = 0.0

        # A slip is only interesting mid-word, and only on letters.
        if (
            profile.typo_rate > 0
            and ch.isalpha()
            and index >= indent_len
            and rng.random() < profile.typo_rate
        ):
            wrong = _typo_for(ch, rng)
            if wrong is not None:
                yield Keystroke("char", wrong, delay)
                notice = rng.uniform(profile.typo_notice_min, profile.typo_notice_max)
                yield Keystroke("key", "backspace", notice)
                delay = _char_delay(ch, None, profile, rng, in_indent=False)

        yield Keystroke("char", ch, delay)
        previous = ch

        think = _maybe_think(profile, rng)
        if think:
            pending += think


def plan(
    text: str,
    profile: TypingProfile,
    *,
    indent_mode: IndentMode = IndentMode.LITERAL,
    seed: int | None = None,
    start_delay: float = 0.0,
) -> list[Keystroke]:
    """Turn `text` into the exact sequence of keystrokes to replay.

    `text` is expected to be normalised already (see text.normalise) -- no
    tabs, no CRLF. Lines are joined with an explicit Enter key rather than a
    literal newline character, because a newline typed as a character does
    nothing in most single-line and rich-text fields.
    """
    rng = random.Random(seed)
    lines = text.split("\n")
    out: list[Keystroke] = []
    lead = start_delay

    for index, raw in enumerate(lines):
        line = raw.lstrip(" ") if indent_mode is IndentMode.STRIP else raw

        if index > 0:
            newline_delay = lead + profile.base_delay() + profile.newline_pause
            if _opens_or_closes_block(lines[index - 1]):
                newline_delay += profile.block_pause
            out.append(Keystroke("key", "enter", newline_delay))
            lead = 0.0

            # Select whatever the editor auto-indented, so the first typed
            # character overwrites it. Pointless on a blank line, and worse
            # than pointless -- it would leave a live selection behind.
            if indent_mode is IndentMode.RESET and line.strip():
                out.append(Keystroke("key", "shift+home", profile.base_delay() * 0.6))

        if line:
            out.extend(_type_line(line, profile, rng, lead_delay=lead))
            lead = 0.0

    return out


def duration(keystrokes: list[Keystroke]) -> float:
    """Total wall-clock seconds a plan will take to replay."""
    return sum(k.delay for k in keystrokes)


def transcript(keystrokes: list[Keystroke]) -> str:
    """Reconstruct the text a plan would produce, for --dry-run and tests.

    This models a real field: backspace deletes, and shift+Home selects back
    to the line start so the next character replaces the selection. If the
    transcript does not match the input, the plan is wrong.
    """
    buffer: list[str] = []
    selecting = False

    for stroke in keystrokes:
        if stroke.kind == "key":
            if stroke.value == "enter":
                buffer.append("\n")
                selecting = False
            elif stroke.value == "backspace":
                if buffer:
                    buffer.pop()
                selecting = False
            elif stroke.value == "shift+home":
                selecting = True
            else:  # pragma: no cover - guards against a new key name
                raise ValueError(f"unknown key: {stroke.value}")
            continue

        if selecting:
            # Drop everything back to the start of the current line: that is
            # what the selection covered.
            while buffer and buffer[-1] != "\n":
                buffer.pop()
            selecting = False
        buffer.append(stroke.value)

    return "".join(buffer)
