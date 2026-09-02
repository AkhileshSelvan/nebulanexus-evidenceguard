import statistics
import unittest
from dataclasses import replace

from humantype.planner import Keystroke, duration, plan, transcript
from humantype.profile import PROFILES, IndentMode, TypingProfile

CODE = "def add(a, b):\n    total = a + b\n\n    return total\n"


def keys_of(keystrokes, name):
    return [k for k in keystrokes if k.kind == "key" and k.value == name]


class FidelityTests(unittest.TestCase):
    """The plan must reproduce the input exactly. Nothing else matters if it doesn't."""

    def test_literal_mode_reproduces_the_text(self):
        ks = plan(CODE, PROFILES["natural"], seed=1)
        self.assertEqual(transcript(ks), CODE)

    def test_reset_mode_reproduces_the_text(self):
        ks = plan(CODE, PROFILES["natural"], indent_mode=IndentMode.RESET, seed=1)
        self.assertEqual(transcript(ks), CODE)

    def test_typos_are_always_corrected(self):
        noisy = replace(PROFILES["natural"], typo_rate=0.5)
        ks = plan(CODE, noisy, seed=4)
        self.assertTrue(keys_of(ks, "backspace"), "expected this seed to produce typos")
        self.assertEqual(transcript(ks), CODE)

    def test_every_profile_is_faithful(self):
        for name, profile in PROFILES.items():
            with self.subTest(profile=name):
                self.assertEqual(transcript(plan(CODE, profile, seed=2)), CODE)

    def test_unicode_survives_the_plan(self):
        text = "s = 'café'\n"
        self.assertEqual(transcript(plan(text, PROFILES["fast"], seed=1)), text)

    def test_empty_text_produces_no_keystrokes(self):
        self.assertEqual(plan("", PROFILES["fast"], seed=1), [])

    def test_single_line_needs_no_enter(self):
        ks = plan("x = 1", PROFILES["fast"], seed=1)
        self.assertEqual(keys_of(ks, "enter"), [])
        self.assertEqual(transcript(ks), "x = 1")

    def test_blank_lines_are_preserved(self):
        text = "a\n\n\nb"
        ks = plan(text, PROFILES["fast"], seed=1)
        self.assertEqual(len(keys_of(ks, "enter")), 3)
        self.assertEqual(transcript(ks), text)


class NewlineTests(unittest.TestCase):
    def test_newlines_are_enter_keys_not_characters(self):
        # A literal "\n" character does nothing in most portal fields.
        ks = plan(CODE, PROFILES["fast"], seed=1)
        self.assertNotIn("\n", [k.value for k in ks if k.kind == "char"])
        self.assertEqual(len(keys_of(ks, "enter")), CODE.count("\n"))


class IndentModeTests(unittest.TestCase):
    def test_reset_selects_to_line_start_before_indented_lines(self):
        ks = plan(CODE, PROFILES["fast"], indent_mode=IndentMode.RESET, seed=1)
        # Three newlines, but one leads a blank line, and the trailing newline
        # ends the text -- so only the two content lines get a selection.
        self.assertEqual(len(keys_of(ks, "shift+home")), 2)

    def test_reset_never_selects_on_a_blank_line(self):
        # A selection left open on a blank line would eat the line above as
        # soon as the next character arrived.
        ks = plan("a\n\nb", PROFILES["fast"], indent_mode=IndentMode.RESET, seed=1)
        kinds = [(k.kind, k.value) for k in ks]
        first_enter = kinds.index(("key", "enter"))
        self.assertNotEqual(kinds[first_enter + 1], ("key", "shift+home"))

    def test_literal_mode_never_selects(self):
        ks = plan(CODE, PROFILES["fast"], indent_mode=IndentMode.LITERAL, seed=1)
        self.assertEqual(keys_of(ks, "shift+home"), [])

    def test_strip_mode_drops_our_indentation(self):
        ks = plan(CODE, PROFILES["fast"], indent_mode=IndentMode.STRIP, seed=1)
        self.assertEqual(transcript(ks), "def add(a, b):\ntotal = a + b\n\nreturn total\n")


class DeterminismTests(unittest.TestCase):
    def test_same_seed_gives_identical_timings(self):
        a = plan(CODE, PROFILES["careful"], seed=99)
        b = plan(CODE, PROFILES["careful"], seed=99)
        self.assertEqual(a, b)

    def test_different_seeds_give_different_timings(self):
        a = plan(CODE, PROFILES["careful"], seed=1)
        b = plan(CODE, PROFILES["careful"], seed=2)
        self.assertNotEqual([k.delay for k in a], [k.delay for k in b])

    def test_keystrokes_compare_by_value(self):
        self.assertEqual(Keystroke("char", "a", 0.1), Keystroke("char", "a", 0.1))


class RhythmTests(unittest.TestCase):
    def test_no_delay_is_ever_zero_or_negative(self):
        # A zero delay would fire keys faster than any field can accept them.
        for name, profile in PROFILES.items():
            with self.subTest(profile=name):
                ks = plan(CODE * 4, profile, seed=5)
                self.assertTrue(all(k.delay > 0 for k in ks))

    def test_faster_wpm_finishes_sooner(self):
        slow = plan(CODE, replace(PROFILES["robot"], wpm=100), seed=1)
        fast = plan(CODE, replace(PROFILES["robot"], wpm=400), seed=1)
        self.assertLess(duration(fast), duration(slow))

    def test_wpm_is_honoured_within_a_few_percent(self):
        text = "the quick brown fox jumps over the lazy dog"
        profile = TypingProfile(
            wpm=200, jitter=0.0, symbol_factor=1.0, repeat_factor=1.0,
            indent_factor=1.0, newline_pause=0.0, block_pause=0.0, thinking_rate=0.0,
        )
        expected = len(text) * (60.0 / (200 * 5))
        self.assertAlmostEqual(duration(plan(text, profile, seed=1)), expected, places=6)

    def test_robot_profile_is_metronomic(self):
        ks = plan("abcdefghij", PROFILES["robot"], seed=1)
        self.assertEqual(len(set(round(k.delay, 9) for k in ks)), 1)

    def test_jitter_makes_delays_uneven(self):
        ks = plan("abcdefghij" * 5, replace(PROFILES["robot"], jitter=0.4), seed=1)
        self.assertGreater(statistics.pstdev([k.delay for k in ks]), 0)

    def test_symbols_are_slower_than_letters(self):
        profile = replace(PROFILES["robot"], symbol_factor=2.0)
        letters = duration(plan("abcdefgh", profile, seed=1))
        symbols = duration(plan("!@#$%^&*", profile, seed=1))
        self.assertGreater(symbols, letters)

    def test_indentation_is_typed_faster_than_body_text(self):
        profile = replace(PROFILES["robot"], indent_factor=0.25)
        indented = plan("        x", profile, seed=1)
        leading = [k.delay for k in indented[:8]]
        body = indented[8].delay
        self.assertLess(max(leading), body)

    def test_a_thinking_pause_is_longer_than_a_keystroke(self):
        profile = replace(PROFILES["robot"], thinking_rate=1.0, thinking_min=0.5, thinking_max=0.5)
        ks = plan("abc", profile, seed=1)
        self.assertGreater(ks[1].delay, 0.5)

    def test_start_delay_is_charged_to_the_first_keystroke(self):
        ks = plan("abc", PROFILES["robot"], seed=1, start_delay=2.0)
        self.assertGreater(ks[0].delay, 2.0)

    def test_duration_is_the_sum_of_delays(self):
        ks = plan(CODE, PROFILES["natural"], seed=1)
        self.assertAlmostEqual(duration(ks), sum(k.delay for k in ks))


class TranscriptTests(unittest.TestCase):
    """The transcript models a real text field, so it can verify the plan."""

    def test_backspace_deletes_the_previous_character(self):
        ks = [Keystroke("char", "a", 0), Keystroke("char", "b", 0), Keystroke("key", "backspace", 0)]
        self.assertEqual(transcript(ks), "a")

    def test_backspace_on_an_empty_field_is_harmless(self):
        self.assertEqual(transcript([Keystroke("key", "backspace", 0)]), "")

    def test_typing_over_a_selection_replaces_the_line_so_far(self):
        ks = [
            Keystroke("char", "a", 0),
            Keystroke("key", "enter", 0),
            Keystroke("char", " ", 0),
            Keystroke("char", " ", 0),
            Keystroke("key", "shift+home", 0),
            Keystroke("char", "b", 0),
        ]
        self.assertEqual(transcript(ks), "a\nb")

    def test_an_unused_selection_is_dropped_by_the_next_enter(self):
        ks = [Keystroke("char", "a", 0), Keystroke("key", "shift+home", 0), Keystroke("key", "enter", 0)]
        self.assertEqual(transcript(ks), "a\n")

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError):
            transcript([Keystroke("key", "escape", 0)])


class ProfileTests(unittest.TestCase):
    def test_base_delay_follows_the_five_character_word(self):
        self.assertAlmostEqual(TypingProfile(wpm=60).base_delay(), 0.2)

    def test_zero_wpm_is_rejected(self):
        with self.assertRaises(ValueError):
            TypingProfile(wpm=0).base_delay()


if __name__ == "__main__":
    unittest.main()
