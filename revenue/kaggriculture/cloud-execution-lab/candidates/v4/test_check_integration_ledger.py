#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import check_integration_ledger as ledger


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _base() -> tuple[dict[str, object], dict[str, object]]:
    canonical = {
        "canonical_branch": "main",
        "workspace": "revenue/kaggriculture/cloud-execution-lab/candidates/v4",
    }
    integration = {
        "canonical_branch": "main",
        "workspace": canonical["workspace"],
        "landed": [],
        "recovered_not_yet_composed": [],
        "custody_blocked": [],
        "negative_or_parked": [],
    }
    return canonical, integration


class IntegrationLedgerCustodyContractTests(unittest.TestCase):
    def validate_with(self, row: dict[str, object], *, manifest: dict[str, object] | None = None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            canonical, integration = _base()
            integration["custody_blocked"] = [row]
            _write_json(root / "CANONICAL.json", canonical)
            _write_json(root / "INTEGRATION.json", integration)

            custody_path = row.get("custody_path")
            if isinstance(custody_path, str):
                directory = root / custody_path
                directory.mkdir(parents=True)
                if manifest is not None:
                    _write_json(directory / "MANIFEST.json", manifest)

            return ledger.validate(root)

    def test_live_raw_payload_blocker_remains_strict(self):
        row = {
            "lane": "raw guard pack",
            "custody_path": "repairs/gameplay/raw-guard",
            "status": "awaiting_raw_payload",
        }
        manifest = {
            "lane": "raw guard pack",
            "status": "awaiting_raw_payload",
            "required_next_step": "publish exact bytes",
        }
        self.assertEqual([], self.validate_with(row, manifest=manifest))

    def test_live_raw_payload_blocker_without_manifest_fails_closed(self):
        row = {
            "lane": "raw guard pack",
            "custody_path": "repairs/gameplay/raw-guard",
            "status": "awaiting_raw_payload",
        }
        errors = self.validate_with(row)
        self.assertTrue(any("MANIFEST.json" in error for error in errors), errors)

    def test_nonblocking_historical_gap_does_not_require_awaiting_manifest(self):
        row = {
            "lane": "historical packet",
            "custody_path": "repairs/gameplay/current-component",
            "status": "historical_evidence_gap_not_source_blocker",
            "available": "exact current source and tests",
            "missing": "old benchmark receipt",
            "required": "archive exact old bytes if recovered; do not reconstruct",
        }
        self.assertEqual([], self.validate_with(row))

    def test_nonblocking_historical_gap_requires_explicit_missing_scope(self):
        row = {
            "lane": "historical packet",
            "custody_path": "repairs/gameplay/current-component",
            "status": "historical_evidence_gap_not_source_blocker",
            "available": "exact current source and tests",
            "missing": "",
            "required": "archive exact old bytes if recovered",
        }
        errors = self.validate_with(row)
        self.assertIn("historical evidence gap lane 'historical packet' lacks missing", errors)

    def test_unknown_custody_status_is_rejected(self):
        row = {
            "lane": "mystery packet",
            "custody_path": "repairs/gameplay/mystery",
            "status": "maybe_blocked",
        }
        errors = self.validate_with(row)
        self.assertIn("custody lane 'mystery packet' has unsupported status 'maybe_blocked'", errors)


if __name__ == "__main__":
    unittest.main()
