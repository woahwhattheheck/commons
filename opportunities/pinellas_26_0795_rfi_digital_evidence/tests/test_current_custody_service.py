import copy
import inspect
import threading
import unittest

import current_custody_service as current_module
from custody_reference import AuthorityRecord, AuthoritySnapshot, CustodyError
from current_custody_service import CurrentCustodyService

T0 = "2026-09-14T04:30:00Z"
T1 = "2026-09-14T04:31:00Z"
T2 = "2026-09-14T04:32:00Z"
T3 = "2026-09-14T04:33:00Z"
T4 = "2026-09-14T04:34:00Z"


def record(evidence_id, kind, decision, *, issuer, generation=1, at=T1):
    return AuthorityRecord(
        evidence_id=evidence_id, kind=kind, generation=generation,
        case_id="CASE-1", object_id="OBJ-1", decision=decision,
        issuer=issuer, at=at,
    )


def destruction_snapshot(prefix="", *, at=T1):
    return AuthoritySnapshot([
        record(prefix + "RET", "RETENTION_ELIGIBILITY", "ELIGIBLE", issuer="schedule", at=at),
        record(prefix + "NOTICE", "NOTICE_COMPLETE", "COMPLETE", issuer="notice-office", at=at),
        record(prefix + "APP-A", "APPROVAL", "APPROVED", issuer="judge-a", at=at),
        record(prefix + "APP-B", "APPROVAL", "APPROVED", issuer="judge-b", at=at),
        record(prefix + "DEST", "DESTRUCTION_AUTHORITY", "AUTHORIZED", issuer="records-director", at=at),
    ])


class MemoryHostProvider:
    def __init__(self, snapshot, now=T0):
        self.now = now
        self.witnesses = {}
        self.current = snapshot
        self.archives = {snapshot.root: snapshot}
        self.fail_writes = False
        self.read_barrier = None
        self._lock = threading.Lock()

    def current_time_utc(self):
        return self.now

    def retained_custody_witness(self, case_id, object_id):
        with self._lock:
            value = copy.deepcopy(self.witnesses[(case_id, object_id)])
        barrier = self.read_barrier
        if barrier is not None:
            barrier.wait(timeout=5)
        return value

    def compare_and_retain_custody_witness(
        self, case_id, object_id, expected_witness, successor_witness
    ):
        if self.fail_writes:
            raise RuntimeError("host witness store unavailable")
        key = (case_id, object_id)
        with self._lock:
            actual = self.witnesses.get(key)
            if actual != expected_witness:
                return False
            self.witnesses[key] = copy.deepcopy(successor_witness)
            return True

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
        self.provider.now = T0
        evidence = self.service.submit_current(
            case_id="CASE-1", object_id="OBJ-1", original=b"abc", actor="submitter"
        )
        self.provider.now = T1
        self.service.accept_current(evidence, actor="judge")
        return evidence

    def destroy(self, evidence):
        return self.service.destroy_current(
            evidence, actor="records", retention_evidence_id="RET",
            notice_evidence_id="NOTICE", approval_evidence_ids=["APP-A", "APP-B"],
            destruction_authority_evidence_id="DEST",
        )

    def test_current_submit_and_accept_retain_host_witness(self):
        evidence = self.accepted()
        self.assertTrue(self.service.verify_current(evidence)["ok"])
        self.assertEqual(self.provider.witnesses[("CASE-1", "OBJ-1")], evidence.witness())

    def test_current_destroy_uses_host_snapshot_and_verifies(self):
        evidence = self.accepted()
        self.provider.now = T2
        receipt = self.destroy(evidence)
        self.assertTrue(evidence.destroyed)
        self.assertEqual(receipt["data"]["authority_snapshot_root"], self.snapshot.root)
        self.assertTrue(self.service.verify_current(evidence)["ok"])

    def test_current_operations_accept_no_request_time_or_trust_material(self):
        for name in (
            "submit_current", "view_current", "classify_current", "accept_current",
            "replace_original_current", "set_hold_current", "destroy_current", "verify_current",
        ):
            params = set(inspect.signature(getattr(self.service, name)).parameters)
            for forbidden in (
                "at", "snapshot", "trusted_snapshot_root",
                "expected_witness", "trusted_snapshot_roots",
            ):
                self.assertNotIn(forbidden, params, (name, forbidden))

    def test_future_authority_cannot_be_promoted_by_caller_time(self):
        future = destruction_snapshot("F-", at=T3)
        provider = MemoryHostProvider(future)
        service = CurrentCustodyService(provider)
        provider.now = T0
        evidence = service.submit_current(
            case_id="CASE-1", object_id="OBJ-1", original=b"abc", actor="submitter"
        )
        provider.now = T1
        service.accept_current(evidence, actor="judge")
        provider.now = T2
        with self.assertRaises(CustodyError):
            service.destroy_current(
                evidence, actor="records", retention_evidence_id="F-RET",
                notice_evidence_id="F-NOTICE", approval_evidence_ids=["F-APP-A", "F-APP-B"],
                destruction_authority_evidence_id="F-DEST",
            )
        self.assertFalse(evidence.destroyed)
        with self.assertRaises(TypeError):
            service.destroy_current(
                evidence, actor="records", at=T4, retention_evidence_id="F-RET",
                notice_evidence_id="F-NOTICE", approval_evidence_ids=["F-APP-A", "F-APP-B"],
                destruction_authority_evidence_id="F-DEST",
            )
        provider.now = T4
        receipt = service.destroy_current(
            evidence, actor="records", retention_evidence_id="F-RET",
            notice_evidence_id="F-NOTICE", approval_evidence_ids=["F-APP-A", "F-APP-B"],
            destruction_authority_evidence_id="F-DEST",
        )
        self.assertEqual(receipt["at"], T4)

    def test_direct_caller_minted_snapshot_cannot_become_current(self):
        evidence = self.accepted()
        attacker = destruction_snapshot("X-")
        evidence.destroy(
            actor="attacker", at=T2, snapshot=attacker,
            trusted_snapshot_root=attacker.root, retention_evidence_id="X-RET",
            notice_evidence_id="X-NOTICE", approval_evidence_ids=["X-APP-A", "X-APP-B"],
            destruction_authority_evidence_id="X-DEST",
        )
        self.provider.archives[attacker.root] = attacker
        self.provider.now = T2
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_fresh_caller_witness_cannot_replace_host_witness(self):
        evidence = self.accepted()
        evidence.view(actor="attacker", at=T2, purpose="coherent rewrite candidate")
        self.provider.now = T2
        self.assertNotEqual(
            evidence.witness(), self.provider.witnesses[("CASE-1", "OBJ-1")]
        )
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_mutation_is_not_exposed_when_host_cas_write_fails(self):
        evidence = self.accepted()
        before = copy.deepcopy(evidence.events)
        self.provider.now = T2
        self.provider.fail_writes = True
        with self.assertRaises(RuntimeError):
            self.service.view_current(evidence, actor="clerk", purpose="review")
        self.assertEqual(evidence.events, before)

    def test_atomic_cas_allows_only_one_same_predecessor_writer(self):
        evidence = self.accepted()
        left = copy.deepcopy(evidence)
        right = copy.deepcopy(evidence)
        self.provider.now = T2
        self.provider.read_barrier = threading.Barrier(2)
        outcomes, errors = [], []

        def worker(target, purpose):
            try:
                self.service.view_current(target, actor=purpose, purpose=purpose)
                outcomes.append(target)
            except Exception as exc:
                errors.append(exc)

        a = threading.Thread(target=worker, args=(left, "left"))
        b = threading.Thread(target=worker, args=(right, "right"))
        a.start(); b.start(); a.join(5); b.join(5)
        self.provider.read_barrier = None
        self.assertFalse(a.is_alive()); self.assertFalse(b.is_alive())
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CustodyError)
        winner = outcomes[0]
        loser = right if winner is left else left
        self.assertEqual(len(winner.events), len(evidence.events) + 1)
        self.assertEqual(len(loser.events), len(evidence.events))
        self.assertEqual(self.provider.witnesses[("CASE-1", "OBJ-1")], winner.witness())

    def test_archived_snapshot_must_match_event_root(self):
        evidence = self.accepted()
        self.provider.now = T2
        self.destroy(evidence)
        self.provider.archives[self.snapshot.root] = destruction_snapshot("X-")
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_existing_service_survives_provider_and_module_rebinding(self):
        evidence = self.accepted()
        self.provider.now = T2
        saved = {
            "Evidence": current_module.Evidence,
            "AuthoritySnapshot": current_module.AuthoritySnapshot,
            "CustodyError": current_module.CustodyError,
            "CurrentCustodyService": current_module.CurrentCustodyService,
        }
        try:
            self.provider.retained_custody_witness = lambda *_args: {"forged": True}
            self.provider.compare_and_retain_custody_witness = lambda *_args: True
            current_module.Evidence = object
            current_module.AuthoritySnapshot = object
            current_module.CustodyError = RuntimeError
            current_module.CurrentCustodyService = lambda *_args, **_kwargs: None
            self.assertTrue(self.service.verify_current(evidence)["ok"])
            with self.assertRaises(AttributeError):
                self.service.verify_current = lambda *_args: {"ok": True}
            with self.assertRaises(AttributeError):
                self.service._retained_witness = lambda *_args: {"forged": True}
        finally:
            for name, value in saved.items():
                setattr(current_module, name, value)

    def test_provider_clock_rollback_makes_future_retained_event_noncurrent(self):
        evidence = self.accepted()
        self.provider.now = T2
        self.service.view_current(evidence, actor="clerk", purpose="review")
        self.provider.now = T1
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)


if __name__ == "__main__":
    unittest.main()
