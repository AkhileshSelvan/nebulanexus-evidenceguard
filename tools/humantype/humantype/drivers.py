"""Backends that actually press keys.

Kept deliberately thin. Everything worth testing lives in the planner; a
driver's only job is to turn a Keystroke into an OS-level key event, which is
what makes the text land in *any* focused window -- editor, terminal, remote
console, browser field -- rather than only in pages that cooperate.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Protocol


class DriverError(RuntimeError):
    """Raised when a backend cannot be used on this machine."""


class Driver(Protocol):
    """Minimal surface the runner needs."""

    name: str

    def type_char(self, ch: str) -> None: ...

    def press_key(self, name: str) -> None: ...

    def close(self) -> None: ...


class DryRunDriver:
    """Records keystrokes instead of sending them. Used by --dry-run."""

    name = "dry-run"

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def type_char(self, ch: str) -> None:
        self.events.append(("char", ch))

    def press_key(self, name: str) -> None:
        self.events.append(("key", name))

    def close(self) -> None:
        return None


class PynputDriver:
    """Cross-platform backend (Windows, macOS, Linux/X11) via pynput."""

    name = "pynput"

    def __init__(self) -> None:
        try:
            from pynput.keyboard import Controller, Key
        except ImportError as exc:  # pragma: no cover - environment specific
            raise DriverError(
                "pynput is not installed. Install it with:\n"
                "    pip install pynput"
            ) from exc
        except Exception as exc:  # pragma: no cover - headless import failure
            raise DriverError(
                f"pynput could not start ({exc}). On Linux this usually means "
                "no X11 display is available."
            ) from exc

        self._keyboard = Controller()
        self._Key = Key

    def type_char(self, ch: str) -> None:
        self._keyboard.type(ch)

    def press_key(self, name: str) -> None:
        Key = self._Key
        if name == "enter":
            self._keyboard.tap(Key.enter)
        elif name == "backspace":
            self._keyboard.tap(Key.backspace)
        elif name == "shift+home":
            with self._keyboard.pressed(Key.shift):
                self._keyboard.tap(Key.home)
        else:  # pragma: no cover - guards against a new key name
            raise DriverError(f"unsupported key: {name}")

    def close(self) -> None:
        return None


class XdotoolDriver:
    """Linux/X11 fallback for when pynput will not install.

    Slower per keystroke (one subprocess each), so the planner's timing is
    approximate here. Fine for code-sized payloads.
    """

    name = "xdotool"

    _KEYS = {"enter": "Return", "backspace": "BackSpace", "shift+home": "shift+Home"}

    def __init__(self) -> None:
        if not shutil.which("xdotool"):
            raise DriverError(
                "xdotool not found. Install it with:\n"
                "    sudo apt install xdotool"
            )

    def _run(self, args: list[str]) -> None:
        result = subprocess.run(
            ["xdotool", *args], capture_output=True, text=True
        )
        if result.returncode != 0:  # pragma: no cover - environment specific
            raise DriverError(f"xdotool failed: {result.stderr.strip()}")

    def type_char(self, ch: str) -> None:
        # `--` stops xdotool reading a leading dash as a flag.
        self._run(["type", "--clearmodifiers", "--", ch])

    def press_key(self, name: str) -> None:
        key = self._KEYS.get(name)
        if key is None:  # pragma: no cover - guards against a new key name
            raise DriverError(f"unsupported key: {name}")
        self._run(["key", "--clearmodifiers", key])

    def close(self) -> None:
        return None


def available_backends() -> list[str]:
    """Backend names in the order auto-selection tries them."""
    return ["pynput", "xdotool"]


def make_driver(name: str = "auto") -> Driver:
    """Build a driver by name, or pick the first one that works."""
    if name == "dry-run":
        return DryRunDriver()
    if name == "pynput":
        return PynputDriver()
    if name == "xdotool":
        return XdotoolDriver()
    if name != "auto":
        raise DriverError(f"unknown backend: {name}")

    problems = []
    for candidate in available_backends():
        if candidate == "xdotool" and not sys.platform.startswith("linux"):
            continue
        try:
            return make_driver(candidate)
        except DriverError as exc:
            problems.append(f"  {candidate}: {exc}")

    raise DriverError(
        "No usable keyboard backend on this machine.\n" + "\n".join(problems)
    )
