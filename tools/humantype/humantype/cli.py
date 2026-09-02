"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from . import __version__
from .clipboard import ClipboardError, read_clipboard
from .drivers import DriverError, make_driver
from .planner import duration, plan, transcript
from .profile import DEFAULT_PROFILE, PROFILES, IndentMode, TypingProfile
from .runner import countdown, run
from .text import describe_character, normalise, unsupported_characters

EPILOG = """\
examples:
  humantype                          type the clipboard, after a 5s countdown
  humantype --file main.py           type a file instead of the clipboard
  cat main.py | humantype --stdin    type whatever is piped in
  humantype --indent reset           for editors that auto-indent (VS Code)
  humantype --profile demo           slow enough to follow on a screencast
  humantype --dry-run                show the plan without touching the keyboard
  humantype --hotkey '<ctrl>+<alt>+v'   daemon: type the clipboard on a hotkey

The countdown exists so you can click into the target field. Whatever window
has focus when the countdown ends is what gets typed into.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="humantype",
        description="Replay text as human-like keystrokes into the focused window.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"humantype {__version__}")

    source = parser.add_argument_group("source (default: clipboard)")
    source.add_argument("--file", metavar="PATH", help="read the text from a file")
    source.add_argument("--stdin", action="store_true", help="read the text from stdin")
    source.add_argument("--text", metavar="STRING", help="use this literal string")

    rhythm = parser.add_argument_group("rhythm")
    rhythm.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=DEFAULT_PROFILE,
        help=f"named timing profile (default: {DEFAULT_PROFILE})",
    )
    rhythm.add_argument("--wpm", type=float, help="override words per minute")
    rhythm.add_argument("--jitter", type=float, help="override timing spread (0 = metronome)")
    rhythm.add_argument("--typos", type=float, metavar="RATE",
                        help="per-letter chance of a typo that gets corrected, e.g. 0.01")
    rhythm.add_argument("--speed", type=float, default=1.0,
                        help="divide every delay by this (2.0 = twice as fast)")
    rhythm.add_argument("--seed", type=int, help="fix the RNG seed for a reproducible rhythm")

    shape = parser.add_argument_group("text handling")
    shape.add_argument(
        "--indent",
        choices=[m.value for m in IndentMode],
        default=IndentMode.LITERAL.value,
        help="literal: type as-is (plain fields). reset: overwrite the editor's "
             "auto-indent. strip: let the editor indent. (default: literal)",
    )
    shape.add_argument("--tab-width", type=int, default=4,
                       help="spaces per tab; tabs are never sent raw (default: 4)")
    shape.add_argument("--keep-trailing", action="store_true",
                       help="keep trailing whitespace on each line")
    shape.add_argument("--keep-smart-quotes", action="store_true",
                       help="do not rewrite curly quotes and dashes to ASCII")

    output = parser.add_argument_group("execution")
    output.add_argument("--delay", type=float, default=5.0,
                        help="countdown before typing starts (default: 5)")
    output.add_argument("--backend", default="auto",
                        choices=["auto", "pynput", "xdotool", "dry-run"],
                        help="keyboard backend (default: auto)")
    output.add_argument("--dry-run", action="store_true",
                        help="print the plan and the resulting text; press no keys")
    output.add_argument("--preview", action="store_true",
                        help="print size and estimated duration, then exit")
    output.add_argument("--quiet", action="store_true", help="suppress progress messages")
    output.add_argument("--hotkey", metavar="COMBO",
                        help="stay resident and type the clipboard whenever COMBO is pressed")
    return parser


def load_text(args: argparse.Namespace) -> str:
    """Resolve the input source. Exactly one may be given.

    Presence, not truthiness: `--text ""` is a deliberate empty payload and
    must not silently fall through to the clipboard.
    """
    chosen = [
        name
        for name in ("file", "stdin", "text")
        if getattr(args, name) is not None and getattr(args, name) is not False
    ]
    if len(chosen) > 1:
        raise SystemExit(f"humantype: pick one source, not {' and '.join('--' + c for c in chosen)}")

    if args.file is not None:
        try:
            with open(args.file, "r", encoding="utf-8") as handle:
                return handle.read()
        except OSError as exc:
            raise SystemExit(f"humantype: cannot read {args.file}: {exc}") from exc
    if args.stdin:
        return sys.stdin.read()
    if args.text is not None:
        return args.text
    try:
        return read_clipboard()
    except ClipboardError as exc:
        raise SystemExit(f"humantype: {exc}") from exc


def resolve_profile(args: argparse.Namespace) -> TypingProfile:
    profile = PROFILES[args.profile]
    overrides = {}
    if args.wpm is not None:
        if args.wpm <= 0:
            raise SystemExit("humantype: --wpm must be positive")
        overrides["wpm"] = args.wpm
    if args.jitter is not None:
        if args.jitter < 0:
            raise SystemExit("humantype: --jitter cannot be negative")
        overrides["jitter"] = args.jitter
    if args.typos is not None:
        if not 0.0 <= args.typos <= 1.0:
            raise SystemExit("humantype: --typos must be between 0 and 1")
        overrides["typo_rate"] = args.typos
    return replace(profile, **overrides) if overrides else profile


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m {seconds % 60:04.1f}s"


def prepare(args: argparse.Namespace, raw: str, log) -> list:
    """Normalise the text, warn about anything odd, and build the plan."""
    clean, report = normalise(
        raw,
        tab_width=args.tab_width,
        strip_trailing=not args.keep_trailing,
        fix_punctuation=not args.keep_smart_quotes,
    )
    if report.touched:
        for note in report.summary():
            log(f"  cleaned: {note}")

    exotic = unsupported_characters(clean)
    if exotic:
        shown = ", ".join(describe_character(ch) for ch in exotic[:5])
        more = f" (+{len(exotic) - 5} more)" if len(exotic) > 5 else ""
        log(f"  warning: {len(exotic)} character(s) may not type on your keyboard layout: {shown}{more}")

    return plan(
        clean,
        resolve_profile(args),
        indent_mode=IndentMode(args.indent),
        seed=args.seed,
    )


def type_once(args: argparse.Namespace, raw: str, log) -> int:
    keystrokes = prepare(args, raw, log)
    if not keystrokes:
        log("Nothing to type.")
        return 0

    lines = raw.count("\n") + 1
    estimate = duration(keystrokes) / args.speed
    log(f"{len(keystrokes)} keystrokes over {lines} line(s) -- about {_format_duration(estimate)}.")

    if args.preview:
        return 0

    if args.dry_run:
        print(transcript(keystrokes), end="" if raw.endswith("\n") else "\n")
        return 0

    try:
        driver = make_driver(args.backend)
    except DriverError as exc:
        raise SystemExit(f"humantype: {exc}") from exc

    countdown(args.delay, log)
    log("Typing...")
    try:
        sent = run(keystrokes, driver, speed=args.speed)
    except DriverError as exc:
        raise SystemExit(f"humantype: {exc}") from exc
    except KeyboardInterrupt:
        log("\nStopped. The target field holds a partial paste.")
        return 130
    finally:
        driver.close()

    log(f"Done -- {sent} keystrokes sent.")
    return 0


def run_hotkey_daemon(args: argparse.Namespace, log) -> int:
    """Stay resident and type the clipboard whenever the hotkey fires.

    This is the mode that avoids the countdown entirely: focus is already
    where you want it when you press the key.
    """
    try:
        from pynput import keyboard
    except ImportError:
        raise SystemExit(
            "humantype: --hotkey needs pynput. Install it with:\n    pip install pynput"
        )

    try:
        driver = make_driver(args.backend if args.backend != "auto" else "pynput")
    except DriverError as exc:
        raise SystemExit(f"humantype: {exc}") from exc

    def fire() -> None:
        try:
            raw = read_clipboard()
        except ClipboardError as exc:
            log(f"  clipboard unavailable: {exc}")
            return
        if not raw.strip():
            log("  clipboard is empty.")
            return
        keystrokes = prepare(args, raw, log)
        log(f"  typing {len(keystrokes)} keystrokes...")
        run(keystrokes, driver, speed=args.speed)
        log("  done.")

    log(f"Listening for {args.hotkey}. Press Ctrl+C to stop.")
    try:
        with keyboard.GlobalHotKeys({args.hotkey: fire}) as listener:
            listener.join()
    except KeyboardInterrupt:
        log("\nStopped.")
    except ValueError as exc:
        raise SystemExit(
            f"humantype: could not parse hotkey {args.hotkey!r}: {exc}\n"
            "Use pynput syntax, e.g. '<ctrl>+<alt>+v'"
        ) from exc
    finally:
        driver.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log = (lambda _msg: None) if args.quiet else (lambda msg: print(msg, file=sys.stderr))

    if args.speed <= 0:
        raise SystemExit("humantype: --speed must be positive")

    if args.hotkey:
        return run_hotkey_daemon(args, log)
    return type_once(args, load_text(args), log)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
