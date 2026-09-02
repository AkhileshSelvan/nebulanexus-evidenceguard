"""humantype -- replay text as human-like keystrokes.

Split into a pure planner (what keys, with what delays) and a thin driver
(actually send them), so the interesting behaviour is testable without a
display, a clipboard, or a focused window.
"""

from .profile import TypingProfile, PROFILES, IndentMode
from .planner import Keystroke, plan
from .runner import run

__all__ = ["TypingProfile", "PROFILES", "IndentMode", "Keystroke", "plan", "run"]
__version__ = "0.1.0"
