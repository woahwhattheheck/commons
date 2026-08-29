#!/usr/bin/env python3
"""Proofs for bounded local velocity and coalesced main verification."""
from __future__ import annotations

import importlib.util
import pathlib
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
        self.assertFalse(result["approval_required"])


class MainRangeTests(unittest.TestCase):
    def test_many_commits_plan_each_verifier_once(self):
        paths = ["host/a.py", "ground/rule.md"] * 1000
        names = [name for name, _ in main_range.plan(paths)]
        self.assertEqual(names, ["imports", "open-door", "muhlnickel", "path-manifest"])

    def test_projection_only_range_skips_manifest_suite(self):
        names = [name for name, _ in main_range.plan(["p/1.md", "fresh.md"])]
        self.assertEqual(names, ["imports", "open-door", "muhlnickel"])

    def test_receipt_freezes_range_and_has_no_approval_gate(self):
        with mock.patch.object(main_range, "resolve_range", return_value=("base", "head", 2375)), \
             mock.patch.object(main_range, "changed_paths", return_value=["host/a.py"]), \
             mock.patch.object(main_range.main_velocity, "measure", return_value={"high_velocity": True}):
            receipt = main_range.build_receipt("HEAD", None, 30, False)
        self.assertEqual(receipt["commit_count"], 2375)
        self.assertEqual(receipt["main_movement_policy"], "freeze_then_next_range")
        self.assertFalse(receipt["approval_required"])
        self.assertEqual(receipt["observations"]["protected_path_touches"], 0)

    def test_five_observers_do_not_amplify_every_main_push(self):
        names = ("import-check.yml", "muhlnickel-spec-guard.yml", "open-door-guard.yml", "path-manifest.yml", "record-guard.yml")
        for name in names:
            text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            self.assertNotIn("\n  push:\n", text, name)
        workflow = (ROOT / ".github/workflows/main-range-verify.yml").read_text(encoding="utf-8")
        self.assertIn("\n  schedule:\n", workflow)
        self.assertIn("group: commons-main-range-verify", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()
