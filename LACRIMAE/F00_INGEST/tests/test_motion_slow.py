import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "CODEBASE"))
from f00_motion_slow import in_requested_range, parse_ranges


class MotionSlowContractTests(unittest.TestCase):
    def test_parse_partial_ranges(self):
        self.assertEqual(parse_ranges("3-7,8-9", 60.0, 10.0), [(3.0, 7.0), (8.0, 9.0)])

    def test_reject_overlapping_ranges(self):
        with self.assertRaises(ValueError):
            parse_ranges("3-7,6-8", 60.0, 10.0)

    def test_sequence_intersects_requested_range(self):
        row = {"timeline_start_frame": 180, "duration_frames": 7}
        self.assertTrue(in_requested_range(row, [(3.0, 7.0)], 60.0))

    def test_sequence_outside_requested_range(self):
        row = {"timeline_start_frame": 480, "duration_frames": 7}
        self.assertFalse(in_requested_range(row, [(3.0, 7.0)], 60.0))


if __name__ == "__main__":
    unittest.main()
