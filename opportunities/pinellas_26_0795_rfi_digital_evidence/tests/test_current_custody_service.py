import copy
import inspect
import unittest

from custody_reference import AuthorityRecord, AuthoritySnapshot, CustodyError
from current_custody_service import CurrentCustodyService

T0 = "2026-09-14T04:30:00Z"
T1 = "2026-09-14T04:31:00Z"
T2 = "2026-09-14T04:32:00Z"
T3 = "2026-09-14T04:33:00Z"


def record(evidence_id, kind, decision, *, issuer, generation=1, at=T1):
    return AuthorityRecord(
        evidence_id=evidence_id,
        kind=kind,
        generation=generation,
        case_id="CASE-1",
        object_id="OBJ-1",
        decision=decision,
        issuer=issuer,
        at=at,
    )


def destruction_snapshot(prefix=""):
    return AuthoritySnapshot([
        record(prefix + "RET", "RETENTION_ELIGIBILITY", "ELIGIBLE", issuer="schedule"),
        record(prefix + "NOTICE", "NOTICE_COMPLETE", "COMPLETE", issuer="notice-office"),
        record(prefix + "APP-A", "APPROVAL", "APPROVED", issuer="judge-a"),
        record(prefix + "APP-B", "APPROVAL", "APPROVED", issuer="judge-b"),
        record(prefix + "DEST", "DESTRUCTION_AUTHORITY", "AUTHORIZED", issuer="records-director"),
    ])


class MemoryHostProvider:
    def __init__(self, snapshot):
        self.witnesses = {}
        self.current = snapshot
        self.archives = {snapshot.root: snapshot}
        self.fail_writes = False

    def retained_custody_witness(self, case_id, object_id):
        return copy.deepcopy(self.witnesses[(case_id, object_id)])

    def retain_custody_witness(self, case_id, object_id, witness):
        if self.fail_writes:
            raise RuntimeError("host witness store unavailable")
        self.witnesses[(case_id, object_id)] = copy.deepcopy(witness)

    def current_authority_snapshot(self, case_id, object_id):
        return self.current

    def archived_authority_snapshot(self, case_id, object_id, root):
        return self.archives.get(root)


class TestCurrentCustodyService(unittest.TestCase):
    def setUp(self):
        self.snapshot = destruction_snapshot()
        self.provider = MemoryHostProvider(self.snapshot)
        self.service = CurrentCustodyService(self.provider)

    def accepted(self):
        evidence = self.service.submit_current(
            case_id="CASE-1", object_id="OBJ-1", original=b"abc", actor="submitter", at=T0
        )
        self.service.accept_current(evidence, actor="judge", at=T1)
        return evidence

    def test_current_submit_and_accept_retain_host_witness(self):
        evidence = self.accepted()
        self.assertTrue(self.service.verify_current(evidence)["ok"])
        self.assertEqual(
            self.provider.witnesses[("CASE-1", "OBJ-1")], evidence.witness()
        )

    def test_current_destroy_uses_host_snapshot_and_verifies(self):
        evidence = self.accepted()
        receipt = self.service.destroy_current(
            evidence,
            actor="records",
            at=T2,
            retention_evidence_id="RET",
            notice_evidence_id="NOTICE",
            approval_evidence_ids=["APP-A", "APP-B"],
            destruction_authority_evidence_id="DEST",
        )
        self.assertTrue(evidence.destroyed)
        self.assertEqual(receipt["data"]["authority_snapshot_root"], self.snapshot.root)
        self.assertTrue(self.service.verify_current(evidence)["ok"])

    def test_current_destroy_has_no_request_supplied_snapshot_or_root(self):
        params = set(inspect.signature(CurrentCustodyService.destroy_current).parameters)
        self.assertNotIn("snapshot", params)
        self.assertNotIn("trusted_snapshot_root", params)
        self.assertNotIn("expected_witness", params)
        verify_params = set(inspect.signature(CurrentCustodyService.verify_current).parameters)
        self.assertEqual(verify_params, {"self", "evidence"})

    def test_direct_caller_minted_snapshot_cannot_become_current(self):
        evidence = self.accepted()
        attacker = destruction_snapshot("X-")
        # The low-level Evidence primitive can model a self-consistent candidate
        # transition, but the host witness was not advanced by CurrentCustodyService.
        evidence.destroy(
            actor="attacker",
            at=T2,
            snapshot=attacker,
            trusted_snapshot_root=attacker.root,
            retention_evidence_id="X-RET",
            notice_evidence_id="X-NOTICE",
            approval_evidence_ids=["X-APP-A", "X-APP-B"],
            destruction_authority_evidence_id="X-DEST",
        )
        self.provider.archives[attacker.root] = attacker
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_fresh_caller_witness_cannot_replace_host_witness(self):
        evidence = self.accepted()
        evidence.view(actor="attacker", at=T2, purpose="coherent rewrite candidate")
        fresh_attacker_witness = evidence.witness()
        self.assertNotEqual(
            fresh_attacker_witness, self.provider.witnesses[("CASE-1", "OBJ-1")]
        )
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_mutation_is_not_exposed_when_host_witness_write_fails(self):
        evidence = self.accepted()
        before = copy.deepcopy(evidence.events)
        self.provider.fail_writes = True
        with self.assertRaises(RuntimeError):
            self.service.view_current(evidence, actor="clerk", at=T2, purpose="review")
        self.assertEqual(evidence.events, before)
        self.assertFalse(evidence.destroyed)

    def test_archived_snapshot_must_match_event_root(self):
        evidence = self.accepted()
        self.service.destroy_current(
            evidence,
            actor="records",
            at=T2,
            retention_evidence_id="RET",
            notice_evidence_id="NOTICE",
            approval_evidence_ids=["APP-A", "APP-B"],
            destruction_authority_evidence_id="DEST",
        )
        self.provider.archives[self.snapshot.root] = destruction_snapshot("X-")
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_host_provider_methods_are_captured_at_service_construction(self):
        evidence = self.accepted()
        original = copy.deepcopy(self.provider.witnesses[("CASE-1", "OBJ-1")])
        self.provider.retained_custody_witness = lambda *_args: {"forged": True}
        # The bound method captured during construction still reads the host store.
        self.assertTrue(self.service.verify_current(evidence)["ok"])
        self.assertEqual(original, self.provider.witnesses[("CASE-1", "OBJ-1")])


if __name__ == "__main__":
    unittest.main()
