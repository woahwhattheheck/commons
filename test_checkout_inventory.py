from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
MOD_PATH = ROOT / "host" / "checkout_inventory.py"
SNAPSHOT = ROOT / "revenue" / "checkout_inventory" / "provider_snapshot.json"
LEGACY = ROOT / "land" / "stripe-payment-links-20260826.md"
spec = importlib.util.spec_from_file_location("checkout_inventory_test_target", MOD_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


class CheckoutInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        cls.legacy = LEGACY.read_text(encoding="utf-8")

    def compile(self, snapshot=None, legacy=None):
        return m.compile_inventory(snapshot or copy.deepcopy(self.snapshot), legacy or self.legacy)

    def test_current_snapshot_counts(self):
        r = self.compile()
        self.assertEqual(r["counts"], {
            "active_links": 36,
            "keyed_links": 32,
            "unkeyed_links": 4,
            "manual_capture_links": 4,
            "subscription_links": 4,
            "single_use_zero_completed_links": 23,
            "payment_intents_observed": 0,
            "balance_transactions_observed": 0,
        })

    def test_duplicate_groups_are_tip_and_unlock(self):
        r = self.compile()
        groups = {g["offer_key"]: g for g in r["duplicate_key_groups"]}
        self.assertEqual(set(groups), {"sku-tip-20260826", "sku-unlock-20260826"})
        self.assertEqual(groups["sku-tip-20260826"]["link_count"], 3)
        self.assertEqual(groups["sku-unlock-20260826"]["link_count"], 2)

    def test_legacy_catalog_selects_one_active_canonical_per_legacy_key(self):
        r = self.compile()
        for row in r["legacy_reconciliation"]:
            self.assertEqual(row["state"], "CANONICAL_ACTIVE", row)
            self.assertEqual(row["active_match_count"], 1, row)
        groups = {g["offer_key"]: g for g in r["duplicate_key_groups"]}
        tip = next(x for x in groups["sku-tip-20260826"]["links"] if x["legacy_canonical"])
        unlock = next(x for x in groups["sku-unlock-20260826"]["links"] if x["legacy_canonical"])
        self.assertEqual(tip["unit_amount_cents"], 500)
        self.assertEqual(unlock["unit_amount_cents"], 500)

    def test_cleanup_is_review_only_and_only_noncanonical_duplicates(self):
        r = self.compile()
        self.assertEqual(len(r["cleanup_review"]), 3)
        self.assertEqual({x["offer_key"] for x in r["cleanup_review"]}, {"sku-tip-20260826", "sku-unlock-20260826"})
        self.assertTrue(all(x["reason"].endswith("REVIEW_ONLY") for x in r["cleanup_review"]))
        self.assertFalse(r["authority"]["link_deactivation_authorized"])
        self.assertFalse(r["authority"]["stripe_write_authorized"])

    def test_zero_provider_objects_does_not_mint_global_cash_truth(self):
        r = self.compile()
        self.assertEqual(r["counts"]["payment_intents_observed"], 0)
        self.assertEqual(r["counts"]["balance_transactions_observed"], 0)
        for key in ("purchase_inferred", "buyer_acceptance_inferred", "payment_inferred", "cash_inferred", "revenue_inferred", "bank_availability_inferred"):
            self.assertIs(r["authority"][key], False)
        self.assertIn("this retained Stripe snapshot", r["truth_note"])

    def test_unkeyed_links_are_visible_not_dropped(self):
        r = self.compile()
        self.assertEqual(len(r["unkeyed_links"]), 4)
        names = {x["product_name"] for x in r["unkeyed_links"]}
        self.assertIn("Agent Failure Autopsy", names)
        self.assertIn("Completed open-source contribution - agentlily-runtime issue 267", names)

    def test_duplicate_link_id_fails(self):
        s = copy.deepcopy(self.snapshot)
        s["links"][1]["link_id"] = s["links"][0]["link_id"]
        with self.assertRaisesRegex(m.InventoryError, "duplicate link_id"):
            m.validate_snapshot(s)

    def test_duplicate_url_fails(self):
        s = copy.deepcopy(self.snapshot)
        s["links"][1]["url"] = s["links"][0]["url"]
        with self.assertRaisesRegex(m.InventoryError, "duplicate payment URL"):
            m.validate_snapshot(s)

    def test_subscription_shape_fails_closed(self):
        s = copy.deepcopy(self.snapshot)
        row = next(x for x in s["links"] if x["mode"] == "subscription")
        row["recurring_interval"] = None
        with self.assertRaisesRegex(m.InventoryError, "monthly recurrence"):
            m.validate_snapshot(s)

    def test_completion_count_cannot_exceed_limit(self):
        s = copy.deepcopy(self.snapshot)
        row = next(x for x in s["links"] if x["completed_limit"] == 1)
        row["completed_count"] = 2
        with self.assertRaisesRegex(m.InventoryError, "exceeds"):
            m.validate_snapshot(s)

    def test_legacy_catalog_drift_fails_closed(self):
        bad = self.legacy.replace("https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08", "not-a-url")
        with self.assertRaisesRegex(m.InventoryError, "exactly seven"):
            self.compile(legacy=bad)

    def test_report_verifier_detects_tamper(self):
        r = self.compile()
        self.assertEqual(m.verify_inventory(self.snapshot, self.legacy, r), r)
        bad = copy.deepcopy(r)
        bad["authority"]["cash_inferred"] = True
        with self.assertRaisesRegex(m.InventoryError, "differs"):
            m.verify_inventory(self.snapshot, self.legacy, bad)

    def test_strict_json_rejects_duplicate_key_and_nan(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            dup = td / "dup.json"; dup.write_text('{"a":1,"a":2}', encoding="utf-8")
            nan = td / "nan.json"; nan.write_text('{"a":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(m.InventoryError, "duplicate JSON key"):
                m.read_json(dup)
            with self.assertRaisesRegex(m.InventoryError, "non-finite"):
                m.read_json(nan)

    def test_cli_compile_verify_and_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            report = td / "report.json"
            p = subprocess.run([sys.executable, str(MOD_PATH), "compile", str(SNAPSHOT), str(LEGACY), "--output", str(report)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            p2 = subprocess.run([sys.executable, str(MOD_PATH), "compile", str(SNAPSHOT), str(LEGACY), "--output", str(report)], cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(p2.returncode, 0)
            self.assertIn("refusing to overwrite", p2.stderr)
            verified = td / "verified.json"
            p3 = subprocess.run([sys.executable, str(MOD_PATH), "verify", str(SNAPSHOT), str(LEGACY), str(report), "--output", str(verified)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(p3.returncode, 0, p3.stderr)
            self.assertEqual(json.loads(report.read_text()), json.loads(verified.read_text()))


if __name__ == "__main__":
    unittest.main()
