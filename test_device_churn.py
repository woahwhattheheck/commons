#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

import device_churn as dc


class DeviceChurnTests(unittest.TestCase):
    def test_classify_empty_is_unmeasured(self):
        got = dc.classify({})
        self.assertEqual(got["state"], "UNMEASURED")
        self.assertIn("not stillness", got["note"])

    def test_workflow_run_is_not_landed(self):
        flags = dc.workflow_flags(
            "on:\n  workflow_run:\n    workflows: [\"commons-board\"]\n",
            "name: commons-board\n",
        )
        row = dc.measure_from_rows(
            {
                "reservation_count": 0,
                "batch_count": 0,
                "result_count": 48,
                "scope_device_count": 0,
            },
            flags,
            {"catalog": True},
        )
        self.assertTrue(row["flags"]["workflow_run"])
        self.assertEqual(dc.classify(row)["state"], "NOT_LANDED")
        self.assertIn("no-op churn", dc.classify(row)["note"])

    def test_gated_call_with_canary_is_integrated(self):
        flags = dc.workflow_flags(
            "on:\n  workflow_call:\n  workflow_dispatch:\n",
            (
                "device_action_state.py preflight\n"
                "has_pending_device: ${{ steps.device_pending.outputs.has_pending }}\n"
                "uses: ./.github/workflows/commons-device-executor.yml\n"
            ),
        )
        row = dc.measure_from_rows(
            {
                "reservation_count": 0,
                "batch_count": 0,
                "result_count": 48,
                "scope_device_count": 0,
            },
            flags,
            {"catalog": True, "canary": {"ran": True, "ok": True}},
        )
        self.assertFalse(row["flags"]["workflow_run"])
        self.assertTrue(row["flags"]["board_gates_pending"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["dc_inject"])
        self.assertFalse(row["self_hosted_dispatch"])
        self.assertEqual(dc.classify(row)["state"], "INTEGRATED")

    def test_failed_canary_is_candidate(self):
        flags = dc.workflow_flags(
            "on:\n  workflow_call:\n  workflow_dispatch:\n",
            (
                "device_action_state.py preflight\n"
                "has_pending_device: x\n"
                "uses: ./.github/workflows/commons-device-executor.yml\n"
            ),
        )
        row = dc.measure_from_rows(
            {"reservation_count": 0},
            flags,
            {"catalog": True, "canary": {"ran": True, "ok": False}},
        )
        self.assertEqual(dc.classify(row)["state"], "CANDIDATE")

    def test_measure_root_reads_live_tree(self):
        root = Path(__file__).resolve().parent
        row = dc.measure_root(str(root))
        self.assertTrue(row["measured"])
        self.assertIn("flags", row)
        self.assertGreaterEqual(row["result_count"], 0)
        self.assertEqual(row["titan"], "NOT_WRITTEN")

    def test_count_helpers_missing_dir_is_null(self):
        with tempfile.TemporaryDirectory() as td:
            missing = dc.list_json_files(os.path.join(td, "missing"))
            self.assertFalse(missing["ok"])
            self.assertIsNone(missing["count"])
            self.assertIn("FINDER-FAILED", missing["error"])
            self.assertIsNone(dc.count_json_files(os.path.join(td, "missing")))
            results = Path(td) / "results"
            results.mkdir()
            (results / "ok.json").write_text(
                json.dumps({"scope": "device"}), encoding="utf-8"
            )
            (results / "other.json").write_text(
                json.dumps({"scope": "github"}), encoding="utf-8"
            )
            (results / "broken.json").write_text("{", encoding="utf-8")
            self.assertEqual(dc.count_json_files(str(results)), 3)
            scopes = dc.count_scope_device(str(results))
            self.assertTrue(scopes["ok"])
            self.assertEqual(scopes["count"], 1)
            self.assertEqual(scopes["parse_failures"], 1)

    def test_self_test_passes(self):
        self.assertTrue(dc._self_test())


if __name__ == "__main__":
    unittest.main()
