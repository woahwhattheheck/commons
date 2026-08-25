#!/usr/bin/env python3
"""Grok harness leftover measures; it does not mutate Grok."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from grok_harness_gap import (
    classify,
    compare,
    load_inspect,
    mcp_names_from_text,
    measure_from_rows,
    measure_root,
    preconditions_agree,
    smallest_safe_patch,
)


class TestGrokHarnessGap(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_slack_claim_quarantines_until_preconditions(self):
        inspect = load_inspect(
            json.dumps(
                {
                    "source": "slack-claim",
                    "mcp_count": 0,
                    "lsp_count": 0,
                    "permissions_policy": 0,
                    "home_present": False,
                    "inspect_ran": False,
                }
            )
        )
        self.assertFalse(preconditions_agree(inspect))
        measured = measure_from_rows(
            [
                {
                    "kind": "mcp",
                    "path": "mcp_server/cursor_config.json",
                    "present": True,
                    "names": ["commons"],
                    "coordinator": "GROK",
                }
            ],
            inspect,
            {"catalog": True, "home_exists": False},
        )
        self.assertGreaterEqual(measured["gap_count"], 1)
        self.assertFalse(measured["mutate_grok"])
        self.assertFalse(measured["patch"]["apply"])
        self.assertEqual(classify(measured)["state"], "QUARANTINED")

    def test_missing_catalog_is_not_landed(self):
        measured = measure_from_rows([], {}, {"catalog": False})
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_inspect_zero_mcp_is_candidate(self):
        inspect = {
            "source": "grok-inspect",
            "mcp_count": 0,
            "lsp_count": 0,
            "permissions_policy": 0,
            "inspect_ran": True,
            "home_present": True,
            "source_sha": "deadbeef",
            "live_session": "owner-pc",
        }
        measured = measure_from_rows(
            [
                {
                    "kind": "mcp",
                    "path": "mcp_server/cursor_config.json",
                    "present": True,
                    "names": ["commons"],
                }
            ],
            inspect,
            {"catalog": True},
        )
        self.assertTrue(preconditions_agree(inspect))
        self.assertEqual(classify(measured)["state"], "CANDIDATE")
        kinds = [gap["kind"] for gap in measured["gaps"]]
        self.assertIn("mcp", kinds)
        self.assertIn("permissions_policy", kinds)
        policy = [gap for gap in measured["gaps"] if gap["kind"] == "permissions_policy"][0]
        self.assertEqual(policy["action"], "do_not_add")

    def test_patch_never_applies_itself(self):
        patch = smallest_safe_patch(
            [
                {
                    "present": True,
                    "path": "mcp_server/cursor_config.json",
                    "names": ["commons"],
                }
            ]
        )
        self.assertFalse(patch["apply"])
        self.assertFalse(patch["mutate_grok"])
        self.assertFalse(patch["restart_grok"])
        self.assertIsNone(patch["permissions_policy"])
        self.assertEqual(patch["mcpServers"]["commons"]["from"], "mcp_server/cursor_config.json")

    def test_mcp_names_parse(self):
        self.assertEqual(
            mcp_names_from_text('{"mcpServers":{"commons":{},"independent-commons":{}}}'),
            ["commons", "independent-commons"],
        )
        self.assertEqual(mcp_names_from_text(""), [])
        compared = compare(
            [{"names": ["commons"], "present": True, "path": "x", "kind": "mcp"}],
            {"mcp_count": 0, "lsp_count": 1, "permissions_policy": 1},
        )
        self.assertEqual(compared["gap_count"], 1)
        self.assertEqual(compared["gaps"][0]["kind"], "mcp")

    def test_live_tree_has_canonical_mcp_and_quarantines_slack_claim(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertTrue(measured["catalog"])
        self.assertIn("commons", measured["canonical_mcp"])
        self.assertFalse(measured["mutate_grok"])
        self.assertFalse(measured["restart_grok"])
        self.assertEqual(classify(measured)["state"], "QUARANTINED")
        self.assertFalse(measured["inspect_ran"])
        self.assertFalse(measured["home_exists"])


if __name__ == "__main__":
    unittest.main()
