import unittest

from football_video.clip import parse_timestamp
from football_video.comp import clock_label, merge_windows
from football_video.db import event_video_time
from football_video.probe import VideoError


class TimestampTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_timestamp("90"), 90)
        self.assertEqual(parse_timestamp("01:30"), 90)
        self.assertEqual(parse_timestamp("01:00:30"), 3630)

    def test_bad_input(self):
        with self.assertRaises(VideoError):
            parse_timestamp("abc")


class EventTimeTests(unittest.TestCase):
    def test_first_half(self):
        self.assertEqual(event_video_time(600, 1, 120, 3500), 720)

    def test_second_half(self):
        self.assertEqual(event_video_time(75 * 60 + 21, 2, 120, 3500), 3500 + 30 * 60 + 21)

    def test_second_half_before_45(self):
        with self.assertRaises(VideoError):
            event_video_time(30 * 60, 2, 0, 0)


class CompTests(unittest.TestCase):
    def test_overlapping_windows_merge(self):
        ws = [{"start": 10, "end": 20, "types": ["Goal"], "clock": 15},
              {"start": 18, "end": 30, "types": ["Shot"], "clock": 24},
              {"start": 50, "end": 60, "types": ["Pass"], "clock": 55}]
        out = merge_windows(ws)
        self.assertEqual(len(out), 2)
        self.assertEqual((out[0]["start"], out[0]["end"]), (10, 30))
        self.assertEqual(out[0]["types"], ["Goal", "Shot"])

    def test_clock_label(self):
        self.assertEqual(clock_label(75 * 60 + 21), "75:21")


if __name__ == "__main__":
    unittest.main()