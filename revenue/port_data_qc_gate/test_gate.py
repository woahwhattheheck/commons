from __future__ import annotations

import copy
import hashlib
import json
import random
import unittest

from revenue.port_data_qc_gate.gate import GateInputError, evaluate, verify


EVAL = "2026-09-13T09:00:00Z"
CAPTURE = "2026-09-13T08:59:00Z"


def policy():
    return {
        "schema": "port-data-qc-policy/v1",
        "max_snapshot_age_seconds": 600,
        "sources": {
            "edi": {
                "schema_version": "v1",
                "allowed_fields": ["container", "status", "terminal"],
                "required_fields": ["container", "status"],
            },
            "api": {
                "schema_version": "v2",
                "allowed_fields": ["container", "eta", "status"],
                "required_fields": ["container", "status"],
            },
        },
    }


def event(source, event_id, record_id, business_key, schema, previous, *, observed="2026-09-13T08:58:00Z", effective="2026-09-13T08:57:00Z", **values):
    return {
        "source_id": source,
        "event_id": event_id,
        "record_id": record_id,
        "business_key": business_key,
        "schema_version": schema,
        "previous_event_id": previous,
        "effective_at": effective,
        "observed_at": observed,
        "values": values,
    }


def snapshot(events, *, complete=True, captured=CAPTURE):
    return {
        "schema": "port-data-qc-snapshot/v1",
        "capture_complete": complete,
        "captured_at": captured,
        "events": events,
    }


def happy_events():
    return [
        event("edi", "e1", "r1", "CONT-1", "v1", None, container="CONT-1", status="ARRIVED", terminal="T1"),
        event("edi", "e2", "r1", "CONT-1", "v1", "e1", observed="2026-09-13T08:58:20Z", effective="2026-09-13T08:58:10Z", container="CONT-1", status="RELEASED", terminal="T1"),
        event("api", "a1", "r9", "CONT-1", "v2", None, container="CONT-1", status="READY", eta="2026-09-13"),
    ]


class GateTests(unittest.TestCase):
    def test_happy_path_is_content_bound_and_verifiable(self):
        p = policy()
        s = snapshot(happy_events())
        result = evaluate(p, s, evaluated_at=EVAL)
        receipt = result["receipt"]
        self.assertEqual("PASS", receipt["decision"])
        self.assertEqual([], receipt["holds"])
        self.assertEqual(3, receipt["unique_event_count"])
        self.assertEqual(2, receipt["report_row_count"])
        self.assertEqual("EVIDENCE_ONLY_NO_OPERATIONAL_RELEASE", receipt["authority"])
        self.assertTrue(verify(result, policy=p, snapshot=s))

    def test_input_order_does_not_change_report_or_receipt(self):
        p = policy()
        original = happy_events()
        shuffled = copy.deepcopy(original)
        random.Random(7).shuffle(shuffled)
        r1 = evaluate(p, snapshot(original), evaluated_at=EVAL)
        r2 = evaluate(p, snapshot(shuffled), evaluated_at=EVAL)
        self.assertEqual(r1["report"], r2["report"])
        self.assertNotEqual(r1["receipt"]["snapshot_sha256"], r2["receipt"]["snapshot_sha256"])
        self.assertEqual(r1["receipt"]["report_sha256"], r2["receipt"]["report_sha256"])

    def test_exact_duplicate_collapses_deterministically(self):
        events = happy_events()
        events.append(copy.deepcopy(events[0]))
        result = evaluate(policy(), snapshot(events), evaluated_at=EVAL)
        self.assertEqual("PASS", result["receipt"]["decision"])
        self.assertEqual(1, result["receipt"]["duplicate_event_count"])
        self.assertEqual(3, result["receipt"]["unique_event_count"])

    def test_conflicting_duplicate_event_id_holds(self):
        events = happy_events()
        conflicting = copy.deepcopy(events[0])
        conflicting["values"]["status"] = "GATED"
        events.append(conflicting)
        result = evaluate(policy(), snapshot(events), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertIn("EVENT_ID_CONFLICT", result["receipt"]["holds"])
        self.assertTrue(any(row["code"] == "EVENT_ID_CONFLICT" for row in result["exceptions"]["exceptions"]))

    def test_branch_conflict_quarantines_record(self):
        events = happy_events()
        events.append(event("edi", "e3", "r1", "CONT-1", "v1", "e1", container="CONT-1", status="HELD", terminal="T2"))
        result = evaluate(policy(), snapshot(events), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertIn("RECORDS_QUARANTINED", result["receipt"]["holds"])
        self.assertTrue(any(row["code"] == "BRANCH_CONFLICT" for row in result["exceptions"]["exceptions"]))
        self.assertFalse(any(row["record_id"] == "r1" for row in result["report"]["rows"]))

    def test_missing_predecessor_quarantines_record(self):
        events = happy_events()
        events[1]["previous_event_id"] = "never-seen"
        result = evaluate(policy(), snapshot(events), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertTrue(any(row["code"] == "MISSING_PREDECESSOR" for row in result["exceptions"]["exceptions"]))

    def test_business_key_drift_quarantines_record(self):
        events = happy_events()
        events[1]["business_key"] = "CONT-OTHER"
        result = evaluate(policy(), snapshot(events), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertTrue(any(row["code"] == "BUSINESS_KEY_DRIFT" for row in result["exceptions"]["exceptions"]))

    def test_incomplete_snapshot_holds(self):
        result = evaluate(policy(), snapshot(happy_events(), complete=False), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertIn("SNAPSHOT_INCOMPLETE", result["receipt"]["holds"])

    def test_stale_snapshot_holds(self):
        p = policy()
        p["max_snapshot_age_seconds"] = 10
        result = evaluate(p, snapshot(happy_events()), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertIn("SNAPSHOT_STALE", result["receipt"]["holds"])

    def test_missing_approved_source_holds(self):
        events = [e for e in happy_events() if e["source_id"] == "edi"]
        result = evaluate(policy(), snapshot(events), evaluated_at=EVAL)
        self.assertEqual("HOLD", result["receipt"]["decision"])
        self.assertIn("APPROVED_SOURCE_MISSING", result["receipt"]["holds"])

    def test_unknown_source_rejected_before_receipt(self):
        events = happy_events()
        events.append(event("rogue", "x1", "x", "X", "v1", None, container="X", status="X"))
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_wrong_schema_version_rejected(self):
        events = happy_events()
        events[0]["schema_version"] = "v999"
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_unknown_field_rejected(self):
        events = happy_events()
        events[0]["values"]["surprise"] = "x"
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_missing_required_field_rejected(self):
        events = happy_events()
        del events[0]["values"]["status"]
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_nested_or_float_payload_rejected(self):
        for bad in ({"nested": True}, 1.5, ["x"]):
            events = happy_events()
            events[0]["values"]["terminal"] = bad
            with self.subTest(bad=bad), self.assertRaises(GateInputError):
                evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_future_observation_rejected(self):
        events = happy_events()
        events[0]["observed_at"] = "2026-09-13T09:01:00Z"
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_effective_after_observed_rejected(self):
        events = happy_events()
        events[0]["effective_at"] = "2026-09-13T08:58:30Z"
        events[0]["observed_at"] = "2026-09-13T08:58:00Z"
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(events), evaluated_at=EVAL)

    def test_snapshot_from_future_rejected(self):
        with self.assertRaises(GateInputError):
            evaluate(policy(), snapshot(happy_events(), captured="2026-09-13T09:00:01Z"), evaluated_at=EVAL)

    def test_tampered_report_breaks_verification(self):
        p = policy()
        s = snapshot(happy_events())
        result = evaluate(p, s, evaluated_at=EVAL)
        result["report"]["rows"][0]["values"]["status"] = "TAMPERED"
        self.assertFalse(verify(result, policy=p, snapshot=s))

    def test_self_consistent_rehashed_forgery_is_rejected(self):
        p = policy()
        s = snapshot(happy_events())
        result = evaluate(p, s, evaluated_at=EVAL)
        result["report"]["rows"][0]["values"]["status"] = "FORGED"

        def digest(value):
            raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
            return hashlib.sha256(raw).hexdigest()

        result["receipt"]["report_sha256"] = digest(result["report"])
        core = dict(result["receipt"])
        core.pop("receipt_sha256")
        result["receipt"]["receipt_sha256"] = digest(core)
        self.assertFalse(verify(result, policy=p, snapshot=s))

    def test_tampered_receipt_breaks_verification(self):
        p = policy()
        s = snapshot(happy_events())
        result = evaluate(p, s, evaluated_at=EVAL)
        result["receipt"]["decision"] = "HOLD"
        self.assertFalse(verify(result, policy=p, snapshot=s))

    def test_wrong_policy_or_snapshot_breaks_verification(self):
        p = policy()
        s = snapshot(happy_events())
        result = evaluate(p, s, evaluated_at=EVAL)
        p2 = policy()
        p2["max_snapshot_age_seconds"] = 601
        self.assertFalse(verify(result, policy=p2, snapshot=s))
        s2 = copy.deepcopy(s)
        s2["events"][0]["values"]["status"] = "OTHER"
        self.assertFalse(verify(result, policy=p, snapshot=s2))

    def test_verifier_rejects_extra_receipt_fields(self):
        p = policy()
        s = snapshot(happy_events())
        result = evaluate(p, s, evaluated_at=EVAL)
        result["receipt"]["release_authorized"] = True
        self.assertFalse(verify(result, policy=p, snapshot=s))

    def test_bool_not_accepted_as_integer_policy_age(self):
        p = policy()
        p["max_snapshot_age_seconds"] = True
        with self.assertRaises(GateInputError):
            evaluate(p, snapshot(happy_events()), evaluated_at=EVAL)

    def test_policy_requires_exact_field_sets(self):
        p = policy()
        p["sources"]["edi"]["extra"] = "nope"
        with self.assertRaises(GateInputError):
            evaluate(p, snapshot(happy_events()), evaluated_at=EVAL)


if __name__ == "__main__":
    unittest.main()
