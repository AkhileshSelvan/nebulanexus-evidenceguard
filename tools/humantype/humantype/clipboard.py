"""Reading the system clipboard without hard-depending on pyperclip."""

from __future__ import annotations

import shutil
import subprocess
import sys


class ClipboardError(RuntimeError):
    """Raised when no clipboard could be read on this machine."""


def _try_command(args: list[str]) -> str | None:
    if not shutil.which(args[0]):
        return None
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout


def read_clipboard() -> str:
    """Return the clipboard's text content.

    Tries pyperclip first (it handles all three platforms and is what most
    people already have), then falls back to whatever CLI tool is present.
    """
    try:
        import pyperclip  # type: ignore

        return pyperclip.paste()
    except ImportError:
        pass
    except Exception:  # pragma: no cover - pyperclip raises its own errors
        pass

    if sys.platform == "darwin":
        text = _try_command(["pbpaste"])
        if text is not None:
            return text
    elif sys.platform.startswith("linux"):
        for args in (
            ["wl-paste", "--no-newline"],
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        ):
            text = _try_command(args)
            if text is not None:
                return text
    elif sys.platform.startswith("win"):
        text = _try_command(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]
        )
        if text is not None:
            return text

    raise ClipboardError(
        "Could not read the clipboard. Install pyperclip:\n"
        "    pip install pyperclip\n"
        "or pass the text another way: --file <path>, or pipe it on stdin."
    )
