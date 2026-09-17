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
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def issued():
    return {
        "schema_version": 1,
        "offer_id": "OFFER-001",
        "source_generation": "src-001",
        "source_digest": DIGEST_A,
        "pricing_revision": "price-r1",
        "currency": "USD",
        "scope": {"deliverables": ["diagnostic"], "acceptance": ["receipt verified"]},
        "economics": {"fixed_minor_units": 500000, "payment_terms": "Net 15"},
        "issued_on": "2026-09-10T12:00:00Z",
        "validity": {"mode": "VALID_UNTIL", "valid_until": "2026-09-30T23:59:59-04:00"},
        "buyer_deadline": "2026-09-25T14:00:00-04:00",
        "payment_rail": {"checkout_url": "https://example.invalid/offer-001", "state": "PRESENT"},
    }


def current():
    src = issued()
    return {
        "schema_version": 1,
        "offer_id": src["offer_id"],
        "source_generation": src["source_generation"],
        "source_digest": src["source_digest"],
        "source_status": "CURRENT",
        "source_observed_at": "2026-09-16T19:00:00Z",
        "pricing_revision": src["pricing_revision"],
        "currency": src["currency"],
        "scope": copy.deepcopy(src["scope"]),
        "economics": copy.deepcopy(src["economics"]),
        "payment_rail": copy.deepcopy(src["payment_rail"]),
        "superseding_events": [],
    }


def move_source(b, *, generation="src-002", digest=DIGEST_B):
    b["source_generation"] = generation
    b["source_digest"] = digest
    return b


def event(kind="AMENDMENT", *, when="2026-09-11T00:00:00Z", offer_id="OFFER-001", generation="src-001", digest=DIGEST_A):
    row = {
        "kind": kind,
        "event_id": f"{kind}-1",
        "observed_at": when,
        "applies_to_offer_id": offer_id,
        "source_generation": generation,
    }
    if digest is not None:
        row["source_digest"] = digest
    return row


class GateTests(unittest.TestCase):
    def compile(self, a=None, b=None, now=NOW):
        return gate._evaluate_at(a or issued(), b or current(), now)

    def test_current_owner_use_and_payment_rail_is_not_acceptance(self):
        out = self.compile()
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertFalse(out["authority"]["buyer_acceptance"])
        self.assertFalse(out["authority"]["checkout_or_payment_rail_is_acceptance"])
        self.assertTrue(gate._verify_packet_at(issued(), current(), out, NOW))

    def test_expired_requires_requote(self):
        self.assertEqual(self.compile(now=dt.datetime(2026, 10, 1, tzinfo=UTC))["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_no_expiry_stated_holds(self):
        a = issued(); a["validity"] = {"mode": "NO_EXPIRY_STATED"}
        self.assertEqual(self.compile(a=a)["status"], "HOLD_NO_VALIDITY_BASIS")

    def test_missing_timezone_fails_closed(self):
        a = issued(); a["validity"] = {"mode": "VALID_UNTIL", "valid_until": "2026-09-30T23:59:59"}
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_source_generation_drift_holds_without_explicit_delta(self):
        b = move_source(current())
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_source_digest_drift_holds_without_explicit_delta(self):
        b = current(); b["source_digest"] = DIGEST_B
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_legacy_missing_source_evidence_is_accepted_but_cannot_mint_current(self):
        a = issued(); a.pop("source_digest")
        b = current()
        for key in ("source_digest", "source_status", "source_observed_at"):
            b.pop(key)
        self.assertEqual(self.compile(a=a, b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_source_observed_before_issue_cannot_mint_current(self):
        b = current(); b["source_observed_at"] = "2026-09-09T23:59:59Z"
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_future_source_observation_holds(self):
        b = current(); b["source_observed_at"] = "2026-09-16T21:00:00Z"
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_noncurrent_source_status_holds(self):
        for value in ("STALE", "WITHDRAWN", "UNKNOWN"):
            b = current(); b["source_status"] = value
            with self.subTest(value=value):
                self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_semantic_drift_supersedes_with_fresh_source_evidence(self):
        mutations = {
            "currency": lambda b: b.__setitem__("currency", "CAD"),
            "scope": lambda b: b["scope"]["deliverables"].append("implementation"),
            "economics": lambda b: b["economics"].__setitem__("fixed_minor_units", 600000),
            "pricing_revision": lambda b: b.__setitem__("pricing_revision", "price-r2"),
        }
        for label, mutate in mutations.items():
            b = move_source(current())
            mutate(b)
            with self.subTest(field=label):
                out = self.compile(b=b)
                self.assertEqual(out["status"], "SUPERSEDED")
                self.assertIn(label, {row["field"] for row in out["requote_delta"]["changes"]})

    def test_amendment_redline_change_order_reprice_withdrawal_supersede(self):
        for kind in ("AMENDMENT", "REDLINE", "CHANGE_ORDER", "REPRICE", "WITHDRAWAL"):
            b = current(); b["superseding_events"] = [event(kind)]
            with self.subTest(kind=kind):
                self.assertEqual(self.compile(b=b)["status"], "SUPERSEDED")

    def test_pre_issue_relevant_event_does_not_supersede_or_block(self):
        b = current(); b["superseding_events"] = [event("REDLINE", when="2026-09-09T00:00:00Z", digest=None)]
        self.assertEqual(self.compile(b=b)["status"], "CURRENT_FOR_OWNER_USE")

    def test_nonrelevant_historical_event_does_not_block(self):
        b = current(); b["superseding_events"] = [event("WITHDRAWAL", when="2026-09-12T00:00:00Z", offer_id="OTHER", generation="old", digest=None)]
        self.assertEqual(self.compile(b=b)["status"], "CURRENT_FOR_OWNER_USE")

    def test_post_issue_event_must_bind_current_source_generation_and_digest(self):
        for mutation in ("generation", "digest", "missing-digest"):
            b = current(); row = event("REPRICE")
            if mutation == "generation": row["source_generation"] = "src-other"
            elif mutation == "digest": row["source_digest"] = DIGEST_B
            else: row.pop("source_digest")
            b["superseding_events"] = [row]
            with self.subTest(mutation=mutation):
                self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_supersession_cannot_postdate_source_observation(self):
        b = current(); b["superseding_events"] = [event("REPRICE", when="2026-09-16T19:00:01Z")]
        self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_payment_road_missing_replaced_or_inactive_holds(self):
        variants = []
        b = current(); b["payment_rail"] = None; variants.append(b)
        b = current(); b["payment_rail"]["checkout_url"] = "https://example.invalid/replaced"; variants.append(b)
        b = current(); b["payment_rail"]["state"] = "INACTIVE"; variants.append(b)
        for b in variants:
            with self.subTest(rail=b.get("payment_rail")):
                self.assertEqual(self.compile(b=b)["status"], "HOLD_SOURCE_DRIFT")

    def test_new_payment_road_on_offer_that_had_none_holds(self):
        a = issued(); a["payment_rail"] = None
        b = current(); b["payment_rail"] = {"checkout_url": "https://example.invalid/new", "state": "PRESENT"}
        self.assertEqual(self.compile(a=a, b=b)["status"], "HOLD_SOURCE_DRIFT")

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

    def test_bool_float_and_unsafe_integer_money_fail_closed(self):
        a = issued(); a["economics"]["fixed_minor_units"] = True
        with self.assertRaises(gate.GateError): self.compile(a=a)
        a = issued(); a["economics"]["fixed_minor_units"] = 5000.5
        with self.assertRaises(gate.GateError): self.compile(a=a)
        a = issued(); a["economics"]["fixed_minor_units"] = gate.MAX_SAFE_INT + 1
        with self.assertRaises(gate.GateError): self.compile(a=a)

    def test_strict_json_integer_boundary_and_runtime_edges(self):
        self.assertEqual(gate.strict_json_loads('{"n":9007199254740991}')["n"], gate.MAX_SAFE_INT)
        self.assertEqual(gate.strict_json_loads('{"n":-9007199254740991}')["n"], -gate.MAX_SAFE_INT)
        for hostile in (
            '{"n":9007199254740992}',
            '{"n":' + ("9" * 5000) + '}',
            '{"a":1.25}',
            '{"a":NaN}',
            '{"a":1,"a":2}',
            '{"\\ud800":1}',
            '{"v":"\\ud800"}',
            '{"\\ud800":1,"\\ud800":2}',
            ("[" * 5000) + "0" + ("]" * 5000),
        ):
            with self.subTest(hostile=hostile[:40]):
                with self.assertRaises(gate.GateError):
                    gate.strict_json_loads(hostile)
        self.assertEqual(gate.strict_json_loads('{"emoji":"\\ud83d\\ude00"}')["emoji"], "😀")

    def test_verify_rejects_tampered_packet(self):
        out = self.compile(); out["status"] = "SUPERSEDED"
        self.assertFalse(gate._verify_packet_at(issued(), current(), out, NOW))

    def test_verify_rejects_future_evaluated_packet(self):
        future = NOW + dt.timedelta(hours=1)
        packet = self.compile(now=future)
        self.assertFalse(gate._verify_packet_at(issued(), current(), packet, NOW))

    def test_current_packet_verifies_while_semantics_unchanged(self):
        packet = self.compile()
        self.assertTrue(gate._verify_packet_at(issued(), current(), packet, NOW + dt.timedelta(hours=1)))

    def test_old_current_packet_does_not_verify_after_expiry(self):
        a = issued(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2026-09-20T00:00:00Z"}
        b = current()
        packet = gate._evaluate_at(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        self.assertEqual(packet["status"], "CURRENT_FOR_OWNER_USE")
        self.assertFalse(gate._verify_packet_at(a, b, packet, dt.datetime(2026, 9, 21, 0, 0, tzinfo=UTC)))

    def test_same_coarse_status_but_changed_source_semantics_does_not_verify(self):
        packet = self.compile()
        b = current(); b["source_observed_at"] = "2026-09-16T19:30:00Z"
        self.assertEqual(self.compile(b=b)["status"], "CURRENT_FOR_OWNER_USE")
        self.assertFalse(gate._verify_packet_at(issued(), b, packet, NOW + dt.timedelta(hours=1)))

    def test_valid_for_seconds(self):
        a = issued(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_FOR_SECONDS", "valid_for_seconds":86400}
        b = current(); b["source_observed_at"] = "2026-09-10T13:00:00Z"
        self.assertEqual(self.compile(a=a, b=b, now=dt.datetime(2026,9,10,18,tzinfo=UTC))["status"], "CURRENT_FOR_OWNER_USE")
        self.assertEqual(self.compile(a=a, b=b, now=dt.datetime(2026,9,12,18,tzinfo=UTC))["status"], "EXPIRED_REQUOTE_REQUIRED")

    def test_authority_is_hard_false(self):
        authority = self.compile()["authority"]
        self.assertTrue(authority["owner_review_only"])
        for key in ("buyer_acceptance", "contract_signed", "checkout_or_payment_rail_is_acceptance", "payment_authorized", "revenue_recognized", "outbound_authorized"):
            self.assertFalse(authority[key], key)

    def test_public_current_clock_resists_ordinary_module_rebinding(self):
        a = issued(); a["buyer_deadline"] = None; a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2099-12-31T00:00:00Z"}
        b = current()
        original_utc_now = gate._utc_now
        original_trusted = gate._TRUSTED_UTC_NOW
        original_datetime = gate._dt.datetime
        class FrozenDateTime(original_datetime):
            @classmethod
            def now(cls, tz=None):
                frozen = cls(2100, 1, 1, tzinfo=UTC)
                return frozen if tz is None else frozen.astimezone(tz)
        try:
            gate._utc_now = lambda: dt.datetime(2100, 1, 1, tzinfo=UTC)
            gate._TRUSTED_UTC_NOW = lambda: dt.datetime(2100, 1, 1, tzinfo=UTC)
            gate._dt.datetime = FrozenDateTime
            out = gate.evaluate_offer(a, b)
            self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        finally:
            gate._utc_now = original_utc_now
            gate._TRUSTED_UTC_NOW = original_trusted
            gate._dt.datetime = original_datetime

    def test_cli_compile_verify_and_no_overwrite_normal_and_optimized(self):
        a = issued(); a["validity"] = {"mode":"VALID_UNTIL", "valid_until":"2099-12-31T00:00:00Z"}; a["buyer_deadline"] = None
        b = current()
        with tempfile.TemporaryDirectory() as td_raw:
            td = Path(td_raw); (td/"issued.json").write_text(json.dumps(a), encoding="utf-8"); (td/"current.json").write_text(json.dumps(b), encoding="utf-8")
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(gate.__file__).parent)
            for prefix in ([sys.executable], [sys.executable, "-O"]):
                out_path = td / ("packet-o.json" if "-O" in prefix else "packet.json")
                cmd = prefix + [gate.__file__, "compile", "--issued", str(td/"issued.json"), "--current", str(td/"current.json"), "--out", str(out_path)]
                first = subprocess.run(cmd, text=True, capture_output=True, env=env)
                self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
                verify = subprocess.run(prefix + [gate.__file__, "verify", "--issued", str(td/"issued.json"), "--current", str(td/"current.json"), "--packet", str(out_path)], text=True, capture_output=True, env=env)
                self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr); self.assertIn("VERIFIED", verify.stdout)
                second = subprocess.run(cmd, text=True, capture_output=True, env=env)
                self.assertEqual(second.returncode, 2); self.assertIn("refusing to overwrite", second.stdout)

    def test_cli_hostile_json_is_bounded_normal_and_optimized(self):
        hostiles = [
            '{"value":' + ("9" * 5000) + '}',
            '{"\\ud800":1,"\\ud800":2}',
            ("[" * 5000) + "0" + ("]" * 5000),
        ]
        with tempfile.TemporaryDirectory() as td_raw:
            td = Path(td_raw); current_path = td/"current.json"; current_path.write_text("{}", encoding="utf-8")
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(gate.__file__).parent); env["PYTHONIOENCODING"] = "utf-8:strict"
            for idx, hostile in enumerate(hostiles):
                issued_path = td/f"hostile-{idx}.json"; issued_path.write_text(hostile, encoding="utf-8")
                for prefix in ([sys.executable], [sys.executable, "-O"]):
                    proc = subprocess.run(prefix + [gate.__file__, "compile", "--issued", str(issued_path), "--current", str(current_path), "--out", str(td/f"out-{idx}-{len(prefix)}.json")], text=True, capture_output=True, env=env)
                    combined = proc.stdout + proc.stderr
                    self.assertEqual(proc.returncode, 2, combined)
                    self.assertTrue(proc.stdout.startswith("ERROR:"), combined)
                    self.assertNotIn("Traceback", combined)
                    self.assertNotIn("ValueError", combined)
                    self.assertNotIn("UnicodeEncodeError", combined)

    def test_cli_exposes_no_as_of_normal_and_optimized(self):
        for prefix in ([sys.executable], [sys.executable, "-O"]):
            proc = subprocess.run(
                prefix + [gate.__file__, "compile", "--issued", "i.json", "--current", "c.json", "--out", "o.json", "--as-of", "2020-01-01T00:00:00Z"],
                text=True, capture_output=True,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn("Traceback", proc.stdout + proc.stderr)
            self.assertIn("unrecognized arguments", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
