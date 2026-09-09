#!/usr/bin/env python3
"""Focused tests for the incremental Resource Master delta compiler."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from host import resource_master_delta as delta

ROOT = Path(__file__).resolve().parent
OBSERVATIONS = ROOT / "inventory" / "resources" / "resource_master_delta_observations.json"
REPORT = ROOT / "inventory" / "resources" / "resource_master_delta_report.json"


class ResourceMasterDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        cls.report = delta.compile_report(cls.source)

    def test_checked_in_report_matches_deterministic_compile(self) -> None:
        self.assertEqual(delta.canonical_json(self.report), REPORT.read_text(encoding="utf-8"))

    def test_watermark_advances_exactly(self) -> None:
        self.assertNotEqual(self.report["previous_watermark"]["main_sha"], self.report["next_watermark"]["main_sha"])
        self.assertEqual(self.report["next_watermark"]["main_sha"], "c695243f0e3b25b7d48b9551f684434d35a5b5ad")

    def test_projection_churn_is_not_material_capacity(self) -> None:
        self.assertEqual(self.report["summary"]["material_changed_paths"], 0)
        self.assertEqual(self.report["summary"]["projection_only_paths"], 8)

    def test_new_pull_requests_are_exact_and_sorted(self) -> None:
        rows = self.report["github"]["new_pull_requests"]
        self.assertEqual([row["number"] for row in rows], [7299, 7312, 7313, 7314])
        self.assertTrue(all(len(row["head_sha"]) == 40 for row in rows))

    def test_new_slack_events_are_source_unique(self) -> None:
        events = self.report["slack"]["events"]
        source_ids = [row["source_id"] for row in events]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        self.assertEqual(len(events), 5)

    def test_hartwick_order_is_routed_once_under_existing_id(self) -> None:
        orders = self.report["slack"]["routed_build_orders"]
        self.assertEqual([row["id"] for row in orders], ["hartwick-grain-flour-bake-lims-01"])
        self.assertEqual(orders[0]["state"], "ROUTED")

    def test_no_new_gmail_receipt_after_watermark(self) -> None:
        self.assertEqual(self.report["summary"]["new_business_gmail_receipts"], 0)
        self.assertFalse(self.report["connected_state"]["gmail_delta"]["private_content_persisted"])

    def test_unchanged_plugins_and_automations_remain_zero_delta(self) -> None:
        self.assertEqual(self.report["summary"]["automation_state_changes"], 0)
        self.assertEqual(self.report["summary"]["plugin_route_changes"], 0)

    def test_report_is_advisory_and_open_door(self) -> None:
        policy = self.report["policy"]
        self.assertTrue(policy["metadata_only"])
        self.assertFalse(policy["admission_gate"])
        self.assertFalse(policy["authentication_gate"])
        self.assertFalse(policy["spend_authority"])

    def test_input_is_not_mutated_and_compile_is_deterministic(self) -> None:
        original = copy.deepcopy(self.source)
        self.assertEqual(delta.compile_report(self.source), delta.compile_report(copy.deepcopy(self.source)))
        self.assertEqual(self.source, original)

    def test_rejects_nonadvancing_timestamp(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["current_watermark"]["observed_at"] = bad["previous_watermark"]["observed_at"]
        with self.assertRaises(delta.ResourceDeltaError):
            delta.compile_report(bad)

    def test_rejects_duplicate_slack_source(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["new_slack_events"].append(copy.deepcopy(bad["new_slack_events"][0]))
        with self.assertRaises(delta.ResourceDeltaError):
            delta.compile_report(bad)

    def test_rejects_rerouted_existing_order(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["previously_routed_order_ids"] = ["hartwick-grain-flour-bake-lims-01"]
        with self.assertRaises(delta.ResourceDeltaError):
            delta.compile_report(bad)

    def test_rejects_private_mail_content(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["gmail_delta"]["private_content_persisted"] = True
        with self.assertRaises(delta.ResourceDeltaError):
            delta.compile_report(bad)

    def test_rejects_secret_shapes(self) -> None:
        bad = copy.deepcopy(self.source)
        bad["evidence"]["bad"] = "api_key=definitely-secret-value"
        with self.assertRaises(delta.ResourceDeltaError):
            delta.compile_report(bad)

    def test_cli_verify_self_test_and_output(self) -> None:
        self.assertEqual(delta.main(["--verify"]), 0)
        self.assertEqual(delta.main(["--self-test"]), 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            self.assertEqual(delta.main(["--output", str(path)]), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
