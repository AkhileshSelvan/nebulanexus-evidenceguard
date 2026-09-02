import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from humantype.cli import build_parser, main, resolve_profile


def run_cli(*argv):
    """Run main() capturing both streams; returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class DryRunTests(unittest.TestCase):
    def test_dry_run_prints_the_text_it_would_type(self):
        code, out, _ = run_cli("--text", "x = 1", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out, "x = 1\n")

    def test_dry_run_round_trips_indented_code(self):
        source = "def f():\n    return 1\n"
        code, out, _ = run_cli("--text", source, "--dry-run", "--indent", "reset")
        self.assertEqual(code, 0)
        self.assertEqual(out, source)

    def test_dry_run_presses_no_keys_even_with_a_real_backend_requested(self):
        # --dry-run must short-circuit before a driver is ever constructed,
        # or a headless machine would fail here instead of printing.
        code, out, _ = run_cli("--text", "hi", "--dry-run", "--backend", "pynput")
        self.assertEqual(code, 0)
        self.assertEqual(out, "hi\n")

    def test_tabs_are_expanded_and_reported(self):
        code, out, err = run_cli("--text", "if x:\n\treturn", "--dry-run")
        self.assertEqual(out, "if x:\n    return\n")
        self.assertIn("expanded 1 tab", err)

    def test_exotic_characters_produce_a_warning(self):
        _, _, err = run_cli("--text", "café", "--dry-run")
        self.assertIn("may not type on your keyboard layout", err)
        self.assertIn("U+00E9", err)

    def test_quiet_suppresses_progress_but_not_output(self):
        code, out, err = run_cli("--text", "x", "--dry-run", "--quiet")
        self.assertEqual(out, "x\n")
        self.assertEqual(err, "")


class PreviewTests(unittest.TestCase):
    def test_preview_reports_size_and_duration_without_output(self):
        code, out, err = run_cli("--text", "hello", "--preview")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("5 keystrokes", err)
        self.assertIn("1 line(s)", err)

    def test_preview_scales_with_speed(self):
        _, _, slow = run_cli("--text", "hello world", "--preview", "--speed", "1")
        _, _, fast = run_cli("--text", "hello world", "--preview", "--speed", "10")
        self.assertNotEqual(slow, fast)

    def test_a_long_duration_is_formatted_in_minutes(self):
        _, _, err = run_cli("--text", "x" * 4000, "--preview", "--wpm", "60")
        self.assertRegex(err, r"\d+m \d+\.\d+s")


class RunnerIntegrationTests(unittest.TestCase):
    def test_the_dry_run_backend_completes_a_real_run(self):
        code, _, err = run_cli(
            "--text", "a\nb", "--backend", "dry-run", "--delay", "0", "--speed", "1000"
        )
        self.assertEqual(code, 0)
        self.assertIn("3 keystrokes sent", err)

    def test_empty_input_types_nothing(self):
        code, _, err = run_cli("--text", "", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to type", err)


class SourceTests(unittest.TestCase):
    def test_an_explicitly_empty_text_never_falls_back_to_the_clipboard(self):
        # Regression: --text "" is falsy, and an earlier truthiness check sent
        # it to the clipboard instead of treating it as an empty payload.
        with mock.patch("humantype.cli.read_clipboard", side_effect=AssertionError("clipboard read")):
            code, out, err = run_cli("--text", "", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to type", err)

    def test_text_is_read_from_stdin(self):
        with mock.patch.object(sys, "stdin", io.StringIO("from stdin\n")):
            code, out, _ = run_cli("--stdin", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out, "from stdin\n")

    def test_text_is_read_from_a_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
            handle.write("x = 1\n")
            path = handle.name
        code, out, _ = run_cli("--file", path, "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out, "x = 1\n")

    def test_the_clipboard_is_the_default_source(self):
        with mock.patch("humantype.cli.read_clipboard", return_value="pasted"):
            code, out, _ = run_cli("--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out, "pasted\n")

    def test_an_unreadable_clipboard_explains_the_alternatives(self):
        from humantype.clipboard import ClipboardError

        with mock.patch("humantype.cli.read_clipboard", side_effect=ClipboardError("no clipboard")):
            with self.assertRaises(SystemExit) as ctx:
                run_cli("--dry-run")
        self.assertIn("no clipboard", str(ctx.exception))


class ArgumentTests(unittest.TestCase):
    def test_two_sources_are_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--text", "a", "--stdin", "--dry-run")
        self.assertIn("pick one source", str(ctx.exception))

    def test_a_missing_file_is_reported_clearly(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--file", "/no/such/file.py", "--dry-run")
        self.assertIn("cannot read", str(ctx.exception))

    def test_non_positive_wpm_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--text", "a", "--wpm", "0", "--dry-run")
        self.assertIn("--wpm must be positive", str(ctx.exception))

    def test_non_positive_speed_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--text", "a", "--speed", "0", "--dry-run")
        self.assertIn("--speed must be positive", str(ctx.exception))

    def test_an_out_of_range_typo_rate_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--text", "a", "--typos", "2", "--dry-run")
        self.assertIn("--typos must be between 0 and 1", str(ctx.exception))

    def test_negative_jitter_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--text", "a", "--jitter", "-1", "--dry-run")
        self.assertIn("--jitter cannot be negative", str(ctx.exception))


class ProfileOverrideTests(unittest.TestCase):
    def test_overrides_are_applied_on_top_of_the_named_profile(self):
        args = build_parser().parse_args(
            ["--profile", "demo", "--wpm", "300", "--typos", "0.5"]
        )
        profile = resolve_profile(args)
        self.assertEqual(profile.wpm, 300)
        self.assertEqual(profile.typo_rate, 0.5)
        # Untouched fields still come from "demo".
        self.assertEqual(profile.newline_pause, 0.35)

    def test_without_overrides_the_named_profile_is_used_unchanged(self):
        args = build_parser().parse_args(["--profile", "natural"])
        self.assertEqual(resolve_profile(args).wpm, 210.0)


if __name__ == "__main__":
    unittest.main()
