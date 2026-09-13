from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.revenue_proof_ledger.ledger import INPUT_SCHEMA, main, reduce_ledger, render_summary


def dg(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def opportunity(source: str, *, amount="500.00", authority="complete", digest=None):
    return {
        "kind": "opportunity",
        "opportunity_id": "github:acme/widget#42",
        "source": source,
        "authority": authority,
        "evidence_digest": digest or dg("opportunity-" + source),
        "currency": "USD",
        "expected_amount": amount,
        "identity_status": "canonical",
    }


def lookup(scope: str, *, authority="complete", digest=None):
    return {
        "kind": "lookup",
        "opportunity_id": "github:acme/widget#42",
        "source": "reader:" + scope,
        "authority": authority,
        "evidence_digest": digest or dg("lookup-" + scope + authority),
        "scope": scope,
    }


def delivery(*, current=True, state="accepted", amount="500", delivery_id="github:acme/widget@abc"):
    row = {
        "kind": "delivery",
        "opportunity_id": "github:acme/widget#42",
        "delivery_id": delivery_id,
        "source": "github:pull/99",
        "authority": "complete",
        "evidence_digest": dg("delivery-" + delivery_id + state + str(current)),
        "state": state,
        "current": current,
        "currency": "USD",
        "credit": {
            "source_authors": ["Builder-A"],
            "reviewers": ["Reviewer-B"],
            "mergers": ["Merger-C"],
        },
    }
    if state == "accepted":
        row["earned_amount"] = amount
    return row


def settlement(
    settlement_id: str,
    amount: str,
    *,
    movement="payment",
    state="settled",
    delivery_id="github:acme/widget@abc",
    source="payment:stripe",
    authority="complete",
):
    return {
        "kind": "settlement",
        "opportunity_id": "github:acme/widget#42",
        "delivery_id": delivery_id,
        "settlement_id": settlement_id,
        "source": source,
        "authority": authority,
        "evidence_digest": dg(source + settlement_id + movement + amount),
        "movement": movement,
        "state": state,
        "currency": "USD",
        "amount": amount,
    }


def payload(*rows):
    return {"schema": INPUT_SCHEMA, "receipts": list(rows)}


def row(ledger):
    return ledger["opportunities"][0]


class RevenueProofLedgerTests(unittest.TestCase):
    def test_cross_source_opportunity_dedupes_once(self):
        ledger = reduce_ledger(
            payload(
                opportunity("slack:thread"),
                opportunity("github:issue"),
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
            )
        )
        self.assertEqual(len(ledger["opportunities"]), 1)
        self.assertEqual(row(ledger)["pipeline_expected"], "500")
        self.assertEqual(row(ledger)["earned_unsettled"], "500")
        self.assertEqual(row(ledger)["cash_settled"], "0")
        self.assertEqual(row(ledger)["authority"], "complete")

    def test_accepted_without_payment_is_earned_unsettled_only(self):
        ledger = reduce_ledger(
            payload(opportunity("github"), delivery(), lookup("delivery"), lookup("settlement"))
        )
        self.assertEqual(row(ledger)["earned_unsettled"], "500")
        self.assertEqual(row(ledger)["cash_settled"], "0")

    def test_duplicate_identical_settlement_id_counts_once(self):
        first = settlement("stripe:pi_1", "500", source="payment:a")
        duplicate = settlement("stripe:pi_1", "500", source="payment:b")
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                first,
                duplicate,
            )
        )
        self.assertEqual(row(ledger)["cash_settled"], "500")
        self.assertEqual(row(ledger)["settlement_ids"], ["stripe:pi_1"])

    def test_partial_multi_payment_remains_partial(self):
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                settlement("stripe:pi_a", "125.25"),
                settlement("stripe:pi_b", "74.75"),
            )
        )
        self.assertEqual(row(ledger)["cash_settled"], "200")
        self.assertEqual(row(ledger)["earned_unsettled"], "300")

    def test_refund_backs_cash_out_without_erasing_delivery(self):
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                settlement("stripe:pi_1", "500"),
                settlement("stripe:re_1", "125", movement="refund"),
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["cash_settled"], "375")
        self.assertEqual(proof["reversed_or_disputed"], "125")
        self.assertEqual(proof["earned_unsettled"], "125")
        self.assertEqual(proof["delivery_id"], "github:acme/widget@abc")

    def test_unknown_payment_lookup_mints_zero_cash(self):
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                lookup("delivery"),
                lookup("settlement", authority="unknown"),
                settlement("stripe:pi_1", "500"),
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["authority"], "unknown")
        self.assertEqual(proof["observed_net_cash"], "500")
        self.assertEqual(proof["cash_settled"], "0")
        self.assertEqual(proof["earned_unsettled"], "500")

    def test_missing_payment_lookup_is_unknown_and_zero_cash(self):
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                lookup("delivery"),
                settlement("stripe:pi_1", "500"),
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["authority"], "unknown")
        self.assertIn("settlement_lookup_missing", proof["issues"])
        self.assertEqual(proof["cash_settled"], "0")

    def test_credit_lineage_does_not_remint_source_authorship(self):
        duplicate = delivery()
        duplicate["source"] = "github:merge"
        duplicate["evidence_digest"] = dg("delivery-second-source")
        duplicate["credit"] = {
            "source_authors": ["Builder-A"],
            "reviewers": ["Reviewer-B", "Reviewer-D"],
            "mergers": ["Merger-C", "Merger-E"],
        }
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                duplicate,
                lookup("delivery"),
                lookup("settlement"),
            )
        )
        credit = row(ledger)["credit_lineage"]
        self.assertEqual(credit["source_authors"], ["Builder-A"])
        self.assertEqual(credit["reviewers"], ["Reviewer-B", "Reviewer-D"])
        self.assertEqual(credit["mergers"], ["Merger-C", "Merger-E"])

    def test_reused_settlement_identity_fails_closed(self):
        conflicting = settlement("stripe:pi_1", "400")
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                settlement("stripe:pi_1", "500"),
                conflicting,
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["authority"], "unknown")
        self.assertIn("settlement_id_reused:stripe:pi_1", proof["issues"])
        self.assertEqual(proof["cash_settled"], "0")

    def test_settlement_on_superseded_delivery_fails_closed(self):
        old = delivery(current=False, delivery_id="github:acme/widget@old")
        ledger = reduce_ledger(
            payload(
                opportunity("github"),
                old,
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                settlement("stripe:pi_old", "500", delivery_id="github:acme/widget@old"),
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["authority"], "unknown")
        self.assertIn("settlement_on_noncurrent_delivery:stripe:pi_old", proof["issues"])
        self.assertEqual(proof["cash_settled"], "0")

    def test_ambiguous_opportunity_identity_fails_closed(self):
        ambiguous = opportunity("slack")
        ambiguous["identity_status"] = "ambiguous"
        ledger = reduce_ledger(
            payload(
                ambiguous,
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                settlement("stripe:pi_1", "500"),
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["authority"], "unknown")
        self.assertIn("opportunity_identity_ambiguous", proof["issues"])
        self.assertEqual(proof["cash_settled"], "0")

    def test_unknown_receipt_field_is_rejected(self):
        bad = opportunity("github")
        bad["curreny"] = "USD"
        with self.assertRaisesRegex(Exception, "unknown fields: curreny"):
            reduce_ledger(payload(bad))

    def test_amount_mismatch_between_discovery_sources_fails_closed(self):
        ledger = reduce_ledger(
            payload(
                opportunity("slack", amount="500"),
                opportunity("github", amount="450"),
                delivery(),
                lookup("delivery"),
                lookup("settlement"),
                settlement("stripe:pi_1", "500"),
            )
        )
        proof = row(ledger)
        self.assertEqual(proof["authority"], "unknown")
        self.assertIn("opportunity_amount_mismatch", proof["issues"])
        self.assertEqual(proof["pipeline_expected"], "0")
        self.assertEqual(proof["cash_settled"], "0")

    def test_permutation_is_deterministic(self):
        receipts = [
            opportunity("slack"),
            opportunity("github"),
            delivery(),
            lookup("delivery"),
            lookup("settlement"),
            settlement("stripe:pi_a", "200"),
        ]
        left = reduce_ledger(payload(*receipts))
        right = reduce_ledger(payload(*reversed(receipts)))
        self.assertEqual(left, right)
        self.assertEqual(render_summary(left), render_summary(right))

    def test_cli_outputs_are_create_exclusive(self):
        source = payload(
            opportunity("github"), delivery(), lookup("delivery"), lookup("settlement")
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "input.json"
            out = root / "ledger.json"
            summary = root / "ledger.md"
            src.write_text(json.dumps(source), encoding="utf-8")
            self.assertEqual(
                main([str(src), "--json-out", str(out), "--summary-out", str(summary)]),
                0,
            )
            before_json = out.read_bytes()
            before_summary = summary.read_bytes()
            with self.assertRaises(SystemExit) as caught:
                main([str(src), "--json-out", str(out), "--summary-out", str(summary)])
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(out.read_bytes(), before_json)
            self.assertEqual(summary.read_bytes(), before_summary)

    def test_ledger_digest_is_bound_to_content(self):
        ledger = reduce_ledger(
            payload(opportunity("github"), delivery(), lookup("delivery"), lookup("settlement"))
        )
        clone = copy.deepcopy(ledger)
        digest = clone.pop("ledger_digest")
        canonical = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(digest, "sha256:" + hashlib.sha256(canonical).hexdigest())


if __name__ == "__main__":
    unittest.main()
