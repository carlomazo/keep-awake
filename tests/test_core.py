# -*- coding: utf-8 -*-
"""
tests/test_core.py — Unit tests for pure functions in core.py.

No external dependencies; uses only unittest from the standard library.
Run with:  python -m unittest discover tests
       or: python -m pytest tests/ -v
"""

import sys
import os
import datetime
import time
import unittest

# Make sure the project root is on the path so we can import our modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the functions under test.
from core import _parse_duration, _format_duration, _in_schedule_window, _build_tooltip

# AppState is needed to build isolated state objects for the schedule/tooltip tests.
from state import AppState


# ---------------------------------------------------------------------------
# _parse_duration
# ---------------------------------------------------------------------------

class TestParseDuration(unittest.TestCase):

    def test_hours_only(self):
        secs, err = _parse_duration("1h")
        self.assertEqual(secs, 3600)
        self.assertIsNone(err)

    def test_minutes_only(self):
        secs, err = _parse_duration("20m")
        self.assertEqual(secs, 20 * 60)
        self.assertIsNone(err)

    def test_seconds_only(self):
        secs, err = _parse_duration("45s")
        self.assertEqual(secs, 45)
        self.assertIsNone(err)

    def test_hours_and_minutes(self):
        secs, err = _parse_duration("1h30m")
        self.assertEqual(secs, 3600 + 30 * 60)
        self.assertIsNone(err)

    def test_full_hms(self):
        secs, err = _parse_duration("2h30m15s")
        self.assertEqual(secs, 2 * 3600 + 30 * 60 + 15)
        self.assertIsNone(err)

    def test_plain_integer_string(self):
        secs, err = _parse_duration("90")
        self.assertEqual(secs, 90)
        self.assertIsNone(err)

    def test_empty_string(self):
        secs, err = _parse_duration("")
        self.assertIsNone(secs)
        self.assertIsNone(err)

    def test_whitespace_only(self):
        secs, err = _parse_duration("   ")
        self.assertIsNone(secs)
        self.assertIsNone(err)

    def test_invalid_string(self):
        secs, err = _parse_duration("abc")
        self.assertIsNone(secs)
        self.assertIsNotNone(err)

    def test_zero_values_produce_zero(self):
        # "0h0m0s" matches the hms pattern; all groups present → 0
        secs, err = _parse_duration("0h0m0s")
        # The pattern groups exist (all "0"), so result is 0 seconds.
        self.assertEqual(secs, 0)
        self.assertIsNone(err)


# ---------------------------------------------------------------------------
# _format_duration
# ---------------------------------------------------------------------------

class TestFormatDuration(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(_format_duration(0), "0s")

    def test_seconds_only(self):
        self.assertEqual(_format_duration(45), "45s")

    def test_minutes_only(self):
        self.assertEqual(_format_duration(60), "1m")

    def test_hours_only(self):
        self.assertEqual(_format_duration(3600), "1h")

    def test_hours_and_minutes(self):
        self.assertEqual(_format_duration(3600 + 30 * 60), "1h30m")

    def test_full_hms(self):
        self.assertEqual(_format_duration(2 * 3600 + 5 * 60 + 10), "2h5m10s")

    def test_minutes_and_seconds(self):
        self.assertEqual(_format_duration(90), "1m30s")

    def test_large_value(self):
        # 10 hours exactly
        self.assertEqual(_format_duration(36000), "10h")


# ---------------------------------------------------------------------------
# _in_schedule_window
# ---------------------------------------------------------------------------

class TestInScheduleWindow(unittest.TestCase):
    """Tests use a patched datetime via monkeypatching _now() inside the
    function.  Because _in_schedule_window calls datetime.datetime.now()
    directly, we monkey-patch it at the datetime module level."""

    def _make_state(self, start_hm, end_hm, days=None):
        """Helper: build an AppState with a single schedule block."""
        st = AppState()
        st.schedule_blocks = [{"start": list(start_hm), "end": list(end_hm)}]
        st.schedule_days   = set(days) if days is not None else {0, 1, 2, 3, 4}
        return st

    def _patch_now(self, weekday, hour, minute):
        """Return a datetime whose weekday, hour, minute match the args."""
        # Build a real date that has the requested weekday.
        base = datetime.datetime(2024, 1, 1)  # Monday (weekday 0)
        delta = (weekday - base.weekday()) % 7
        d = base + datetime.timedelta(days=delta)
        return datetime.datetime(d.year, d.month, d.day, hour, minute, 0)

    def setUp(self):
        import core
        self._core = core
        self._orig_now = datetime.datetime.now

    def tearDown(self):
        # Restore datetime.datetime.now after each test.
        import core
        # Nothing to restore because we patched at instance level.

    def _call_with_time(self, st, weekday, hour, minute):
        """Call _in_schedule_window(st) after patching datetime.datetime.now."""
        import core
        fake_now = self._patch_now(weekday, hour, minute)
        original = datetime.datetime.now

        class _PatchedDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fake_now

        import datetime as _dt
        orig_cls = _dt.datetime
        _dt.datetime = _PatchedDatetime
        try:
            result = _in_schedule_window(st)
        finally:
            _dt.datetime = orig_cls
        return result

    def test_inside_block(self):
        st = self._make_state((8, 0), (18, 0), days={0, 1, 2, 3, 4})
        # Wednesday (2), 12:00 — inside block
        self.assertTrue(self._call_with_time(st, 2, 12, 0))

    def test_outside_block_time(self):
        st = self._make_state((8, 0), (18, 0), days={0, 1, 2, 3, 4})
        # Monday (0), 07:59 — just before block starts
        self.assertFalse(self._call_with_time(st, 0, 7, 59))

    def test_at_start_boundary(self):
        st = self._make_state((8, 0), (18, 0), days={0, 1, 2, 3, 4})
        # Exactly at 08:00 — inside (start-inclusive)
        self.assertTrue(self._call_with_time(st, 0, 8, 0))

    def test_at_end_boundary(self):
        st = self._make_state((8, 0), (18, 0), days={0, 1, 2, 3, 4})
        # Exactly at 18:00 — outside (end-exclusive)
        self.assertFalse(self._call_with_time(st, 0, 18, 0))

    def test_wrong_day(self):
        # Block only valid Mon–Fri; Saturday is weekday 5
        st = self._make_state((8, 0), (18, 0), days={0, 1, 2, 3, 4})
        self.assertFalse(self._call_with_time(st, 5, 12, 0))

    def test_multiple_blocks_first_matches(self):
        st = AppState()
        st.schedule_blocks = [
            {"start": [8, 0],  "end": [10, 0]},
            {"start": [14, 0], "end": [16, 0]},
        ]
        st.schedule_days = {0, 1, 2, 3, 4}
        # 09:00 — in first block
        self.assertTrue(self._call_with_time(st, 0, 9, 0))

    def test_multiple_blocks_second_matches(self):
        st = AppState()
        st.schedule_blocks = [
            {"start": [8, 0],  "end": [10, 0]},
            {"start": [14, 0], "end": [16, 0]},
        ]
        st.schedule_days = {0, 1, 2, 3, 4}
        # 15:00 — in second block
        self.assertTrue(self._call_with_time(st, 0, 15, 0))

    def test_multiple_blocks_between_blocks(self):
        st = AppState()
        st.schedule_blocks = [
            {"start": [8, 0],  "end": [10, 0]},
            {"start": [14, 0], "end": [16, 0]},
        ]
        st.schedule_days = {0, 1, 2, 3, 4}
        # 12:00 — between blocks
        self.assertFalse(self._call_with_time(st, 0, 12, 0))


# ---------------------------------------------------------------------------
# _build_tooltip
# ---------------------------------------------------------------------------

class TestBuildTooltip(unittest.TestCase):

    def _base_state(self):
        st = AppState()
        st.running        = False
        st.schedule_enabled = False
        st.meeting_active  = False
        st.battery_paused  = False
        return st

    def test_paused_no_schedule(self):
        st = self._base_state()
        tip = _build_tooltip(st)
        self.assertIn("paused", tip)
        self.assertNotIn("schedule enabled", tip)

    def test_paused_with_schedule(self):
        st = self._base_state()
        st.schedule_enabled = True
        tip = _build_tooltip(st)
        self.assertIn("paused", tip)
        self.assertIn("schedule enabled", tip)

    def test_in_meeting(self):
        st = self._base_state()
        st.meeting_active = True
        tip = _build_tooltip(st)
        self.assertIn("in meeting", tip)

    def test_battery_paused(self):
        st = self._base_state()
        st.battery_paused = True
        tip = _build_tooltip(st)
        self.assertIn("low battery", tip)

    def test_active_basic(self):
        st = self._base_state()
        st.running      = True
        st.active_since = time.monotonic() - 125  # 2 minutes 5 seconds ago
        tip = _build_tooltip(st)
        self.assertIn("ACTIVE", tip)

    def test_active_with_auto_stop(self):
        st = self._base_state()
        st.running        = True
        st.active_since   = time.monotonic() - 60  # 1 minute elapsed
        st.auto_stop_after = 3600                   # 1 hour limit
        tip = _build_tooltip(st)
        self.assertIn("stops in", tip)

    def test_active_with_schedule(self):
        st = self._base_state()
        st.running          = True
        st.active_since     = time.monotonic()
        st.schedule_enabled = True
        tip = _build_tooltip(st)
        self.assertIn("schedule enabled", tip)


if __name__ == "__main__":
    unittest.main()
