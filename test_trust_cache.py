#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from host import trust_cache


class TrustCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifact = self.root / "artifact.bin"
        self.artifact.write_bytes(b"alpha")
        self.ledger = self.root / "receipts.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_state_machine_and_waste_gate(self) -> None:
        self.assertEqual(
            trust_cache.status(self.artifact, "unit", self.ledger)["state"],
            "UNVERIFIED",
        )
        marker = self.root / "ran.txt"
        command = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('once')",
        ]
        first, code = trust_cache.run_check(
            self.artifact, "unit", command, self.ledger
        )
        self.assertEqual(code, 0)
        self.assertEqual(first["event"], "PASS")
        self.assertTrue(marker.exists())
        marker.unlink()

        second, code = trust_cache.run_check(
            self.artifact, "unit", command, self.ledger
        )
        self.assertEqual(code, 0)
        self.assertEqual(second["state"], "TRUSTED")
        self.assertEqual(second["event"], "WASTE")
        self.assertFalse(second["executed"])
        self.assertFalse(marker.exists())

        self.artifact.write_bytes(b"beta")
        self.assertEqual(
            trust_cache.status(self.artifact, "unit", self.ledger)["state"],
            "STALE",
        )

    def test_receipts_are_append_only_five_field_jsonl(self) -> None:
        trust_cache.append_receipt(
            self.ledger,
            trust_cache.sha256_file(self.artifact),
            "schema",
            "PASS",
            {"event": "TEST"},
        )
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        row = json.loads(lines[0])
        self.assertEqual(set(row), trust_cache.RECEIPT_FIELDS)
        self.assertEqual(
            row["evidence"]["schema_version"],
            trust_cache.SCHEMA_VERSION,
        )

    def test_canary_rejects_schema_drift(self) -> None:
        self.ledger.write_text(
            json.dumps(
                {
                    "artifact_sha256": "0" * 64,
                    "check_id": "bad",
                    "result": "PASS",
                    "recorded_at": "2026-08-28T00:00:00Z",
                    "evidence": {"schema_version": "wrong"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(trust_cache.TrustCacheError):
            trust_cache.status(self.artifact, "bad", self.ledger)

    def test_missing_artifact_fails_canary(self) -> None:
        with self.assertRaises(trust_cache.TrustCacheError):
            trust_cache.status(self.root / "missing", "unit", self.ledger)


if __name__ == "__main__":
    unittest.main()
