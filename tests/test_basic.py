import unittest

from football_video.clip import parse_timestamp
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


if __name__ == "__main__":
    unittest.main()