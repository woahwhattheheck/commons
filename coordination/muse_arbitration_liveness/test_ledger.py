# SPDX-License-Identifier: MIT
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .ledger import LedgerError, compile_ledger, loads_strict, read_json_file, verify_ledger, write_json_exclusive

H = lambda text: hashlib.sha256(text.encode()).hexdigest()
BASE = {
    "request_key": "REQ-1",
    "seat_id": "Z-A",
    "counterparty_key": "OPP-1",
    "route_sha256": H("route"),
    "purpose_sha256": H("purpose"),
    "retry_policy_generation": "v1",
}

def request(eid="r1", at="2026-09-16T10:00:00Z", **changes):
    row = {"type":"REQUEST","provider_event_id":eid,"provider_event_sha256":H(eid),"observed_at":at,**BASE}
    row.update(changes)
    return row

def decision(eid="d1", at="2026-09-16T10:01:00Z", disposition="SELECTED", **changes):
    row = {
        "type":"DECISION","provider_event_id":eid,"provider_event_sha256":H(eid),"observed_at":at,
        "decision":disposition,
        "bound_request_key":BASE["request_key"],"bound_seat_id":BASE["seat_id"],
        "bound_counterparty_key":BASE["counterparty_key"],"bound_route_sha256":BASE["route_sha256"],
        "bound_purpose_sha256":BASE["purpose_sha256"],"bound_retry_policy_generation":BASE["retry_policy_generation"],
    }
    row.update(changes)
    return row

def sent(eid="s1", at="2026-09-16T10:02:00Z", **changes):
    row = {
        "type":"SEND_RECEIPT","provider_event_id":eid,"provider_event_sha256":H(eid),"observed_at":at,
        "bound_request_key":BASE["request_key"],"bound_seat_id":BASE["seat_id"],
        "bound_counterparty_key":BASE["counterparty_key"],"bound_route_sha256":BASE["route_sha256"],
        "bound_purpose_sha256":BASE["purpose_sha256"],"bound_retry_policy_generation":BASE["retry_policy_generation"],
    }
    row.update(changes)
    return row

def payload(events, as_of="2026-09-16T10:03:00Z", resubmit=120, stale=300):
    return {"schema_version":1,"as_of_utc":as_of,"policy":{"resubmit_after_seconds":resubmit,"selection_stale_after_seconds":stale},"events":events}

def status(events, **kw):
    return compile_ledger(payload(events, **kw))["items"][0]["status"]

class LedgerTests(unittest.TestCase):
    def test_pending(self): self.assertEqual(status([request()], as_of="2026-09-16T10:01:00Z"), "PENDING_DECISION")
    def test_resubmit_due(self): self.assertEqual(status([request()], as_of="2026-09-16T10:03:00Z"), "OWNER_REVIEW_RESUBMIT_DUE")
    def test_exact_retry_collapses_to_one_request(self):
        p = compile_ledger(payload([request(), request("r2","2026-09-16T10:02:00Z")], as_of="2026-09-16T10:02:30Z"))
        self.assertEqual(p["summary"]["request_count"],1); self.assertEqual(p["items"][0]["attempt_count"],2)
    def test_request_tuple_drift_conflicts(self):
        self.assertEqual(status([request(),request("r2","2026-09-16T10:00:10Z",route_sha256=H("other"))]),"CONFLICT")
    def test_underbound_clear_is_not_selected(self):
        self.assertEqual(status([request(),decision(bound_purpose_sha256=None)]),"MALFORMED_OR_UNDERBOUND_DECISION")
    def test_wrong_seat_is_underbound(self):
        self.assertEqual(status([request(),decision(bound_seat_id="Z-B")]),"MALFORMED_OR_UNDERBOUND_DECISION")
    def test_hold(self): self.assertEqual(status([request(),decision(disposition="HOLD")]),"HOLD_OR_COLLISION")
    def test_collision(self): self.assertEqual(status([request(),decision(disposition="COLLISION")]),"HOLD_OR_COLLISION")
    def test_selected_waiting(self): self.assertEqual(status([request(),decision()]),"SELECTED_AWAITING_SEND_RECEIPT")
    def test_stale_selection_review(self):
        self.assertEqual(status([request(),decision()],as_of="2026-09-16T10:10:00Z",stale=300),"OWNER_REVIEW_STALE_SELECTION")
    def test_exact_send_is_dnr(self): self.assertEqual(status([request(),decision(),sent()]),"SENT_DNR")
    def test_send_without_selection_conflicts(self): self.assertEqual(status([request(),sent()]),"CONFLICT")
    def test_send_before_selection_conflicts(self):
        self.assertEqual(status([request(),decision(at="2026-09-16T10:02:00Z"),sent(at="2026-09-16T10:01:00Z")]),"CONFLICT")
    def test_decision_before_request_conflicts(self):
        self.assertEqual(status([request(at="2026-09-16T10:02:00Z"),decision(at="2026-09-16T10:01:00Z")]),"CONFLICT")
    def test_contradictory_decisions_conflict(self):
        self.assertEqual(status([request(),decision(),decision("d2","2026-09-16T10:01:10Z","HOLD")]),"CONFLICT")
    def test_changed_provider_event_bytes_conflict(self):
        d=decision(); d2=dict(d); d2["provider_event_sha256"]=H("changed")
        self.assertEqual(status([request(),d,d2]),"CONFLICT")
    def test_later_request_answer_does_not_answer_earlier(self):
        r2=request("r2","2026-09-16T10:00:30Z",request_key="REQ-2")
        d2=decision("d2","2026-09-16T10:01:00Z",bound_request_key="REQ-2")
        p=compile_ledger(payload([request(),r2,d2],as_of="2026-09-16T10:03:00Z"))
        got={i["request_key"]:i["status"] for i in p["items"]}
        self.assertEqual(got["REQ-1"],"OWNER_REVIEW_RESUBMIT_DUE"); self.assertEqual(got["REQ-2"],"SELECTED_AWAITING_SEND_RECEIPT")
    def test_orphan_decision_is_reported_not_promoted(self):
        p=compile_ledger(payload([request(),decision(bound_request_key="NOPE")]))
        self.assertEqual(p["summary"]["orphan_event_count"],1); self.assertNotEqual(p["items"][0]["status"],"SELECTED_AWAITING_SEND_RECEIPT")
    def test_deterministic_under_input_order(self):
        a=compile_ledger(payload([request(),decision(),sent()])); b=compile_ledger(payload([sent(),request(),decision()])); self.assertEqual(a,b)
    def test_authority_all_false(self): self.assertTrue(all(v is False for v in compile_ledger(payload([request()]))["authority"].values()))
    def test_public_authority_mutation_cannot_widen_compiled_flags(self):
        import coordination.muse_arbitration_liveness.ledger as ledger
        p = payload([request()])
        original = dict(ledger.AUTHORITY)
        try:
            ledger.AUTHORITY["can_send_external"] = True
            ledger.AUTHORITY["can_assert_payment"] = True
            ledger.AUTHORITY["can_recognize_revenue"] = True
            packet = compile_ledger(p)
            self.assertTrue(all(v is False for v in packet["authority"].values()))
            self.assertTrue(verify_ledger(p, packet))
            self.assertTrue(packet["authority"]["can_send_external"] is False)
        finally:
            ledger.AUTHORITY.clear()
            ledger.AUTHORITY.update(original)
    def test_public_authority_rebind_cannot_widen_compiled_flags(self):
        import coordination.muse_arbitration_liveness.ledger as ledger
        p = payload([request()])
        original = ledger.AUTHORITY
        try:
            ledger.AUTHORITY = {key: True for key in original}
            packet = compile_ledger(p)
            self.assertTrue(all(v is False for v in packet["authority"].values()))
            self.assertTrue(verify_ledger(p, packet))
            self.assertEqual(set(packet["authority"]), set(original))
        finally:
            ledger.AUTHORITY = original
    def test_verify_detects_tamper(self):
        p=payload([request(),decision()]); packet=compile_ledger(p); self.assertTrue(verify_ledger(p,packet)); packet["items"][0]["status"]="SENT_DNR"; self.assertFalse(verify_ledger(p,packet))
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(LedgerError): loads_strict('{"a":1,"a":2}')
    def test_nonfinite_rejected(self):
        with self.assertRaises(LedgerError): loads_strict('{"a":NaN}')
    def test_huge_integer_rejected(self):
        with self.assertRaises(LedgerError): loads_strict('{"a":123456789012345678901}')
    def test_bool_is_not_int_policy(self):
        p=payload([request()]); p["policy"]["resubmit_after_seconds"]=True
        with self.assertRaises(LedgerError): compile_ledger(p)
    def test_bool_schema_version_rejected(self):
        p=payload([request()]); p["schema_version"]=True
        with self.assertRaises(LedgerError): compile_ledger(p)
    def test_unhashable_event_type_is_bounded(self):
        bad=request(); bad["type"]=[]
        with self.assertRaises(LedgerError): compile_ledger(payload([bad]))
    def test_unhashable_decision_is_bounded(self):
        bad=decision(); bad["decision"]=[]
        with self.assertRaises(LedgerError): compile_ledger(payload([request(),bad]))
    def test_unknown_field_rejected(self):
        p=payload([request(extra="x")]);
        with self.assertRaises(LedgerError): compile_ledger(p)
    @unittest.skipUnless(hasattr(os,"mkfifo"),"POSIX")
    def test_fifo_input_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            fifo=Path(td)/"fifo"; os.mkfifo(fifo)
            with self.assertRaises(LedgerError): read_json_file(str(fifo))
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"out.json"; path.write_text("old")
            with self.assertRaises(LedgerError): write_json_exclusive(str(path),{"x":1})
    def test_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"target"; target.write_text("old"); link=Path(td)/"out"; link.symlink_to(target)
            with self.assertRaises(LedgerError): write_json_exclusive(str(link),{"x":1})
            self.assertEqual(target.read_text(),"old")
    def test_future_hold_is_conflict(self):
        self.assertEqual(status([request(),decision(at="2026-09-16T10:04:00Z",disposition="HOLD")],as_of="2026-09-16T10:03:00Z"),"CONFLICT")
    def test_future_send_is_conflict(self):
        self.assertEqual(status([request(),decision(),sent(at="2026-09-16T10:04:00Z")],as_of="2026-09-16T10:03:00Z"),"CONFLICT")
    def test_multiple_distinct_send_receipts_conflict(self):
        self.assertEqual(status([request(),decision(),sent(),sent("s2","2026-09-16T10:02:10Z")]),"CONFLICT")
    def test_provider_id_same_digest_changed_semantics_conflicts(self):
        a=decision(); b=dict(a); b["decision"]="HOLD"
        self.assertEqual(status([request(),a,b]),"CONFLICT")
    def test_cli_compile_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"in.json"; out=root/"out.json"
            inp.write_text(json.dumps(payload([request(),decision()])),encoding="utf-8")
            env=dict(os.environ); env["PYTHONPATH"]=str(Path(__file__).resolve().parents[2])
            c=subprocess.run([sys.executable,"-m","coordination.muse_arbitration_liveness.cli","compile",str(inp),str(out)],env=env,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            v=subprocess.run([sys.executable,"-m","coordination.muse_arbitration_liveness.cli","verify",str(inp),str(out)],env=env,capture_output=True,text=True)
            self.assertEqual(v.returncode,0,v.stderr)

if __name__ == "__main__": unittest.main()
