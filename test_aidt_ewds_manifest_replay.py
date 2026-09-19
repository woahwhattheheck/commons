"""Independent regressions for AIDT V2 manifest replay and collection semantics.

All records are synthetic. Rehashing below checks internal consistency boundaries;
it neither represents live records nor tests a third-party system.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import unittest

from revenue.aidt_ewds_workshare import core as c


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record(identity, value="payload"):
    return {"record_id": identity, "record_sha256": digest(value)}


def reseal(receipt):
    result = copy.deepcopy(receipt)
    result.pop("receipt_sha256", None)
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    result["receipt_sha256"] = hashlib.sha256(raw.encode("ascii")).hexdigest()
    return result


def migration(good=True, identity="row-1"):
    source = [record(identity)]
    return c.reconcile_migration(source, source if good else [])


def sync(good=True, identity="event-1", payload="payload"):
    event = {"source_system": "salesforce", "target_system": "adobe_lms",
             "event_id": identity, "entity_ref": "synthetic-applicant",
             "operation": "enroll", "payload_sha256": digest(payload)}
    observed = {"accepted": good, "target_ref": "synthetic-target",
                "target_payload_sha256": digest(payload)}
    return c.compile_sync_receipt(event, observed)


def evidence():
    return {key: digest(key) for key in c.REQUIRED_WORKSHARE_EVIDENCE}


class ManifestReplayTests(unittest.TestCase):
    def test_manifest_records_retained_and_order_independent(self):
        rows = [record("b"), record("a")]
        result = c.reconcile_migration(rows, list(reversed(rows)))
        self.assertEqual(result, c.reconcile_migration(list(reversed(rows)), rows))
        self.assertEqual(result["source_records"], [record("a"), record("b")])
        self.assertTrue(c.verify_migration_receipt(result))

    def test_independent_pins_and_changed_source_generation(self):
        first = migration()
        successor = migration(identity="other-row")
        self.assertTrue(c.verify_migration_receipt(successor))
        # A self-consistent replacement remains caller-authored data, not the
        # independently retained generation. Pin mismatch must reject it.
        with self.assertRaisesRegex(c.WorkshareError, "independent pin mismatch"):
            c.verify_migration_receipt(successor,
                expected_source_manifest_sha256=first["source_manifest_sha256"])
        self.assertTrue(c.verify_migration_receipt(first,
            expected_source_manifest_sha256=first["source_manifest_sha256"],
            expected_target_manifest_sha256=first["target_manifest_sha256"]))

    def test_each_independent_pin_is_validated(self):
        for argument in ("expected_source_manifest_sha256", "expected_target_manifest_sha256"):
            with self.subTest(argument=argument):
                with self.assertRaises(c.WorkshareError):
                    c.verify_migration_receipt(migration(), **{argument: "not-a-digest"})

    def test_resealed_contradictory_counts_rejected(self):
        for field, value in (("source_count", 99), ("target_count", 99),
                             ("source_count", True), ("target_count", -1)):
            with self.subTest(field=field, value=value):
                receipt = migration()
                receipt[field] = value
                with self.assertRaises(c.WorkshareError):
                    c.verify_migration_receipt(reseal(receipt))

    def test_resealed_different_manifest_hash_rejected(self):
        for field in ("source_manifest_sha256", "target_manifest_sha256"):
            with self.subTest(field=field):
                receipt = migration()
                receipt[field] = digest("not the actual retained manifest")
                with self.assertRaisesRegex(c.WorkshareError, "semantic or digest mismatch"):
                    c.verify_migration_receipt(reseal(receipt))

    def test_erased_missing_records_cannot_be_reconciled_by_rehash(self):
        receipt = migration(False)
        receipt["missing_record_ids"] = []
        receipt["decision"] = "MIGRATION_RECONCILED"
        with self.assertRaisesRegex(c.WorkshareError, "decision inconsistent"):
            c.verify_migration_receipt(reseal(receipt))
        with self.assertRaises(c.WorkshareError):
            c.compile_readiness(evidence(), [reseal(receipt)], [sync()])

    def test_resealed_finding_ids_replayed_from_manifests(self):
        receipt = c.reconcile_migration([record("missing"), record("shared")],
                                       [record("extra"), record("shared", "different")])
        self.assertTrue(c.verify_migration_receipt(receipt))
        for field in ("missing_record_ids", "extra_record_ids", "mismatched_record_ids"):
            with self.subTest(field=field):
                changed = copy.deepcopy(receipt)
                changed[field] = ["unrelated-id"]
                with self.assertRaises(c.WorkshareError):
                    c.verify_migration_receipt(reseal(changed))

    def test_retained_record_change_requires_new_semantics(self):
        receipt = migration()
        receipt["target_records"][0]["record_sha256"] = digest("different")
        with self.assertRaises(c.WorkshareError):
            c.verify_migration_receipt(reseal(receipt))

    def test_noncanonical_retained_order_rejected(self):
        receipt = c.reconcile_migration([record("b"), record("a")], [record("a"), record("b")])
        receipt["source_records"].reverse()
        with self.assertRaises(c.WorkshareError):
            c.verify_migration_receipt(reseal(receipt))

    def test_summary_findings_must_be_bounded_identifiers(self):
        for findings in ([["nested"]], [1], ["\n"], ["a"] * (c.MAX_RECORDS + 1)):
            with self.subTest(kind=type(findings[0]).__name__):
                receipt = migration(False)
                receipt["missing_record_ids"] = findings
                with self.assertRaises(c.WorkshareError):
                    c.verify_migration_receipt(reseal(receipt))

    def test_empty_collection_is_not_positive_migration_proof(self):
        receipt = c.reconcile_migration([], [])
        self.assertEqual(receipt["decision"], "NO_RECORDS_TO_RECONCILE")
        self.assertTrue(c.verify_migration_receipt(receipt))
        parent = c.compile_readiness(evidence(), [receipt], [sync()])
        self.assertEqual(parent["state"], "HOLD_WORKSHARE_INCOMPLETE")
        self.assertEqual(parent["blocking_migration_receipts"], [receipt["receipt_sha256"]])

    def test_legacy_summary_is_not_silently_upgraded(self):
        receipt = migration()
        receipt["schema"] = "aidt-ewds-migration/v1"
        receipt.pop("source_records")
        receipt.pop("target_records")
        with self.assertRaisesRegex(c.WorkshareError, "regenerate legacy receipt"):
            c.verify_migration_receipt(reseal(receipt))

    def test_identifier_does_not_receive_false_privacy_certification(self):
        receipt = migration(identity="person@example.invalid")
        self.assertEqual(receipt["pii_assessment"], "NOT_PERFORMED")
        self.assertIs(receipt["raw_record_payloads_included"], False)
        self.assertNotIn("contains_live_pii", receipt)
        self.assertEqual(receipt["evidence_authority"], "CALLER_SUPPLIED_MANIFESTS")

    def test_record_bounds_and_plain_types(self):
        for rows in ([record("a")] * (c.MAX_RECORDS + 1), "records", {"records": []}):
            with self.subTest(type=type(rows).__name__):
                with self.assertRaises(c.WorkshareError):
                    c.reconcile_migration(rows, [])
        class CustomList(list):
            pass
        with self.assertRaises(c.WorkshareError):
            c.reconcile_migration(CustomList(), [])

    def test_exhaustive_small_manifest_reference_model(self):
        # Each of three synthetic IDs is absent, payload A or payload B.
        # All 27 x 27 source/target assignments use an independent reference.
        options = list(itertools.product((None, "A", "B"), repeat=3))
        for left, right in itertools.product(options, repeat=2):
            source = {f"id-{i}": value for i, value in enumerate(left) if value is not None}
            target = {f"id-{i}": value for i, value in enumerate(right) if value is not None}
            receipt = c.reconcile_migration([record(i, v) for i, v in source.items()],
                                           [record(i, v) for i, v in target.items()])
            self.assertEqual(receipt["missing_record_ids"], sorted(source.keys() - target.keys()))
            self.assertEqual(receipt["extra_record_ids"], sorted(target.keys() - source.keys()))
            self.assertEqual(receipt["mismatched_record_ids"],
                             sorted(i for i in source.keys() & target.keys() if source[i] != target[i]))
            expected = ("NO_RECORDS_TO_RECONCILE" if not source and not target else
                        "MIGRATION_RECONCILED" if source == target else "HOLD_MIGRATION_RECONCILIATION")
            self.assertEqual(receipt["decision"], expected)
            self.assertTrue(c.verify_migration_receipt(receipt))


class CollectionReadinessTests(unittest.TestCase):
    def test_mixed_migration_batch_holds_with_exact_blocker(self):
        good, bad = migration(identity="a"), migration(False, identity="b")
        parent = c.compile_readiness(evidence(), [good, bad], [sync()])
        self.assertEqual(parent["state"], "HOLD_WORKSHARE_INCOMPLETE")
        self.assertEqual(parent["blocking_migration_receipts"], [bad["receipt_sha256"]])
        self.assertTrue(c.verify_readiness(parent))

    def test_mixed_sync_batch_holds_with_exact_blocker(self):
        good, bad = sync(identity="a"), sync(False, identity="b")
        parent = c.compile_readiness(evidence(), [migration()], [good, bad])
        self.assertEqual(parent["state"], "HOLD_WORKSHARE_INCOMPLETE")
        self.assertEqual(parent["blocking_sync_receipts"], [bad["receipt_sha256"]])
        self.assertTrue(c.verify_readiness(parent))

    def test_all_success_failure_presence_combinations(self):
        choices = ((), (True,), (False,), (True, False), (True, True))
        for mvalues, svalues in itertools.product(choices, repeat=2):
            ms = [migration(value, f"m-{i}") for i, value in enumerate(mvalues)]
            ss = [sync(value, f"s-{i}") for i, value in enumerate(svalues)]
            parent = c.compile_readiness(evidence(), ms, ss)
            expected = bool(mvalues and svalues and all(mvalues) and all(svalues))
            self.assertEqual(parent["state"] == "WORKSHARE_READY_FOR_PRIME_REVIEW", expected)
            self.assertTrue(c.verify_readiness(parent))

    def test_parent_blockers_cannot_be_erased_and_resealed(self):
        parent = c.compile_readiness(evidence(), [migration(False)], [sync()])
        parent["blocking_migration_receipts"] = []
        parent["hold_reasons"] = []
        parent["state"] = "WORKSHARE_READY_FOR_PRIME_REVIEW"
        with self.assertRaises(c.WorkshareError):
            c.verify_readiness(reseal(parent))

    def test_identical_duplicate_receipts_rejected(self):
        m, s = migration(), sync()
        for ms, ss in (([m, m], [s]), ([m], [s, s])):
            with self.subTest(migrations=len(ms), syncs=len(ss)):
                with self.assertRaisesRegex(c.WorkshareError, "duplicate receipt"):
                    c.compile_readiness(evidence(), ms, ss)

    def test_conflicting_current_observations_for_one_event_rejected(self):
        for second in (sync(False), sync(payload="different-payload")):
            with self.subTest(decision=second["decision"]):
                with self.assertRaisesRegex(c.WorkshareError, "conflicting current observations"):
                    c.compile_readiness(evidence(), [migration()], [sync(), second])

    def test_input_mutations_do_not_change_emitted_packet(self):
        m, s, ev = migration(), sync(), evidence()
        parent = c.compile_readiness(ev, [m], [s])
        saved = copy.deepcopy(parent)
        m["source_records"][0]["record_sha256"] = digest("changed later")
        m["missing_record_ids"].append("invented-later")
        s["observed_accepted"] = False
        ev.clear()
        self.assertEqual(parent, saved)
        self.assertTrue(c.verify_readiness(parent))

    def test_collection_order_is_deterministic(self):
        ms = [migration(identity="a"), migration(identity="b")]
        ss = [sync(identity="a"), sync(identity="b")]
        self.assertEqual(c.compile_readiness(evidence(), ms, ss),
                         c.compile_readiness(evidence(), ms[::-1], ss[::-1]))

    def test_no_external_or_complete_project_authority(self):
        parent = c.compile_readiness(evidence(), [migration()], [sync()])
        self.assertEqual(parent["coverage_authority"], "CALLER_SELECTED_COLLECTION_NOT_PROJECT_COMPLETENESS")
        for field in ("prime_qualified", "alabama_buys_registered", "external_outbound_authorized",
                      "proposal_submission_authorized", "buyer_acceptance_claim_authorized",
                      "award_claim_authorized", "payment_claim_authorized", "revenue_claim_authorized"):
            self.assertIs(parent[field], False)
            changed = copy.deepcopy(parent)
            changed[field] = 0  # JSON 0 must not alias source-literal false.
            with self.assertRaises(c.WorkshareError):
                c.verify_readiness(reseal(changed))

    def test_sync_false_authority_and_true_observation_are_exact_booleans(self):
        for field, value in (("observed_accepted", 1), ("transport_performed_by_compiler", 0),
                             ("external_submission_authorized", 0)):
            changed = sync()
            changed[field] = value
            with self.assertRaises(c.WorkshareError):
                c.verify_sync_receipt(reseal(changed))

    def test_child_collection_bound_checked_before_member_traversal(self):
        invalid = [object()] * (c.MAX_CHILD_RECEIPTS + 1)
        with self.assertRaisesRegex(c.WorkshareError, "collection limit exceeded"):
            c.compile_readiness(evidence(), invalid, [])
        with self.assertRaisesRegex(c.WorkshareError, "collection limit exceeded"):
            c.compile_readiness(evidence(), [], invalid)

    def test_total_record_budget_checked_before_semantic_traversal(self):
        # Sentinel records would otherwise fail _obj: the aggregate length must
        # reject before traversing a >20,000-record supplied collection.
        fake = {"source_records": [object()] * c.MAX_RECORDS,
                "target_records": [object()] * c.MAX_RECORDS}
        with self.assertRaisesRegex(c.WorkshareError, "record budget exceeded"):
            c.compile_readiness(evidence(), [fake, fake], [])

    def test_malformed_child_receipt_containers_rejected(self):
        for bad in ({}, "receipts", iter([])):
            with self.assertRaises(c.WorkshareError):
                c.compile_readiness(evidence(), bad, [])


if __name__ == "__main__":
    unittest.main()
