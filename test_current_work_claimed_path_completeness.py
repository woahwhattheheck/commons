#!/usr/bin/env python3
"""A malformed claimed path cannot be dropped to manufacture closure."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import current_work as cw


def work(paths, job_id="complete-paths-20260907"):
    return {
        "id": job_id,
        "title": "Every claimed path must exist",
        "kind": "BUILDABLE",
        "claimed_paths": paths,
    }


def snapshot(prs=()):
    return {"main_sha": "a" * 40, "main_paths": {"delivered.txt": True}, "open_prs": list(prs)}


class ClaimedPathCompletenessTests(unittest.TestCase):
    def test_mixed_invalid_paths_never_close_in_either_order(self):
        for invalid in (None, False, 0, 7, [], {}, ""):
            for paths in (["delivered.txt", invalid], [invalid, "delivered.txt"]):
                for prs in ((), (123,)):
                    with self.subTest(invalid=invalid, paths=paths, prs=prs):
                        item = work(paths)
                        before = copy.deepcopy(item)
                        self.assertTrue(cw.validate_item(item))
                        result = cw.reconcile_item(item, snapshot(prs))
                        self.assertEqual(result["status"], "OPEN")
                        self.assertEqual(result["main_sha"], "")
                        self.assertEqual(item, before)

    def test_valid_complete_and_duplicate_paths_still_close(self):
        for paths in (["delivered.txt"], ["delivered.txt", "delivered.txt"]):
            for prs in ((), (123,)):
                with self.subTest(paths=paths, prs=prs):
                    result = cw.reconcile_item(work(paths), snapshot(prs))
                    self.assertEqual(result["status"], "CLOSED")
                    self.assertEqual(result["main_sha"], "a" * 40)

    def test_missing_valid_path_and_empty_or_non_list_paths_stay_open(self):
        for paths in (["delivered.txt", "missing.txt"], [], None, "delivered.txt", 7):
            with self.subTest(paths=paths):
                self.assertEqual(cw.reconcile_item(work(paths), snapshot())["status"], "OPEN")

    def test_valid_paths_still_need_exact_main_evidence(self):
        for sha in ("", "a" * 39, "a" * 40 + "\n"):
            with self.subTest(sha=sha):
                evidence = snapshot()
                evidence["main_sha"] = sha
                self.assertEqual(cw.reconcile_item(work(["delivered.txt"]), evidence)["status"], "OPEN")

    def catalog(self):
        return {
            "schema": cw.SCHEMA,
            "add_work": {"preferred": cw.SHIP_LOOP},
            "items": [
                work(["delivered.txt", None]),
                work(["delivered.txt"], "complete-valid-20260907"),
            ],
        }

    def test_project_reports_problem_and_keeps_malformed_work_open(self):
        result = cw.project(self.catalog(), snapshot())
        self.assertIn("claimed_paths must be a list of nonempty strings", result["problems"])
        self.assertEqual([row["status"] for row in result["items"]], ["OPEN", "CLOSED"])
        self.assertEqual([row["id"] for row in result["open_now"]], ["complete-paths-20260907"])

    def test_real_tree_and_cli_preserve_incomplete_work(self):
        with tempfile.TemporaryDirectory() as root:
            ground = Path(root) / "ground"
            ground.mkdir()
            (ground / "CURRENT_WORK.json").write_text(json.dumps(self.catalog()), encoding="utf-8")
            (Path(root) / "delivered.txt").write_text("real delivered file\n", encoding="utf-8")
            result = cw.measure_tree(root, "a" * 40)
            self.assertEqual([row["status"] for row in result["items"]], ["OPEN", "CLOSED"])
            completed = subprocess.run(
                [sys.executable, str(Path(cw.__file__).resolve()), "--root", root, "--main-sha", "a" * 40],
                capture_output=True, text=True, check=False, timeout=10,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(json.loads(completed.stdout), result)

    def test_device_pin_is_unchanged(self):
        item = work(["delivered.txt", None])
        item["kind"] = "DEVICE_PINNED"
        result = cw.reconcile_item(item, snapshot())
        self.assertEqual(result["status"], "PINNED")
        self.assertFalse(result["executable"])


if __name__ == "__main__":
    unittest.main()
