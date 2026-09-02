import unittest

from humantype.text import (
    describe_character,
    expand_tabs,
    normalise,
    unsupported_characters,
)


class NormaliseTests(unittest.TestCase):
    def test_crlf_becomes_lf_and_is_reported(self):
        clean, report = normalise("a\r\nb\rc")
        self.assertEqual(clean, "a\nb\nc")
        self.assertTrue(report.crlf_normalised)

    def test_tabs_expand_to_the_next_tab_stop(self):
        # Not a blind 4-space swap: "ab\tc" must land on column 4.
        clean, report = normalise("ab\tc", tab_width=4)
        self.assertEqual(clean, "ab  c")
        self.assertEqual(report.tabs_expanded, 1)

    def test_tab_stops_reset_on_each_line(self):
        clean, _ = normalise("abc\n\tx", tab_width=4)
        self.assertEqual(clean, "abc\n    x")

    def test_non_breaking_space_becomes_a_real_space(self):
        clean, report = normalise("a b")
        self.assertEqual(clean, "a b")
        self.assertEqual(report.lookalike_spaces, 1)

    def test_smart_quotes_are_rewritten_to_ascii(self):
        clean, report = normalise("print(“hi”)")
        self.assertEqual(clean, 'print("hi")')
        self.assertEqual(report.smart_punctuation, 2)

    def test_smart_quotes_can_be_kept(self):
        clean, report = normalise("“hi”", fix_punctuation=False)
        self.assertEqual(clean, "“hi”")
        self.assertEqual(report.smart_punctuation, 0)

    def test_zero_width_characters_are_removed(self):
        clean, report = normalise("a​b﻿")
        self.assertEqual(clean, "ab")
        self.assertEqual(report.invisible_removed, 2)

    def test_trailing_whitespace_is_stripped_per_line(self):
        clean, report = normalise("a   \nb\nc  ")
        self.assertEqual(clean, "a\nb\nc")
        self.assertEqual(report.trailing_stripped, 2)

    def test_trailing_whitespace_can_be_kept(self):
        clean, report = normalise("a   ", strip_trailing=False)
        self.assertEqual(clean, "a   ")
        self.assertEqual(report.trailing_stripped, 0)

    def test_leading_indentation_is_never_stripped(self):
        clean, _ = normalise("def f():\n    return 1\n")
        self.assertEqual(clean, "def f():\n    return 1\n")

    def test_clean_text_reports_nothing_touched(self):
        clean, report = normalise("x = 1\n")
        self.assertEqual(clean, "x = 1\n")
        self.assertFalse(report.touched)
        self.assertEqual(report.summary(), [])

    def test_summary_lists_every_change(self):
        _, report = normalise("a\t “x”  \r\n")
        self.assertTrue(report.touched)
        self.assertEqual(len(report.summary()), 5)


class ExpandTabsTests(unittest.TestCase):
    def test_matches_editor_rendering(self):
        self.assertEqual(expand_tabs("\tx", 4), "    x")
        self.assertEqual(expand_tabs("a\tx", 4), "a   x")
        self.assertEqual(expand_tabs("abcd\tx", 4), "abcd    x")


class UnsupportedCharacterTests(unittest.TestCase):
    def test_plain_ascii_is_all_supported(self):
        self.assertEqual(unsupported_characters("def f(): return 'a' + 1\n"), [])

    def test_reports_each_exotic_character_once(self):
        self.assertEqual(unsupported_characters("café é"), ["é"])

    def test_describes_a_character_for_the_warning(self):
        self.assertIn("U+00E9", describe_character("é"))


if __name__ == "__main__":
    unittest.main()
