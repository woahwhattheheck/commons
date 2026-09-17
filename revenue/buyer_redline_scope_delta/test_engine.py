from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from revenue.buyer_redline_scope_delta.engine import RedlineError, compile_redline, parse_draft, semantic_digest, strict_json_loads, verify_packet


def base_obj():
    return {
        "schema": "buyer-redline-draft/v1",
        "document_id": "acme-pilot-sow",
        "generation_id": "g1",
        "observed_at": "2026-09-16T20:00:00Z",
        "clauses": [
            {"id":"accept.complete","category":"acceptance","metric":"criterion","statement":"Delivery passes the agreed acceptance suite","value":"PASS"},
            {"id":"commercial.currency","category":"price_payment","metric":"currency","statement":"Currency","value":"USD"},
            {"id":"commercial.net","category":"price_payment","metric":"net_days","statement":"Payment timing","value":15},
            {"id":"commercial.price","category":"price_payment","metric":"fixed_price_minor","statement":"Fixed fee","value":1250000},
            {"id":"liability.unlimited","category":"liability_warranty","metric":"unlimited_liability","statement":"Unlimited liability","value":False},
            {"id":"schedule.duration","category":"schedule","metric":"duration_days","statement":"Delivery duration","value":10},
            {"id":"scope.core","category":"scope","metric":"work","statement":"Build the evidence compiler","value":"compiler"},
        ],
    }


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def pair(mutator=None):
    baseline = base_obj()
    braw = encoded(baseline)
    digest = semantic_digest(parse_draft(braw, role="baseline"))
    counter = copy.deepcopy(baseline)
    counter["generation_id"] = "g2"
    counter["observed_at"] = "2026-09-16T20:05:00Z"
    counter["baseline_semantic_sha256"] = digest
    if mutator:
        mutator(counter)
    return braw, encoded(counter)


class RedlineTests(unittest.TestCase):
    def test_unchanged_is_acceptable(self):
        p = compile_redline(*pair())
        self.assertEqual(p["status"], "ACCEPTABLE_AS_WRITTEN")
        self.assertTrue(verify_packet(p))

    def test_added_scope_without_price_bump_requote(self):
        def m(c): c["clauses"].append({"id":"scope.extra","category":"scope","metric":"work","statement":"Additional integration","value":"erp"})
        self.assertEqual(compile_redline(*pair(m))["status"], "REQUOTE_REQUIRED")

    def test_deleted_acceptance_owner_review(self):
        def m(c): c["clauses"] = [x for x in c["clauses"] if x["id"] != "accept.complete"]
        self.assertEqual(compile_redline(*pair(m))["status"], "OWNER_REVIEW")

    def test_currency_drift_requote(self):
        def m(c): next(x for x in c["clauses"] if x["id"] == "commercial.currency")["value"] = "EUR"
        self.assertEqual(compile_redline(*pair(m))["status"], "REQUOTE_REQUIRED")

    def test_wider_net_terms_requote(self):
        def m(c): next(x for x in c["clauses"] if x["id"] == "commercial.net")["value"] = 60
        self.assertEqual(compile_redline(*pair(m))["status"], "REQUOTE_REQUIRED")

    def test_shorter_schedule_requote(self):
        def m(c): next(x for x in c["clauses"] if x["id"] == "schedule.duration")["value"] = 3
        self.assertEqual(compile_redline(*pair(m))["status"], "REQUOTE_REQUIRED")

    def test_unlimited_liability_legal(self):
        def m(c): next(x for x in c["clauses"] if x["id"] == "liability.unlimited")["value"] = True
        self.assertEqual(compile_redline(*pair(m))["status"], "LEGAL_REVIEW_REQUIRED")

    def test_ip_change_legal(self):
        def m(c): c["clauses"].append({"id":"ip.assignment","category":"ip","metric":"ownership","statement":"IP assignment","value":"buyer"})
        self.assertEqual(compile_redline(*pair(m))["status"], "LEGAL_REVIEW_REQUIRED")

    def test_removed_assumption_requote(self):
        b, c = pair()
        bo = json.loads(b); bo["clauses"].append({"id":"assumption.access","category":"assumptions","metric":"input","statement":"Buyer supplies access","value":True})
        b = encoded(bo)
        digest = semantic_digest(parse_draft(b, role="baseline"))
        co = json.loads(c); co["baseline_semantic_sha256"] = digest
        self.assertEqual(compile_redline(b, encoded(co))["status"], "REQUOTE_REQUIRED")

    def test_wrong_parent_digest_holds(self):
        b, c = pair(); co = json.loads(c); co["baseline_semantic_sha256"] = "0" * 64
        p = compile_redline(b, encoded(co))
        self.assertEqual(p["status"], "HOLD_CONTRADICTION")
        self.assertFalse(p["source"]["binding_ok"])

    def test_document_id_mismatch_holds(self):
        b, c = pair(); co = json.loads(c); co["document_id"] = "other"
        self.assertEqual(compile_redline(b, encoded(co))["status"], "HOLD_CONTRADICTION")

    def test_counter_before_baseline_holds(self):
        b, c = pair(); co = json.loads(c); co["observed_at"] = "2026-09-16T19:59:00Z"
        self.assertEqual(compile_redline(b, encoded(co))["status"], "HOLD_CONTRADICTION")

    def test_same_generation_changed_semantics_holds(self):
        b, c = pair(); co = json.loads(c); co["generation_id"] = "g1"; next(x for x in co["clauses"] if x["id"] == "scope.core")["value"] = "changed"
        self.assertEqual(compile_redline(b, encoded(co))["status"], "HOLD_CONTRADICTION")

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(RedlineError): strict_json_loads('{"a":1,"a":2}')

    def test_nan_rejected(self):
        with self.assertRaises(RedlineError): strict_json_loads('{"a":NaN}')

    def test_float_rejected(self):
        b = base_obj(); next(x for x in b["clauses"] if x["id"] == "commercial.price")["value"] = 12.5
        with self.assertRaises(RedlineError): parse_draft(encoded(b), role="baseline")

    def test_duplicate_clause_id_rejected(self):
        b = base_obj(); b["clauses"].append(copy.deepcopy(b["clauses"][0]))
        with self.assertRaises(RedlineError): parse_draft(encoded(b), role="baseline")

    def test_conflicting_singleton_rejected(self):
        b = base_obj(); b["clauses"].append({"id":"commercial.currency.2","category":"price_payment","metric":"currency","statement":"Other currency","value":"EUR"})
        with self.assertRaises(RedlineError): parse_draft(encoded(b), role="baseline")

    def test_non_nfc_rejected(self):
        b = base_obj(); b["clauses"][0]["statement"] = "Cafe\u0301"
        with self.assertRaises(RedlineError): parse_draft(encoded(b), role="baseline")

    def test_surrogate_rejected(self):
        raw = '{"schema":"buyer-redline-draft/v1","document_id":"x","generation_id":"g","observed_at":"2026-09-16T20:00:00Z","clauses":[{"id":"a","category":"scope","metric":"x","statement":"\\ud800","value":1}]}'
        with self.assertRaises(RedlineError): parse_draft(raw, role="baseline")

    def test_receipt_tamper_rejected(self):
        p = compile_redline(*pair()); p["status"] = "OWNER_REVIEW"
        self.assertFalse(verify_packet(p))

    def test_authority_must_remain_false(self):
        p = compile_redline(*pair())
        self.assertTrue(all(v is False for v in p["authority"].values()))
        p["authority"]["accept_terms"] = True
        self.assertFalse(verify_packet(p))

    def test_deterministic(self):
        self.assertEqual(compile_redline(*pair()), compile_redline(*pair()))

    def test_raw_digest_changes_when_whitespace_changes_but_semantics_hold(self):
        b, c = pair(); bo = json.loads(b); b2 = json.dumps(bo, indent=2).encode()
        co = json.loads(c); co["baseline_semantic_sha256"] = semantic_digest(parse_draft(b2, role="baseline")); c2 = encoded(co)
        p = compile_redline(b2, c2)
        self.assertEqual(p["status"], "ACCEPTABLE_AS_WRITTEN")
        self.assertEqual(p["source"]["baseline_raw_sha256"], hashlib.sha256(b2).hexdigest())

    def test_synthetic_demo_requires_requote(self):
        root = Path(__file__).resolve().parent / "examples"
        p = compile_redline((root / "baseline.json").read_bytes(), (root / "counter-scope-expansion.json").read_bytes())
        self.assertEqual(p["status"], "REQUOTE_REQUIRED")
        self.assertTrue(verify_packet(p))

    def test_cli_compile_verify_and_no_overwrite(self):
        b, c = pair()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/"b.json").write_bytes(b); (root/"c.json").write_bytes(c)
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
            cmd = [sys.executable, "-m", "revenue.buyer_redline_scope_delta.cli", "compile", str(root/"b.json"), str(root/"c.json"), str(root/"p.json"), "--markdown", str(root/"p.md")]
            first = subprocess.run(cmd, env=env, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            verify = subprocess.run([sys.executable, "-m", "revenue.buyer_redline_scope_delta.cli", "verify", str(root/"p.json")], env=env, capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            second = subprocess.run(cmd, env=env, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing to overwrite", second.stdout)


if __name__ == "__main__":
    unittest.main()
