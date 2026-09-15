import copy
import hashlib
import json
import unittest
from custody_reference import CustodyError, Evidence

T0="2026-09-14T04:30:00Z"; T1="2026-09-14T04:31:00Z"; T2="2026-09-14T04:32:00Z"; T3="2026-09-14T04:33:00Z"
RETENTION_EVIDENCE="RETENTION-SCHEDULE-7"
NOTICE_EVIDENCE="NOTICE-COPY-OPPORTUNITY-55"


def rehash(event):
    body={k:event[k] for k in event if k!="event_hash"}
    event["event_hash"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


class TestCustody(unittest.TestCase):
    def new(self): return Evidence.submit(case_id="CASE-1",object_id="OBJ-1",original=b"abc",actor="submitter",at=T0)
    def accepted(self):
        e=self.new(); e.accept(actor="judge",at=T1); return e
    def destroy(self,e,**overrides):
        args={
            "actor":"records","at":T2,"retention_eligible":True,"notice_complete":True,
            "retention_evidence_id":RETENTION_EVIDENCE,"notice_evidence_id":NOTICE_EVIDENCE,
            "approval_ids":["a","b"],"authority":"schedule",
        }
        args.update(overrides)
        return e.destroy(**args)

    def test_submit_verifies(self): self.assertTrue(self.new().verify()["ok"])
    def test_view_is_audited(self):
        e=self.new(); e.view(actor="clerk",at=T1,purpose="review"); self.assertEqual(e.events[-1]["kind"],"VIEWED")
    def test_empty_view_purpose_rejected(self):
        with self.assertRaises(CustodyError): self.new().view(actor="clerk",at=T1,purpose=" ")
    def test_classification_bool_strict(self):
        with self.assertRaises(CustodyError): self.new().classify(actor="clerk",at=T1,status="REVIEW",confidential=1)
    def test_accept_locks_original(self):
        e=self.new(); e.accept(actor="judge",at=T1)
        with self.assertRaises(CustodyError): e.replace_original(new_bytes=b"changed",actor="clerk",at=T2)
    def test_double_accept_rejected(self):
        e=self.new(); e.accept(actor="judge",at=T1)
        with self.assertRaises(CustodyError): e.accept(actor="judge",at=T2)
    def test_replace_before_accept_changes_hash(self):
        e=self.new(); old=e.original_sha256; e.replace_original(new_bytes=b"changed",actor="clerk",at=T2); self.assertNotEqual(old,e.original_sha256)
    def test_destruction_requires_accepted_evidence(self):
        with self.assertRaises(CustodyError): self.destroy(self.new(),at=T1)
    def test_hold_blocks_destruction(self):
        e=self.accepted(); e.set_hold(actor="records",at=T2,enabled=True,authority="appeal")
        with self.assertRaises(CustodyError): self.destroy(e,at=T3)
    def test_retention_required(self):
        e=self.accepted()
        with self.assertRaises(CustodyError): self.destroy(e,retention_eligible=False)
    def test_notice_required(self):
        e=self.accepted()
        with self.assertRaises(CustodyError): self.destroy(e,notice_complete=False)
    def test_predicate_evidence_ids_required(self):
        e=self.accepted()
        with self.assertRaises(CustodyError): self.destroy(e,retention_evidence_id=" ")
        with self.assertRaises(CustodyError): self.destroy(e,notice_evidence_id="")
    def test_two_distinct_approvals_required(self):
        e=self.accepted()
        with self.assertRaises(CustodyError): self.destroy(e,approval_ids=["a","a"])
    def test_successful_destruction_receipt_binds_predicates_and_provenance(self):
        e=self.accepted(); r=self.destroy(e,approval_ids=["b","a"])
        self.assertEqual(r["data"]["approval_ids"],["a","b"])
        self.assertIs(r["data"]["retention_eligible"],True)
        self.assertIs(r["data"]["notice_complete"],True)
        self.assertEqual(r["data"]["retention_evidence_id"],RETENTION_EVIDENCE)
        self.assertEqual(r["data"]["notice_evidence_id"],NOTICE_EVIDENCE)
        self.assertTrue(e.destroyed); self.assertTrue(e.verify()["ok"])
    def test_post_destroy_lifecycle_blocked(self):
        e=self.accepted(); self.destroy(e)
        with self.assertRaises(CustodyError): e.view(actor="x",at=T3,purpose="peek")
    def test_rehashed_legacy_destroy_without_predicates_or_provenance_rejected(self):
        e=self.accepted()
        e._append("DESTROYED",actor="records",at=T2,data={
            "original_sha256":e.original_sha256,"approval_ids":["a","b"],"authority":"schedule",
        })
        e.destroyed=True
        with self.assertRaises(CustodyError): e.verify()
    def test_rehashed_false_destroy_predicate_rejected(self):
        e=self.accepted(); r=self.destroy(e); r["data"]["retention_eligible"]=False; rehash(r)
        with self.assertRaises(CustodyError): e.verify()
    def test_rehashed_missing_predicate_provenance_rejected(self):
        e=self.accepted(); r=self.destroy(e); r["data"]["notice_evidence_id"]=""; rehash(r)
        with self.assertRaises(CustodyError): e.verify()
    def test_event_mutation_detected(self):
        e=self.new(); e.view(actor="clerk",at=T1,purpose="review"); e.events[1]["data"]["purpose"]="tamper"
        with self.assertRaises(CustodyError): e.verify()
    def test_event_deletion_detected(self):
        e=self.new(); e.view(actor="a",at=T1,purpose="x"); e.view(actor="b",at=T2,purpose="y"); del e.events[1]
        with self.assertRaises(CustodyError): e.verify()
    def test_event_reorder_detected(self):
        e=self.new(); e.view(actor="a",at=T1,purpose="x"); e.view(actor="b",at=T2,purpose="y"); e.events[1],e.events[2]=e.events[2],e.events[1]
        with self.assertRaises(CustodyError): e.verify()
    def test_case_identity_tamper_detected(self):
        e=self.new(); e.events[0]["case_id"]="CASE-2"
        with self.assertRaises(CustodyError): e.verify()
    def test_whole_second_utc_required(self):
        with self.assertRaises(CustodyError): Evidence.submit(case_id="C",object_id="O",original=b"x",actor="a",at="2026-09-14T04:30:00.1Z")
    def test_timezone_offset_rejected(self):
        with self.assertRaises(CustodyError): Evidence.submit(case_id="C",object_id="O",original=b"x",actor="a",at="2026-09-14T00:30:00-04:00")
    def test_backward_timestamp_rejected_without_state_mutation(self):
        e=self.new(); e.view(actor="a",at=T2,purpose="x")
        before=len(e.events)
        with self.assertRaises(CustodyError): e.set_hold(actor="records",at=T1,enabled=True,authority="appeal")
        self.assertFalse(e.legal_hold); self.assertEqual(len(e.events),before)
    def test_failed_accept_does_not_lock(self):
        e=self.new(); e.view(actor="a",at=T2,purpose="x")
        with self.assertRaises(CustodyError): e.accept(actor="judge",at=T1)
        self.assertFalse(e.accepted)
    def test_preaccept_replace_is_audited(self):
        e=self.new(); old=e.original_sha256; e.replace_original(new_bytes=b"changed",actor="clerk",at=T1)
        self.assertEqual(e.events[-1]["data"]["old_sha256"],old); self.assertEqual(e.events[-1]["data"]["new_sha256"],e.original_sha256)
    def test_current_digest_state_tamper_detected(self):
        e=self.new(); e.original_sha256="0"*64
        with self.assertRaises(CustodyError): e.verify()
    def test_accepted_state_tamper_detected(self):
        e=self.new(); e.accepted=True
        with self.assertRaises(CustodyError): e.verify()
    def test_hold_state_tamper_detected(self):
        e=self.new(); e.legal_hold=True
        with self.assertRaises(CustodyError): e.verify()
    def test_destroyed_state_tamper_detected(self):
        e=self.new(); e.destroyed=True
        with self.assertRaises(CustodyError): e.verify()
    def test_semantic_event_tamper_detected_even_if_rehashed(self):
        e=self.new(); e.accept(actor="judge",at=T1)
        forged=copy.deepcopy(e.events[-1]); forged["seq"]=3; forged["prev_hash"]=e.events[-1]["event_hash"]; forged["at"]=T2
        rehash(forged); e.events.append(forged)
        with self.assertRaises(CustodyError): e.verify()
    def test_non_string_view_purpose_rejected(self):
        with self.assertRaises(CustodyError): self.new().view(actor="clerk",at=T1,purpose=None)
    def test_hash_is_deterministic(self):
        a=self.new(); b=self.new(); self.assertEqual(a.events,b.events)


if __name__ == "__main__":
    unittest.main()
