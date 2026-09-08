#!/usr/bin/env python3
"""Focused contract for viewport_backfill.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "viewport_backfill.py"
TAG = '<meta name="viewport" content="width=device-width, initial-scale=1">'
MISSING = '<!doctype html><html><head><meta charset="utf-8"><title>x</title></head><body>x</body></html>'
WITH = '<!doctype html><html><head>' + TAG + '<title>x</title></head><body>x</body></html>'


def run(args, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_repo(root: Path, pages: dict[str, str]) -> None:
    done = run(["git", "init", "-q"], root)
    if done.returncode:
        raise RuntimeError(done.stderr)
    for rel, text in pages.items():
        write(root, rel, text)
    run(["git", "add", "-A"], root)
    done = run(
        ["git", "-c", "user.name=viewport-test", "-c", "user.email=viewport@test.invalid",
         "commit", "-q", "-m", "fixture"],
        root,
    )
    if done.returncode:
        raise RuntimeError(done.stderr)


def invoke(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(TOOL), *args], root)


class ViewportBackfillTests(unittest.TestCase):
    def test_dry_run_is_bounded_deterministic_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(
                root,
                {
                    "p/a.html": MISSING,
                    "p/b.html": MISSING,
                    "p/c.html": MISSING,
                    "p/already.html": WITH,
                    "r/receipt.html": "RECEIPT\nnot an html document\n",
                },
            )
            first = invoke(root, "--limit", "2")
            self.assertEqual(first.returncode, 0, first.stderr)
            plan = json.loads(first.stdout)
            self.assertEqual([r["path"] for r in plan["changes"]], ["p/a.html", "p/b.html"])
            self.assertEqual(plan["next_cursor"], "p/b.html")
            self.assertEqual(plan["selected_count"], 2)
            self.assertEqual(plan["missing_viewport_count"], 3)

            second = invoke(root, "--limit", "2", "--cursor", "p/b.html")
            self.assertEqual(second.returncode, 0, second.stderr)
            resumed = json.loads(second.stdout)
            self.assertEqual([r["path"] for r in resumed["changes"]], ["p/c.html"])
            self.assertIsNone(resumed["next_cursor"])

    def test_apply_aborts_entire_batch_on_moved_preimage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root, {"p/a.html": MISSING, "p/b.html": MISSING})
            manifest = root / "plan.json"
            dry = invoke(root, "--limit", "2", "--manifest-out", str(manifest))
            self.assertEqual(dry.returncode, 0, dry.stderr)
            before_b = (root / "p/b.html").read_bytes()
            write(root, "p/a.html", MISSING.replace("<title>x</title>", "<title>moved</title>"))

            applied = invoke(root, "--apply", "--manifest", str(manifest))
            self.assertEqual(applied.returncode, 2)
            self.assertIn("preimage", applied.stderr)
            self.assertEqual((root / "p/b.html").read_bytes(), before_b)
            self.assertNotIn(TAG.encode(), before_b)

    def test_apply_inserts_only_exact_tag_then_becomes_idempotent_after_commit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root, {"p/a.html": MISSING})
            manifest = root / "plan.json"
            before = (root / "p/a.html").read_bytes()
            dry = invoke(root, "--limit", "1", "--manifest-out", str(manifest))
            self.assertEqual(dry.returncode, 0, dry.stderr)

            applied = invoke(root, "--apply", "--manifest", str(manifest))
            self.assertEqual(applied.returncode, 0, applied.stderr)
            after = (root / "p/a.html").read_bytes()
            marker = b"<head>"
            expected = before.replace(marker, marker + TAG.encode("ascii"), 1)
            self.assertEqual(after, expected)

            run(["git", "add", "p/a.html"], root)
            committed = run(
                ["git", "-c", "user.name=viewport-test", "-c", "user.email=viewport@test.invalid",
                 "commit", "-q", "-m", "apply"],
                root,
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            repeat = invoke(root, "--limit", "10")
            self.assertEqual(repeat.returncode, 0, repeat.stderr)
            repeated = json.loads(repeat.stdout)
            self.assertEqual(repeated["selected_count"], 0)
            self.assertEqual(repeated["missing_viewport_count"], 0)

    def test_current_checkout_dry_run_is_read_only_and_bounded(self) -> None:
        # On hosted PR CI this emits the measured current-repository dry-run
        # requested by issue #2407. No exact count is asserted because main moves.
        before = run(["git", "status", "--porcelain"], ROOT)
        self.assertEqual(before.returncode, 0, before.stderr)
        dry = invoke(ROOT, "--limit", "3")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        plan = json.loads(dry.stdout)
        after = run(["git", "status", "--porcelain"], ROOT)
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(after.stdout, before.stdout)
        self.assertEqual(plan["mode"], "dry-run")
        self.assertLessEqual(plan["selected_count"], 3)
        summary = {
            "base_head_sha": plan["base_head_sha"],
            "tracked_html_count": plan["tracked_html_count"],
            "derived_tracked_count": plan["derived_tracked_count"],
            "missing_viewport_count": plan["missing_viewport_count"],
            "selectable_count": plan["selectable_count"],
            "unsupported_missing_head_count": plan["unsupported_missing_head_count"],
            "selected": [row["path"] for row in plan["changes"]],
            "next_cursor": plan["next_cursor"],
        }
        print("CURRENT_CHECKOUT_DRY_RUN=" + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
