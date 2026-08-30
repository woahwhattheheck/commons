#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import sys
import unittest

from host import ai_engineering_toolkit as toolkit


ROOT = Path(__file__).resolve().parent


class AiEngineeringToolkitTests(unittest.TestCase):
    def test_catalog_composes_all_four_invention_families(self):
        catalog = toolkit.load_catalog()
        self.assertEqual(
            [row["id"] for row in catalog["components"]],
            ["muhlnickel", "titan", "whitebox", "subzero"],
        )
        self.assertFalse(catalog["cost_contract"]["training_required"])
        self.assertEqual(catalog["cost_contract"]["cash_required_for_planning_usd"], 0)

    def test_every_source_is_present_and_digest_bound(self):
        rows = toolkit.resolve_sources(toolkit.load_catalog())
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertTrue((ROOT / row["path"]).is_file())
            self.assertEqual(len(row["sha256"]), 64)
            self.assertGreater(row["bytes"], 0)
            self.assertEqual(len(row["git_blob"]), 40)

    def test_plan_uses_every_component_without_unmeasured_superiority(self):
        plan = toolkit.build_plan(
            "Engineer an inspectable persistent agent that beats a named baseline on a measured task",
            toolkit.load_catalog(),
        )
        self.assertEqual(
            plan["selected_components"],
            ["muhlnickel", "titan", "whitebox", "subzero"],
        )
        self.assertEqual(plan["superiority_state"], "BENCHMARK_REQUIRED")
        self.assertFalse(plan["benchmark_contract"]["claim_before_measurement"])
        self.assertFalse(any(plan["boundaries"].values()))

    def test_cli_emits_zero_training_zero_cash_plan(self):
        raw = subprocess.check_output(
            [sys.executable, "host/ai_engineering_toolkit.py", "offline evidence-bound agent"],
            cwd=ROOT,
            text=True,
        )
        plan = json.loads(raw)
        self.assertFalse(plan["training_required"])
        self.assertEqual(plan["cash_required_for_planning_usd"], 0)
        self.assertEqual(len(plan["source_receipts"]), 8)

    def test_empty_objective_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            toolkit.build_plan("  ", toolkit.load_catalog())


if __name__ == "__main__":
    unittest.main()
