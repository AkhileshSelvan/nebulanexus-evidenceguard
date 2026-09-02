"""Turning arbitrary clipboard content into something safe to type.

The hazards are mundane but unforgiving: a raw Tab moves focus out of the
field in a browser, a CR types a second newline, and a non-breaking space
looks identical to a space but is a different character.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

#: Characters that look like a plain space but are not one. Portals paste
#: these in constantly (copied from rendered HTML) and compilers hate them.
LOOKALIKE_SPACES = "               　"

#: Smart punctuation that a code editor will happily accept and a compiler
#: will not. Mapped back to the ASCII the author almost certainly meant.
SMART_PUNCTUATION = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "−": "-",
    "…": "...",
}

#: Zero-width and directional marks: invisible, and silently break parsers.
INVISIBLE = "​‌‍‎‏⁠﻿"


@dataclass(frozen=True)
class CleanupReport:
    """What normalise() had to change, so the CLI can say so out loud."""

    tabs_expanded: int = 0
    lookalike_spaces: int = 0
    smart_punctuation: int = 0
    invisible_removed: int = 0
    trailing_stripped: int = 0
    crlf_normalised: bool = False

    @property
    def touched(self) -> bool:
        return bool(
            self.tabs_expanded
            or self.lookalike_spaces
            or self.smart_punctuation
            or self.invisible_removed
            or self.trailing_stripped
            or self.crlf_normalised
        )

    def summary(self) -> list[str]:
        notes = []
        if self.crlf_normalised:
            notes.append("normalised CRLF line endings")
        if self.tabs_expanded:
            notes.append(f"expanded {self.tabs_expanded} tab(s) to spaces")
        if self.lookalike_spaces:
            notes.append(f"replaced {self.lookalike_spaces} non-breaking/exotic space(s)")
        if self.smart_punctuation:
            notes.append(f"replaced {self.smart_punctuation} smart quote(s)/dash(es)")
        if self.invisible_removed:
            notes.append(f"removed {self.invisible_removed} zero-width character(s)")
        if self.trailing_stripped:
            notes.append(f"stripped trailing whitespace on {self.trailing_stripped} line(s)")
        return notes


def expand_tabs(line: str, tab_width: int) -> str:
    """Expand tabs to the next tab stop, the way an editor renders them.

    str.expandtabs does exactly this, but only when applied per line -- run
    over a whole document it still works, since \\n resets the column. Kept
    as a named function because the intent is easy to lose.
    """
    return line.expandtabs(tab_width)


def normalise(
    text: str,
    *,
    tab_width: int = 4,
    strip_trailing: bool = True,
    fix_punctuation: bool = True,
) -> tuple[str, CleanupReport]:
    """Make `text` safe to send as keystrokes.

    Returns the cleaned text and a report of what was changed. Nothing here
    is cosmetic: every transform exists because the untransformed character
    misbehaves when typed into a real field.
    """
    crlf = "\r" in text
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    invisible_removed = sum(text.count(ch) for ch in INVISIBLE)
    if invisible_removed:
        text = text.translate({ord(ch): None for ch in INVISIBLE})

    lookalikes = sum(text.count(ch) for ch in LOOKALIKE_SPACES)
    if lookalikes:
        text = text.translate({ord(ch): " " for ch in LOOKALIKE_SPACES})

    smart = 0
    if fix_punctuation:
        smart = sum(text.count(ch) for ch in SMART_PUNCTUATION)
        if smart:
            text = text.translate({ord(k): v for k, v in SMART_PUNCTUATION.items()})

    tabs = text.count("\t")
    if tabs:
        text = "\n".join(expand_tabs(line, tab_width) for line in text.split("\n"))

    trailing = 0
    if strip_trailing:
        lines = text.split("\n")
        stripped = [line.rstrip() for line in lines]
        trailing = sum(1 for a, b in zip(lines, stripped) if a != b)
        text = "\n".join(stripped)

    report = CleanupReport(
        tabs_expanded=tabs,
        lookalike_spaces=lookalikes,
        smart_punctuation=smart,
        invisible_removed=invisible_removed,
        trailing_stripped=trailing,
        crlf_normalised=crlf,
    )
    return text, report


def unsupported_characters(text: str) -> list[str]:
    """Characters a keyboard driver is unlikely to be able to produce.

    Anything outside Basic Latin that isn't a newline. These do not fail
    loudly -- they usually type as nothing at all -- so the CLI warns first
    rather than letting the user discover a silently truncated paste.
    """
    seen: dict[str, None] = {}
    for ch in text:
        if ch == "\n":
            continue
        if ord(ch) < 0x20 or ord(ch) > 0x7E:
            seen.setdefault(ch, None)
    return list(seen)


def describe_character(ch: str) -> str:
    """Human-readable label for a character, for warning messages."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = "unnamed control character"
    return f"U+{ord(ch):04X} ({name})"
