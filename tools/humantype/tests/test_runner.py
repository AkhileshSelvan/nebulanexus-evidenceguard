import unittest

from humantype.drivers import DriverError, DryRunDriver, make_driver
from humantype.planner import Keystroke, plan, transcript
from humantype.profile import PROFILES
from humantype.runner import countdown, run


class FakeClock:
    """Records sleeps instead of performing them, so tests run instantly."""

    def __init__(self):
        self.slept = []

    def __call__(self, seconds):
        self.slept.append(seconds)

    @property
    def total(self):
        return sum(self.slept)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.driver = DryRunDriver()
        self.clock = FakeClock()

    def test_every_keystroke_reaches_the_driver_in_order(self):
        ks = plan("ab\ncd", PROFILES["fast"], seed=1)
        sent = run(ks, self.driver, sleep=self.clock)
        self.assertEqual(sent, len(ks))
        self.assertEqual(
            self.driver.events,
            [("char", "a"), ("char", "b"), ("key", "enter"), ("char", "c"), ("char", "d")],
        )

    def test_the_driver_receives_exactly_the_planned_text(self):
        text = "def f():\n    return 1\n"
        ks = plan(text, PROFILES["natural"], seed=3)
        run(ks, self.driver, sleep=self.clock)
        replayed = [Keystroke(kind, value, 0.0) for kind, value in self.driver.events]
        self.assertEqual(transcript(replayed), text)

    def test_total_sleep_matches_the_planned_duration(self):
        ks = plan("hello world", PROFILES["natural"], seed=1)
        run(ks, self.driver, sleep=self.clock)
        self.assertAlmostEqual(self.clock.total, sum(k.delay for k in ks))

    def test_speed_divides_every_delay(self):
        ks = plan("hello world", PROFILES["natural"], seed=1)
        run(ks, self.driver, speed=4.0, sleep=self.clock)
        self.assertAlmostEqual(self.clock.total, sum(k.delay for k in ks) / 4.0)

    def test_progress_callback_sees_a_running_count(self):
        seen = []
        run(plan("abc", PROFILES["fast"], seed=1), self.driver,
            sleep=self.clock, on_progress=lambda n, k: seen.append(n))
        self.assertEqual(seen, [1, 2, 3])

    def test_non_positive_speed_is_rejected(self):
        with self.assertRaises(ValueError):
            run([], self.driver, speed=0)

    def test_an_empty_plan_sends_nothing(self):
        self.assertEqual(run([], self.driver, sleep=self.clock), 0)
        self.assertEqual(self.driver.events, [])


class CountdownTests(unittest.TestCase):
    def test_counts_down_in_whole_seconds(self):
        clock = FakeClock()
        messages = []
        countdown(3, messages.append, sleep=clock)
        self.assertEqual(len(messages), 3)
        self.assertIn("3", messages[0])
        self.assertIn("1", messages[-1])
        self.assertAlmostEqual(clock.total, 3.0)

    def test_a_fractional_countdown_still_sleeps_the_full_time(self):
        clock = FakeClock()
        countdown(2.5, lambda _m: None, sleep=clock)
        self.assertAlmostEqual(clock.total, 2.5)

    def test_zero_delay_does_nothing(self):
        clock = FakeClock()
        messages = []
        countdown(0, messages.append, sleep=clock)
        self.assertEqual(messages, [])
        self.assertEqual(clock.total, 0)


class DriverTests(unittest.TestCase):
    def test_dry_run_driver_is_selectable_by_name(self):
        self.assertIsInstance(make_driver("dry-run"), DryRunDriver)

    def test_an_unknown_backend_is_rejected(self):
        with self.assertRaises(DriverError):
            make_driver("telepathy")

    def test_dry_run_driver_records_both_kinds_of_event(self):
        driver = make_driver("dry-run")
        driver.type_char("x")
        driver.press_key("enter")
        driver.close()
        self.assertEqual(driver.events, [("char", "x"), ("key", "enter")])


if __name__ == "__main__":
    unittest.main()
