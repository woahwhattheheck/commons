#!/usr/bin/env python3
"""Fail-closed tests for AT-GROK-ADAPTER-EVIDENCE-01."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import at_grok_adapter_evidence as ev


class AtGrokAdapterEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = ev.load_ledger()

    def test_four_exact_buyer_instruments_present(self) -> None:
        labels = [row["buyer_label"] for row in self.ledger["instruments"]]
        self.assertEqual(len(labels), 4)
        self.assertEqual(labels, list(ev.BUYER_LABELS))
        self.assertEqual(self.ledger["buyer_labels"], list(ev.BUYER_LABELS))
        self.assertEqual(self.ledger["counts"]["instruments"], 4)

    def test_unknown_versus_documented_is_honest(self) -> None:
        self.assertEqual(self.ledger["counts"]["schema_unknown"], 4)
        self.assertEqual(self.ledger["counts"]["schema_documented"], 0)
        self.assertEqual(self.ledger["counts"]["framing_documented_partial"], 1)
        self.assertEqual(self.ledger["counts"]["framing_transport_named"], 2)
        self.assertEqual(self.ledger["counts"]["framing_unknown"], 1)
        self.assertEqual(self.ledger["counts"]["export_fixtures"], 0)
        by_label = {row["buyer_label"]: row for row in self.ledger["instruments"]}
        self.assertEqual(by_label["Metrohm Eco IC"]["framing_status"], "DOCUMENTED_PARTIAL")
        self.assertEqual(by_label["Seivers M5310C"]["framing_status"], "TRANSPORT_NAMED")
        self.assertEqual(by_label["Seal Analytical AQ300"]["framing_status"], "TRANSPORT_NAMED")
        self.assertEqual(by_label["Perkin Elmer PinAAcle 900Z"]["framing_status"], "UNKNOWN")
        for row in self.ledger["instruments"]:
            self.assertEqual(row["schema_status"], "UNKNOWN")
            self.assertIn("BUYER OR VENDOR SAMPLE REQUIRED", row["schema_reason"])
            self.assertTrue(row["schema_reason"].startswith("UNKNOWN"))
            self.assertIsNone(row["fixture"])

    def test_seivers_spelling_preserved(self) -> None:
        packed = json.dumps(self.ledger, ensure_ascii=True)
        self.assertIn("Seivers M5310C", packed)
        self.assertNotIn('"Sievers M5310C"', packed)
        seivers = next(row for row in self.ledger["instruments"] if row["buyer_label"] == "Seivers M5310C")
        self.assertEqual(seivers["oem_trademark_spelling"], "Sievers M5310 C")
        self.assertIn("Do not normalize Seivers to Sievers", seivers["spelling_rule"])
        failures = ev.sievers_normalization_probe(self.ledger)
        self.assertTrue(failures)
        self.assertTrue(any("Sievers" in item for item in failures))

    def test_no_invented_field_names(self) -> None:
        metrohm = next(row for row in self.ledger["instruments"] if row["buyer_label"] == "Metrohm Eco IC")
        names = [item["name"] for item in metrohm["verbatim_names"]]
        self.assertEqual(names, list(ev.METROHM_VERBATIM))
        for item in metrohm["verbatim_names"]:
            self.assertTrue(item["source_url"].startswith("https://www.metrohm.com/"))
            self.assertTrue(item["page_or_section"])
        for row in self.ledger["instruments"]:
            if row["buyer_label"] == "Metrohm Eco IC":
                continue
            self.assertEqual(row["verbatim_names"], [])
            for banned in ev.FORBIDDEN_SCHEMA_KEYS:
                self.assertNotIn(banned, row)

    def test_guessed_schema_fails_closed(self) -> None:
        failures = ev.guessed_schema_probe(self.ledger)
        self.assertTrue(failures)
        blob = " ".join(failures)
        self.assertIn("UNKNOWN", blob)
        self.assertTrue("export_schema" in blob or "guessed schema" in blob.lower() or "verbatim" in blob)

    def test_runner_exits_nonzero_on_guessed_schema(self) -> None:
        poisoned = deepcopy(self.ledger)
        poisoned["instruments"][2]["schema_status"] = "GUESSED"
        poisoned["instruments"][2]["csv_columns"] = ["Sample", "Result", "Unit"]
        poisoned["counts"]["schema_unknown"] = 3
        poisoned["counts"]["schema_documented"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "uncertainty_ledger.json"
            path.write_text(json.dumps(poisoned), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(Path(ev.__file__).resolve()), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("FAIL", proc.stderr)

    def test_honest_ledger_validates_and_cli_exits_zero(self) -> None:
        self.assertEqual(ev.validate_ledger(self.ledger), [])
        result = ev.run()
        self.assertEqual(result["id"], ev.DEMAND_ID)
        self.assertEqual(len(result["ledger_sha256"]), 64)
        proc = subprocess.run(
            [sys.executable, str(Path(ev.__file__).resolve())],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Seivers M5310C", proc.stdout)
        self.assertIn("UNKNOWN / BUYER OR VENDOR SAMPLE REQUIRED", proc.stdout)
        self.assertIn("python3 at_grok_adapter_evidence.py", proc.stdout)
        parsed = json.loads(proc.stdout[proc.stdout.index("{") :])
        self.assertEqual(parsed["counts"]["schema_unknown"], 4)
        self.assertEqual(parsed["counts"]["schema_documented"], 0)

    def test_off_limits_and_state_hold(self) -> None:
        self.assertEqual(self.ledger["state"], ev.STATE)
        self.assertEqual(self.ledger["cash_usd"], 0)
        for leftover in ev.OFF_LIMITS:
            self.assertIn(leftover, self.ledger["off_limits"])
            self.assertNotEqual(leftover, ev.DEMAND_ID)
        for claim in ("production", "spend", "certification", "compliance"):
            self.assertIn(claim, self.ledger["not_claims"])


if __name__ == "__main__":
    unittest.main()
