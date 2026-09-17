import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.revenue_funnel_control.engine import FunnelError, compile_bundle, compile_portfolio, verify_bundle

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64

def event(i, kind, at, source="GITHUB", amount=None, sha=SHA_A):
    return {
        "id": i,
        "kind": kind,
        "observed_at": at,
        "source_class": source,
        "ref": f"https://example.invalid/{i}",
        "sha256": sha,
        "amount_cents": amount,
    }

def base_doc():
    return {
        "schema": "TJL_REVENUE_FUNNEL_V1",
        "evaluation_at": "2026-09-17T06:50:00Z",
        "micro_batch_threshold_cents": 2500,
        "opportunities": [
            {
                "id": "workshare-1",
                "title": "Accepted implementation",
                "lane": "CONTRACT",
                "currency": "USD",
                "reference_amount_cents": 40000,
                "events": [
                    event("q1", "QUALIFIED", "2026-09-16T10:00:00Z", sha=SHA_A),
                    event("p1", "PROPOSAL_SENT", "2026-09-16T11:00:00Z", source="BUYER_MESSAGE", amount=40000, sha=SHA_B),
                    event("a1", "ACCEPTED", "2026-09-16T12:00:00Z", source="BUYER_MESSAGE", sha=SHA_C),
                ],
            },
            {
                "id": "bounty-1",
                "title": "Merged paid maintenance",
                "lane": "BOUNTY",
                "currency": "USD",
                "reference_amount_cents": 9000,
                "events": [
                    event("q2", "QUALIFIED", "2026-09-16T10:00:00Z", sha=SHA_A),
                    event("c2", "CLAIM_SUBMITTED", "2026-09-16T11:00:00Z", amount=9000, sha=SHA_B),
                    event("m2", "MERGED", "2026-09-16T12:00:00Z", sha=SHA_C),
                    event("w2", "AWARDED", "2026-09-16T13:00:00Z", source="SPONSOR_MESSAGE", amount=9000, sha=SHA_D),
                    event("pay2", "PAYMENT_RECEIVED", "2026-09-16T14:00:00Z", source="PROVIDER_RECEIPT", amount=9000, sha=SHA_E),
                ],
            },
            {
                "id": "micro-1",
                "title": "Tiny merged batchable claim",
                "lane": "BOUNTY",
                "currency": "USD",
                "reference_amount_cents": 100,
                "events": [
                    event("q3", "QUALIFIED", "2026-09-16T10:00:00Z", sha=SHA_A),
                    event("c3", "CLAIM_SUBMITTED", "2026-09-16T11:00:00Z", amount=100, sha=SHA_B),
                    event("m3", "MERGED", "2026-09-16T12:00:00Z", sha=SHA_C),
                ],
            },
        ],
    }


class FunnelTests(unittest.TestCase):
    def test_stage_and_portfolio_truth(self):
        packet = compile_portfolio(base_doc())
        rows = {row["id"]: row for row in packet["opportunities"]}
        self.assertEqual(rows["workshare-1"]["stage"], "ACCEPTED_OR_MERGED")
        self.assertEqual(rows["workshare-1"]["next_action"], "COLLECTION_REVIEW")
        self.assertTrue(rows["workshare-1"]["economically_unfinished"])
        self.assertEqual(rows["bounty-1"]["stage"], "PAID")
        self.assertEqual(rows["bounty-1"]["next_action"], "DONE_PAID")
        self.assertFalse(rows["bounty-1"]["economically_unfinished"])
        self.assertTrue(rows["micro-1"]["micro_batch_candidate"])
        self.assertEqual(packet["summary"]["payment_received_by_currency"]["USD"], 9000)
        self.assertEqual(packet["summary"]["economically_unfinished_count"], 2)
        self.assertFalse(packet["summary"]["merged_or_accepted_is_paid"])
        self.assertFalse(packet["summary"]["advertised_or_reference_amount_is_revenue"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_dnr_beats_collection(self):
        doc = base_doc()
        doc["opportunities"][0]["events"].append(event("dnr", "DNR", "2026-09-16T15:00:00Z", source="SLACK", sha=SHA_D))
        row = compile_portfolio(doc)["opportunities"][2]
        self.assertEqual(row["id"], "workshare-1")
        self.assertEqual(row["next_action"], "INBOUND_ONLY_DNR")

    def test_new_inbound_reopens_dnr(self):
        doc = base_doc()
        ev = doc["opportunities"][0]["events"]
        ev.append(event("dnr", "DNR", "2026-09-16T15:00:00Z", source="SLACK", sha=SHA_D))
        ev.append(event("in", "INBOUND_RECEIVED", "2026-09-16T16:00:00Z", source="BUYER_MESSAGE", sha=SHA_E))
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["workshare-1"]
        self.assertEqual(row["next_action"], "RESPOND_TO_NEW_INBOUND")

    def test_collision_requires_later_muse(self):
        doc = base_doc()
        op = doc["opportunities"][0]
        op["events"] = [event("q", "QUALIFIED", "2026-09-16T10:00:00Z", sha=SHA_A)]
        op["events"].append(event("col", "COLLISION_HOLD", "2026-09-16T11:00:00Z", source="SLACK", sha=SHA_B))
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["workshare-1"]
        self.assertEqual(row["next_action"], "HOLD_COLLISION")
        op["events"].append(event("muse", "MUSE_CLEAR", "2026-09-16T12:00:00Z", source="SLACK", sha=SHA_C))
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["workshare-1"]
        self.assertEqual(row["next_action"], "OWNER_OUTBOUND_REVIEW")

    def test_merged_never_implies_paid(self):
        doc = base_doc()
        op = doc["opportunities"][1]
        op["events"] = op["events"][:3]
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["bounty-1"]
        self.assertEqual(row["stage"], "ACCEPTED_OR_MERGED")
        self.assertEqual(row["payment_received_cents"], 0)

    def test_payment_requires_provider_receipt(self):
        doc = base_doc()
        doc["opportunities"][1]["events"][-1]["source_class"] = "GITHUB"
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_payment_requires_award_or_invoice(self):
        doc = base_doc()
        op = doc["opportunities"][1]
        op["events"] = [e for e in op["events"] if e["kind"] != "AWARDED"]
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_progress_requires_qualification(self):
        doc = base_doc()
        doc["opportunities"][0]["events"] = doc["opportunities"][0]["events"][1:]
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_future_evidence_rejected(self):
        doc = base_doc()
        doc["opportunities"][0]["events"][0]["observed_at"] = "2026-09-18T00:00:00Z"
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_fractional_timestamp_rejected(self):
        doc = base_doc()
        doc["opportunities"][0]["events"][0]["observed_at"] = "2026-09-16T10:00:00.1Z"
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_bool_money_rejected(self):
        doc = base_doc()
        doc["opportunities"][0]["reference_amount_cents"] = True
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_unknown_field_rejected(self):
        doc = base_doc()
        doc["opportunities"][0]["surprise"] = 1
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_duplicate_event_id_rejected(self):
        doc = base_doc()
        doc["opportunities"][0]["events"].append(copy.deepcopy(doc["opportunities"][0]["events"][0]))
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_duplicate_evidence_binding_rejected_even_different_ids(self):
        doc = base_doc()
        dupe = copy.deepcopy(doc["opportunities"][0]["events"][0])
        dupe["id"] = "different"
        doc["opportunities"][0]["events"].append(dupe)
        with self.assertRaises(FunnelError):
            compile_portfolio(doc)

    def test_partial_and_overpayment(self):
        doc = base_doc()
        pay = doc["opportunities"][1]["events"][-1]
        pay["amount_cents"] = 1000
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["bounty-1"]
        self.assertEqual(row["stage"], "PARTIALLY_PAID")
        pay["amount_cents"] = 10000
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["bounty-1"]
        self.assertEqual(row["stage"], "OVERPAID_RECONCILE")

    def test_unknown_target_payment_is_not_paid(self):
        doc = base_doc()
        doc["opportunities"][1]["reference_amount_cents"] = None
        row = {x["id"]: x for x in compile_portfolio(doc)["opportunities"]}["bounty-1"]
        self.assertEqual(row["stage"], "PAYMENT_RECORDED_TARGET_UNKNOWN")
        self.assertNotEqual(row["next_action"], "DONE_PAID")

    def test_bundle_roundtrip_and_rehashed_semantic_tamper(self):
        bundle = compile_bundle(base_doc())
        self.assertTrue(verify_bundle(bundle))
        forged = copy.deepcopy(bundle)
        forged["packet"]["summary"]["merged_or_accepted_is_paid"] = True
        forged["receipt"]["packet_sha256"] = hashlib.sha256(
            json.dumps(forged["packet"], ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        self.assertFalse(verify_bundle(forged))

    def test_authority_tamper_rejected(self):
        bundle = compile_bundle(base_doc())
        bundle["receipt"]["authority"]["external_send"] = True
        self.assertFalse(verify_bundle(bundle))

    def test_input_order_does_not_change_packet(self):
        doc = base_doc()
        a = compile_portfolio(doc)
        doc2 = copy.deepcopy(doc)
        doc2["opportunities"].reverse()
        for op in doc2["opportunities"]:
            op["events"].reverse()
        b = compile_portfolio(doc2)
        self.assertEqual(a, b)

    def test_cli_compile_verify_and_exclusive_output(self):
        doc = base_doc()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "in.json"
            out = root / "out.json"
            inp.write_text(json.dumps(doc), encoding="utf-8")
            cmd = [sys.executable, "-m", "revenue.revenue_funnel_control.engine", "compile", str(inp), str(out)]
            cp = subprocess.run(cmd, check=False, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
            verify = subprocess.run(
                [sys.executable, "-m", "revenue.revenue_funnel_control.engine", "verify", str(out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)
            self.assertEqual(json.loads(verify.stdout), {"valid": True})
            second = subprocess.run(cmd, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertTrue(out.exists())

    def test_cli_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "in.json"
            out = root / "out.json"
            inp.write_text('{"schema":"TJL_REVENUE_FUNNEL_V1","schema":"x"}', encoding="utf-8")
            cp = subprocess.run(
                [sys.executable, "-m", "revenue.revenue_funnel_control.engine", "compile", str(inp), str(out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(cp.returncode, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
