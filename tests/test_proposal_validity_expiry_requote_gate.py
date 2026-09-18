import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "revenue" / "proposal_validity_expiry_requote_gate"))
import gate

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 16, 20, 0, tzinfo=UTC)


def issued():
    return {
        "schema_version": 1,
        "offer_id": "OFFER-001",
        "source_generation": "src-001",
        "pricing_revision": "price-r1",
        "currency": "USD",
        "scope": {"deliverables": ["diagnostic"], "acceptance": ["receipt verified"]},
        "economics": {"fixed_minor_units": 500000, "payment_terms": "Net 15"},
        "issued_on": "2026-09-10T12:00:00Z",
        "validity": {"mode": "VALID_UNTIL", "valid_until": "2026-09-30T23:59:59-04:00"},
        "buyer_deadline": "2026-09-25T14:00:00-04:00",
        "payment_rail": {"checkout_url": "https://example.invalid/stale", "state": "PRESENT"},
    }


def current():
    src = issued()
    return {
        "schema_version": 1,
        "offer_id": src["offer_id"],
        "source_generation": src["source_generation"],
        "pricing_revision": src["pricing_revision"],
        "currency": src["currency"],
        "scope": copy.deepcopy(src["scope"]),
        "economics": copy.deepcopy(src["economics"]),
        "superseding_events": [],
    }


class GateTests(unittest.TestCase):
    def compile(self, a=None, b=None, now=NOW):
        return gate._evaluate_at(a or issued(), b or current(), now)

    def test_current_owner_use_and_payment_rail_is_not_acceptance(self):
        out = self.compile()
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertFalse(out["authority"]["buyer_acceptance"])
        self.assertFalse(out["authority"]["checkout_or_payment_rail_is_acceptance"])
        self.assertTrue(gate.verify_packet(issued(), current(), out))

    def test_expired_requires_requote(self):
        self.assertEqual(self.compile(now=dt.datetime(2026, 10, 1, tzinfo=UTC))["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_no_expiry_stated_holds(self):
        a = issued(); a["validity"] = {"mode": "NO_EXPIRY_STATED"}
        self.assertEqual(self.compile(a=a)["status"], "HOLD_NO_VALIDITY_BASIS")

    def test_missing_timezone_fails_closed(self):
        a = issued(); a["validity"] = {"mode": "VALID_UNTIL", "valid_until": "2026-09-30T23:59:59"}
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_source_generation_drift_holds(self):
        b = current(); b["source_generation"] = "src-002"
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_currency_drift_supersedes(self):
        b = current(); b["currency"] = "CAD"
        self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_scope_drift_supersedes(self):
        b = current(); b["scope"]["deliverables"].append("implementation")
        out = self.compile(b=b)
        self.assertEqual(out["status"], "SUPERSEDED")
        self.assertEqual([x["field"] for x in out["requote_delta"]["changes"]], ["scope"])

    def test_economics_drift_supersedes(self):
        b = current(); b["economics"]["fixed_minor_units"] = 600000
        self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_pricing_revision_drift_supersedes(self):
        b = current(); b["pricing_revision"] = "price-r2"
        self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_amendment_after_quote_supersedes(self):
        b = current(); b["superseding_events"] = [{
            "kind":"AMENDMENT", "event_id":"A-1", "observed_at":"2026-09-11T00:00:00Z",
            "applies_to_offer_id":"OFFER-001", "source_generation":"src-amend-1"}]
        self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")


    def test_redline_and_change_order_after_quote_supersede(self):
        for kind in ("REDLINE", "CHANGE_ORDER"):
            b = current(); b["superseding_events"] = [{
                "kind":kind, "event_id":kind+"-1", "observed_at":"2026-09-12T00:00:00Z",
                "applies_to_offer_id":"OFFER-001", "source_generation":"src-event"}]
            self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_pre_issue_event_does_not_supersede(self):
        b = current(); b["superseding_events"] = [{
            "kind":"REDLINE", "event_id":"R-0", "observed_at":"2026-09-09T00:00:00Z",
            "applies_to_offer_id":"OFFER-001", "source_generation":"src-old"}]
        self.assertEqual(self.compile(b=b)["status"], "CURRENT_FOR_OWNER_USE")

    def test_buyer_deadline_caps_validity(self):
        out = self.compile(now=dt.datetime(2026, 9, 26, tzinfo=UTC))
        self.assertEqual(out["status"], "EXPIRED_REQUOTE_REQUIRED")
        self.assertIn("BUYER_DEADLINE_CAP", out["validity_basis"])

    def test_new_rfp_reuse_with_expired_deadline_cannot_roll_forward(self):
        a = issued(); a["buyer_deadline"] = "2026-09-12T17:00:00Z"
        self.assertEqual(self.compile(a=a)["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_packet_clock_injection_is_rejected(self):
        a = issued(); a["as_of"] = "2026-09-11T00:00:00Z"
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_bool_and_float_money_fail_closed(self):
        a = issued(); a["economics"]["fixed_minor_units"] = True
        with self.assertRaises(gate.GateError): self.compile(a=a)
        a = issued(); a["economics"]["fixed_minor_units"] = 5000.5
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_duplicate_key_and_nonfinite_json_rejected(self):
        with self.assertRaises(gate.GateError): gate.strict_json_loads('{"a":1,"a":2}')
        with self.assertRaises(gate.GateError): gate.strict_json_loads('{"a":NaN}')

    def test_verify_rejects_tampered_packet(self):
        out = self.compile(); out["status"] = "CURRENT_FOR_OWNER_USE" if out["status"] != "CURRENT_FOR_OWNER_USE" else "SUPERSEDED"
        self.assertFalse(gate.verify_packet(issued(), current(), out))

    def test_old_current_packet_does_not_verify_after_runtime_expiry(self):
        a = issued(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2026-09-20T00:00:00Z"}
        b = current()
        packet = self.compile(a=a, b=b, now=dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        self.assertEqual(packet["status"], "CURRENT_FOR_OWNER_USE")
        original = gate._utc_now
        try:
            gate._utc_now = lambda: dt.datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
            self.assertFalse(gate.verify_packet(a, b, packet))
        finally:
            gate._utc_now = original

    def test_valid_for_seconds(self):
        a = issued(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_FOR_SECONDS", "valid_for_seconds":86400}
        self.assertEqual(self.compile(a=a, now=dt.datetime(2026,9,10,18,tzinfo=UTC))["status"], "CURRENT_FOR_OWNER_USE")
        self.assertEqual(self.compile(a=a, now=dt.datetime(2026,9,12,18,tzinfo=UTC))["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_current_same_offer_id_changed_economics_delta_is_explicit(self):
        b = current(); b["economics"]["fixed_minor_units"] = 700000; b["source_generation"] = "src-002"
        out = self.compile(b=b)
        self.assertEqual(out["status"], "SUPERSEDED")
        fields = {x["field"] for x in out["requote_delta"]["changes"]}
        self.assertEqual(fields, {"source_generation", "economics"})
        self.assertEqual(out["requote_delta"]["status"], "PROPOSED_NOT_ACCEPTED")

    def test_cli_compile_verify_and_no_overwrite(self):
        a = issued(); a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2099-12-31T00:00:00Z"}; a["buyer_deadline"] = None
        b = current()
        b["source_generation"] = a["source_generation"]; b["pricing_revision"] = a["pricing_revision"]; b["currency"] = a["currency"]; b["scope"] = a["scope"]; b["economics"] = a["economics"]
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); (td/"issued.json").write_text(json.dumps(a), encoding="utf-8"); (td/"current.json").write_text(json.dumps(b), encoding="utf-8")
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(gate.__file__).parent)
            cmd = [sys.executable, gate.__file__, "compile", "--issued", str(td/"issued.json"), "--current", str(td/"current.json"), "--out", str(td/"packet.json")]
            first = subprocess.run(cmd, text=True, capture_output=True, env=env)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            verify = subprocess.run([sys.executable, gate.__file__, "verify", "--issued", str(td/"issued.json"), "--current", str(td/"current.json"), "--packet", str(td/"packet.json")], text=True, capture_output=True, env=env)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr); self.assertIn("VERIFIED", verify.stdout)
            second = subprocess.run(cmd, text=True, capture_output=True, env=env)
            self.assertEqual(second.returncode, 2); self.assertIn("refusing to overwrite", second.stdout)


if __name__ == "__main__":
    unittest.main()
