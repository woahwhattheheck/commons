import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "revenue" / "proposal_validity_expiry_requote_gate"))
import gate

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC)
DIGEST = "a" * 64
DIGEST2 = "b" * 64


def issued_v2():
    return {
        "schema_version": 2,
        "offer_id": "OFFER-001",
        "source_generation": "src-001",
        "source_digest_sha256": DIGEST,
        "pricing_revision": "price-r1",
        "currency": "USD",
        "scope": {"deliverables": ["diagnostic"], "acceptance": ["receipt verified"]},
        "economics": {"fixed_minor_units": 500000, "payment_terms": "Net 15"},
        "issued_on": "2026-09-10T12:00:00Z",
        "validity": {"mode": "VALID_UNTIL", "valid_until": "2026-09-30T23:59:59-04:00"},
        "buyer_deadline": "2026-09-25T14:00:00-04:00",
        "payment_rail": {"checkout_url": "https://example.invalid/checkout-1", "state": "PRESENT"},
    }


def current_v2():
    src = issued_v2()
    return {
        "schema_version": 2,
        "offer_id": src["offer_id"],
        "source_generation": src["source_generation"],
        "source_digest_sha256": src["source_digest_sha256"],
        "source_status": "CURRENT",
        "source_observed_at": "2026-09-17T17:00:00Z",
        "pricing_revision": src["pricing_revision"],
        "currency": src["currency"],
        "scope": copy.deepcopy(src["scope"]),
        "economics": copy.deepcopy(src["economics"]),
        "superseding_events": [],
        "payment_rail": {"checkout_url": "https://example.invalid/checkout-1", "state": "ACTIVE"},
    }


def issued_v1():
    a = issued_v2()
    a["schema_version"] = 1
    del a["source_digest_sha256"]
    return a


def current_v1():
    b = current_v2()
    b["schema_version"] = 1
    for key in ("source_digest_sha256", "source_status", "source_observed_at", "payment_rail"):
        del b[key]
    return b


class GateTests(unittest.TestCase):
    def compile(self, a=None, b=None, now=NOW, basis="TEST_EXPLICIT"):
        return gate._evaluate_at(a or issued_v2(), b or current_v2(), now, _clock_basis=basis)

    def process_packet(self, a=None, b=None, now=NOW):
        with mock.patch.object(gate, "_utc_now", return_value=now):
            return gate.evaluate_offer(a or issued_v2(), b or current_v2())

    def test_current_owner_use_and_authority_is_hard_false(self):
        out = self.compile()
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertEqual(out["clock_basis"], "TEST_EXPLICIT")
        self.assertFalse(out["authority"]["buyer_acceptance"])
        self.assertFalse(out["authority"]["checkout_or_payment_rail_is_acceptance"])
        self.assertFalse(out["authority"]["payment_authorized"])
        self.assertFalse(out["authority"]["revenue_recognized"])
        self.assertFalse(out["authority"]["outbound_authorized"])

    def test_test_clock_packet_cannot_verify_as_current_process_evidence(self):
        self.assertFalse(gate.verify_packet(issued_v2(), current_v2(), self.compile()))

    def test_process_packet_verifies_while_semantics_stable(self):
        packet = self.process_packet()
        with mock.patch.object(gate, "_utc_now", return_value=NOW + dt.timedelta(hours=1)):
            self.assertTrue(gate.verify_packet(issued_v2(), current_v2(), packet))

    def test_legacy_v1_inputs_are_accepted_but_truth_narrowed(self):
        out = self.compile(issued_v1(), current_v1())
        self.assertEqual(out["status"], "HOLD_SOURCE_DRIFT")
        self.assertIn("LEGACY_SOURCE_EVIDENCE_MISSING", out["requote_delta"]["source_currentness_reasons"])

    def test_expired_requires_requote(self):
        self.assertEqual(self.compile(now=dt.datetime(2026, 10, 1, tzinfo=UTC))["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_no_expiry_stated_holds(self):
        a = issued_v2(); a["validity"] = {"mode": "NO_EXPIRY_STATED"}
        self.assertEqual(self.compile(a=a)["status"], "HOLD_NO_VALIDITY_BASIS")

    def test_missing_timezone_fails_closed(self):
        a = issued_v2(); a["validity"] = {"mode": "VALID_UNTIL", "valid_until": "2026-09-30T23:59:59"}
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_source_generation_drift_holds(self):
        b = current_v2(); b["source_generation"] = "src-002"
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_source_digest_drift_holds(self):
        b = current_v2(); b["source_digest_sha256"] = DIGEST2
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_source_status_stale_or_withdrawn_holds(self):
        for status in ("STALE", "WITHDRAWN"):
            with self.subTest(status=status):
                b = current_v2(); b["source_status"] = status
                out = self.compile(b=b)
                self.assertEqual(out["status"], "HOLD_SOURCE_DRIFT")
                self.assertIn("SOURCE_STATUS_" + status, out["requote_delta"]["source_currentness_reasons"])

    def test_source_observation_before_issue_cannot_mint_current(self):
        b = current_v2(); b["source_observed_at"] = "2026-09-09T12:00:00Z"
        out = self.compile(b=b)
        self.assertEqual(out["status"], "HOLD_SOURCE_DRIFT")
        self.assertIn("SOURCE_OBSERVED_BEFORE_ISSUANCE", out["requote_delta"]["source_currentness_reasons"])

    def test_source_observation_in_future_cannot_mint_current(self):
        b = current_v2(); b["source_observed_at"] = "2026-09-18T12:00:00Z"
        out = self.compile(b=b)
        self.assertEqual(out["status"], "HOLD_SOURCE_DRIFT")
        self.assertIn("SOURCE_OBSERVED_IN_FUTURE", out["requote_delta"]["source_currentness_reasons"])

    def test_currency_scope_economics_pricing_drift_supersede(self):
        mutations = [
            ("currency", lambda b: b.__setitem__("currency", "CAD")),
            ("scope", lambda b: b["scope"]["deliverables"].append("implementation")),
            ("economics", lambda b: b["economics"].__setitem__("fixed_minor_units", 600000)),
            ("pricing_revision", lambda b: b.__setitem__("pricing_revision", "price-r2")),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                b = current_v2(); mutate(b)
                self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_all_supersession_event_kinds_after_issue_supersede(self):
        for kind in ("AMENDMENT", "REDLINE", "CHANGE_ORDER", "REPRICE", "WITHDRAWAL"):
            with self.subTest(kind=kind):
                b = current_v2()
                b["source_generation"] = "src-002"
                b["source_digest_sha256"] = DIGEST2
                b["superseding_events"] = [{
                    "kind": kind,
                    "event_id": kind + "-1",
                    "observed_at": "2026-09-12T00:00:00Z",
                    "applies_to_offer_id": "OFFER-001",
                    "source_generation": "src-002",
                    "source_digest_sha256": DIGEST2,
                }]
                self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_pre_issue_relevant_event_does_not_supersede(self):
        b = current_v2()
        b["superseding_events"] = [{
            "kind":"REDLINE", "event_id":"R-0", "observed_at":"2026-09-09T00:00:00Z",
            "applies_to_offer_id":"OFFER-001", "source_generation":"src-001",
            "source_digest_sha256": DIGEST,
        }]
        self.assertEqual(self.compile(b=b)["status"], "CURRENT_FOR_OWNER_USE")

    def test_event_must_bind_current_source_generation_and_digest(self):
        b = current_v2()
        event = {
            "kind":"AMENDMENT", "event_id":"A-1", "observed_at":"2026-09-12T00:00:00Z",
            "applies_to_offer_id":"OFFER-001", "source_generation":"src-X",
            "source_digest_sha256": DIGEST,
        }
        b["superseding_events"] = [event]
        with self.assertRaisesRegex(gate.GateError, "source generation"):
            self.compile(b=b)
        b = current_v2(); event = copy.deepcopy(event); event["source_generation"] = "src-001"; event["source_digest_sha256"] = DIGEST2; b["superseding_events"] = [event]
        with self.assertRaisesRegex(gate.GateError, "source digest"):
            self.compile(b=b)

    def test_event_cannot_postdate_current_source_observation(self):
        b = current_v2(); b["source_observed_at"] = "2026-09-12T00:00:00Z"
        b["superseding_events"] = [{
            "kind":"AMENDMENT", "event_id":"A-1", "observed_at":"2026-09-12T00:00:01Z",
            "applies_to_offer_id":"OFFER-001", "source_generation":"src-001",
            "source_digest_sha256": DIGEST,
        }]
        with self.assertRaisesRegex(gate.GateError, "postdates"):
            self.compile(b=b)

    def test_buyer_deadline_caps_validity(self):
        out = self.compile(now=dt.datetime(2026, 9, 26, tzinfo=UTC))
        self.assertEqual(out["status"], "EXPIRED_REQUOTE_REQUIRED")
        self.assertIn("BUYER_DEADLINE_CAP", out["validity_basis"])
        self.assertIn("BUYER_DEADLINE_PASSED", out["requote_delta"]["time_reasons"])

    def test_stale_or_replaced_payment_rail_holds(self):
        for state in ("INACTIVE", "REPLACED", "WITHDRAWN"):
            with self.subTest(state=state):
                b = current_v2(); b["payment_rail"]["state"] = state
                out = self.compile(b=b)
                self.assertEqual(out["status"], "HOLD_SOURCE_DRIFT")
                self.assertIn("PAYMENT_RAIL_NOT_CURRENT", out["requote_delta"]["source_currentness_reasons"])

    def test_changed_payment_rail_identity_holds(self):
        b = current_v2(); b["payment_rail"]["checkout_url"] = "https://example.invalid/replaced"
        out = self.compile(b=b)
        self.assertEqual(out["status"], "HOLD_SOURCE_DRIFT")
        self.assertIn("PAYMENT_RAIL_IDENTITY_DRIFT", out["requote_delta"]["source_currentness_reasons"])

    def test_packet_clock_injection_is_rejected(self):
        a = issued_v2(); a["as_of"] = "2026-09-11T00:00:00Z"
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_bool_and_float_money_fail_closed(self):
        a = issued_v2(); a["economics"]["fixed_minor_units"] = True
        with self.assertRaises(gate.GateError): self.compile(a=a)
        a = issued_v2(); a["economics"]["fixed_minor_units"] = 5000.5
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_duplicate_nonfinite_float_and_giant_integer_json_are_bounded(self):
        hostile = [
            '{"a":1,"a":2}',
            '{"a":NaN}',
            '{"a":1.5}',
            '{"a":' + ('9' * 5000) + '}',
        ]
        for text in hostile:
            with self.subTest(prefix=text[:20]):
                with self.assertRaises(gate.GateError): gate.strict_json_loads(text)

    def test_lone_surrogate_key_and_value_are_rejected_without_echo(self):
        for text in ('{"\\ud800":1}', '{"a":"\\ud800"}'):
            with self.subTest(text=text):
                with self.assertRaises(gate.GateError) as ctx:
                    gate.strict_json_loads(text)
                self.assertNotIn("\\ud800", str(ctx.exception))

    def test_deep_nesting_is_bounded(self):
        text = '[' * 80 + '0' + ']' * 80
        with self.assertRaises(gate.GateError): gate.strict_json_loads(text)

    def test_verify_rejects_tampered_packet(self):
        out = self.process_packet(); out["status"] = "SUPERSEDED"
        with mock.patch.object(gate, "_utc_now", return_value=NOW):
            self.assertFalse(gate.verify_packet(issued_v2(), current_v2(), out))

    def test_old_current_packet_does_not_verify_after_runtime_expiry(self):
        a = issued_v2(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2026-09-20T00:00:00Z"}
        b = current_v2()
        packet = self.process_packet(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        with mock.patch.object(gate, "_utc_now", return_value=dt.datetime(2026, 9, 21, 0, 0, tzinfo=UTC)):
            self.assertFalse(gate.verify_packet(a, b, packet))

    def test_same_coarse_expired_state_with_new_time_reason_does_not_verify(self):
        a = issued_v2(); a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2026-09-15T00:00:00Z"}; a["buyer_deadline"] = "2026-09-18T00:00:00Z"
        b = current_v2(); b["source_observed_at"] = "2026-09-16T17:00:00Z"
        packet = self.process_packet(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        self.assertEqual(packet["status"], "EXPIRED_REQUOTE_REQUIRED")
        self.assertNotIn("BUYER_DEADLINE_PASSED", packet["requote_delta"]["time_reasons"])
        with mock.patch.object(gate, "_utc_now", return_value=dt.datetime(2026, 9, 19, 0, 0, tzinfo=UTC)):
            self.assertFalse(gate.verify_packet(a, b, packet))

    def test_stable_expired_semantics_can_still_verify(self):
        a = issued_v2(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2026-09-15T00:00:00Z"}
        b = current_v2(); b["source_observed_at"] = "2026-09-16T17:00:00Z"
        packet = self.process_packet(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        with mock.patch.object(gate, "_utc_now", return_value=dt.datetime(2026, 9, 19, 0, 0, tzinfo=UTC)):
            self.assertTrue(gate.verify_packet(a, b, packet))

    def test_valid_for_seconds(self):
        a = issued_v2(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_FOR_SECONDS", "valid_for_seconds":86400}
        b = current_v2(); b["source_observed_at"] = "2026-09-10T13:00:00Z"
        self.assertEqual(self.compile(a=a, b=b, now=dt.datetime(2026,9,10,18,tzinfo=UTC))["status"], "CURRENT_FOR_OWNER_USE")
        self.assertEqual(self.compile(a=a, b=b, now=dt.datetime(2026,9,12,18,tzinfo=UTC))["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_ordinary_datetime_rebinding_cannot_freeze_public_clock(self):
        a = issued_v2(); a["issued_on"] = "2026-01-01T00:00:00Z"; a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2099-01-01T00:00:00Z"}; a["buyer_deadline"] = None
        b = current_v2(); b["source_observed_at"] = "2026-01-02T00:00:00Z"
        original = gate._dt.datetime
        class FakeDateTime(original):
            @classmethod
            def now(cls, tz=None):
                return cls(2020, 1, 1, tzinfo=tz)
        gate._dt.datetime = FakeDateTime
        try:
            out = gate.evaluate_offer(a, b)
        finally:
            gate._dt.datetime = original
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertTrue(out["evaluated_at"].startswith("2026-"))
        self.assertEqual(out["clock_basis"], "PROCESS_UTC")

    def test_cli_compile_verify_no_overwrite_no_as_of_and_bounded_hostile(self):
        a = issued_v2(); a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2099-12-31T00:00:00Z"}; a["buyer_deadline"] = None
        b = current_v2(); b["source_observed_at"] = "2026-09-17T17:00:00Z"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); (td/"issued.json").write_text(json.dumps(a), encoding="utf-8"); (td/"current.json").write_text(json.dumps(b), encoding="utf-8")
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(gate.__file__).parent)
            base = [sys.executable] + (["-O"] if sys.flags.optimize else []) + [gate.__file__]
            cmd = base + ["compile", "--issued", str(td/"issued.json"), "--current", str(td/"current.json"), "--out", str(td/"packet.json")]
            first = subprocess.run(cmd, text=True, capture_output=True, env=env)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            verify = subprocess.run(base + ["verify", "--issued", str(td/"issued.json"), "--current", str(td/"current.json"), "--packet", str(td/"packet.json")], text=True, capture_output=True, env=env)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr); self.assertIn("VERIFIED", verify.stdout)
            second = subprocess.run(cmd, text=True, capture_output=True, env=env)
            self.assertEqual(second.returncode, 2); self.assertIn("refusing to overwrite", second.stdout)
            no_as_of = subprocess.run(cmd + ["--as-of", "2020-01-01T00:00:00Z"], text=True, capture_output=True, env=env)
            self.assertEqual(no_as_of.returncode, 2)
            self.assertNotIn("Traceback", no_as_of.stderr + no_as_of.stdout)
            hostile = json.dumps(a).replace('500000', '9' * 5000)
            (td/"hostile.json").write_text(hostile, encoding="utf-8")
            hostile_run = subprocess.run(base + ["compile", "--issued", str(td/"hostile.json"), "--current", str(td/"current.json"), "--out", str(td/"hostile-out.json")], text=True, capture_output=True, env=env)
            self.assertEqual(hostile_run.returncode, 2)
            self.assertNotIn("Traceback", hostile_run.stderr + hostile_run.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
