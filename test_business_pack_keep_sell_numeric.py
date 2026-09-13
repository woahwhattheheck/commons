#!/usr/bin/env python3
"""Malformed numeric ledgers must return validation errors, not exceptions."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "host" / "business_pack_keep_sell.py"


def load_module():
    spec = importlib.util.spec_from_file_location("keep_sell_numeric_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MOD = load_module()


class NumericValidationTests(unittest.TestCase):
    def ledger(self):
        return MOD.empty_ledger()

    def test_malformed_cash_values_return_errors(self):
        for value in ("not-a-number", "NaN", "Infinity", True, object()):
            with self.subTest(value=repr(value)):
                ledger = self.ledger()
                ledger["cash_usd"] = value
                errors = MOD.validate_ledger(ledger)
                self.assertTrue(any("cash_usd must be a finite decimal" in row for row in errors))

    def test_malformed_buyer_values_return_errors(self):
        for value in ("oops", 0.5, float("nan"), True, object()):
            with self.subTest(value=repr(value)):
                ledger = self.ledger()
                ledger["buyers"] = value
                errors = MOD.validate_ledger(ledger)
                self.assertTrue(any("buyers must be an integer" in row for row in errors))

    def test_malformed_tiers_return_errors(self):
        for value in ("oops", 20.5, float("nan"), True, object()):
            with self.subTest(value=repr(value)):
                ledger = self.ledger()
                MOD.record_decision(
                    ledger,
                    pack_id="numeric-test-pack-20260908",
                    decision="SELL",
                    title="Numeric test",
                )
                ledger["packs"][0]["tier_usd"] = value
                errors = MOD.validate_ledger(ledger)
                self.assertTrue(any("tier_usd must be an integer" in row for row in errors))

    def test_wrong_pack_container_returns_error(self):
        for value in ({"id": "not-a-list"}, "not-a-list", 7):
            with self.subTest(value=repr(value)):
                ledger = self.ledger()
                ledger["packs"] = value
                errors = MOD.validate_ledger(ledger)
                self.assertIn("packs must be a list", errors)

    def test_integral_encodings_remain_accepted(self):
        for tier in (20, 20.0, "20"):
            with self.subTest(tier=tier):
                ledger = self.ledger()
                ledger["cash_usd"] = "0.000"
                ledger["buyers"] = "0"
                MOD.record_decision(
                    ledger,
                    pack_id="integral-tier-pack-20260908",
                    decision="KEEP",
                    title="Integral tier",
                )
                ledger["packs"][0]["tier_usd"] = tier
                self.assertEqual(MOD.validate_ledger(ledger), [])

    def test_nonzero_and_unknown_values_keep_existing_messages(self):
        ledger = self.ledger()
        ledger["cash_usd"] = "1.25"
        ledger["buyers"] = 1
        MOD.record_decision(
            ledger,
            pack_id="unknown-tier-pack-20260908",
            decision="SELL",
            title="Unknown tier",
        )
        ledger["packs"][0]["tier_usd"] = 30
        errors = MOD.validate_ledger(ledger)
        self.assertIn("cash_usd must stay 0.00 without BANK_AVAILABLE", errors)
        self.assertIn("buyers must stay 0 without a receipt", errors)
        self.assertIn(
            "unknown-tier-pack-20260908 tier_usd must be one of (20, 100, 200, 1000, 10000)",
            errors,
        )

    def test_cli_validate_reports_invalid_without_traceback(self):
        ledger = self.ledger()
        ledger["cash_usd"] = "not-a-number"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text(json.dumps(ledger), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = MOD.main(["--ledger", str(path), "validate"])
        self.assertEqual(code, 1)
        self.assertTrue(output.getvalue().startswith("INVALID\n"))
        self.assertIn("cash_usd must be a finite decimal", output.getvalue())

    def test_valid_current_ledger_and_mutation_isolation(self):
        ledger = self.ledger()
        before = deepcopy(ledger)
        self.assertEqual(MOD.validate_ledger(ledger), [])
        self.assertEqual(ledger, before)


if __name__ == "__main__":
    unittest.main()
