#!/usr/bin/env python3
"""Exercise saved receipt projections through the real filesystem and CLI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host.agent_liveness_index import AgentLivenessError, check_snapshot, scan


SCRIPT = Path(__file__).resolve().parent / "host" / "agent_liveness_index.py"
OBSERVED = "2026-09-08T12:00:00Z"
COMMIT = "a" * 40


class SnapshotIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        rows = [
            {"from": "BASALT", "id": "receipt-one", "ts": OBSERVED},
            {"from": "UNKNOWN", "id": "receipt-two", "ts": ""},
        ]
        documents = {
            "presence.json": rows,
            "lastseen.json": rows,
            "claims.json": {"claims": [{"id": "receipt-one", "status": "OPEN"}]},
        }
        for name, value in documents.items():
            (self.root / name).write_text(json.dumps(value), encoding="utf-8")
        self.expected = scan(self.root, OBSERVED, COMMIT)
        self.snapshot = self.root / "snapshot.json"
        self.save(self.expected)

    def save(self, value: object) -> None:
        self.snapshot.write_text(json.dumps(value), encoding="utf-8")

    def rejects(self, path: tuple[str | int, ...], value: object) -> None:
        changed = copy.deepcopy(self.expected)
        target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        self.save(changed)
        with self.assertRaisesRegex(AgentLivenessError, "differs from its exact source inputs"):
            check_snapshot(self.root, self.snapshot)

    def cli(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), "--check", str(self.snapshot)],
            capture_output=True, text=True, timeout=10, check=False,
        )

    def test_unchanged_snapshot_matches(self) -> None:
        self.assertEqual(check_snapshot(self.root, self.snapshot), self.expected)

    def test_json_object_order_and_whitespace_are_not_integrity_changes(self) -> None:
        def reverse_keys(value: object) -> object:
            if isinstance(value, dict):
                return {key: reverse_keys(item) for key, item in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse_keys(item) for item in value]
            return value
        self.snapshot.write_text(json.dumps(reverse_keys(self.expected), indent=4) + "\n", encoding="utf-8")
        self.assertEqual(check_snapshot(self.root, self.snapshot), self.expected)

    def test_truth_booleans_cannot_be_replaced_by_numbers(self) -> None:
        for field in (
            "board_presence_is_not_runtime_liveness",
            "fresh_receipt_is_not_session_reachability",
            "open_claim_is_not_active_capacity",
        ):
            for value in (1, 1.0):
                with self.subTest(field=field, value=repr(value)):
                    self.rejects(("truth", field), value)

    def test_zero_mutation_counts_cannot_be_replaced_by_false(self) -> None:
        for field in ("sessions_woken", "claims_mutated", "messages_sent"):
            with self.subTest(field=field):
                self.rejects(("truth", field), False)

    def test_summary_counts_cannot_be_replaced_by_booleans(self) -> None:
        for field in ("fresh_6h", "claims", "claim_ids_matching_lastseen", "unknown_timestamp"):
            with self.subTest(field=field):
                self.rejects(("summary", field), True)
        self.rejects(("summary", "stale_over_24h"), False)

    def test_nested_claim_status_count_cannot_be_true(self) -> None:
        self.rejects(("summary", "claim_statuses", "OPEN"), True)

    def test_nested_age_cannot_be_false_or_float(self) -> None:
        for value in (False, 0.0, -0.0):
            with self.subTest(value=repr(value)):
                self.rejects(("identities", 0, "age_seconds"), value)

    def test_integer_thresholds_cannot_be_float(self) -> None:
        for field, value in (("fresh", 21600.0), ("recent", 86400.0)):
            with self.subTest(field=field):
                self.rejects(("thresholds_seconds", field), value)

    def test_unknown_age_must_remain_null(self) -> None:
        self.assertIsNone(check_snapshot(self.root, self.snapshot)["identities"][1]["age_seconds"])
        self.rejects(("identities", 1, "age_seconds"), 0)

    def test_other_payload_changes_remain_rejected(self) -> None:
        self.rejects(("identities", 0, "session_reachability"), "VERIFIED")
        self.rejects(("identities",), list(reversed(self.expected["identities"])))
        changed = copy.deepcopy(self.expected)
        changed["unexpected"] = 0
        self.save(changed)
        with self.assertRaises(AgentLivenessError):
            check_snapshot(self.root, self.snapshot)

    def test_source_byte_change_invalidates_original_snapshot(self) -> None:
        source = self.root / "presence.json"
        source.write_bytes(source.read_bytes() + b"\n")
        with self.assertRaises(AgentLivenessError):
            check_snapshot(self.root, self.snapshot)

    def test_cli_rejects_type_changed_snapshot_without_writing_inputs(self) -> None:
        changed = copy.deepcopy(self.expected)
        changed["truth"]["fresh_receipt_is_not_session_reachability"] = 1
        self.save(changed)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("differs from its exact source inputs", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_cli_matches_unchanged_snapshot_without_writing_inputs(self) -> None:
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "MATCH 2 identities 1 fresh 0 stale 1 unknown\n")
        self.assertEqual(result.stderr, "")
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
