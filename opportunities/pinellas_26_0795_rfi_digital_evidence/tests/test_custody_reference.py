import copy
import hashlib
import json
import unittest

from custody_reference import AuthorityRecord, AuthoritySnapshot, CustodyError, Evidence

T0 = "2026-09-14T04:30:00Z"
T1 = "2026-09-14T04:31:00Z"
T2 = "2026-09-14T04:32:00Z"
T3 = "2026-09-14T04:33:00Z"
T4 = "2026-09-14T04:34:00Z"
T5 = "2026-09-14T04:35:00Z"


def rehash(event):
    body = {key: event[key] for key in event if key != "event_hash"}
    event["event_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def record(evidence_id, kind, decision, *, generation=1, issuer="records", at=T1,
           revoked=False, case_id="CASE-1", object_id="OBJ-1"):
    return AuthorityRecord(
        evidence_id=evidence_id,
        kind=kind,
        generation=generation,
        case_id=case_id,
        object_id=object_id,
        decision=decision,
        issuer=issuer,
        at=at,
        revoked=revoked,
    )


def destruction_snapshot(*, approval_a_issuer="judge-a", approval_b_issuer="judge-b",
                         approval_a_extra=None, retention_case="CASE-1", authority_at=T1):
    rows = [
        record("RET-7", "RETENTION_ELIGIBILITY", "ELIGIBLE", issuer="schedule", at=authority_at,
               case_id=retention_case),
        record("NOTICE-55", "NOTICE_COMPLETE", "COMPLETE", issuer="notice-office", at=authority_at),
        record("APP-A", "APPROVAL", "APPROVED", issuer=approval_a_issuer, at=authority_at),
        record("APP-B", "APPROVAL", "APPROVED", issuer=approval_b_issuer, at=authority_at),
        record("DEST-AUTH", "DESTRUCTION_AUTHORITY", "AUTHORIZED", issuer="records-director", at=authority_at),
    ]
    if approval_a_extra is not None:
        rows.append(approval_a_extra)
    return AuthoritySnapshot(rows)


def hold_enable_snapshot():
    return AuthoritySnapshot([
        record("HOLD-9", "LEGAL_HOLD", "ENABLED", generation=1, issuer="court", at=T1)
    ])


def hold_release_snapshot():
    return AuthoritySnapshot([
        record("HOLD-9", "LEGAL_HOLD", "ENABLED", generation=1, issuer="court", at=T1),
        record("HOLD-9", "LEGAL_HOLD", "RELEASED", generation=2, issuer="court", at=T2),
    ])


class TestCustody(unittest.TestCase):
    def new(self):
        return Evidence.submit(case_id="CASE-1", object_id="OBJ-1", original=b"abc", actor="submitter", at=T0)

    def accepted(self):
        evidence = self.new()
        evidence.accept(actor="judge", at=T1)
        return evidence

    def verify_now(self, evidence, *snapshots):
        mapping = {snapshot.root: snapshot for snapshot in snapshots}
        return evidence.verify(
            expected_witness=evidence.witness(),
            authority_snapshots=mapping,
            trusted_snapshot_roots=set(mapping),
        )

    def destroy(self, evidence, snapshot=None, trusted_root=None, **overrides):
        snapshot = snapshot or destruction_snapshot()
        args = {
            "actor": "records",
            "at": T3,
            "snapshot": snapshot,
            "trusted_snapshot_root": trusted_root or snapshot.root,
            "retention_evidence_id": "RET-7",
            "notice_evidence_id": "NOTICE-55",
            "approval_evidence_ids": ["APP-A", "APP-B"],
            "destruction_authority_evidence_id": "DEST-AUTH",
        }
        args.update(overrides)
        return evidence.destroy(**args)

    def test_submit_verifies_against_external_witness(self):
        self.assertTrue(self.verify_now(self.new())["ok"])

    def test_external_witness_digest_tamper_rejected(self):
        evidence = self.new()
        witness = evidence.witness()
        witness["witness_sha256"] = "0" * 64
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_external_witness_from_different_history_rejected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.view(actor="clerk", at=T1, purpose="review")
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_view_is_audited(self):
        evidence = self.new()
        evidence.view(actor="clerk", at=T1, purpose="review")
        self.assertEqual(evidence.events[-1]["kind"], "VIEWED")
        self.assertTrue(self.verify_now(evidence)["ok"])

    def test_empty_view_purpose_rejected(self):
        with self.assertRaises(CustodyError):
            self.new().view(actor="clerk", at=T1, purpose=" ")

    def test_non_string_view_purpose_rejected(self):
        with self.assertRaises(CustodyError):
            self.new().view(actor="clerk", at=T1, purpose=None)

    def test_classification_bool_strict(self):
        with self.assertRaises(CustodyError):
            self.new().classify(actor="clerk", at=T1, status="REVIEW", confidential=1)

    def test_accept_locks_original(self):
        evidence = self.accepted()
        with self.assertRaises(CustodyError):
            evidence.replace_original(new_bytes=b"changed", actor="clerk", at=T2)

    def test_double_accept_rejected(self):
        evidence = self.accepted()
        with self.assertRaises(CustodyError):
            evidence.accept(actor="judge", at=T2)

    def test_replace_before_accept_changes_hash_and_verifies(self):
        evidence = self.new()
        old = evidence.original_sha256
        evidence.replace_original(new_bytes=b"changed", actor="clerk", at=T1)
        self.assertNotEqual(old, evidence.original_sha256)
        self.assertTrue(self.verify_now(evidence)["ok"])

    def test_destruction_requires_accepted_evidence(self):
        with self.assertRaises(CustodyError):
            self.destroy(self.new())

    def test_hold_blocks_destruction(self):
        evidence = self.accepted()
        hold = hold_enable_snapshot()
        evidence.set_hold(actor="records", at=T2, snapshot=hold,
                          trusted_snapshot_root=hold.root, authority_evidence_id="HOLD-9")
        with self.assertRaises(CustodyError):
            self.destroy(evidence, at=T3)

    def test_hold_release_is_authority_bound_and_verifies(self):
        evidence = self.accepted()
        enabled = hold_enable_snapshot()
        released = hold_release_snapshot()
        evidence.set_hold(actor="records", at=T2, snapshot=enabled,
                          trusted_snapshot_root=enabled.root, authority_evidence_id="HOLD-9")
        evidence.set_hold(actor="records", at=T3, snapshot=released,
                          trusted_snapshot_root=released.root, authority_evidence_id="HOLD-9")
        self.assertFalse(evidence.legal_hold)
        self.assertTrue(self.verify_now(evidence, enabled, released)["ok"])

    def test_release_without_existing_hold_rejected(self):
        evidence = self.accepted()
        released = hold_release_snapshot()
        with self.assertRaises(CustodyError):
            evidence.set_hold(actor="records", at=T3, snapshot=released,
                              trusted_snapshot_root=released.root, authority_evidence_id="HOLD-9")

    def test_caller_minted_hold_release_root_rejected(self):
        evidence = self.accepted()
        enabled = hold_enable_snapshot()
        attacker = AuthoritySnapshot([
            record("HOLD-9", "LEGAL_HOLD", "RELEASED", generation=1, issuer="attacker", at=T2)
        ])
        evidence.set_hold(actor="records", at=T2, snapshot=enabled,
                          trusted_snapshot_root=enabled.root, authority_evidence_id="HOLD-9")
        with self.assertRaises(CustodyError):
            evidence.set_hold(actor="records", at=T3, snapshot=attacker,
                              trusted_snapshot_root=enabled.root, authority_evidence_id="HOLD-9")

    def test_missing_retention_evidence_rejected(self):
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), retention_evidence_id="NO-SUCH-RETENTION")

    def test_missing_notice_evidence_rejected(self):
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), notice_evidence_id="NO-SUCH-NOTICE")

    def test_two_distinct_approval_ids_required(self):
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), approval_evidence_ids=["APP-A", "APP-A"])

    def test_two_distinct_approval_issuers_required(self):
        snapshot = destruction_snapshot(approval_a_issuer="same", approval_b_issuer="same")
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), snapshot=snapshot)

    def test_revoked_current_approval_rejected(self):
        revoked = record("APP-A", "APPROVAL", "APPROVED", generation=2,
                         issuer="judge-a", at=T2, revoked=True)
        snapshot = destruction_snapshot(approval_a_extra=revoked)
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), snapshot=snapshot)

    def test_future_authority_record_rejected(self):
        snapshot = destruction_snapshot(authority_at=T5)
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), snapshot=snapshot, at=T3)

    def test_wrong_subject_authority_rejected(self):
        snapshot = destruction_snapshot(retention_case="CASE-X")
        with self.assertRaises(CustodyError):
            self.destroy(self.accepted(), snapshot=snapshot)

    def test_caller_minted_destruction_root_rejected(self):
        evidence = self.accepted()
        attacker = destruction_snapshot()
        independently_trusted_other = AuthoritySnapshot([
            record("HOLD-X", "LEGAL_HOLD", "ENABLED", issuer="court")
        ])
        with self.assertRaises(CustodyError):
            self.destroy(evidence, snapshot=attacker, trusted_root=independently_trusted_other.root)

    def test_successful_destruction_receipt_binds_authority_generation(self):
        evidence = self.accepted()
        snapshot = destruction_snapshot()
        receipt = self.destroy(evidence, snapshot=snapshot)
        data = receipt["data"]
        self.assertEqual(data["authority_snapshot_root"], snapshot.root)
        self.assertEqual(data["retention"]["evidence_id"], "RET-7")
        self.assertEqual(data["notice"]["evidence_id"], "NOTICE-55")
        self.assertEqual([binding["evidence_id"] for binding in data["approvals"]], ["APP-A", "APP-B"])
        self.assertEqual(data["destruction_authority"]["evidence_id"], "DEST-AUTH")
        self.assertTrue(evidence.destroyed)
        self.assertTrue(self.verify_now(evidence, snapshot)["ok"])

    def test_destruction_after_authorized_hold_release_verifies(self):
        evidence = self.accepted()
        enabled = hold_enable_snapshot()
        released = hold_release_snapshot()
        destroy = destruction_snapshot(authority_at=T3)
        evidence.set_hold(actor="records", at=T2, snapshot=enabled,
                          trusted_snapshot_root=enabled.root, authority_evidence_id="HOLD-9")
        evidence.set_hold(actor="records", at=T3, snapshot=released,
                          trusted_snapshot_root=released.root, authority_evidence_id="HOLD-9")
        self.destroy(evidence, snapshot=destroy, at=T4)
        self.assertTrue(self.verify_now(evidence, enabled, released, destroy)["ok"])

    def test_post_destroy_lifecycle_blocked(self):
        evidence = self.accepted()
        snapshot = destruction_snapshot()
        self.destroy(evidence, snapshot=snapshot)
        with self.assertRaises(CustodyError):
            evidence.view(actor="x", at=T4, purpose="peek")

    def test_coherent_fully_rehashed_alternate_history_rejected_by_external_witness(self):
        evidence = self.accepted()
        enabled = hold_enable_snapshot()
        released = hold_release_snapshot()
        evidence.set_hold(actor="records", at=T2, snapshot=enabled,
                          trusted_snapshot_root=enabled.root, authority_evidence_id="HOLD-9")
        evidence.set_hold(actor="records", at=T3, snapshot=released,
                          trusted_snapshot_root=released.root, authority_evidence_id="HOLD-9")
        evidence.view(actor="clerk", at=T4, purpose="review")
        retained_witness = copy.deepcopy(evidence.witness())

        forged_view = copy.deepcopy(evidence.events[-1])
        forged_view["seq"] = 3
        forged_view["prev_hash"] = evidence.events[1]["event_hash"]
        rehash(forged_view)
        evidence.events = [evidence.events[0], evidence.events[1], forged_view]
        self.assertFalse(evidence.legal_hold)

        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=retained_witness)

    def test_authority_root_transplant_rejected_even_with_attacker_witness(self):
        evidence = self.accepted()
        legitimate = hold_enable_snapshot()
        attacker = AuthoritySnapshot([
            record("HOLD-9", "LEGAL_HOLD", "ENABLED", generation=1, issuer="attacker", at=T1)
        ])
        evidence.set_hold(actor="records", at=T2, snapshot=legitimate,
                          trusted_snapshot_root=legitimate.root, authority_evidence_id="HOLD-9")
        event = evidence.events[-1]
        event["data"]["authority_snapshot_root"] = attacker.root
        event["data"]["authority"] = attacker.bind_current(
            evidence_id="HOLD-9", case_id="CASE-1", object_id="OBJ-1",
            kind="LEGAL_HOLD", decision="ENABLED", transition_at=T2,
        )
        rehash(event)
        attacker_witness = evidence.witness()
        with self.assertRaises(CustodyError):
            evidence.verify(
                expected_witness=attacker_witness,
                authority_snapshots={legitimate.root: legitimate, attacker.root: attacker},
                trusted_snapshot_roots={legitimate.root},
            )

    def test_stale_approval_generation_rejected_after_local_rehash(self):
        old = record("APP-A", "APPROVAL", "APPROVED", generation=1, issuer="judge-a", at=T1)
        current = record("APP-A", "APPROVAL", "APPROVED", generation=2, issuer="judge-a", at=T2)
        snapshot = AuthoritySnapshot([
            record("RET-7", "RETENTION_ELIGIBILITY", "ELIGIBLE", issuer="schedule", at=T1),
            record("NOTICE-55", "NOTICE_COMPLETE", "COMPLETE", issuer="notice-office", at=T1),
            old, current,
            record("APP-B", "APPROVAL", "APPROVED", issuer="judge-b", at=T1),
            record("DEST-AUTH", "DESTRUCTION_AUTHORITY", "AUTHORIZED", issuer="records-director", at=T1),
        ])
        evidence = self.accepted()
        receipt = self.destroy(evidence, snapshot=snapshot)
        receipt["data"]["approvals"][0] = {
            "evidence_id": "APP-A", "generation": 1, "record_root": old.root,
        }
        rehash(receipt)
        forged_witness = evidence.witness()
        with self.assertRaises(CustodyError):
            evidence.verify(
                expected_witness=forged_witness,
                authority_snapshots={snapshot.root: snapshot},
                trusted_snapshot_roots={snapshot.root},
            )

    def test_missing_archived_authority_snapshot_rejected(self):
        evidence = self.accepted()
        hold = hold_enable_snapshot()
        evidence.set_hold(actor="records", at=T2, snapshot=hold,
                          trusted_snapshot_root=hold.root, authority_evidence_id="HOLD-9")
        witness = evidence.witness()
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness, trusted_snapshot_roots={hold.root})

    def test_event_mutation_detected(self):
        evidence = self.new()
        evidence.view(actor="clerk", at=T1, purpose="review")
        witness = evidence.witness()
        evidence.events[1]["data"]["purpose"] = "tamper"
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_event_deletion_detected(self):
        evidence = self.new()
        evidence.view(actor="a", at=T1, purpose="x")
        evidence.view(actor="b", at=T2, purpose="y")
        witness = evidence.witness()
        del evidence.events[1]
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_event_reorder_detected(self):
        evidence = self.new()
        evidence.view(actor="a", at=T1, purpose="x")
        evidence.view(actor="b", at=T2, purpose="y")
        witness = evidence.witness()
        evidence.events[1], evidence.events[2] = evidence.events[2], evidence.events[1]
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_case_identity_tamper_detected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.events[0]["case_id"] = "CASE-2"
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_whole_second_utc_required(self):
        with self.assertRaises(CustodyError):
            Evidence.submit(case_id="C", object_id="O", original=b"x", actor="a",
                            at="2026-09-14T04:30:00.1Z")

    def test_timezone_offset_rejected(self):
        with self.assertRaises(CustodyError):
            Evidence.submit(case_id="C", object_id="O", original=b"x", actor="a",
                            at="2026-09-14T00:30:00-04:00")

    def test_backward_timestamp_rejected_without_state_mutation(self):
        evidence = self.accepted()
        evidence.view(actor="a", at=T3, purpose="x")
        hold = hold_enable_snapshot()
        before = len(evidence.events)
        with self.assertRaises(CustodyError):
            evidence.set_hold(actor="records", at=T2, snapshot=hold,
                              trusted_snapshot_root=hold.root, authority_evidence_id="HOLD-9")
        self.assertFalse(evidence.legal_hold)
        self.assertEqual(len(evidence.events), before)

    def test_failed_accept_does_not_lock(self):
        evidence = self.new()
        evidence.view(actor="a", at=T2, purpose="x")
        with self.assertRaises(CustodyError):
            evidence.accept(actor="judge", at=T1)
        self.assertFalse(evidence.accepted)

    def test_preaccept_replace_is_audited(self):
        evidence = self.new()
        old = evidence.original_sha256
        evidence.replace_original(new_bytes=b"changed", actor="clerk", at=T1)
        self.assertEqual(evidence.events[-1]["data"]["old_sha256"], old)
        self.assertEqual(evidence.events[-1]["data"]["new_sha256"], evidence.original_sha256)

    def test_current_digest_state_tamper_detected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.original_sha256 = "0" * 64
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_uppercase_digest_is_not_valid_sha256_representation(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.original_sha256 = evidence.original_sha256.upper()
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_nonhex_event_hash_rejected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.events[0]["event_hash"] = "g" * 64
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_accepted_state_tamper_detected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.accepted = True
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_hold_state_tamper_detected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.legal_hold = True
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_destroyed_state_tamper_detected(self):
        evidence = self.new()
        witness = evidence.witness()
        evidence.destroyed = True
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_semantic_event_tamper_detected_even_if_rehashed(self):
        evidence = self.accepted()
        witness = evidence.witness()
        forged = copy.deepcopy(evidence.events[-1])
        forged["seq"] = 3
        forged["prev_hash"] = evidence.events[-1]["event_hash"]
        forged["at"] = T2
        rehash(forged)
        evidence.events.append(forged)
        with self.assertRaises(CustodyError):
            evidence.verify(expected_witness=witness)

    def test_authority_duplicate_generation_rejected(self):
        row = record("A", "APPROVAL", "APPROVED")
        with self.assertRaises(CustodyError):
            AuthoritySnapshot([row, row])

    def test_authority_decision_must_match_kind(self):
        with self.assertRaises(CustodyError):
            record("A", "APPROVAL", "ELIGIBLE")

    def test_authority_root_is_deterministic_across_input_order(self):
        a = record("A", "APPROVAL", "APPROVED", issuer="judge-a")
        b = record("B", "APPROVAL", "APPROVED", issuer="judge-b")
        self.assertEqual(AuthoritySnapshot([a, b]).root, AuthoritySnapshot([b, a]).root)

    def test_hash_chain_is_deterministic(self):
        first = self.new()
        second = self.new()
        self.assertEqual(first.events, second.events)
        self.assertEqual(first.witness(), second.witness())


if __name__ == "__main__":
    unittest.main()
