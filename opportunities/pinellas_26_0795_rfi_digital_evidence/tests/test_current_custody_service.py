import copy
import hashlib
import inspect
import json
import threading
import unittest

import custody_reference as low
import current_custody_service as current_module
from custody_reference import AuthorityRecord, AuthoritySnapshot, CustodyError
from current_custody_service import CurrentCustodyService

T0 = "2026-09-14T04:30:00Z"
T1 = "2026-09-14T04:31:00Z"
T2 = "2026-09-14T04:32:00Z"
T3 = "2026-09-14T04:33:00Z"
T4 = "2026-09-14T04:34:00Z"
_MISSING = object()


def record(evidence_id, kind, decision, issuer, at=T1):
    return AuthorityRecord(
        evidence_id=evidence_id,
        kind=kind,
        generation=1,
        case_id="CASE-1",
        object_id="OBJ-1",
        decision=decision,
        issuer=issuer,
        at=at,
    )


def snapshot(prefix="", at=T1):
    return AuthoritySnapshot([
        record(prefix + "RET", "RETENTION_ELIGIBILITY", "ELIGIBLE", "schedule", at),
        record(prefix + "NOTICE", "NOTICE_COMPLETE", "COMPLETE", "notice", at),
        record(prefix + "APP-A", "APPROVAL", "APPROVED", "judge-a", at),
        record(prefix + "APP-B", "APPROVAL", "APPROVED", "judge-b", at),
        record(prefix + "DEST", "DESTRUCTION_AUTHORITY", "AUTHORIZED", "records", at),
    ])


def restore_class_attr(cls, name, value):
    if value is _MISSING:
        delattr(cls, name)
    else:
        setattr(cls, name, value)


def restore_module_attr(module, name, value):
    if value is _MISSING:
        delattr(module, name)
    else:
        setattr(module, name, value)


class MemoryHostProvider:
    def __init__(self, authority_snapshot):
        self.now = T0
        self.current = authority_snapshot
        self.archives = {authority_snapshot.root: authority_snapshot}
        self.witnesses = {}
        self.fail_writes = False
        self.read_barrier = None
        self._lock = threading.Lock()

    def current_time_utc(self):
        return self.now

    def retained_custody_witness(self, case_id, object_id):
        with self._lock:
            value = copy.deepcopy(self.witnesses[(case_id, object_id)])
        if self.read_barrier is not None:
            self.read_barrier.wait(timeout=5)
        return value

    def compare_and_retain_custody_witness(
        self, case_id, object_id, expected_witness, successor_witness
    ):
        if self.fail_writes:
            raise RuntimeError("host witness store unavailable")
        key = (case_id, object_id)
        with self._lock:
            if self.witnesses.get(key) != expected_witness:
                return False
            self.witnesses[key] = copy.deepcopy(successor_witness)
            return True

    def current_authority_snapshot(self, case_id, object_id):
        return self.current

    def archived_authority_snapshot(self, case_id, object_id, root):
        return self.archives.get(root)


class TestCurrentCustodyService(unittest.TestCase):
    def setUp(self):
        self.snapshot = snapshot()
        self.provider = MemoryHostProvider(self.snapshot)
        self.service = CurrentCustodyService(self.provider)

    def accepted(self):
        self.provider.now = T0
        evidence = self.service.submit_current(
            case_id="CASE-1",
            object_id="OBJ-1",
            original=b"abc",
            actor="submitter",
        )
        self.provider.now = T1
        self.service.accept_current(evidence, actor="judge")
        return evidence

    def destroy(self, evidence, prefix=""):
        return self.service.destroy_current(
            evidence,
            actor="records",
            retention_evidence_id=prefix + "RET",
            notice_evidence_id=prefix + "NOTICE",
            approval_evidence_ids=[prefix + "APP-A", prefix + "APP-B"],
            destruction_authority_evidence_id=prefix + "DEST",
        )

    def test_current_round_trip_uses_host_time_snapshot_and_witness(self):
        evidence = self.accepted()
        self.provider.now = T2
        receipt = self.destroy(evidence)
        self.assertTrue(evidence.destroyed)
        self.assertEqual(receipt["at"], T2)
        self.assertTrue(self.service.verify_current(evidence)["ok"])
        self.assertEqual(
            self.provider.witnesses[("CASE-1", "OBJ-1")]["event_count"],
            len(evidence.events),
        )

    def test_public_factory_exposes_only_provider(self):
        self.assertEqual(set(inspect.signature(CurrentCustodyService).parameters), {"provider"})
        attempted = {
            "_normalize_host_time": lambda _value: T4,
            "_Evidence": object,
            "_AuthoritySnapshot": object,
            "_deepcopy": lambda value: value,
        }
        for name, value in attempted.items():
            with self.subTest(name=name), self.assertRaises(TypeError):
                CurrentCustodyService(self.provider, **{name: value})

    def test_future_authority_cannot_be_promoted_by_request_time(self):
        future = snapshot("F-", T3)
        self.provider.current = future
        self.provider.archives[future.root] = future
        evidence = self.accepted()
        self.provider.now = T2
        with self.assertRaises(CustodyError):
            self.destroy(evidence, "F-")
        with self.assertRaises(TypeError):
            self.service.destroy_current(
                evidence,
                actor="records",
                at=T4,
                retention_evidence_id="F-RET",
                notice_evidence_id="F-NOTICE",
                approval_evidence_ids=["F-APP-A", "F-APP-B"],
                destruction_authority_evidence_id="F-DEST",
            )
        self.provider.now = T4
        self.destroy(evidence, "F-")
        self.assertTrue(evidence.destroyed)

    def test_rebinding_low_level_utc_cannot_promote_future_authority(self):
        future = snapshot("F-", T3)
        self.provider.current = future
        self.provider.archives[future.root] = future
        evidence = self.accepted()
        self.provider.now = T2
        original_utc = low._utc
        try:
            low._utc = lambda _value: T4
            with self.assertRaises(CustodyError):
                self.destroy(evidence, "F-")
        finally:
            low._utc = original_utc
        self.assertFalse(evidence.destroyed)

    def test_rebinding_low_level_methods_cannot_redirect_current_service(self):
        evidence = self.accepted()
        self.provider.now = T2
        original_root = low.AuthoritySnapshot.root
        original_bind = low.AuthoritySnapshot.bind_current
        original_witness = low.Evidence.witness
        original_verify = low.Evidence.verify
        try:
            low.AuthoritySnapshot.root = property(lambda _snapshot: "0" * 64)
            low.AuthoritySnapshot.bind_current = lambda *_args, **_kwargs: {"forged": True}
            low.Evidence.witness = lambda _evidence: {"forged": True}
            low.Evidence.verify = lambda *_args, **_kwargs: {"ok": True}
            self.service.view_current(evidence, actor="clerk", purpose="review")
            self.assertTrue(self.service.verify_current(evidence)["ok"])
        finally:
            low.AuthoritySnapshot.root = original_root
            low.AuthoritySnapshot.bind_current = original_bind
            low.Evidence.witness = original_witness
            low.Evidence.verify = original_verify

    def test_authority_record_descriptor_rebinding_cannot_redirect_raw_fields(self):
        evidence = self.accepted()
        self.provider.now = T2
        saved = {
            name: vars(low.AuthorityRecord).get(name, _MISSING)
            for name in ("evidence_id", "decision", "issuer", "at", "revoked")
        }
        try:
            low.AuthorityRecord.evidence_id = property(lambda _row: "FORGED")
            low.AuthorityRecord.decision = property(lambda _row: "DENIED")
            low.AuthorityRecord.issuer = property(lambda _row: "one-issuer")
            low.AuthorityRecord.at = property(lambda _row: T4)
            low.AuthorityRecord.revoked = property(lambda _row: True)
            receipt = self.destroy(evidence)
            self.assertEqual(receipt["at"], T2)
            self.assertTrue(self.service.verify_current(evidence)["ok"])
        finally:
            for name, value in saved.items():
                restore_class_attr(low.AuthorityRecord, name, value)

    def test_current_module_builtin_shadowing_does_not_redirect_bound_graph(self):
        evidence = self.accepted()
        self.provider.now = T2
        names = ("type", "str", "dict", "set", "len", "sorted", "any", "getattr", "ord", "format")
        saved = {name: vars(current_module).get(name, _MISSING) for name in names}
        try:
            for name in names:
                setattr(current_module, name, lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError(name)))
            self.service.view_current(evidence, actor="clerk", purpose="review")
            rebound_service = CurrentCustodyService(self.provider)
            self.assertTrue(rebound_service.verify_current(evidence)["ok"])
        finally:
            for name, value in saved.items():
                restore_module_attr(current_module, name, value)

    def test_hashlib_rebinding_after_import_does_not_redirect_current_graph(self):
        evidence = self.accepted()
        self.provider.now = T2
        original = hashlib.sha256
        try:
            current_module.hashlib.sha256 = lambda _data=b"": (_ for _ in ()).throw(AssertionError("late sha256"))
            self.service.view_current(evidence, actor="clerk", purpose="review")
            self.assertTrue(self.service.verify_current(evidence)["ok"])
        finally:
            hashlib.sha256 = original

    def test_existing_service_survives_provider_and_module_rebinding(self):
        evidence = self.accepted()
        self.provider.now = T2
        saved = (
            current_module.Evidence,
            current_module.AuthoritySnapshot,
            current_module.AuthorityRecord,
            current_module.CustodyError,
            current_module.CurrentCustodyService,
        )
        try:
            self.provider.retained_custody_witness = lambda *_args: {"forged": True}
            self.provider.compare_and_retain_custody_witness = lambda *_args: True
            current_module.Evidence = object
            current_module.AuthoritySnapshot = object
            current_module.AuthorityRecord = object
            current_module.CustodyError = RuntimeError
            current_module.CurrentCustodyService = lambda *_args, **_kwargs: None
            self.service.view_current(evidence, actor="clerk", purpose="review")
            self.assertTrue(self.service.verify_current(evidence)["ok"])
        finally:
            (
                current_module.Evidence,
                current_module.AuthoritySnapshot,
                current_module.AuthorityRecord,
                current_module.CustodyError,
                current_module.CurrentCustodyService,
            ) = saved

    def test_bound_service_has_no_writable_trust_callables(self):
        with self.assertRaises(AttributeError):
            self.service.verify_current = lambda _evidence: {"ok": True}
        with self.assertRaises(AttributeError):
            self.service._retained_witness = lambda *_args: {"forged": True}

    def test_atomic_cas_allows_one_same_predecessor_writer(self):
        evidence = self.accepted()
        left = copy.deepcopy(evidence)
        right = copy.deepcopy(evidence)
        self.provider.now = T2
        self.provider.read_barrier = threading.Barrier(2)
        winners = []
        errors = []

        def worker(target, purpose):
            try:
                self.service.view_current(target, actor=purpose, purpose=purpose)
                winners.append(target)
            except Exception as exc:
                errors.append(exc)

        first = threading.Thread(target=worker, args=(left, "left"))
        second = threading.Thread(target=worker, args=(right, "right"))
        first.start()
        second.start()
        first.join(5)
        second.join(5)
        self.provider.read_barrier = None
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CustodyError)
        winner = winners[0]
        loser = right if winner is left else left
        self.assertEqual(len(winner.events), len(evidence.events) + 1)
        self.assertEqual(len(loser.events), len(evidence.events))

    def test_failed_host_write_does_not_expose_local_mutation(self):
        evidence = self.accepted()
        before = copy.deepcopy(evidence.events)
        self.provider.now = T2
        self.provider.fail_writes = True
        with self.assertRaises(RuntimeError):
            self.service.view_current(evidence, actor="clerk", purpose="review")
        self.assertEqual(evidence.events, before)

    def test_evidence_descriptors_cannot_split_host_cas_from_raw_publication(self):
        evidence = self.accepted()
        self.provider.now = T2
        fields = (
            "case_id",
            "object_id",
            "original_sha256",
            "accepted",
            "legal_hold",
            "destroyed",
            "events",
        )
        saved = {name: vars(low.Evidence).get(name, _MISSING) for name in fields}

        def poison(name):
            def get(instance):
                return object.__getattribute__(instance, "__dict__")[name]

            def set_value(_instance, _value):
                raise AssertionError(f"descriptor setter invoked for {name}")

            return property(get, set_value)

        try:
            for name in fields:
                setattr(low.Evidence, name, poison(name))
            receipt = self.destroy(evidence)
            raw = object.__getattribute__(evidence, "__dict__")
            self.assertEqual(receipt["kind"], "DESTROYED")
            self.assertTrue(raw["destroyed"])
            self.assertTrue(self.service.verify_current(evidence)["ok"])
            retained = self.provider.witnesses[("CASE-1", "OBJ-1")]
            self.assertEqual(retained["event_count"], len(raw["events"]))
            self.assertEqual(retained["head_event_hash"], raw["events"][-1]["event_hash"])
        finally:
            for name, value in saved.items():
                restore_class_attr(low.Evidence, name, value)

    def test_direct_low_level_mutation_cannot_become_current(self):
        evidence = self.accepted()
        self.provider.now = T2
        body = {
            "seq": len(evidence.events) + 1,
            "case_id": evidence.case_id,
            "object_id": evidence.object_id,
            "kind": "VIEWED",
            "actor": "attacker",
            "at": T2,
            "prev_hash": evidence.events[-1]["event_hash"],
            "data": {"purpose": "local-only"},
        }
        body["event_hash"] = hashlib.sha256(
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        evidence.events.append(body)
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_archived_snapshot_root_mismatch_rejects(self):
        evidence = self.accepted()
        self.provider.now = T2
        self.destroy(evidence)
        self.provider.archives[self.snapshot.root] = snapshot("X-")
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_current_snapshot_must_be_archivable_before_commit(self):
        unarchived = snapshot("N-", T1)
        self.provider.current = unarchived
        evidence = self.accepted()
        self.provider.now = T2
        before = copy.deepcopy(evidence.events)
        with self.assertRaises(CustodyError):
            self.destroy(evidence, "N-")
        self.assertEqual(evidence.events, before)
        self.assertFalse(evidence.destroyed)

    def test_host_clock_rollback_makes_retained_future_event_noncurrent(self):
        evidence = self.accepted()
        self.provider.now = T2
        self.service.view_current(evidence, actor="clerk", purpose="review")
        self.provider.now = T1
        with self.assertRaises(CustodyError):
            self.service.verify_current(evidence)

    def test_snapshot_record_root_is_recomputed_without_low_level_properties(self):
        evidence = self.accepted()
        self.provider.now = T2
        original_root = low.AuthorityRecord.root
        try:
            low.AuthorityRecord.root = property(lambda _row: "0" * 64)
            self.destroy(evidence)
            self.assertTrue(self.service.verify_current(evidence)["ok"])
        finally:
            low.AuthorityRecord.root = original_root


if __name__ == "__main__":
    unittest.main()
