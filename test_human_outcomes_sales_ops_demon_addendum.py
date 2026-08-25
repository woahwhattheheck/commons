#!/usr/bin/env python3
"""Additive R6/R7 sales-ops addendum. Does not edit PR #2324 blobs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
OPS = os.path.join(ROOT, "revenue", "human_outcomes", "sales_ops")
POST_ID = "demon-human-outcomes-sales-ops-addendum-20260825-02"
R6_TOKENS = 3256699
R7_TOKENS = 1574079
COMBINED_TOKENS = 4830778
FORBIDDEN_VALUE_MARKERS = (
    "acct_",
    "sk_live",
    "rk_live",
    "IBAN ",
    "routing:",
    "ssn:",
    "ein:",
)
PEER_BLOBS = {
    "revenue/human_outcomes/sales_ops/README.md": "2a0a731c0eaddf2ecb7f7f08c88890a7a838111e",
    "revenue/human_outcomes/sales_ops/owner_activation.json": "3c0afab7bffe015a5c041d92fe0332696f86c2f6",
    "revenue/human_outcomes/sales_ops/sow_template.md": "feb07e99ac15ab072fd0f4c70c3d045456dd7efb",
    "revenue/human_outcomes/sales_ops/invoice_template.md": "9a727d12fed5aa039a10c938efb46287b38ac917",
    "revenue/human_outcomes/sales_ops/outreach.json": "a67a0c97f9f4bf96a868964cf54eab00a06d4612",
    "revenue/human_outcomes/sales_ops/targets.json": "3e484fafcb9a619eb04c254e44073370f2674a83",
    "test_human_outcomes_sales_ops.py": "506b13adb16beb5132b760a538076bf34b2661c6",
    "p/demon-human-outcomes-sales-ops-20260825-01.md": "fe19cfb7e57c4932d3db5f161166a91814a037f9",
}
CATALOG_BLOBS = {
    "humans.html": "f0b250d6b6eb83f0b8b914f7720d9d84f20645e4",
    "revenue/human_outcomes/offers.json": "1b72639aaea1a3d41c0d2419470add5a3ca8d839",
    "revenue/human_outcomes/README.md": "66c64b6eba9b7aba035223940676bb134590a660",
    "revenue/human_outcomes/fulfillment.md": "fbaf8be09bc4bc544ea470670f3eb6435ebc5838",
}
ADDENDUM_PATHS = (
    "revenue/human_outcomes/sales_ops/demand_r6.json",
    "revenue/human_outcomes/sales_ops/rails_r7.json",
    "revenue/human_outcomes/sales_ops/DEMON_ADDENDUM.md",
    "test_human_outcomes_sales_ops_demon_addendum.py",
    f"p/{POST_ID}.md",
)
URL_RE = re.compile(r"https://[^\s\"']+")


def git_hash(rel: str) -> str:
    path = os.path.join(ROOT, rel)
    out = subprocess.check_output(["git", "hash-object", path], cwd=ROOT)
    return out.decode("utf-8").strip()


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
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
    if row.get("send_ready_count", -1) != 0:
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "a signal is send_ready before founder qualification",
        }
    if row.get("catalog_price_support_count", -1) != 0:
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "a signal supports catalog price without qualification",
        }
    return {"state": "INTEGRATED", "z": "OK", "note": "addendum present; cash $0"}


def measure_root() -> dict:
    misses = [rel for rel in ADDENDUM_PATHS if not os.path.isfile(os.path.join(ROOT, rel))]
    peer_hits = [rel for rel, expected in PEER_BLOBS.items() if git_hash(rel) != expected]
    catalog_hits = [rel for rel, expected in CATALOG_BLOBS.items() if git_hash(rel) != expected]
    demand = load_json("revenue/human_outcomes/sales_ops/demand_r6.json")
    rails = load_json("revenue/human_outcomes/sales_ops/rails_r7.json")
    truth = demand.get("truth") or {}
    send_ready_count = sum(1 for row in demand.get("targets") or [] if row.get("send_ready"))
    return {
        "measured": True,
        "calibration_ok": not misses and not peer_hits and not catalog_hits,
        "misses": misses,
        "peer_hits": peer_hits,
        "catalog_hits": catalog_hits,
        "collected_cash_usd": truth.get("collected_cash_usd"),
        "send_ready_count": send_ready_count,
        "catalog_price_support_count": truth.get("targets_supporting_current_catalog_price"),
        "stripe": (rails.get("recommended_primary") or {}).get("provider"),
        "square": (rails.get("fallback") or {}).get("provider"),
        "upwork": (rails.get("escrow_option") or {}).get("provider"),
        "r6_tokens": (demand.get("research") or {}).get("total_tokens"),
        "r7_tokens": (rails.get("research") or {}).get("total_tokens"),
    }


class TestHumanOutcomesSalesOpsDemonAddendum(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify({"measured": True, "calibration_ok": False, "misses": []})
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("Instrument failure", verdict["note"])

    def test_peer_2324_blobs_untouched(self):
        for rel, expected in PEER_BLOBS.items():
            self.assertEqual(git_hash(rel), expected, rel)
        for rel, expected in CATALOG_BLOBS.items():
            self.assertEqual(git_hash(rel), expected, rel)

    def test_addendum_paths_exist(self):
        for rel in ADDENDUM_PATHS:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_demand_is_eight_buyer_signals_not_venues(self):
        demand = load_json("revenue/human_outcomes/sales_ops/demand_r6.json")
        truth = demand["truth"]
        self.assertEqual(demand["research"]["total_tokens"], R6_TOKENS)
        self.assertEqual(truth["collected_cash_usd"], 0)
        self.assertEqual(truth["cash_state"], "NOT_LANDED")
        self.assertFalse(truth["banking_only_blocker"])
        self.assertEqual(truth["buyer_authorizations_observed"], 0)
        self.assertEqual(truth["targets_supporting_current_catalog_price"], 0)
        self.assertEqual(truth["send_ready_without_founder_qualification"], 0)
        self.assertEqual(len(demand["targets"]), 8)
        venue_urls = {
            row["url"]
            for row in load_json("revenue/human_outcomes/sales_ops/targets.json")[
                "current_public_targets"
            ]
        }
        for row in demand["targets"]:
            self.assertFalse(row["send_ready"], row["id"])
            self.assertTrue(row["public_url"].startswith("https://"), row["id"])
            self.assertTrue(row["disqualifier"], row["id"])
            self.assertTrue(row["founder_action"], row["id"])
            self.assertNotIn(row["public_url"], venue_urls, row["id"])

    def test_rails_are_stripe_square_upwork_and_not_bank_only(self):
        rails = load_json("revenue/human_outcomes/sales_ops/rails_r7.json")
        self.assertEqual(rails["research"]["total_tokens"], R7_TOKENS)
        self.assertEqual(
            rails["research"]["total_tokens"]
            + load_json("revenue/human_outcomes/sales_ops/demand_r6.json")["research"][
                "total_tokens"
            ],
            COMBINED_TOKENS,
        )
        self.assertEqual(rails["recommended_primary"]["provider"], "Stripe")
        self.assertEqual(rails["fallback"]["provider"], "Square")
        self.assertEqual(rails["escrow_option"]["provider"], "Upwork")
        self.assertEqual(
            rails["recommended_primary"]["bank_destination_needed_before_buyer_can_pay"],
            "NO_REPORTED_BY_OFFICIAL_SOURCE_RESEARCH",
        )
        threshold = rails["bank_details_only_threshold"]
        self.assertFalse(threshold["reached"])
        joined = " ".join(threshold["preconditions"]).lower()
        self.assertIn("legal payee", joined)
        self.assertIn("kyc", joined)
        self.assertIn("buyer", joined)
        self.assertIn("slot", joined)
        self.assertIn("no buyer authorization", threshold["why_not_reached"])
        self.assertEqual(rails["truth"]["collected_cash_usd"], 0)
        self.assertFalse(rails["truth"]["banking_only_blocker"])

    def test_no_secret_or_contact_claim(self):
        demand = load_json("revenue/human_outcomes/sales_ops/demand_r6.json")
        rails = load_json("revenue/human_outcomes/sales_ops/rails_r7.json")
        raw = json.dumps(demand) + json.dumps(rails)
        for marker in FORBIDDEN_VALUE_MARKERS:
            self.assertNotIn(marker, raw)
        without_urls = URL_RE.sub("", raw)
        self.assertIsNone(re.search(r"\b\d{9}\b", without_urls))
        with open(os.path.join(OPS, "DEMON_ADDENDUM.md"), encoding="utf-8") as handle:
            addendum = handle.read()
        self.assertIn("$0 / NOT_LANDED", addendum)
        self.assertIn("Contact sent remains false", addendum)
        self.assertIn("send-ready", addendum.lower())
        self.assertIn("Stripe", addendum)
        self.assertIn("Square", addendum)
        self.assertIn("Upwork", addendum)

    def test_board_post_is_exact_id(self):
        path = os.path.join(ROOT, "p", f"{POST_ID}.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(f"id: {POST_ID}", text)
        self.assertIn("PLAIN:", text)
        self.assertIn("1787650647.916419", text)
        self.assertIn("PR #2324", text)
        self.assertNotIn("supersedes:", text.split("---", 2)[0])
        self.assertIn("4,830,778", text)
        self.assertIn("$0 / NOT_LANDED", text)

    def test_live_tree_is_integrated_and_cash_is_zero(self):
        row = measure_root()
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED", (verdict, row))
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["send_ready_count"], 0)
        self.assertEqual(row["catalog_price_support_count"], 0)
        self.assertEqual(row["stripe"], "Stripe")
        self.assertEqual(row["square"], "Square")
        self.assertEqual(row["upwork"], "Upwork")
        self.assertEqual(row["r6_tokens"], R6_TOKENS)
        self.assertEqual(row["r7_tokens"], R7_TOKENS)
        self.assertEqual(row["peer_hits"], [])
        self.assertEqual(row["catalog_hits"], [])
        self.assertEqual(row["misses"], [])


if __name__ == "__main__":
    unittest.main()
