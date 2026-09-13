from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from itertools import product
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from revenue_closure.compiler import ContractError, compile_queue, loads_strict


AS_OF = datetime(2026, 9, 13, 8, 0, 0, tzinfo=timezone.utc)


def opportunity(
    opportunity_id: str = "deal-1",
    *,
    qualification: str = "ACTIONABLE",
    contact_state: str = "REPLIED",
    do_not_resend: bool = False,
    last_contact_at: str | None = "2026-09-13T06:00:00Z",
    followup_not_before: str | None = None,
    offer: str = "NONE",
    collection: str = "NONE",
    payment: str = "NONE",
    delivery: str = "NOT_READY",
    settlement: str = "NOT_EARNED",
    payment_timing: str = "BEFORE_DELIVERY",
    requires_delivery_acceptance: bool = True,
    cooldown: int = 3600,
    deadline_at: str | None = "2026-09-20T00:00:00Z",
    value: int = 19900,
):
    contact = {"state": contact_state, "do_not_resend": do_not_resend}
    if last_contact_at is not None:
        contact["last_contact_at"] = last_contact_at
    if followup_not_before is not None:
        contact["followup_not_before"] = followup_not_before
    row = {
        "opportunity_id": opportunity_id,
        "expected_value_cents": value,
        "currency": "USD",
        "qualification": qualification,
        "contact": contact,
        "commercial": {
            "offer": offer,
            "collection": collection,
            "payment": payment,
            "delivery": delivery,
            "settlement": settlement,
        },
        "policy": {
            "followup_cooldown_seconds": cooldown,
            "payment_timing": payment_timing,
            "requires_delivery_acceptance": requires_delivery_acceptance,
        },
    }
    if deadline_at is not None:
        row["deadline_at"] = deadline_at
    return row


def payload(*rows, generated_at="2026-09-13T07:00:00Z", max_age=7200):
    return {
        "schema_version": 1,
        "evidence_generated_at": generated_at,
        "max_age_seconds": max_age,
        "opportunities": list(rows),
    }


def action(row, **kwargs):
    result = compile_queue(payload(row), AS_OF)
    return result["queue"][0]["decision"]["action"]


class StrictContractTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ContractError, "duplicate JSON key"):
            loads_strict('{"schema_version":1,"schema_version":1}')

    def test_non_finite_json_rejected(self):
        with self.assertRaisesRegex(ContractError, "non-finite"):
            loads_strict('{"x":NaN}')

    def test_bool_is_not_integer_money(self):
        row = opportunity()
        row["expected_value_cents"] = True
        with self.assertRaisesRegex(ContractError, "must be an integer"):
            compile_queue(payload(row), AS_OF)

    def test_future_evidence_rejected(self):
        with self.assertRaisesRegex(ContractError, "future"):
            compile_queue(payload(opportunity(), generated_at="2026-09-13T08:00:01Z"), AS_OF)

    def test_duplicate_opportunity_id_rejected(self):
        with self.assertRaisesRegex(ContractError, "duplicate opportunity_id"):
            compile_queue(payload(opportunity("x"), opportunity("x")), AS_OF)

    def test_unknown_key_rejected(self):
        row = opportunity()
        row["mystery"] = 1
        with self.assertRaisesRegex(ContractError, "unsupported keys"):
            compile_queue(payload(row), AS_OF)

    def test_all_commercial_state_combinations_fail_closed_or_emit_known_action(self):
        from revenue_closure import compiler as rc

        valid = 0
        rejected = 0
        for offer, collection, payment, delivery, settlement, timing, requires_acceptance in product(
            sorted(rc.OFFER_STATES),
            sorted(rc.COLLECTION_STATES),
            sorted(rc.PAYMENT_STATES),
            sorted(rc.DELIVERY_STATES),
            sorted(rc.SETTLEMENT_STATES),
            sorted(rc.PAYMENT_TIMINGS),
            [False, True],
        ):
            row = opportunity(
                offer=offer,
                collection=collection,
                payment=payment,
                delivery=delivery,
                settlement=settlement,
                payment_timing=timing,
                requires_delivery_acceptance=requires_acceptance,
            )
            try:
                result = compile_queue(payload(row), AS_OF)
            except ContractError:
                rejected += 1
                continue
            decision = result["queue"][0]["decision"]
            self.assertIn(decision["action"], rc.ACTION_PRIORITIES)
            valid += 1
        self.assertEqual((valid, rejected), (360, 8280))

    def test_payment_requires_accepted_offer(self):
        row = opportunity(
            offer="SENT",
            collection="ACTIVE",
            payment="PENDING",
        )
        with self.assertRaisesRegex(ContractError, "payment evidence requires ACCEPTED"):
            compile_queue(payload(row), AS_OF)

    def test_settlement_requires_settled_payment(self):
        row = opportunity(
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="AUTHORIZED",
            delivery="ACCEPTED",
            settlement="SETTLED",
        )
        with self.assertRaisesRegex(ContractError, "SETTLED revenue requires SETTLED payment"):
            compile_queue(payload(row), AS_OF)


class DecisionTests(unittest.TestCase):
    def test_stale_evidence_holds_everything(self):
        row = opportunity()
        result = compile_queue(
            payload(row, generated_at="2026-09-12T00:00:00Z", max_age=3600),
            AS_OF,
        )
        self.assertFalse(result["authoritative"])
        self.assertEqual(result["queue"][0]["decision"]["action"], "HOLD_STALE_EVIDENCE")
        self.assertFalse(result["queue"][0]["decision"]["action_ready"])

    def test_reject_stops(self):
        self.assertEqual(action(opportunity(qualification="REJECT")), "STOP_REJECTED")

    def test_hold_stops(self):
        self.assertEqual(action(opportunity(qualification="HOLD")), "HOLD_QUALIFICATION")

    def test_deadline_passed_stops(self):
        self.assertEqual(
            action(opportunity(deadline_at="2026-09-13T07:59:59Z")),
            "STOP_DEADLINE_PASSED",
        )

    def test_hard_dnr_stops_no_response(self):
        self.assertEqual(
            action(
                opportunity(
                    contact_state="SENT_NO_RESPONSE",
                    do_not_resend=True,
                    offer="NONE",
                )
            ),
            "STOP_DNR",
        )

    def test_reply_can_continue_despite_transport_dnr(self):
        self.assertEqual(
            action(opportunity(contact_state="REPLIED", do_not_resend=True)),
            "QUOTE_READY",
        )

    def test_never_contacted_is_initial_contact(self):
        self.assertEqual(
            action(
                opportunity(
                    contact_state="NEVER_CONTACTED",
                    last_contact_at=None,
                )
            ),
            "INITIAL_CONTACT_READY",
        )

    def test_bounce_requires_route_repair(self):
        self.assertEqual(action(opportunity(contact_state="BOUNCED")), "CONTACT_ROUTE_REPAIR")

    def test_no_response_waits_for_cooldown(self):
        row = opportunity(
            contact_state="SENT_NO_RESPONSE",
            last_contact_at="2026-09-13T07:30:00Z",
            cooldown=3600,
        )
        result = compile_queue(payload(row), AS_OF)["queue"][0]["decision"]
        self.assertEqual(result["action"], "WAIT_FOLLOWUP")
        self.assertEqual(result["not_before"], "2026-09-13T08:30:00Z")

    def test_explicit_not_before_can_extend_cooldown(self):
        row = opportunity(
            contact_state="SENT_NO_RESPONSE",
            last_contact_at="2026-09-13T05:00:00Z",
            followup_not_before="2026-09-13T09:00:00Z",
            cooldown=3600,
        )
        result = compile_queue(payload(row), AS_OF)["queue"][0]["decision"]
        self.assertEqual(result["action"], "WAIT_FOLLOWUP")
        self.assertEqual(result["not_before"], "2026-09-13T09:00:00Z")

    def test_no_response_can_be_followed_after_fence(self):
        self.assertEqual(
            action(
                opportunity(
                    contact_state="SENT_NO_RESPONSE",
                    last_contact_at="2026-09-13T06:00:00Z",
                    cooldown=3600,
                )
            ),
            "FOLLOW_UP_READY",
        )

    def test_quote_states(self):
        self.assertEqual(action(opportunity(offer="NONE")), "QUOTE_READY")
        self.assertEqual(action(opportunity(offer="DRAFT")), "QUOTE_READY")
        self.assertEqual(action(opportunity(offer="SENT")), "AWAIT_QUOTE_DECISION")
        self.assertEqual(action(opportunity(offer="EXPIRED")), "REQUOTE_READY")
        self.assertEqual(action(opportunity(offer="REJECTED")), "CLOSED_LOST")

    def test_accepted_offer_needs_collection_rail(self):
        self.assertEqual(
            action(opportunity(offer="ACCEPTED", collection="NONE")),
            "COLLECTION_RAIL_REQUIRED",
        )
        self.assertEqual(
            action(opportunity(offer="ACCEPTED", collection="READY")),
            "ACTIVATE_COLLECTION_RAIL",
        )

    def test_payment_before_delivery_flow(self):
        base = dict(offer="ACCEPTED", collection="ACTIVE")
        self.assertEqual(action(opportunity(**base, payment="NONE")), "REQUEST_PAYMENT")
        self.assertEqual(action(opportunity(**base, payment="PENDING")), "AWAIT_PAYMENT")
        self.assertEqual(action(opportunity(**base, payment="AUTHORIZED")), "AWAIT_PAYMENT")
        self.assertEqual(action(opportunity(**base, payment="FAILED")), "PAYMENT_RECOVERY")
        self.assertEqual(
            action(opportunity(**base, payment="SETTLED", delivery="NOT_READY")),
            "PREPARE_DELIVERY",
        )
        self.assertEqual(
            action(opportunity(**base, payment="SETTLED", delivery="READY")),
            "FULFILLMENT_READY",
        )
        self.assertEqual(
            action(opportunity(**base, payment="SETTLED", delivery="DELIVERED")),
            "AWAIT_DELIVERY_ACCEPTANCE",
        )

    def test_after_delivery_policy_delivers_before_payment(self):
        row = opportunity(
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="NONE",
            delivery="READY",
            payment_timing="AFTER_DELIVERY",
        )
        self.assertEqual(action(row), "FULFILLMENT_READY")

    def test_accepted_delivery_requires_earned_evidence(self):
        # Contract rejects ACCEPTED+NOT_EARNED, so DELIVERED with optional acceptance
        # is the state where earned evidence can still legitimately be absent.
        row = opportunity(
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="SETTLED",
            delivery="DELIVERED",
            settlement="NOT_EARNED",
            requires_delivery_acceptance=False,
        )
        self.assertEqual(action(row), "EARNINGS_EVIDENCE_REQUIRED")

    def test_earned_value_is_settlement_pending(self):
        row = opportunity(
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="SETTLED",
            delivery="ACCEPTED",
            settlement="EARNED",
        )
        self.assertEqual(action(row), "SETTLEMENT_PENDING")

    def test_settled_value_is_closed_won(self):
        row = opportunity(
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="SETTLED",
            delivery="ACCEPTED",
            settlement="SETTLED",
        )
        self.assertEqual(action(row), "CLOSED_WON")

    def test_refund_is_closed_reversed(self):
        row = opportunity(
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="REFUNDED",
            delivery="DELIVERED",
            settlement="REVERSED",
        )
        self.assertEqual(action(row), "CLOSED_REVERSED")

    def test_terminal_money_truth_outranks_expired_deadline_and_dnr(self):
        row = opportunity(
            contact_state="SENT_NO_RESPONSE",
            do_not_resend=True,
            offer="ACCEPTED",
            collection="ACTIVE",
            payment="SETTLED",
            delivery="ACCEPTED",
            settlement="SETTLED",
            deadline_at="2026-09-12T00:00:00Z",
        )
        self.assertEqual(action(row), "CLOSED_WON")

    def test_explicit_rejection_outranks_contact_dnr(self):
        row = opportunity(
            contact_state="SENT_NO_RESPONSE",
            do_not_resend=True,
            offer="REJECTED",
        )
        self.assertEqual(action(row), "CLOSED_LOST")


class QueueTests(unittest.TestCase):
    def test_priority_deadline_value_and_id_are_deterministic(self):
        rows = [
            opportunity(
                "followup-low",
                contact_state="SENT_NO_RESPONSE",
                last_contact_at="2026-09-13T05:00:00Z",
                cooldown=0,
                value=100,
            ),
            opportunity(
                "payment-late",
                offer="ACCEPTED",
                collection="ACTIVE",
                payment="NONE",
                deadline_at="2026-09-19T00:00:00Z",
                value=50000,
            ),
            opportunity(
                "payment-soon",
                offer="ACCEPTED",
                collection="ACTIVE",
                payment="NONE",
                deadline_at="2026-09-18T00:00:00Z",
                value=100,
            ),
        ]
        result = compile_queue(payload(*rows), AS_OF)
        self.assertEqual(
            [r["opportunity_id"] for r in result["queue"]],
            ["payment-soon", "payment-late", "followup-low"],
        )

    def test_actionable_value_excludes_wait_and_closed(self):
        rows = [
            opportunity(
                "pay",
                offer="ACCEPTED",
                collection="ACTIVE",
                payment="NONE",
                value=10000,
            ),
            opportunity(
                "wait",
                contact_state="SENT_NO_RESPONSE",
                last_contact_at="2026-09-13T07:59:00Z",
                cooldown=3600,
                value=90000,
            ),
            opportunity("reject", qualification="REJECT", value=50000),
        ]
        result = compile_queue(payload(*rows), AS_OF)
        self.assertEqual(result["summary"]["actionable_value_cents_by_currency"], {"USD": 10000})

    def test_digest_is_input_order_independent_for_object_keys(self):
        a = payload(opportunity())
        b = json.loads(json.dumps(a))
        row = b["opportunities"][0]
        b["opportunities"][0] = {key: row[key] for key in reversed(list(row.keys()))}
        self.assertEqual(
            compile_queue(a, AS_OF)["input_sha256"],
            compile_queue(b, AS_OF)["input_sha256"],
        )

    def test_cli_writes_atomic_json_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "input.json"
            out = td / "result.json"
            inp.write_text(json.dumps(payload(opportunity())), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "compiler.py"),
                    str(inp),
                    "--as-of",
                    "2026-09-13T08:00:00Z",
                    "--output",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            parsed = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(parsed["kind"], "REVENUE_CLOSURE_QUEUE")
            self.assertFalse((td / ".result.json.tmp").exists())

    def test_cli_invalid_input_returns_two_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "input.json"
            out = td / "result.json"
            inp.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "compiler.py"),
                    str(inp),
                    "--as-of",
                    "2026-09-13T08:00:00Z",
                    "--output",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("duplicate JSON key", proc.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
