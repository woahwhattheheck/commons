#!/usr/bin/env python3
"""Human-outcomes sales ops is a distribution layer, not cash and not catalog overwrite."""

from __future__ import annotations

import json
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
SALES = os.path.join(ROOT, "revenue", "human_outcomes", "sales_ops")
CATALOG = {
    "humans.html": "f0b250d6b6eb83f0b8b914f7720d9d84f20645e4",
    "revenue/human_outcomes/offers.json": "1b72639aaea1a3d41c0d2419470add5a3ca8d839",
    "revenue/human_outcomes/README.md": "66c64b6eba9b7aba035223940676bb134590a660",
    "revenue/human_outcomes/fulfillment.md": "fbaf8be09bc4bc544ea470670f3eb6435ebc5838",
}
REQUIRED_SALES_PATHS = [
    "revenue/human_outcomes/sales_ops/README.md",
    "revenue/human_outcomes/sales_ops/owner_activation.json",
    "revenue/human_outcomes/sales_ops/sow_template.md",
    "revenue/human_outcomes/sales_ops/invoice_template.md",
    "revenue/human_outcomes/sales_ops/outreach.json",
    "revenue/human_outcomes/sales_ops/targets.json",
    "test_human_outcomes_sales_ops.py",
    "p/demon-human-outcomes-sales-ops-20260825-01.md",
]
REQUIRED_SKUS = (
    "ho-issue-to-pr",
    "ho-meeting-packet",
    "ho-security-questionnaire",
    "ho-pixel-pack",
)
REQUIRED_PRICES = {
    "ho-issue-to-pr": 2500,
    "ho-meeting-packet": 1200,
    "ho-security-questionnaire": 3000,
    "ho-pixel-pack": 800,
}
FORBIDDEN_VALUE_MARKERS = (
    "acct_",
    "sk_live",
    "rk_live",
    "IBAN ",
    "routing:",
    "ssn:",
    "ein:",
)
POST_ID = "demon-human-outcomes-sales-ops-20260825-01"
TAKING_PATH = os.path.join("p", "demon-human-outcomes-revenue-20260825-01.md")


def git_hash(rel: str) -> str:
    path = os.path.join(ROOT, rel)
    out = subprocess.check_output(["git", "hash-object", path], cwd=ROOT)
    return out.decode("utf-8").strip()


def load_json(rel: str) -> dict:
    path = os.path.join(ROOT, rel)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def classify(row: dict) -> dict:
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "z": "FINDER-FAILED",
            "note": "empty measure is not stillness",
        }
    if not row.get("calibration_ok"):
        return {
            "state": "UNMEASURED",
            "z": "FINDER-FAILED",
            "note": "Instrument failure: calibration missed a required path",
        }
    if row.get("misses"):
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "required path missing",
        }
    if int(row.get("collected_cash_usd", -1)) != 0:
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "claimed cash is not BANK_AVAILABLE",
        }
    if row.get("contact_sent") is not False:
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "contact_sent must stay false on this leftover",
        }
    if row.get("no_checkout") is not True:
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "checkout claimed",
        }
    if row.get("buyer_fiction") is not False:
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "buyer fiction",
        }
    return {"state": "INTEGRATED", "z": "OK", "note": "sales ops files present; cash $0"}


def measure_root() -> dict:
    misses = [rel for rel in REQUIRED_SALES_PATHS if not os.path.isfile(os.path.join(ROOT, rel))]
    catalog_hits = []
    for rel, expected in CATALOG.items():
        if git_hash(rel) != expected:
            catalog_hits.append(rel)
    activation = load_json("revenue/human_outcomes/sales_ops/owner_activation.json")
    outreach = load_json("revenue/human_outcomes/sales_ops/outreach.json")
    targets = load_json("revenue/human_outcomes/sales_ops/targets.json")
    rail = activation.get("rail_decision") or {}
    return {
        "measured": True,
        "calibration_ok": not misses and not catalog_hits,
        "misses": misses,
        "catalog_hits": catalog_hits,
        "collected_cash_usd": activation.get("collected_cash_usd"),
        "contact_sent": activation.get("contact_sent") or outreach.get("contact_sent") or targets.get("contact_sent"),
        "no_checkout": activation.get("no_checkout"),
        "buyer_fiction": targets.get("buyer_fiction"),
        "outreach_status": outreach.get("status"),
        "preferred_rail": rail.get("preferred_rail"),
        "send_from_this_leftover": rail.get("send_from_this_leftover"),
    }


class TestHumanOutcomesSalesOps(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify({"measured": True, "calibration_ok": False, "misses": []})
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("Instrument failure", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = {
            "measured": True,
            "calibration_ok": True,
            "misses": ["revenue/human_outcomes/sales_ops/README.md"],
            "collected_cash_usd": 0,
            "contact_sent": False,
            "no_checkout": True,
            "buyer_fiction": False,
        }
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertEqual(classify(measured)["z"], "FINDER-FAILED")

    def test_claimed_cash_is_not_landed(self):
        measured = {
            "measured": True,
            "calibration_ok": True,
            "misses": [],
            "collected_cash_usd": 12,
            "contact_sent": False,
            "no_checkout": True,
            "buyer_fiction": False,
        }
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_peer_catalog_blobs_untouched(self):
        for rel, expected in CATALOG.items():
            self.assertEqual(git_hash(rel), expected, rel)

    def test_required_paths_exist(self):
        for rel in REQUIRED_SALES_PATHS:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_does_not_remint_catalog_taking(self):
        self.assertFalse(os.path.isfile(os.path.join(ROOT, TAKING_PATH)))

    def test_activation_gate_and_rail(self):
        pack = load_json("revenue/human_outcomes/sales_ops/owner_activation.json")
        self.assertEqual(pack["kind"], "HUMAN_OUTCOMES_SALES_OPS_OWNER_ACTIVATION")
        self.assertEqual(pack["mandate"], POST_ID)
        self.assertEqual(pack["collected_cash_usd"], 0)
        self.assertEqual(pack["collectable_usd"], "NOT_LANDED")
        self.assertTrue(pack["no_checkout"])
        self.assertFalse(pack["contact_sent"])
        self.assertTrue(pack["no_private_data_stored"])
        self.assertTrue(pack["no_buyer_fiction"])
        self.assertEqual(pack["peer_catalog_pr"], 2312)
        self.assertEqual(pack["gate"]["collected_cash"], "NOT_LANDED")
        self.assertTrue(pack["gate"]["ready_does_not_mean_cash"])
        rail = pack["rail_decision"]
        self.assertEqual(rail["preferred_rail"], "stripe_invoice_specific_customer")
        self.assertEqual(rail["preferred_source_http_status"], 200)
        self.assertFalse(rail["send_from_this_leftover"])
        self.assertIn("Stripe Payment Link", rail["do_not_use_on_commons"])
        self.assertEqual(set(rail["events"]), {"AUTHORIZATION", "SETTLEMENT", "PAYOUT", "BANK_AVAILABLE"})
        for sku, price in REQUIRED_PRICES.items():
            miles = rail["milestones_by_sku"][sku]
            self.assertEqual(miles["total_usd"], price)
            self.assertEqual(miles["m1_before_start_usd"] + miles["m2_on_acceptance_usd"], price)
        for field in pack["fields"]:
            self.assertFalse(field["value_stored_here"], field["id"])
        for rel in pack["does_not_touch"]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_outreach_is_founder_reviewed_and_unsent(self):
        pack = load_json("revenue/human_outcomes/sales_ops/outreach.json")
        self.assertTrue(pack["founder_reviewed"])
        self.assertEqual(pack["status"], "NOT_SENT")
        self.assertFalse(pack["contact_sent"])
        self.assertEqual(pack["emails_queued"], 0)
        ids = {draft["sku"] for draft in pack["drafts"]}
        self.assertEqual(ids, set(REQUIRED_SKUS))
        for draft in pack["drafts"]:
            self.assertEqual(draft["status"], "NOT_SENT")
            self.assertIn("no checkout", draft["body"].lower())

    def test_targets_are_venues_not_named_buyers(self):
        pack = load_json("revenue/human_outcomes/sales_ops/targets.json")
        self.assertEqual(pack["demand"], "UNKNOWN")
        self.assertFalse(pack["buyer_fiction"])
        self.assertEqual(pack["named_private_buyers"], [])
        self.assertFalse(pack["contact_sent"])
        self.assertGreaterEqual(len(pack["current_public_targets"]), 8)
        self.assertGreaterEqual(len(pack["not_current_public_from_this_host"]), 3)
        skus = {row["sku"] for row in pack["current_public_targets"]}
        for sku in REQUIRED_SKUS:
            self.assertTrue(sku in skus or "all_four" in skus, sku)
        for row in pack["current_public_targets"]:
            self.assertFalse(row["buyer_named"], row["id"])
            self.assertEqual(row["http_status"], 200, row["id"])
            self.assertTrue(row["url"].startswith("https://"), row["id"])
        statuses = {row["url"]: row["http_status"] for row in pack["not_current_public_from_this_host"]}
        self.assertEqual(statuses["https://github.com/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22"], 404)
        self.assertEqual(statuses["https://www.congress.gov/committee-meetings"], 403)

    def test_templates_keep_owner_fields_blank(self):
        for rel in (
            "revenue/human_outcomes/sales_ops/sow_template.md",
            "revenue/human_outcomes/sales_ops/invoice_template.md",
        ):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("leave blank", text)
            self.assertIn("NOT_PROVIDED_ON_THIS_PAGE", text)
            self.assertIn("$0 / NOT_LANDED", text)
            for sku, price in REQUIRED_PRICES.items():
                self.assertIn(sku, text)
                self.assertIn(str(price), text)
            for marker in FORBIDDEN_VALUE_MARKERS:
                self.assertNotIn(marker, text)

    def test_json_has_no_secret_values(self):
        for rel in (
            "revenue/human_outcomes/sales_ops/owner_activation.json",
            "revenue/human_outcomes/sales_ops/outreach.json",
            "revenue/human_outcomes/sales_ops/targets.json",
        ):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
                raw = handle.read()
            for marker in FORBIDDEN_VALUE_MARKERS:
                self.assertNotIn(marker, raw)
            self.assertIsNone(re.search(r"\b\d{9}\b", raw))

    def test_board_post_is_exact_id(self):
        path = os.path.join(ROOT, "p", f"{POST_ID}.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(f"id: {POST_ID}", text)
        self.assertIn("PLAIN:", text)
        self.assertIn("1787649999.513539", text)
        self.assertNotIn("supersedes:", text.split("---", 2)[0])

    def test_live_tree_is_integrated_and_cash_is_zero(self):
        row = measure_root()
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED", (verdict, row))
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertFalse(row["contact_sent"])
        self.assertTrue(row["no_checkout"])
        self.assertFalse(row["buyer_fiction"])
        self.assertEqual(row["outreach_status"], "NOT_SENT")
        self.assertEqual(row["preferred_rail"], "stripe_invoice_specific_customer")
        self.assertFalse(row["send_from_this_leftover"])
        self.assertEqual(row["catalog_hits"], [])
        self.assertEqual(row["misses"], [])


if __name__ == "__main__":
    unittest.main()
