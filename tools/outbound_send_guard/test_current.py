from __future__ import annotations

import json
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import tools.outbound_send_guard as outbound_package
from tools.outbound_send_guard import current

RECIPIENT = "buyer@example.com"
OFFER = "fixed-proof-001"
NOW = datetime(2026, 9, 14, 4, 55, 0, tzinfo=timezone.utc)


def intent(*, requested_at: str = "2026-09-14T04:54:30Z") -> dict:
    return {
        "schema_version": "outbound-send-intent/v1",
        "intent_id": "intent-current-1",
        "recipient": RECIPIENT,
        "offer_id": OFFER,
        "requested_at": requested_at,
        "route_kind": "email",
    }


def evidence(
    *,
    generated_at: str = "2026-09-14T04:54:20Z",
    mail: list | None = None,
    slack: list | None = None,
    max_age: int = 900,
    max_future: int = 300,
) -> dict:
    return {
        "schema_version": "outbound-send-evidence/v1",
        "generated_at": generated_at,
        "mailbox": {"complete": True, "query_id": "gmail:complete", "messages": list(mail or [])},
        "slack": {"complete": True, "query_id": "slack:complete", "events": list(slack or [])},
        "policy": {
            "cross_offer_cooldown_days": 30,
            "max_evidence_age_seconds": max_age,
            "max_future_skew_seconds": max_future,
        },
    }


def outbound(*, observed_at: str, offer_id: str = OFFER) -> dict:
    return {
        "message_id": "provider-sent-1",
        "direction": "outbound",
        "counterparty": RECIPIENT,
        "observed_at": observed_at,
        "offer_id": offer_id,
    }


def hard_dnr(*, observed_at: str) -> dict:
    return {
        "event_id": "dnr-1",
        "kind": "hard_dnr",
        "recipient": RECIPIENT,
        "observed_at": observed_at,
        "offer_id": None,
        "provider_message_id": None,
    }


def encoded(value: dict, *, indent: int | None = None) -> bytes:
    return json.dumps(value, sort_keys=True, indent=indent).encode("utf-8") + b"\n"


class CurrentGuardTests(unittest.TestCase):
    def test_package_evaluate_is_current_process_clock_boundary(self):
        self.assertIs(outbound_package.evaluate, current.compile_current)

    def compile(self, it: dict | None = None, ev: dict | None = None, *, now: datetime = NOW) -> dict:
        with patch.object(current, "_utc_now", return_value=now):
            return current.compile_current(it or intent(), ev or evidence())

    def verify(self, receipt: dict, it: dict | None = None, ev: dict | None = None, *, now: datetime = NOW) -> dict:
        with patch.object(current, "_utc_now", return_value=now):
            return current.verify_current(it or intent(), ev or evidence(), receipt)

    def test_fresh_complete_snapshot_can_clear_current_preflight(self):
        result = self.compile()
        payload = result["payload"]
        self.assertEqual(payload["mode"], current.MODE_CURRENT)
        self.assertEqual(payload["decision"], "ALLOW_NEW")
        self.assertTrue(payload["current_preflight_clear"])
        self.assertTrue(payload["net_new_send_preflight_clear"])
        self.assertFalse(payload["side_effects_authorized"])
        self.assertEqual(payload["verified_at"], "2026-09-14T04:55:00Z")
        self.assertEqual(payload["valid_until"], "2026-09-14T04:56:00Z")

    def test_matched_stale_intent_and_snapshot_cannot_replay_allow_new(self):
        result = self.compile(
            intent(requested_at="2025-01-01T00:00:10Z"),
            evidence(generated_at="2025-01-01T00:00:00Z", max_age=604800),
        )
        payload = result["payload"]
        self.assertEqual(payload["historical_decision"], "ALLOW_NEW")
        self.assertEqual(payload["decision"], "HOLD")
        self.assertFalse(payload["current_preflight_clear"])
        self.assertIn("evidence snapshot is stale at verifier time", payload["temporal_reasons"])
        self.assertIn("intent request is stale at verifier time", payload["temporal_reasons"])
        self.assertEqual(payload["current_policy"]["max_evidence_age_seconds"], 900)

    def test_matched_future_intent_and_snapshot_fail_closed(self):
        result = self.compile(
            intent(requested_at="2027-01-01T00:00:10Z"),
            evidence(generated_at="2027-01-01T00:00:00Z", max_future=86400),
        )
        payload = result["payload"]
        self.assertEqual(payload["decision"], "HOLD")
        self.assertIn("evidence snapshot is future-dated relative to verifier time", payload["temporal_reasons"])
        self.assertIn("intent request is future-dated relative to verifier time", payload["temporal_reasons"])
        self.assertEqual(payload["current_policy"]["max_future_skew_seconds"], 300)

    def test_fresh_snapshot_with_stale_request_holds(self):
        result = self.compile(
            intent(requested_at="2026-09-14T03:00:00Z"),
            evidence(generated_at="2026-09-14T04:54:20Z", max_age=604800),
        )
        self.assertEqual(result["payload"]["decision"], "HOLD")
        self.assertIn("intent request is stale at verifier time", result["payload"]["temporal_reasons"])

    def test_fresh_request_with_stale_snapshot_holds(self):
        result = self.compile(
            intent(requested_at="2026-09-14T04:54:30Z"),
            evidence(generated_at="2026-09-14T03:00:00Z", max_age=604800),
        )
        self.assertEqual(result["payload"]["decision"], "HOLD")
        self.assertIn("evidence snapshot is stale at verifier time", result["payload"]["temporal_reasons"])

    def test_candidate_policy_can_tighten_but_never_widen_current_ceiling(self):
        widened = self.compile(
            intent(requested_at="2026-09-14T04:00:10Z"),
            evidence(generated_at="2026-09-14T04:00:00Z", max_age=604800),
        )
        self.assertEqual(widened["payload"]["decision"], "HOLD")
        self.assertEqual(widened["payload"]["current_policy"]["max_evidence_age_seconds"], 900)

        tightened = self.compile(
            intent(requested_at="2026-09-14T04:54:30Z"),
            evidence(generated_at="2026-09-14T04:54:20Z", max_age=30),
        )
        self.assertEqual(tightened["payload"]["decision"], "HOLD")
        self.assertEqual(tightened["payload"]["current_policy"]["max_evidence_age_seconds"], 30)

    def test_hard_dnr_remains_terminal_even_when_snapshot_is_stale(self):
        result = self.compile(
            intent(requested_at="2025-01-01T00:00:10Z"),
            evidence(
                generated_at="2025-01-01T00:00:00Z",
                slack=[hard_dnr(observed_at="2024-12-31T23:59:00Z")],
                max_age=604800,
            ),
        )
        self.assertEqual(result["payload"]["historical_decision"], "DO_NOT_RESEND")
        self.assertEqual(result["payload"]["decision"], "DO_NOT_RESEND")
        self.assertFalse(result["payload"]["current_preflight_clear"])

    def test_same_offer_send_remains_do_not_resend(self):
        result = self.compile(ev=evidence(mail=[outbound(observed_at="2026-09-14T04:54:00Z")]))
        self.assertEqual(result["payload"]["decision"], "DO_NOT_RESEND")
        self.assertFalse(result["payload"]["current_preflight_clear"])

    def test_historical_explicit_time_is_permanently_non_authorizing(self):
        result = current.compile_historical_at(intent(), evidence(), historical_at=NOW)
        payload = result["payload"]
        self.assertEqual(payload["mode"], current.MODE_HISTORICAL)
        self.assertEqual(payload["historical_decision"], "ALLOW_NEW")
        self.assertEqual(payload["decision"], "HOLD")
        self.assertFalse(payload["current_preflight_clear"])
        self.assertIn("historical replay cannot authorize", payload["reasons"][0])

    def test_current_receipt_verifies_only_inside_expiry_and_same_semantics(self):
        receipt = self.compile()
        fresh = self.verify(receipt, now=NOW + timedelta(seconds=30))
        self.assertTrue(fresh["payload"]["historical_valid"])
        self.assertFalse(fresh["payload"]["expired"])
        self.assertTrue(fresh["payload"]["current_semantics_match"])
        self.assertTrue(fresh["payload"]["current_preflight_valid"])

        expired = self.verify(receipt, now=NOW + timedelta(seconds=61))
        self.assertTrue(expired["payload"]["historical_valid"])
        self.assertTrue(expired["payload"]["expired"])
        self.assertFalse(expired["payload"]["current_preflight_valid"])
        self.assertIn("receipt is expired", expired["payload"]["reasons"])

    def test_receipt_tamper_and_reseal_does_not_replay(self):
        receipt = self.compile()
        tampered = deepcopy(receipt)
        tampered["payload"]["verified_at"] = "2026-09-14T04:54:59Z"
        tampered["receipt_sha256"] = current.guard.digest_object(tampered["payload"])
        checked = self.verify(tampered, now=NOW)
        self.assertFalse(checked["payload"]["historical_valid"])
        self.assertFalse(checked["payload"]["current_preflight_valid"])

    def test_changed_source_invalidates_bound_receipt(self):
        receipt = self.compile()
        changed = evidence()
        changed["mailbox"]["messages"].append(outbound(observed_at="2026-09-14T04:54:40Z"))
        checked = self.verify(receipt, ev=changed, now=NOW)
        self.assertFalse(checked["payload"]["historical_valid"])
        self.assertFalse(checked["payload"]["current_preflight_valid"])

    def test_exact_byte_mode_hashes_exact_consumed_sources(self):
        ib = encoded(intent(), indent=2)
        eb = encoded(evidence(), indent=4)
        with patch.object(current, "_utc_now", return_value=NOW):
            result = current.compile_current_bytes(ib, eb)
        source = result["payload"]["source"]
        self.assertEqual(source["custody_mode"], "exact_consumed_bytes")
        self.assertEqual(source["byte_custody"]["intent_sha256"], current.guard.digest_bytes(ib))
        self.assertEqual(source["byte_custody"]["evidence_sha256"], current.guard.digest_bytes(eb))
        self.assertFalse(result["payload"]["side_effects_authorized"])

    def test_object_api_detaches_caller_graph_before_engine_use(self):
        it = intent()
        ev = evidence()
        original = deepcopy(ev)
        original_core = current._core

        def core_then_mutate(intent_snapshot, evidence_snapshot, *args, **kwargs):
            result = original_core(intent_snapshot, evidence_snapshot, *args, **kwargs)
            ev["mailbox"]["messages"].append(outbound(observed_at="2026-09-14T04:54:40Z"))
            return result

        with patch.object(current, "_utc_now", return_value=NOW), patch.object(
            current, "_core", side_effect=core_then_mutate
        ):
            result = current.compile_current(it, ev)
        self.assertEqual(result["payload"]["decision"], "ALLOW_NEW")
        self.assertEqual(
            result["payload"]["source"]["evidence_object_sha256"],
            current.guard.digest_object(original),
        )
        self.assertNotEqual(
            result["payload"]["source"]["evidence_object_sha256"],
            current.guard.digest_object(ev),
        )

    def test_cli_uses_process_clock_and_create_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ip = root / "intent.json"
            ep = root / "evidence.json"
            out = root / "receipt.json"
            ip.write_bytes(encoded(intent()))
            ep.write_bytes(encoded(evidence()))
            with patch.object(current, "_utc_now", return_value=NOW):
                rc = current.main(
                    ["compile", "--intent", str(ip), "--evidence", str(ep), "--out", str(out)]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))["payload"]
            self.assertEqual(payload["verified_at"], "2026-09-14T04:55:00Z")
            before = out.read_bytes()
            with patch.object(current, "_utc_now", return_value=NOW):
                second = current.main(
                    ["compile", "--intent", str(ip), "--evidence", str(ep), "--out", str(out)]
                )
            self.assertEqual(second, 2)
            self.assertEqual(out.read_bytes(), before)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_cli_refuses_symlink_input_and_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real_intent = root / "intent-real.json"
            intent_link = root / "intent-link.json"
            ep = root / "evidence.json"
            target = root / "target.json"
            out_link = root / "out-link.json"
            real_intent.write_bytes(encoded(intent()))
            ep.write_bytes(encoded(evidence()))
            target.write_text("sentinel", encoding="utf-8")
            intent_link.symlink_to(real_intent)
            out_link.symlink_to(target)
            with patch.object(current, "_utc_now", return_value=NOW):
                self.assertEqual(
                    current.main(["compile", "--intent", str(intent_link), "--evidence", str(ep)]),
                    2,
                )
                self.assertEqual(
                    current.main(
                        ["compile", "--intent", str(real_intent), "--evidence", str(ep), "--out", str(out_link)]
                    ),
                    2,
                )
            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")


if __name__ == "__main__":
    unittest.main()
