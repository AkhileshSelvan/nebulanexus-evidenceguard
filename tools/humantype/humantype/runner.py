"""Replaying a plan against a driver, in real time."""

from __future__ import annotations

import time
from typing import Callable, Iterable

from .drivers import Driver
from .planner import Keystroke


def run(
    keystrokes: Iterable[Keystroke],
    driver: Driver,
    *,
    speed: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    on_progress: Callable[[int, Keystroke], None] | None = None,
) -> int:
    """Send every keystroke, honouring its delay. Returns the count sent.

    `speed` divides every delay, so 2.0 replays twice as fast while keeping
    the same rhythm. `sleep` is injectable so tests can run instantly.
    """
    if speed <= 0:
        raise ValueError("speed must be positive")

    sent = 0
    for stroke in keystrokes:
        if stroke.delay > 0:
            sleep(stroke.delay / speed)
        if stroke.kind == "char":
            driver.type_char(stroke.value)
        else:
            driver.press_key(stroke.value)
        sent += 1
        if on_progress is not None:
            on_progress(sent, stroke)
    return sent


def countdown(seconds: float, announce: Callable[[str], None], *, sleep=time.sleep) -> None:
    """Give the user time to click into the target field before typing starts.

    Counts whole seconds so the message is useful; a fractional remainder is
    slept off first.
    """
    if seconds <= 0:
        return
    whole = int(seconds)
    remainder = seconds - whole
    if remainder > 0:
        sleep(remainder)
    for remaining in range(whole, 0, -1):
        announce(f"Typing in {remaining}... (click into the target field now)")
        sleep(1.0)
