#!/usr/bin/env python3
"""Contract for the source parse check.

The check exists because a truncation marker in board_ingest.py took the
publisher down (2026-08-24, commit 0759ccf).  These tests pin the two properties
that make it keepable: it catches a real unparseable file, and it cannot be
turned into an admission gate by pointing it at board data.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import source_parses


TRUNCATION_MARKER = "    bits.appe…7248 tokens truncated…\n"


class CheckPythonTests(unittest.TestCase):
    def test_clean_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clean.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("def f():\n    return 1\n")
            self.assertEqual(source_parses.check_python([path]), [])

    def test_exact_production_break_is_caught(self):
        """The literal bytes that landed on main must fail."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "broken.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("def f():\n" + TRUNCATION_MARKER)
            bad = source_parses.check_python([path])
            self.assertEqual(len(bad), 1)
            self.assertIn("U+2026", bad[0][1])

    def test_ellipsis_inside_a_string_is_not_a_failure(self):
        """U+2026 appears 330 times in tracked source, legitimately.

        A character ban would have been 330 false positives.  Parsing is the
        question with no false positives, and this is the case that proves the
        difference.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "prose.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('LABEL = "loading…"\n# an em dash — is fine too\n')
            self.assertEqual(source_parses.check_python([path]), [])

    def test_unreadable_file_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "absent.py")
            bad = source_parses.check_python([path])
            self.assertEqual(len(bad), 1)
            self.assertIn("unreadable", bad[0][1])


class ScopeTests(unittest.TestCase):
    """The check reads source.  Board data is not source and never will be."""

    def test_post_and_record_paths_are_excluded(self):
        for path in (
            "p/some-post-20260824-01.py",
            "by/BRYCE.py",
            "chunks/2026-08-24.py",
            "conflicts/whatever.py",
            "excerpts/20260821/thing.py",
            "COMMANDS/ticket.py",
        ):
            self.assertTrue(
                path.startswith(source_parses.DATA_PREFIXES),
                "%s must be treated as data, not source" % path,
            )

    def test_engine_paths_are_not_excluded(self):
        for path in ("board_ingest.py", "hub_pages.py", "independent_commons_mcp/jobs.py"):
            self.assertFalse(
                path.startswith(source_parses.DATA_PREFIXES),
                "%s is source and must be checked" % path,
            )


class CliTests(unittest.TestCase):
    def test_exit_code_is_nonzero_when_a_file_is_broken(self):
        """Run the check as CI runs it, inside a throwaway git repo."""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            with open(os.path.join(tmp, "engine.py"), "w", encoding="utf-8") as handle:
                handle.write("def f():\n" + TRUNCATION_MARKER)
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
            done = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "source_parses.py"), "--python-only"],
                cwd=tmp, capture_output=True, text=True, check=False,
            )
            self.assertEqual(done.returncode, 1)
            self.assertIn("CANNOT BE PARSED", done.stdout)

    def test_exit_code_is_zero_on_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            with open(os.path.join(tmp, "engine.py"), "w", encoding="utf-8") as handle:
                handle.write("VALUE = 1\n")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
            done = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "source_parses.py"), "--python-only"],
                cwd=tmp, capture_output=True, text=True, check=False,
            )
            self.assertEqual(done.returncode, 0)
            self.assertIn("all readable", done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
