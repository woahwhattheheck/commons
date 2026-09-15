from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import revenue.revenue_targeting_allocator.allocator as allocator_module
from revenue.revenue_targeting_allocator.allocator import (
    AllocationError,
    compile_portfolio,
    validate_input,
    verify_bundle,
)

FIXTURE = Path(__file__).with_name("synthetic_portfolio.json")


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def candidate(**changes):
    base = {
        "opportunity_id": "opp-a",
        "offer_id": "offer-a",
        "currency": "USD",
        "commercial_value_minor": 100_000,
        "route_state": "VERIFIED_CLEAR",
        "relationship_state": "CLEAR",
        "collision_state": "CLEAR",
        "freshness_state": "FRESH",
        "buyer_stage": "PUBLIC_FIT",
        "buyer_stage_state": "VERIFIED",
        "fit_state": "STRONG",
        "delivery_state": "READY",
        "evidence_bundle_sha256": digest("base"),
    }
    base.update(changes)
    return base


def document(*rows):
    return {
        "schema": "revenue-targeting-allocator-input/v1",
        "portfolio_id": "test-port",
        "candidates": list(rows),
    }


class AllocatorTests(unittest.TestCase):
    def test_fixture_compiles(self):
        raw = json.loads(FIXTURE.read_text())
        out, md, receipt = compile_portfolio(raw)
        self.assertEqual(out["counts"], {"total": 4, "expected_value": 2, "evidence_strength": 1, "hold": 1})
        self.assertIn("RELATIONSHIP_DNR", md)
        self.assertFalse(receipt["payment_or_revenue_inferred"])

    def test_input_order_does_not_change_output(self):
        a = candidate(opportunity_id="opp-a", probability_bps=2500, evidence_bundle_sha256=digest("a"))
        b = candidate(opportunity_id="opp-b", probability_bps=5000, evidence_bundle_sha256=digest("b"))
        out1, md1, _ = compile_portfolio(document(a, b))
        out2, md2, _ = compile_portfolio(document(b, a))
        self.assertEqual(out1, out2)
        self.assertEqual(md1, md2)

    def test_expected_value_integer_ranking(self):
        a = candidate(opportunity_id="opp-a", commercial_value_minor=1001, probability_bps=5000, evidence_bundle_sha256=digest("a"))
        b = candidate(opportunity_id="opp-b", commercial_value_minor=800, probability_bps=7000, evidence_bundle_sha256=digest("b"))
        out, _, _ = compile_portfolio(document(a, b))
        rows = [r for r in out["rows"] if r["queue"] == "EXPECTED_VALUE"]
        self.assertEqual([r["opportunity_id"] for r in rows], ["opp-b", "opp-a"])
        self.assertEqual([r["expected_value_minor"] for r in rows], [560, 500])

    def test_missing_probability_never_invented(self):
        out, _, _ = compile_portfolio(document(candidate()))
        row = out["rows"][0]
        self.assertEqual(row["queue"], "EVIDENCE_STRENGTH")
        self.assertIsNone(row["probability_bps"])
        self.assertIsNone(row["expected_value_minor"])

    def test_mixed_currency_never_fx_compared(self):
        usd = candidate(opportunity_id="usd", currency="USD", probability_bps=5000, evidence_bundle_sha256=digest("usd"))
        eur = candidate(opportunity_id="eur", currency="EUR", probability_bps=5000, evidence_bundle_sha256=digest("eur"))
        out, md, _ = compile_portfolio(document(usd, eur))
        self.assertEqual({r["currency"] for r in out["rows"]}, {"USD", "EUR"})
        self.assertTrue(all(r["rank"] == 1 for r in out["rows"]))
        self.assertIn("never converted", md)

    def assertHold(self, **changes):
        out, _, _ = compile_portfolio(document(candidate(**changes)))
        row = out["rows"][0]
        self.assertEqual(row["queue"], "HOLD")
        self.assertTrue(row["hold_reasons"])
        self.assertIsNone(row["rank"])
        return row

    def test_dnr_holds(self):
        self.assertIn("RELATIONSHIP_DNR", self.assertHold(relationship_state="DNR")["hold_reasons"])

    def test_optout_holds(self):
        self.assertIn("RELATIONSHIP_OPTOUT", self.assertHold(relationship_state="OPTOUT")["hold_reasons"])

    def test_unknown_route_holds(self):
        self.assertIn("ROUTE_UNKNOWN", self.assertHold(route_state="UNKNOWN")["hold_reasons"])

    def test_foreign_collision_holds(self):
        self.assertIn("COLLISION_OWNED_OTHER", self.assertHold(collision_state="OWNED_OTHER")["hold_reasons"])

    def test_stale_evidence_holds(self):
        self.assertIn("EVIDENCE_STALE", self.assertHold(freshness_state="STALE")["hold_reasons"])

    def test_buyer_stage_conflict_holds(self):
        self.assertIn("BUYER_STAGE_CONFLICT", self.assertHold(buyer_stage_state="CONFLICT")["hold_reasons"])

    def test_unknown_fit_holds(self):
        self.assertIn("FIT_UNKNOWN", self.assertHold(fit_state="UNKNOWN")["hold_reasons"]

    def test_delivery_hold_holds(self):
        self.assertIn("DELIVERY_HOLD", self.assertHold(delivery_state="HOLD")["hold_reasons"])

    def test_nonpositive_value_holds(self):
        self.assertIn("NON_POSITIVE_COMMERCIAL_VALUE", self.assertHold(commercial_value_minor=0)["hold_reasons"])

    def test_zero_explicit_probability_is_preserved_not_invented(self):
        out, _, _ = compile_portfolio(document(candidate(probability_bps=0)))
        row = out["rows"][0]
        self.assertEqual(row["queue"], "EXPECTED_VALUE")
        self.assertEqual(row["expected_value_minor"], 0)

    def test_duplicate_pair_rejected(self):
        c = candidate()
        with self.assertRaisesRegex(AllocationError, "duplicate opportunity/offer"):
            validate_input(document(c, copy.deepcopy(c)))

    def test_offer_switch_same_opportunity_rejected(self):
        a = candidate(offer_id="offer-a", evidence_bundle_sha256=digest("a"))
        b = candidate(offer_id="offer-b", evidence_bundle_sha256=digest("b"))
        with self.assertRaisesRegex(AllocationError, "cannot switch offers"):
            validate_input(document(a, b))

    def test_unknown_candidate_key_rejected(self):
        c = candidate()
        c["sales_magic"] = True
        with self.assertRaisesRegex(AllocationError, "unknown keys"):
            validate_input(document(c))

    def test_bool_is_not_integer_money(self):
        with self.assertRaisesRegex(AllocationError, "integer minor units"):
            validate_input(document(candidate(commercial_value_minor=True)))

    def test_probability_bounds(self):
        with self.assertRaisesRegex(AllocationError, "0..10000"):
            validate_input(document(candidate(probability_bps=10001)))

    def test_receipt_verifies_exact_semantics(self):
        doc = document(candidate(probability_bps=4000))
        out, md, receipt = compile_portfolio(doc)
        verified = verify_bundle(doc, out, md, receipt)
        self.assertTrue(verified["valid"])
        self.assertFalse(verified["external_send_authorized"])

    def test_tampered_output_rejected(self):
        doc = document(candidate(probability_bps=4000))
        out, md, receipt = compile_portfolio(doc)
        out["rows"][0]["commercial_value_minor"] += 1
        with self.assertRaisesRegex(AllocationError, "output semantic"):
            verify_bundle(doc, out, md, receipt)

    def test_tampered_markdown_rejected(self):
        doc = document(candidate())
        out, md, receipt = compile_portfolio(doc)
        with self.assertRaisesRegex(AllocationError, "markdown semantic"):
            verify_bundle(doc, out, md + "tamper", receipt)

    def test_tampered_receipt_rejected(self):
        doc = document(candidate())
        out, md, receipt = compile_portfolio(doc)
        receipt["counts"]["total"] += 1
        with self.assertRaisesRegex(AllocationError, "receipt semantic"):
            verify_bundle(doc, out, md, receipt)

    def test_every_authority_flag_false(self):
        out, _, receipt = compile_portfolio(document(candidate()))
        for key in ("external_send_authorized", "provider_mutation_authorized", "payment_or_revenue_inferred"):
            self.assertIs(out[key], False)
            self.assertIs(receipt[key], False)
            self.assertIs(out["rows"][0][key], False)

    def test_cli_compile_verify_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            outdir = Path(td) / "out"
            env = dict(os.environ)
            repo_root = Path(__file__).resolve().parents[2]
            env["PYTHONPATH"] = str(repo_root)
            compile_run = subprocess.run(
                [sys.executable, "-m", "revenue.revenue_targeting_allocator.cli", "compile", str(FIXTURE), "--output-dir", str(outdir)],
                cwd=repo_root, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            verify_run = subprocess.run(
                [sys.executable, "-m", "revenue.revenue_targeting_allocator.cli", "verify", str(FIXTURE), "--output-dir", str(outdir)],
                cwd=repo_root, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(verify_run.returncode, 0, verify_run.stderr)
            duplicate = subprocess.run(
                [sys.executable, "-m", "revenue.revenue_targeting_allocator.cli", "compile", str(FIXTURE), "--output-dir", str(outdir)],
                cwd=repo_root, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(duplicate.returncode, 2)
            self.assertIn("File exists", duplicate.stderr)


    def test_ordinary_policy_global_rebinding_does_not_retarget_compiler(self):
        originals = {
            "STAGE_POINTS": allocator_module.STAGE_POINTS,
            "ROUTE_STATES": allocator_module.ROUTE_STATES,
            "CURRENCY_RE": allocator_module.CURRENCY_RE,
            "AUTHORITY_FALSE": allocator_module.AUTHORITY_FALSE,
        }
        try:
            allocator_module.STAGE_POINTS = {"PUBLIC_FIT": 999999}
            allocator_module.ROUTE_STATES = {"UNKNOWN"}
            allocator_module.CURRENCY_RE = allocator_module.re.compile(r"XXX")
            allocator_module.AUTHORITY_FALSE = {
                "external_send_authorized": True,
                "provider_mutation_authorized": True,
                "payment_or_revenue_inferred": True,
            }
            out, _, receipt = compile_portfolio(document(candidate()))
            row = out["rows"][0]
            self.assertEqual(row["stage_points"], 100)
            self.assertEqual(row["queue"], "EVIDENCE_STRENGTH")
            self.assertFalse(row["external_send_authorized"])
            self.assertFalse(out["external_send_authorized"])
            self.assertFalse(receipt["external_send_authorized"])
        finally:
            for name, value in originals.items():
                setattr(allocator_module, name, value)

    def test_duplicate_json_key_cli_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            env = dict(os.environ)
            repo_root = Path(__file__).resolve().parents[2]
            env["PYTHONPATH"] = str(repo_root)
            run = subprocess.run(
                [sys.executable, "-m", "revenue.revenue_targeting_allocator.cli", "compile", str(bad), "--output-dir", str(Path(td)/"out")],
                cwd=repo_root, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(run.returncode, 2)
            self.assertIn("duplicate JSON key", run.stderr)


if __name__ == "__main__":
    unittest.main()
