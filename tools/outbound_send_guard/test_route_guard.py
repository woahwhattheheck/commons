from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.outbound_send_guard import route_guard


NOW = "2026-09-13T15:30:00Z"
OLD = "2026-08-01T12:00:00Z"
OLDER = "2026-07-01T12:00:00Z"
BUYER = "buyer@example.com"
SOURCE_SHA = "a" * 64


class RouteGuardTests(unittest.TestCase):
    def intent(self, *, offer: str = "offer-new") -> dict[str, object]:
        return {
            "schema_version": "outbound-send-intent/v1",
            "intent_id": "intent-route-compose-1",
            "recipient": BUYER,
            "offer_id": offer,
            "requested_at": NOW,
            "route_kind": "email",
        }

    def evidence(
        self,
        *,
        outbound: bool = True,
        outbound_time: str = OLD,
        outbound_offer: str = "offer-old",
        inbound_time: str | None = None,
        slack_only_newer: bool = False,
    ) -> dict[str, object]:
        messages: list[dict[str, object]] = []
        if outbound:
            messages.append(
                {
                    "message_id": "provider-old",
                    "direction": "outbound",
                    "counterparty": BUYER,
                    "observed_at": outbound_time,
                    "offer_id": outbound_offer,
                }
            )
        if inbound_time is not None:
            messages.append(
                {
                    "message_id": "provider-inbound",
                    "direction": "inbound",
                    "counterparty": BUYER,
                    "observed_at": inbound_time,
                    "offer_id": None,
                }
            )
        slack_events: list[dict[str, object]] = []
        if slack_only_newer:
            slack_events.append(
                {
                    "event_id": "slack-newer-send",
                    "kind": "sent",
                    "recipient": BUYER,
                    "observed_at": OLD,
                    "offer_id": "offer-old-2",
                    "provider_message_id": None,
                }
            )
        return {
            "schema_version": "outbound-send-evidence/v1",
            "generated_at": NOW,
            "mailbox": {
                "complete": True,
                "query_id": "mail-query-1",
                "messages": messages,
            },
            "slack": {
                "complete": True,
                "query_id": "slack-query-1",
                "events": slack_events,
            },
            "policy": {
                "cross_offer_cooldown_days": 30,
                "max_evidence_age_seconds": 900,
                "max_future_skew_seconds": 300,
            },
        }

    def route(
        self,
        *,
        decision_kind: str = "unconfirmed",
        recipient: str = BUYER,
        provider_message_id: str = "provider-old",
        sent_at: str = OLD,
        as_of: str = NOW,
    ) -> dict[str, object]:
        events: list[dict[str, object]] = []
        if decision_kind == "block":
            events.append(
                {
                    "event_id": "dsn-block-1",
                    "kind": "dsn",
                    "provider_message_id": provider_message_id,
                    "recipient": recipient,
                    "observed_at": "2026-08-01T12:05:00Z",
                    "source_id": "source-block-1",
                    "source_sha256": SOURCE_SHA,
                    "smtp_code": 550,
                    "enhanced_status": "5.1.1",
                }
            )
        elif decision_kind == "hold":
            events.append(
                {
                    "event_id": "dsn-hold-1",
                    "kind": "dsn",
                    "provider_message_id": provider_message_id,
                    "recipient": recipient,
                    "observed_at": "2026-08-01T12:05:00Z",
                    "source_id": "source-hold-1",
                    "source_sha256": SOURCE_SHA,
                    "smtp_code": 550,
                    "enhanced_status": "5.4.1",
                }
            )
        elif decision_kind == "temporary":
            events.append(
                {
                    "event_id": "dsn-temp-1",
                    "kind": "dsn",
                    "provider_message_id": provider_message_id,
                    "recipient": recipient,
                    "observed_at": "2026-08-01T12:05:00Z",
                    "source_id": "source-temp-1",
                    "source_sha256": SOURCE_SHA,
                    "smtp_code": 450,
                    "enhanced_status": "4.2.2",
                }
            )
        elif decision_kind == "delivered":
            events.append(
                {
                    "event_id": "delivered-1",
                    "kind": "delivered",
                    "provider_message_id": provider_message_id,
                    "recipient": recipient,
                    "observed_at": "2026-08-01T12:05:00Z",
                    "source_id": "source-delivered-1",
                    "source_sha256": SOURCE_SHA,
                    "smtp_code": None,
                    "enhanced_status": None,
                }
            )
        elif decision_kind == "conflict":
            events.extend(
                [
                    {
                        "event_id": "dsn-block-1",
                        "kind": "dsn",
                        "provider_message_id": provider_message_id,
                        "recipient": recipient,
                        "observed_at": "2026-08-01T12:05:00Z",
                        "source_id": "source-block-1",
                        "source_sha256": SOURCE_SHA,
                        "smtp_code": 550,
                        "enhanced_status": "5.1.1",
                    },
                    {
                        "event_id": "delivered-1",
                        "kind": "delivered",
                        "provider_message_id": provider_message_id,
                        "recipient": recipient,
                        "observed_at": "2026-08-01T12:06:00Z",
                        "source_id": "source-delivered-1",
                        "source_sha256": "b" * 64,
                        "smtp_code": None,
                        "enhanced_status": None,
                    },
                ]
            )
        elif decision_kind != "unconfirmed":
            raise AssertionError(decision_kind)
        return {
            "schema_version": "outbound-route-lifecycle-evidence/v1",
            "capture_id": "route-capture-1",
            "recipient": recipient,
            "provider_message_id": provider_message_id,
            "sent_at": sent_at,
            "as_of": as_of,
            "complete": True,
            "next_cursor": None,
            "query_id": "route-query-1",
            "events": events,
        }

    def test_block_route_demotes_allow_new_to_do_not_resend(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="block"))
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "ALLOW_NEW")
        self.assertEqual(receipt["payload"]["route_lifecycle"]["decision"], "BLOCK_ROUTE")
        self.assertEqual(receipt["payload"]["decision"], "DO_NOT_RESEND")
        self.assertFalse(receipt["payload"]["side_effects_authorized"])

    def test_nonallowlisted_permanent_failure_demotes_to_hold(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="hold"))
        self.assertEqual(receipt["payload"]["route_lifecycle"]["decision"], "HOLD_ROUTE")
        self.assertEqual(receipt["payload"]["decision"], "HOLD")

    def test_temporary_failure_demotes_to_hold(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="temporary"))
        self.assertEqual(receipt["payload"]["decision"], "HOLD")

    def test_delivered_route_never_promotes_but_preserves_allow_new(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="delivered"))
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "ALLOW_NEW")
        self.assertEqual(receipt["payload"]["decision"], "ALLOW_NEW")

    def test_unconfirmed_complete_route_preserves_allow_new(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), self.route())
        self.assertEqual(receipt["payload"]["route_lifecycle"]["decision"], "UNCONFIRMED")
        self.assertEqual(receipt["payload"]["decision"], "ALLOW_NEW")

    def test_missing_route_evidence_holds_send_capable_prior_route(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), None)
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "ALLOW_NEW")
        self.assertTrue(receipt["payload"]["route_lifecycle"]["required"])
        self.assertEqual(receipt["payload"]["route_lifecycle"]["status"], "MISSING")
        self.assertEqual(receipt["payload"]["decision"], "HOLD")
        self.assertEqual(receipt["payload"]["authority"], "partial")

    def test_brand_new_recipient_needs_no_route_evidence(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(outbound=False), None)
        self.assertEqual(receipt["payload"]["decision"], "ALLOW_NEW")
        self.assertFalse(receipt["payload"]["route_lifecycle"]["required"])
        self.assertEqual(receipt["payload"]["route_lifecycle"]["status"], "NOT_APPLICABLE")

    def test_irrelevant_route_evidence_without_prior_outbound_is_rejected(self) -> None:
        with self.assertRaisesRegex(route_guard.ComposeError, "no prior outbound"):
            route_guard.evaluate(self.intent(), self.evidence(outbound=False), self.route())

    def test_route_provider_message_must_match_latest_outbound(self) -> None:
        with self.assertRaisesRegex(route_guard.ComposeError, "latest provider message"):
            route_guard.evaluate(
                self.intent(),
                self.evidence(),
                self.route(provider_message_id="provider-other"),
            )

    def test_route_recipient_must_match_intent_route(self) -> None:
        with self.assertRaisesRegex(route_guard.ComposeError, "recipient does not match"):
            route_guard.evaluate(
                self.intent(),
                self.evidence(),
                self.route(recipient="other@example.com"),
            )

    def test_route_sent_time_must_match_provider_evidence(self) -> None:
        with self.assertRaisesRegex(route_guard.ComposeError, "sent_at does not match"):
            route_guard.evaluate(
                self.intent(),
                self.evidence(),
                self.route(sent_at="2026-08-01T12:01:00Z"),
            )

    def test_route_snapshot_boundary_must_match_base_snapshot(self) -> None:
        with self.assertRaisesRegex(route_guard.ComposeError, "as_of must equal"):
            route_guard.evaluate(
                self.intent(),
                self.evidence(),
                self.route(as_of="2026-09-13T15:29:59Z"),
            )

    def test_equivalent_timezone_sent_time_is_accepted(self) -> None:
        receipt = route_guard.evaluate(
            self.intent(),
            self.evidence(),
            self.route(sent_at="2026-08-01T08:00:00-04:00", decision_kind="delivered"),
        )
        self.assertEqual(receipt["payload"]["decision"], "ALLOW_NEW")

    def test_conflicting_delivery_and_block_is_unknown_hold(self) -> None:
        receipt = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="conflict"))
        self.assertEqual(receipt["payload"]["route_lifecycle"]["decision"], "HOLD_ROUTE")
        self.assertEqual(receipt["payload"]["decision"], "HOLD")
        self.assertEqual(receipt["payload"]["authority"], "unknown")

    def test_reply_only_is_demoted_by_blocked_route(self) -> None:
        evidence = self.evidence(inbound_time="2026-09-13T15:00:00Z")
        receipt = route_guard.evaluate(self.intent(), evidence, self.route(decision_kind="block"))
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "REPLY_ONLY")
        self.assertEqual(receipt["payload"]["decision"], "DO_NOT_RESEND")
        self.assertIsNone(receipt["payload"]["reply_message_id"])

    def test_base_do_not_resend_is_never_promoted_by_delivery(self) -> None:
        receipt = route_guard.evaluate(
            self.intent(offer="offer-old"),
            self.evidence(outbound_offer="offer-old"),
            self.route(decision_kind="delivered"),
        )
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "DO_NOT_RESEND")
        self.assertEqual(receipt["payload"]["decision"], "DO_NOT_RESEND")

    def test_base_hold_does_not_require_route_evidence(self) -> None:
        evidence = self.evidence(outbound_time="2026-09-10T12:00:00Z")
        receipt = route_guard.evaluate(self.intent(), evidence, None)
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "HOLD")
        self.assertFalse(receipt["payload"]["route_lifecycle"]["required"])
        self.assertEqual(receipt["payload"]["decision"], "HOLD")

    def test_slack_only_latest_send_cannot_be_route_authorized(self) -> None:
        evidence = self.evidence(outbound_time=OLDER, slack_only_newer=True)
        receipt = route_guard.evaluate(self.intent(), evidence, None)
        self.assertEqual(receipt["payload"]["base_guard"]["decision"], "ALLOW_NEW")
        self.assertEqual(
            receipt["payload"]["route_lifecycle"]["status"],
            "PROVIDER_MESSAGE_UNAVAILABLE",
        )
        self.assertEqual(receipt["payload"]["decision"], "HOLD")

    def test_latest_of_two_provider_outbounds_is_the_only_valid_binding(self) -> None:
        evidence = self.evidence(outbound_time=OLDER)
        evidence["mailbox"]["messages"].append(
            {
                "message_id": "provider-newer",
                "direction": "outbound",
                "counterparty": BUYER,
                "observed_at": OLD,
                "offer_id": "offer-middle",
            }
        )
        with self.assertRaisesRegex(route_guard.ComposeError, "latest provider message"):
            route_guard.evaluate(self.intent(), evidence, self.route(provider_message_id="provider-old", sent_at=OLDER))
        good = self.route(provider_message_id="provider-newer", decision_kind="block")
        receipt = route_guard.evaluate(self.intent(), evidence, good)
        self.assertEqual(receipt["payload"]["decision"], "DO_NOT_RESEND")
        self.assertEqual(
            receipt["payload"]["route_lifecycle"]["target_provider_message_id"],
            "provider-newer",
        )

    def test_inputs_are_snapshotted_not_mutated(self) -> None:
        intent = self.intent()
        evidence = self.evidence()
        route = self.route(decision_kind="block")
        before = copy.deepcopy((intent, evidence, route))
        route_guard.evaluate(intent, evidence, route)
        self.assertEqual((intent, evidence, route), before)

    def test_receipt_is_deterministic_and_hash_bound(self) -> None:
        first = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="block"))
        second = route_guard.evaluate(self.intent(), self.evidence(), self.route(decision_kind="block"))
        self.assertEqual(first, second)
        self.assertEqual(len(first["receipt_sha256"]), 64)
        self.assertEqual(len(first["payload"]["base_guard"]["receipt_sha256"]), 64)
        self.assertEqual(len(first["payload"]["route_lifecycle"]["receipt_sha256"]), 64)

    def test_cli_block_exit_code_and_output(self) -> None:
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            intent = tmp / "intent.json"
            evidence = tmp / "evidence.json"
            route = tmp / "route.json"
            out = tmp / "receipt.json"
            intent.write_text(json.dumps(self.intent()), encoding="utf-8")
            evidence.write_text(json.dumps(self.evidence()), encoding="utf-8")
            route.write_text(json.dumps(self.route(decision_kind="block")), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.outbound_send_guard.route_guard",
                    "--intent",
                    str(intent),
                    "--evidence",
                    str(evidence),
                    "--route-evidence",
                    str(route),
                    "--out",
                    str(out),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 5, result.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["payload"]["decision"], "DO_NOT_RESEND")
            self.assertFalse(payload["payload"]["side_effects_authorized"])

    def test_cli_missing_required_route_exits_hold(self) -> None:
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            intent = tmp / "intent.json"
            evidence = tmp / "evidence.json"
            intent.write_text(json.dumps(self.intent()), encoding="utf-8")
            evidence.write_text(json.dumps(self.evidence()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.outbound_send_guard.route_guard",
                    "--intent",
                    str(intent),
                    "--evidence",
                    str(evidence),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 4, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["payload"]["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
