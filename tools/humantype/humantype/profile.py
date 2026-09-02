"""Timing profiles: how fast, how uneven, how hesitant."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Standard typing-speed convention: one "word" is five characters, so
# characters-per-minute is wpm * 5.
CHARS_PER_WORD = 5


class IndentMode(str, Enum):
    """How to deal with an editor that indents for you.

    LITERAL  -- type the text exactly as-is. Correct for plain <textarea>
                fields and terminals, wrong for editors that auto-indent
                (each line drifts further right).
    RESET    -- after each newline, select from the cursor back to the start
                of the line (shift+Home) before typing. Whatever the editor
                auto-inserted is selected, and the first character typed
                replaces it. Safe when nothing was inserted: the selection is
                simply empty.
    STRIP    -- drop our own leading whitespace and let the editor indent.
                Only sane for editors whose auto-indent you actually trust.
    """

    LITERAL = "literal"
    RESET = "reset"
    STRIP = "strip"


@dataclass(frozen=True)
class TypingProfile:
    """Everything that shapes the rhythm of the output.

    Delays are in seconds. The planner is deterministic for a given seed, so
    two runs with the same profile and seed produce identical timings.
    """

    wpm: float = 220.0
    """Sustained speed in words per minute, before jitter and pauses."""

    jitter: float = 0.32
    """Relative spread of per-character delay. 0 gives metronome timing."""

    symbol_factor: float = 1.55
    """Multiplier for characters that need a modifier key or the number row."""

    repeat_factor: float = 0.72
    """Multiplier when a character repeats the previous one."""

    indent_factor: float = 0.45
    """Multiplier for leading whitespace, which people rattle off."""

    newline_pause: float = 0.11
    """Extra pause charged after Enter, on top of the usual delay."""

    block_pause: float = 0.28
    """Extra pause after a line that opens or closes a block."""

    thinking_rate: float = 0.015
    """Probability, per character, of stopping to think mid-line."""

    thinking_min: float = 0.30
    thinking_max: float = 1.10

    typo_rate: float = 0.0
    """Probability, per letter, of hitting a neighbouring key and fixing it."""

    typo_notice_min: float = 0.12
    typo_notice_max: float = 0.38
    """How long a typo sits on screen before the backspace lands."""

    min_delay: float = 0.004
    """Floor, so jitter can never produce a zero or negative delay."""

    def base_delay(self) -> float:
        """Seconds per character before any per-character adjustment."""
        if self.wpm <= 0:
            raise ValueError("wpm must be positive")
        return 60.0 / (self.wpm * CHARS_PER_WORD)


#: Named starting points. `--profile fast` etc. on the command line.
PROFILES: dict[str, TypingProfile] = {
    # Quick and even -- the default. Reads as a fast, confident typist.
    "fast": TypingProfile(wpm=320.0, jitter=0.26, thinking_rate=0.006),
    # A plausible working developer.
    "natural": TypingProfile(wpm=210.0, jitter=0.34, thinking_rate=0.018),
    # Hesitant, with the occasional corrected slip.
    "careful": TypingProfile(
        wpm=140.0,
        jitter=0.42,
        thinking_rate=0.045,
        thinking_max=1.6,
        typo_rate=0.012,
    ),
    # For screencasts: slow enough to follow on video.
    "demo": TypingProfile(wpm=95.0, jitter=0.30, newline_pause=0.35, block_pause=0.6),
    # No humanising at all -- even timing, useful for debugging.
    "robot": TypingProfile(
        wpm=600.0,
        jitter=0.0,
        symbol_factor=1.0,
        repeat_factor=1.0,
        indent_factor=1.0,
        newline_pause=0.0,
        block_pause=0.0,
        thinking_rate=0.0,
    ),
}

DEFAULT_PROFILE = "fast"
