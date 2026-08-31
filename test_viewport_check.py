#!/usr/bin/env python3
"""Regression contract for the tracked all-page viewport census."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKER = ROOT / "viewport_check.py"
VIEWPORT = '<!doctype html><meta name="viewport" content="width=device-width">\n'
MISSING = "<!doctype html><title>desktop only</title>\n"


def run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def write(root: str, rel: str, content: str) -> None:
    path = Path(root, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ViewportCensusTests(unittest.TestCase):
    def new_repo(self):
        tmp = tempfile.TemporaryDirectory()
        done = run(["git", "init", "-q"], tmp.name)
        self.assertEqual(done.returncode, 0, done.stderr)
        return tmp

    def invoke(self, cwd):
        return run([sys.executable, str(CHECKER)], cwd)

    def test_deep_and_every_generated_page_are_checked(self):
        with self.new_repo() as tmp:
            write(tmp, "index.html", VIEWPORT)
            write(tmp, "deep/a/b/c.html", MISSING)
            write(tmp, "p/old.html", MISSING)
            write(tmp, "p/new.html", VIEWPORT)
            run(["git", "add", "-A"], tmp)

            done = self.invoke(tmp)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn("NO VIEWPORT: deep/a/b/c.html", done.stdout)
            self.assertIn("NO VIEWPORT: p/old.html", done.stdout)
            self.assertNotIn("NO VIEWPORT: p/new.html", done.stdout)
            self.assertIn("4 tracked HTML documents checked", done.stdout)

    def test_untracked_html_is_outside_repository_truth(self):
        with self.new_repo() as tmp:
            write(tmp, "tracked.html", VIEWPORT)
            run(["git", "add", "tracked.html"], tmp)
            write(tmp, "scratch.html", MISSING)

            done = self.invoke(tmp)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("1 tracked HTML documents checked", done.stdout)
            self.assertNotIn("scratch.html", done.stdout)

    def test_plain_text_html_receipt_is_skipped(self):
        with self.new_repo() as tmp:
            write(tmp, "r/receipt.html", "RECEIPT\nnot a document\n")
            run(["git", "add", "-A"], tmp)

            done = self.invoke(tmp)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("0 tracked HTML documents checked", done.stdout)
            self.assertIn("1 non-documents skipped", done.stdout)

    def test_git_inventory_failure_is_loud_bounded_and_never_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = self.invoke(tmp)
            self.assertEqual(done.returncode, 2)
            self.assertEqual(done.stdout, "")
            self.assertIn("INVENTORY FAILED", done.stderr)
            self.assertIn("git ls-files failed", done.stderr)
            self.assertNotIn("missing viewport", done.stderr)
            self.assertLess(len(done.stderr), 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
