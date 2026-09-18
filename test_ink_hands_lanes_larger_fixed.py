"""Hermetic: hands-lane doors carry Larger fixed engagements note."""

from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent

LANDED_FILES = (
    "wakeup.html",
    "commons-apk.html",
    "lab.html",
)


class TestInkHandsLanesLargerFixed(unittest.TestCase):
    def test_larger_fixed_on_each_landed_file(self) -> None:
        for name in LANDED_FILES:
            with self.subTest(file=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("diagnostic.html", text)
                self.assertIn("commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)


if __name__ == "__main__":
    unittest.main()
