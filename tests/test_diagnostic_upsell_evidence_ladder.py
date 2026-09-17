from __future__ import annotations

import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.diagnostic_upsell_evidence_ladder.ladder import (
    LadderError,
    canonical,
    compile_ladder,
    loads_strict,
    render_markdown,
    verify_ladder,
)

NOW = dt.datetime(2026, 9, 17, 0, 45, tzinfo=dt.timezone.utc)


def h(ch: str) -> str:
    return ch * 64


def diagnostic() -> dict:
    return {
        "schema": "commons.completed-diagnostic/v1",
        "diagnostic_id": "diag-001",
        "source_product": {
            "product_id": "agent-failure-autopsy",
            "version": "2026-09-16",
            "source_ref": "agent-rescue.html",
            "source_sha256": h("1"),
        },
        "completed_at": "2026-09-16T22:00:00Z",
        "buyer_scope": {
            "scope_id": "scope-001",
            "authorized_finding_classes": ["RECOVERY_GAP", "EVIDENCE_GAP"],
            "source_ref": "receipt://scope-001",
            "source_sha256": h("2"),
        },
        "findings": [
            {
                "finding_id": "finding-recovery",
                "finding_class": "RECOVERY_GAP",
                "summary": "Recovery path lacks deterministic replay evidence.",
                "contradicted": False,
                "evidence": [
                    {
                        "evidence_id": "evidence-1",
                        "source_ref": "receipt://diag-001/recovery",
                        "sha256": h("3"),
                        "observed_at": "2026-09-16T21:55:00Z",
                        "valid_through": "2099-12-31T23:59:59Z",
                        "sufficiency": "VERIFIED",
                    }
                ],
            }
        ],
        "holds": [],
    }


def catalog() -> dict:
    return {
        "schema": "commons.owner-review-offer-catalog/v1",
        "catalog_id": "catalog-current-001",
        "source_generation": "commons-main-reference-20260916",
        "source_ref": "revenue/OFFERING_FAMILIES.md",
        "source_sha256": h("4"),
        "observed_at": "2026-09-17T00:30:00Z",
        "valid_through": "2099-12-31T23:59:59Z",
        "offers": [
            {
                "offer_id": "recovery-sprint",
                "version": "2026-09-16",
                "source_ref": "revenue/OFFERING_FAMILIES.md#services",
                "source_sha256": h("5"),
                "state": "CURRENT",
                "commercial_state": "PROPOSED_NOT_ACCEPTED",
                "eligible_source_products": ["agent-failure-autopsy"],
                "match_mode": "ANY",
                "applicable_finding_classes": ["RECOVERY_GAP"],
                "scope": {
                    "objective": "Produce a bounded recovery proof and remediation plan.",
                    "deliverables": ["recovery proof packet", "remediation plan"],
                    "acceptance": ["owner verifies deterministic replay receipt"],
                    "exclusions": ["no production deployment", "no customer-result guarantee"],
                },
                "effort_band": {"min_hours": 12, "max_hours": 30},
                "price": {"currency": "USD", "amount_minor": 1500000, "basis": "catalog fixed-price reference"},
                "priority": 80,
            },
            {
                "offer_id": "unrelated-data-service",
                "version": "2026-09-16",
                "source_ref": "example://unrelated",
                "source_sha256": h("6"),
                "state": "CURRENT",
                "commercial_state": "PROPOSED_NOT_ACCEPTED",
                "eligible_source_products": ["agent-failure-autopsy"],
                "match_mode": "ALL",
                "applicable_finding_classes": ["DATA_LICENSE_GAP"],
                "scope": {
                    "objective": "Unrelated reference offer.",
                    "deliverables": ["reference artifact"],
                    "acceptance": ["owner reviews reference artifact"],
                    "exclusions": ["not automatically selected"],
                },
                "effort_band": {"min_hours": 1, "max_hours": 2},
                "price": {"currency": "USD", "amount_minor": 100, "basis": "reference only"},
                "priority": 1,
            },
        ],
    }


class LadderTests(unittest.TestCase):
    def test_verified_finding_surfaces_owner_review_candidate(self):
        packet = compile_ladder(diagnostic(), catalog(), now=NOW)
        self.assertEqual("OWNER_REVIEW_UPSELL_CANDIDATE", packet["status"])
        self.assertEqual(["recovery-sprint"], [c["offer_id"] for c in packet["candidates"]])
        self.assertEqual("PROPOSED_NOT_ACCEPTED", packet["candidates"][0]["commercial_state"])

    def test_all_authority_false(self):
        packet = compile_ladder(diagnostic(), catalog(), now=NOW)
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_evidence_refs_are_retained(self):
        packet = compile_ladder(diagnostic(), catalog(), now=NOW)
        refs = packet["candidates"][0]["evidence_refs"]
        self.assertEqual("evidence-1", refs[0]["evidence_id"])
        self.assertEqual(h("3"), refs[0]["sha256"])

    def test_no_match_is_no_next_step_not_generic_cross_sell(self):
        c = catalog()
        c["offers"][0]["applicable_finding_classes"] = ["SECURITY_GAP"]
        packet = compile_ladder(diagnostic(), c, now=NOW)
        self.assertEqual("NO_NEXT_STEP", packet["status"])
        self.assertEqual([], packet["candidates"])

    def test_source_product_mismatch_is_no_next_step(self):
        c = catalog()
        c["offers"][0]["eligible_source_products"] = ["different-product"]
        packet = compile_ladder(diagnostic(), c, now=NOW)
        self.assertEqual("NO_NEXT_STEP", packet["status"])

    def test_open_blocking_hold_suppresses_candidate(self):
        d = diagnostic()
        d["holds"] = [{"hold_id": "hold-1", "state": "OPEN", "blocking": True, "reason": "Need retained artifact."}]
        packet = compile_ladder(d, catalog(), now=NOW)
        self.assertEqual("HOLD_UNRESOLVED_BLOCKER", packet["status"])
        self.assertEqual([], packet["candidates"])

    def test_resolved_blocker_does_not_suppress_candidate(self):
        d = diagnostic()
        d["holds"] = [{"hold_id": "hold-1", "state": "RESOLVED", "blocking": True, "reason": "Resolved with retained evidence."}]
        self.assertEqual("OWNER_REVIEW_UPSELL_CANDIDATE", compile_ladder(d, catalog(), now=NOW)["status"])

    def test_partial_evidence_suppresses_candidate(self):
        d = diagnostic()
        d["findings"][0]["evidence"][0]["sufficiency"] = "PARTIAL"
        packet = compile_ladder(d, catalog(), now=NOW)
        self.assertEqual("HOLD_EVIDENCE_INSUFFICIENT", packet["status"])

    def test_stale_evidence_suppresses_candidate(self):
        d = diagnostic()
        d["findings"][0]["evidence"][0]["valid_through"] = "2026-09-17T00:44:59Z"
        packet = compile_ladder(d, catalog(), now=NOW)
        self.assertEqual("HOLD_EVIDENCE_INSUFFICIENT", packet["status"])

    def test_contradiction_suppresses_candidate(self):
        d = diagnostic()
        d["findings"][0]["contradicted"] = True
        packet = compile_ladder(d, catalog(), now=NOW)
        self.assertEqual("HOLD_SCOPE_CONTRADICTION", packet["status"])

    def test_catalog_expiry_suppresses_candidate(self):
        c = catalog()
        c["valid_through"] = "2026-09-17T00:44:59Z"
        packet = compile_ladder(diagnostic(), c, now=NOW)
        self.assertEqual("HOLD_CATALOG_INVALID", packet["status"])

    def test_catalog_generation_predating_completion_holds_source_drift(self):
        c = catalog()
        c["observed_at"] = "2026-09-16T21:59:59Z"
        packet = compile_ladder(diagnostic(), c, now=NOW)
        self.assertEqual("HOLD_SOURCE_DRIFT", packet["status"])

    def test_withdrawn_offer_never_candidate(self):
        c = catalog()
        c["offers"][0]["state"] = "WITHDRAWN"
        self.assertEqual("NO_NEXT_STEP", compile_ladder(diagnostic(), c, now=NOW)["status"])

    def test_non_proposed_offer_state_rejected(self):
        c = catalog()
        c["offers"][0]["commercial_state"] = "ACCEPTED"
        with self.assertRaisesRegex(LadderError, "PROPOSED_NOT_ACCEPTED"):
            compile_ladder(diagnostic(), c, now=NOW)

    def test_finding_outside_buyer_scope_rejected(self):
        d = diagnostic()
        d["findings"][0]["finding_class"] = "SECURITY_GAP"
        with self.assertRaisesRegex(LadderError, "outside buyer-authorized scope"):
            compile_ladder(d, catalog(), now=NOW)

    def test_bool_money_rejected(self):
        c = catalog()
        c["offers"][0]["price"]["amount_minor"] = True
        with self.assertRaisesRegex(LadderError, "expected integer"):
            compile_ladder(diagnostic(), c, now=NOW)

    def test_float_json_rejected(self):
        with self.assertRaisesRegex(LadderError, "floating-point"):
            loads_strict('{"amount":1.5}')

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(LadderError, "duplicate JSON key"):
            loads_strict('{"x":1,"x":2}')

    def test_unknown_field_rejected(self):
        d = diagnostic()
        d["surprise"] = True
        with self.assertRaisesRegex(LadderError, "keys mismatch"):
            compile_ladder(d, catalog(), now=NOW)

    def test_packet_receipt_tamper_rejected(self):
        p = compile_ladder(diagnostic(), catalog(), now=NOW)
        p["receipt_sha256"] = "0" * 64
        with self.assertRaisesRegex(LadderError, "receipt mismatch"):
            verify_ladder(diagnostic(), catalog(), p, now=NOW)

    def test_packet_candidate_tamper_rejected_even_with_old_receipt(self):
        p = compile_ladder(diagnostic(), catalog(), now=NOW)
        p["candidates"][0]["price"]["amount_minor"] += 1
        with self.assertRaises(LadderError):
            verify_ladder(diagnostic(), catalog(), p, now=NOW)

    def test_recomputed_tampered_packet_still_fails_semantic_verifier(self):
        p = compile_ladder(diagnostic(), catalog(), now=NOW)
        p["candidates"][0]["scope"]["objective"] = "Self-authored expansion"
        body = copy.deepcopy(p)
        body.pop("receipt_sha256")
        p["receipt_sha256"] = __import__("hashlib").sha256(canonical(body)).hexdigest()
        with self.assertRaisesRegex(LadderError, "semantic mismatch"):
            verify_ladder(diagnostic(), catalog(), p, now=NOW)

    def test_candidate_replay_after_catalog_expiry_fails_current_verification(self):
        c = catalog()
        c["valid_through"] = "2026-09-18T00:00:00Z"
        p = compile_ladder(diagnostic(), c, now=NOW)
        later = dt.datetime(2026, 9, 19, 0, 0, tzinfo=dt.timezone.utc)
        with self.assertRaisesRegex(LadderError, "candidate no longer current"):
            verify_ladder(diagnostic(), c, p, now=later)

    def test_deterministic_at_same_evaluation_time(self):
        a = compile_ladder(diagnostic(), catalog(), now=NOW)
        b = compile_ladder(copy.deepcopy(diagnostic()), copy.deepcopy(catalog()), now=NOW)
        self.assertEqual(canonical(a), canonical(b))

    def test_priority_orders_candidates_but_does_not_accept_one(self):
        c = catalog()
        second = copy.deepcopy(c["offers"][0])
        second["offer_id"] = "lower-priority-recovery"
        second["source_sha256"] = h("7")
        second["priority"] = 20
        c["offers"].append(second)
        p = compile_ladder(diagnostic(), c, now=NOW)
        self.assertEqual(["recovery-sprint", "lower-priority-recovery"], [x["offer_id"] for x in p["candidates"]])
        self.assertTrue(all(x["selection_authority"] == "OWNER_REVIEW_ONLY" for x in p["candidates"]))

    def test_markdown_keeps_authority_ceiling_visible(self):
        md = render_markdown(compile_ladder(diagnostic(), catalog(), now=NOW))
        self.assertIn("PROPOSED_NOT_ACCEPTED", md)
        self.assertIn("owner-review", md.lower())
        self.assertIn("cash", md.lower())

    def test_cli_compile_verify_and_create_exclusive(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            diag = base / "diagnostic.json"
            cat = base / "catalog.json"
            out = base / "packet.json"
            md = base / "packet.md"
            diag.write_text(json.dumps(diagnostic(), sort_keys=True), encoding="utf-8")
            cat.write_text(json.dumps(catalog(), sort_keys=True), encoding="utf-8")
            cmd = [sys.executable, "-m", "revenue.diagnostic_upsell_evidence_ladder.ladder"]
            cp = subprocess.run(cmd + ["compile", "--diagnostic", str(diag), "--catalog", str(cat), "--out", str(out), "--markdown", str(md)], cwd=root, text=True, capture_output=True)
            self.assertEqual(0, cp.returncode, cp.stderr)
            self.assertIn("OWNER_REVIEW_UPSELL_CANDIDATE", cp.stdout)
            verified = subprocess.run(cmd + ["verify", "--diagnostic", str(diag), "--catalog", str(cat), "--packet", str(out)], cwd=root, text=True, capture_output=True)
            self.assertEqual(0, verified.returncode, verified.stderr)
            self.assertIn("VERIFIED", verified.stdout)
            again = subprocess.run(cmd + ["compile", "--diagnostic", str(diag), "--catalog", str(cat), "--out", str(out)], cwd=root, text=True, capture_output=True)
            self.assertEqual(2, again.returncode)

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_cli_refuses_symlink_input(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real = base / "diagnostic.json"
            link = base / "diagnostic-link.json"
            cat = base / "catalog.json"
            out = base / "packet.json"
            real.write_text(json.dumps(diagnostic()), encoding="utf-8")
            cat.write_text(json.dumps(catalog()), encoding="utf-8")
            link.symlink_to(real)
            cp = subprocess.run([sys.executable, "-m", "revenue.diagnostic_upsell_evidence_ladder.ladder", "compile", "--diagnostic", str(link), "--catalog", str(cat), "--out", str(out)], cwd=root, text=True, capture_output=True)
            self.assertEqual(2, cp.returncode)
            self.assertIn("bounded regular file", cp.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
