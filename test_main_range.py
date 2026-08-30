#!/usr/bin/env python3
"""Proofs for bounded local velocity and coalesced main verification."""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


velocity = load("main_velocity", "host/main_velocity.py")
main_range = load("main_range", "host/main_range.py")


class MainVelocityTests(unittest.TestCase):
    def test_four_local_queries_measure_all_windows(self):
        with mock.patch.object(velocity, "_git", side_effect=["abc", "36", "2400", "7000"]) as run:
            result = velocity.measure("origin/main")
        self.assertEqual(run.call_count, 4)
        self.assertEqual(result["windows"]["24h"]["commits"], 2400)
        self.assertTrue(result["high_velocity"])
        self.assertEqual(result["integration_mode"], "coalesce_ranges")
        self.assertNotIn("approval_required", result)


class MainRangeTests(unittest.TestCase):
    def test_many_commits_plan_each_verifier_once(self):
        paths = ["host/a.py", "ground/rule.md"] * 1000
        names = [name for name, _ in main_range.plan(paths)]
        self.assertEqual(names, ["imports", "open-door", "muhlnickel", "path-manifest"])

    def test_projection_only_range_skips_manifest_suite(self):
        names = [name for name, _ in main_range.plan(["p/1.md", "fresh.md"])]
        self.assertEqual(names, ["imports", "open-door", "muhlnickel"])

    def test_receipt_freezes_range_and_reports_verification_touches(self):
        with mock.patch.object(main_range, "resolve_range", return_value=("base", "head", 2375)), \
             mock.patch.object(main_range, "changed_paths", return_value=["host/a.py"]), \
             mock.patch.object(main_range.main_velocity, "measure", return_value={"high_velocity": True}):
            receipt = main_range.build_receipt("HEAD", None, 30, False)
        self.assertEqual(receipt["commit_count"], 2375)
        self.assertEqual(receipt["main_movement_policy"], "freeze_then_next_range")
        self.assertNotIn("approval_required", receipt)
        self.assertEqual(receipt["verification_paths"], [])
        self.assertEqual(receipt["observations"]["verification_path_touches"], 0)

    def test_verification_path_receipt_uses_open_door_vocabulary(self):
        paths = ["host/a.py", "p/one.md", "test_main_range.py"]
        self.assertEqual(
            main_range.verification_paths(paths),
            ["p/one.md", "test_main_range.py"],
        )
        source = (ROOT / "host/main_range.py").read_text(encoding="utf-8")
        self.assertNotIn("PROTECTED_", source)
        self.assertNotIn("protected_paths", source)

    def test_each_result_carries_frozen_range_provenance(self):
        def run(command, **_kwargs):
            return subprocess.CompletedProcess(
                command,
                1 if "open_door_guard.py" in command else 0,
                stdout="finding\n",
            )

        paths = ["docs/changed.md"]
        with mock.patch.object(main_range.subprocess, "run", side_effect=run):
            results, ok = main_range.run_batch("base123", "head456", paths)

        self.assertFalse(ok)
        self.assertEqual(len(results), 4)
        for result in results:
            provenance = result["provenance"]
            self.assertEqual(provenance["base"], "base123")
            self.assertEqual(provenance["head"], "head456")
            self.assertEqual(provenance["range"], "base123..head456")
        open_door = next(row for row in results if row["name"] == "open-door")
        self.assertEqual(open_door["provenance"]["scope"], "FROZEN_RANGE")
        self.assertEqual(open_door["provenance"]["attribution"], "DIRECT_RANGE")

    def test_unrelated_snapshot_failure_stays_unattributed(self):
        provenance = main_range.finding_provenance(
            "imports",
            1,
            "base",
            "head",
            ["docs/unrelated.md"],
        )
        self.assertEqual(provenance["scope"], "FROZEN_HEAD")
        self.assertEqual(provenance["candidate_paths"], [])
        self.assertEqual(
            provenance["attribution"],
            "NO_DIRECT_RANGE_PROVENANCE",
        )

    def test_snapshot_failure_with_named_input_is_direct(self):
        provenance = main_range.finding_provenance(
            "imports",
            1,
            "base",
            "head",
            ["hub_pages.py", "docs/unrelated.md"],
        )
        self.assertEqual(provenance["candidate_paths"], ["hub_pages.py"])
        self.assertEqual(provenance["attribution"], "DIRECT_RANGE")

    def test_observer_push_contracts_distinguish_reporting_from_coalescing(self):
        names = ("import-check.yml", "muhlnickel-spec-guard.yml", "path-manifest.yml", "record-guard.yml")
        for name in names:
            text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            self.assertNotIn("\n  push:\n", text, name)
        open_door = (ROOT / ".github/workflows/open-door-guard.yml").read_text(encoding="utf-8")
        self.assertIn("\n  push:\n    branches: [main]\n", open_door)
        workflow = (ROOT / ".github/workflows/main-range-verify.yml").read_text(encoding="utf-8")
        self.assertIn("\n  schedule:\n", workflow)
        self.assertIn("group: commons-main-range-verify", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()
