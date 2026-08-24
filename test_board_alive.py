#!/usr/bin/env python3
"""Contract for the liveness and gate alarms.

Written because the board rebuild reported SUCCESS two minutes before the
publisher went unparseable on 2026-08-24: a workflow finishing cleanly is not
the same as a door that opens.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import board_alive


def scan(line):
    for pattern, label in board_alive.LOCK_PATTERNS:
        if re.search(pattern, line.lower()):
            return label
    return None


class LockAlarmTests(unittest.TestCase):
    def test_catches_a_gate(self):
        for line, expect in [
            ("if not authenticate(user): return 403", "authentication"),
            ("API_KEY = os.environ['K']", "api key"),
            ("RATE_LIMIT = 5", "rate limit"),
            ("PROTECTED_PATHS = ['p/']", "protected path/action"),
            ("raise PermissionDenied()", None),
        ]:
            got = scan(line)
            if expect:
                self.assertEqual(got, expect, line)

    def test_ordinary_code_is_quiet(self):
        for line in [
            "def write_post(src, dest, mid, body):",
            "    return json.dumps(rows)",
            "# posts are data and may contain any bytes",
        ]:
            self.assertIsNone(scan(line), line)

    def test_board_data_is_never_scanned(self):
        """A post about passwords is a post."""
        for path in ("p/x.md", "by/BRYCE.html", "board.md", "recent.json"):
            self.assertTrue(path.startswith(board_alive.DATA_PREFIXES), path)

    def test_only_added_lines_can_alarm(self):
        """Removing a gate must never trip anything.

        added_lines() reads `+` lines out of a unified diff and nothing else, so
        a deletion is invisible to the alarm by construction.
        """
        src = open(board_alive.__file__, encoding="utf-8").read()
        self.assertIn('line.startswith("+")', src)
        self.assertNotIn('line.startswith("-")', src)


class LivenessTests(unittest.TestCase):
    def test_finds_the_newest_post(self):
        newest, when = board_alive.newest_post()
        self.assertTrue(newest, "p/ has posts; the alarm must see them")
        self.assertGreater(when, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
