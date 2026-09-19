from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.swarm_terminality_registry.core import (
    AUTHORITY_CEILING,
    RegistryError,
    compile_snapshot,
    load_strict_json,
    verify_bundle,
)

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "tools" / "swarm_terminality_registry" / "example.json"


def candidate():
    return load_strict_json(EXAMPLE.read_text(encoding="utf-8"))


def by_id(report, item_id):
    return next(x for x in report["items"] if x["item_id"] == item_id)


class TerminalityRegistryTests(unittest.TestCase):
    def test_example_classifications_and_authority(self):
        bundle = compile_snapshot(candidate())
        report = json.loads(bundle.report_json)
        self.assertEqual(by_id(report, "pr-merged")["classification"], "TERMINAL_MERGED")
        self.assertEqual(by_id(report, "issue-old")["classification"], "SUPERSEDED")
        self.assertEqual(by_id(report, "pr-stale")["recommended_next_action"], "CLOSE_STALE_CARRIER")
        self.assertEqual(by_id(report, "op-active")["classification"], "ACTIVE_CUSTODY")
        self.assertEqual(by_id(report, "op-recover")["classification"], "RECOVERY_ELIGIBLE")
        self.assertEqual(by_id(report, "branch-unknown")["classification"], "HOLD_INCOMPLETE_EVIDENCE")
        self.assertTrue(all(v is False for v in AUTHORITY_CEILING.values()))
        self.assertTrue(verify_bundle(candidate(), bundle.report_json, bundle.report_markdown, bundle.receipt_json))

    def test_closed_is_terminal(self):
        data = candidate()
        op = next(x for x in data["provider_observations"] if x["id"] == "obs-op-recover")
        op["provider_state"] = "CLOSED"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "op-recover")["classification"], "TERMINAL_CLOSED")

    def test_stale_provider_holds(self):
        data = candidate()
        op = next(x for x in data["provider_observations"] if x["id"] == "obs-op-recover")
        op["observed_at_utc"] = "2026-09-17T18:00:00Z"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "op-recover")["classification"], "HOLD_INCOMPLETE_EVIDENCE")
        self.assertEqual(by_id(report, "op-recover")["recommended_next_action"], "REFRESH_EVIDENCE")

    def test_future_provider_holds(self):
        data = candidate()
        op = next(x for x in data["provider_observations"] if x["id"] == "obs-op-recover")
        op["observed_at_utc"] = "2026-09-17T20:00:00Z"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "op-recover")["classification"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_expired_heartbeat_allows_recovery(self):
        data = candidate()
        hb = data["heartbeats"][0]
        hb["observed_at_utc"] = "2026-09-17T19:00:00Z"
        hb["expires_at_utc"] = "2026-09-17T19:10:00Z"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "op-active")["classification"], "RECOVERY_ELIGIBLE")

    def test_future_heartbeat_holds(self):
        data = candidate()
        hb = data["heartbeats"][0]
        hb["observed_at_utc"] = "2026-09-17T19:30:00Z"
        hb["expires_at_utc"] = "2026-09-17T19:40:00Z"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "op-active")["classification"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_cross_item_heartbeat_source_rejected(self):
        data = candidate()
        data["heartbeats"][0]["source_observation_id"] = "obs-op-recover"
        with self.assertRaisesRegex(RegistryError, "not bound to item"):
            compile_snapshot(data)

    def test_cross_item_item_observation_rejected(self):
        data = candidate()
        item = next(x for x in data["items"] if x["id"] == "op-recover")
        item["provider_observation_id"] = "obs-op-active"
        with self.assertRaisesRegex(RegistryError, "cross-item provider observation transplant"):
            compile_snapshot(data)

    def test_successor_needs_both_item_observations(self):
        data = candidate()
        data["successors"][0]["source_observation_ids"] = ["obs-pr-merged"]
        with self.assertRaisesRegex(RegistryError, r"lacks predecessor\+successor"):
            compile_snapshot(data)

    def test_conflicting_successors_rejected(self):
        data = candidate()
        data["successors"].append({
            "id":"succ-old-to-active","predecessor_item_id":"issue-old","successor_item_id":"op-active",
            "relationship":"CANONICAL_SUCCESSOR","source_observation_ids":["obs-issue-old","obs-op-active"]})
        with self.assertRaisesRegex(RegistryError, "conflicting canonical successors"):
            compile_snapshot(data)

    def test_successor_cycle_rejected(self):
        data = candidate()
        data["successors"].append({
            "id":"succ-merged-to-old","predecessor_item_id":"pr-merged","successor_item_id":"issue-old",
            "relationship":"CANONICAL_SUCCESSOR","source_observation_ids":["obs-pr-merged","obs-issue-old"]})
        with self.assertRaisesRegex(RegistryError, "cycle"):
            compile_snapshot(data)

    def test_stale_successor_holds_predecessor(self):
        data = candidate()
        obs = next(x for x in data["provider_observations"] if x["id"] == "obs-pr-merged")
        obs["observed_at_utc"] = "2026-09-17T18:00:00Z"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "issue-old")["classification"], "HOLD_INCOMPLETE_EVIDENCE")

    def test_unknown_successor_holds_predecessor(self):
        data = candidate()
        # Swap successor to an operation whose state can be UNKNOWN without violating kind/state grammar.
        edge = data["successors"][0]
        edge["successor_item_id"] = "op-recover"
        edge["source_observation_ids"] = ["obs-issue-old", "obs-op-recover"]
        next(x for x in data["provider_observations"] if x["id"] == "obs-op-recover")["provider_state"] = "UNKNOWN"
        report = json.loads(compile_snapshot(data).report_json)
        self.assertEqual(by_id(report, "issue-old")["classification"], "HOLD_INCOMPLETE_EVIDENCE")



if __name__ == "__main__":
    unittest.main()
