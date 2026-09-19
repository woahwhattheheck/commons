"""Independent checks: actual published fixture + disposable boundary cases."""
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from . import proposal_profile as profile
    from .verify import Artifact, Event, Snapshot, TERMS, inspect, reconcile
except ImportError:
    import proposal_profile as profile
    from verify import Artifact, Event, Snapshot, TERMS, inspect, reconcile

HERE = Path(__file__).resolve().parent


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.snapshots = []
        for i, mid in enumerate(TERMS):
            gen = f"SYN-G{i}"
            pct, amount, trigger = TERMS[mid]
            p = self.root / f"{mid}.md"
            p.write_text(f"SYNTHETIC {mid} artifact — no real engagement\n", encoding="utf-8")
            a = Artifact(mid + "-A", p.name, "v1", gen, hashlib.sha256(p.read_bytes()).hexdigest(), f"fixture/{mid}/artifact/0")
            epath = self.root / f"{mid}-record.md"
            epath.write_text("SYNTHETIC documentary event; unauthenticated\n", encoding="utf-8")
            proof = Artifact(mid + "-E", epath.name, "v1", gen, hashlib.sha256(epath.read_bytes()).hexdigest(), f"fixture/{mid}/evidence/0")
            event = Event(mid + "-event", trigger, gen, (a.id,), proof.id, "2026-10-03T12:00:00Z", f"fixture/{mid}/event/0")
            events = (event,)
            if mid == "final":
                events = (replace(event, id="final-delivery", kind="final_delivery", at="2026-10-02T12:00:00Z", locator="fixture/final/delivery"), event)
            self.snapshots.append(Snapshot(mid, gen, "USD", pct, amount, trigger, (a,), (proof,), events, (), f"fixture/{mid}"))

    def report(self, row):
        return inspect(row, self.root)

    def codes(self, row):
        return {f["code"] for f in self.report(row)["findings"]}

    def test_three_complete_synthetic_records_not_payment(self):
        for s in self.snapshots:
            r = self.report(s)
            self.assertEqual(r["findings"], [])
            self.assertEqual(r["commercial_record_state"], "recorded_unverified")
            self.assertEqual(r["payment_due"], "NOT_DETERMINED")
            self.assertEqual(r["accepted"], "NOT_DETERMINED")
            self.assertFalse(r["records_authenticated"])
            self.assertFalse(r["invoice_issued"])

    def test_three_amounts_reconcile(self):
        self.assertTrue(reconcile(self.snapshots)["matches_proposed_base"])

    def test_total_only_cannot_hide_redistribution(self):
        rows = list(self.snapshots)
        rows[0] = replace(rows[0], amount_cents=480_000)
        rows[2] = replace(rows[2], amount_cents=960_000)
        self.assertEqual(reconcile(rows)["total_cents"], 2_400_000)
        self.assertFalse(reconcile(rows)["matches_proposed_base"])

    def test_boolean_amount_and_share_rejected(self):
        s = self.snapshots[0]
        for changed in (replace(s, amount_cents=True), replace(s, percent=True)):
            self.assertIn("PROPOSED_TERM_MISMATCH", self.codes(changed))

    def test_wrong_currency_rejected(self):
        self.assertIn("PROPOSED_TERM_MISMATCH", self.codes(replace(self.snapshots[0], currency="EUR")))

    def test_option_leak_rejected(self):
        for value in (True, 0, None):
            self.assertIn("OPTION_LEAKS_INTO_BASE", self.codes(replace(self.snapshots[0], option_included_in_base=value)))

    def test_no_events_remains_not_recorded(self):
        self.assertEqual(self.report(replace(self.snapshots[0], events=()))["commercial_record_state"], "not_recorded")

    def test_open_dependencies_do_not_add_commercial_condition(self):
        for s in self.snapshots[:2]:
            self.assertEqual(self.report(replace(s, open_dependencies=("Unavailable source evidence",)))["commercial_record_state"], "recorded_unverified")

    def test_missing_draft_bytes_do_not_rewrite_delivery_record(self):
        s = self.snapshots[1]
        (self.root / s.artifacts[0].path).unlink()
        r = self.report(s)
        self.assertEqual(r["byte_and_version_integrity"], "unresolved")
        self.assertEqual(r["commercial_record_state"], "recorded_unverified")
        self.assertEqual(r["payment_due"], "NOT_DETERMINED")

    def test_final_delivery_not_acceptance(self):
        s = self.snapshots[2]
        r = self.report(replace(s, events=(s.events[0],)))
        self.assertEqual(r["commercial_record_state"], "not_recorded")

    def test_acceptance_without_delivery_is_conflict(self):
        s = self.snapshots[2]
        self.assertIn("ACCEPTANCE_WITHOUT_PRIOR_DELIVERY_RECORD", self.codes(replace(s, events=(s.events[1],))))

    def test_acceptance_before_delivery_is_conflict(self):
        s = self.snapshots[2]
        bad = replace(s.events[1], at="2026-10-01T12:00:00Z")
        self.assertIn("ACCEPTANCE_WITHOUT_PRIOR_DELIVERY_RECORD", self.codes(replace(s, events=(s.events[0], bad))))

    def test_equal_instant_mixed_offsets_is_consistent(self):
        s = self.snapshots[2]
        events = (replace(s.events[0], at="2026-10-03T08:00:00-04:00"), s.events[1])
        self.assertEqual(self.report(replace(s, events=events))["findings"], [])

    def test_naive_or_invalid_event_time_is_conflict(self):
        s = self.snapshots[0]
        for date in ("2026-99-99", "2026-10-03T12:00:00", ""):
            self.assertIn("EVENT_RECORD_CONFLICT", self.codes(replace(s, events=(replace(s.events[0], at=date),))))

    def test_cross_generation_event_is_conflict(self):
        s = self.snapshots[1]
        self.assertIn("EVENT_RECORD_CONFLICT", self.codes(replace(s, events=(replace(s.events[0], generation="SYN-OTHER"),))))

    def test_missing_generation_is_not_inferred_from_hash(self):
        s = self.snapshots[0]
        self.assertIn("GENERATION_MISSING", self.codes(replace(s, generation="")))
        self.assertIn("EVENT_RECORD_CONFLICT", self.codes(replace(s, generation="", events=(replace(s.events[0], generation=""),))))

    def test_wrong_delivered_set_is_conflict(self):
        s = self.snapshots[1]
        self.assertIn("EVENT_RECORD_CONFLICT", self.codes(replace(s, events=(replace(s.events[0], artifact_ids=()),))))

    def test_duplicate_event_ids_make_all_occurrences_ambiguous(self):
        s = self.snapshots[0]
        r = self.report(replace(s, events=(s.events[0], s.events[0])))
        self.assertTrue(all(e["state"] == "conflicting_record" for e in r["event_records"]))

    def test_missing_documentary_event_evidence_is_conflict(self):
        s = self.snapshots[0]
        (self.root / s.evidence[0].path).unlink()
        self.assertIn("EVENT_RECORD_CONFLICT", self.codes(s))

    def test_changed_bytes_are_not_relabelled_as_new_version(self):
        s = self.snapshots[0]
        (self.root / s.artifacts[0].path).write_text("Changed\n")
        self.assertIn("ARTIFACT_DIGEST_MISMATCH", self.codes(s))

    def test_hash_without_version_is_incomplete(self):
        s = self.snapshots[0]
        self.assertIn("ARTIFACT_VERSION_MISSING", self.codes(replace(s, artifacts=(replace(s.artifacts[0], version=""),))))

    def test_generation_mismatch_is_incomplete(self):
        s = self.snapshots[0]
        self.assertIn("MIXED_DELIVERY_GENERATION", self.codes(replace(s, artifacts=(replace(s.artifacts[0], generation="OTHER"),))))

    def test_duplicate_artifact_ids_are_not_overwritten(self):
        s = self.snapshots[0]
        self.assertIn("DUPLICATE_ARTIFACT_ID", self.codes(replace(s, artifacts=(s.artifacts[0], s.artifacts[0]))))

    def test_empty_packet_is_not_complete(self):
        self.assertIn("EMPTY_DELIVERY_INDEX", self.codes(replace(self.snapshots[0], artifacts=())))

    def test_bad_digest_is_explicit(self):
        s = self.snapshots[0]
        self.assertIn("INVALID_DIGEST", self.codes(replace(s, artifacts=(replace(s.artifacts[0], sha256="bad"),))))

    def test_path_boundaries(self):
        s = self.snapshots[0]
        for p in ("../escape", "/etc/passwd", "C:/test", "x\\y", "x//y", "./file"):
            self.assertIn("ARTIFACT_UNREADABLE", self.codes(replace(s, artifacts=(replace(s.artifacts[0], path=p),))))

    def test_symlink_is_reported_without_following(self):
        s = self.snapshots[0]
        link = self.root / "linked.md"
        link.symlink_to(self.root / s.artifacts[0].path)
        self.assertIn("ARTIFACT_UNREADABLE", self.codes(replace(s, artifacts=(replace(s.artifacts[0], path=link.name),))))

    def test_unicode_path_keeps_exact_content(self):
        s = self.snapshots[0]
        p = self.root / "évidence-研究.md"
        p.write_bytes((self.root / s.artifacts[0].path).read_bytes())
        self.assertEqual(self.report(replace(s, artifacts=(replace(s.artifacts[0], path=p.name),)))["findings"], [])

    def test_read_only_and_deterministic(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        one = [self.report(s) for s in self.snapshots]
        two = [self.report(s) for s in self.snapshots]
        self.assertEqual(one, two)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.source = HERE / "fixtures/upstream-engagement.json"
        self.plan = profile.read(self.source)

    def test_actual_upstream_fixture_byte_binding(self):
        self.assertEqual(profile.blob(self.source.read_bytes()), profile.UPSTREAM_BLOB)

    def test_actual_total_matches_while_split_is_wrong(self):
        result = profile.check(self.plan)
        self.assertEqual(result["declared_total_cents"], 2_400_000)
        self.assertEqual(result["milestone_total_cents"], 2_400_000)
        errors = [d for d in result["diagnostics"] if d["code"] == "MILESTONE_AMOUNT_MISMATCH"]
        self.assertEqual([(e["observed"], e["expected"]) for e in errors], [(480_000, 960_000), (960_000, 480_000)])

    def test_actual_optional_item_is_in_base(self):
        errors = [d for d in profile.check(self.plan)["diagnostics"] if d["code"] == "OPTION_INSIDE_BASE_PACKET"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["locator"], "/milestones/2/index_items/2")

    def test_aligned_copy_has_no_proposal_mismatches(self):
        fixed, changes = profile.align_synthetic(self.plan)
        self.assertTrue(changes)
        self.assertTrue(profile.check(fixed)["aligned_with_bound_proposed_terms"])
        self.assertEqual([m["amount"] for m in fixed["milestones"]], ["9,600.00", "9,600.00", "4,800.00"])

    def test_alignment_preserves_original_and_all_unknowns(self):
        original = copy.deepcopy(self.plan)
        fixed, _ = profile.align_synthetic(self.plan)
        self.assertEqual(original, self.plan)
        for before, after in zip(original["milestones"], fixed["milestones"]):
            for key in ("criteria", "dependencies", "acceptance_record", "submission_state", "delivered_on", "due_date", "transmittal_note"):
                self.assertEqual(before[key], after[key], key)
        self.assertEqual(fixed["separate_optional_items"], [original["milestones"][2]["index_items"][2]])

    def test_alignment_idempotent(self):
        fixed, _ = profile.align_synthetic(self.plan)
        again, edits = profile.align_synthetic(fixed)
        self.assertEqual(fixed, again)
        self.assertEqual(edits, [])

    def test_real_or_missing_synthetic_flag_rejected(self):
        for value in (False, None, "true", 1):
            self.plan["synthetic"] = value
            with self.assertRaises(ValueError):
                profile.align_synthetic(self.plan)

    def test_money_bool_float_ambiguous_and_malformed_grouping_rejected(self):
        for value in (True, 9600.0, "9600", "9,60.00", "NaN", "9,600.000"):
            with self.assertRaises(ValueError, msg=repr(value)):
                profile.cents(value)
        self.assertEqual(profile.cents("$9,600.00"), 960_000)
        self.assertEqual(profile.cents(960_000), 960_000)

    def test_missing_duplicate_and_unknown_milestones_not_aligned(self):
        for records in (self.plan["milestones"][:2], [self.plan["milestones"][0]] * 3):
            bad = {**self.plan, "milestones": records}
            self.assertFalse(profile.check(bad)["aligned_with_bound_proposed_terms"])
            with self.assertRaises(ValueError):
                profile.align_synthetic(bad)

    def test_optional_with_base_reference_needs_human_reconciliation(self):
        self.plan["milestones"][2]["criteria"][0]["evidence_item_ids"].append("IDX-M3-003")
        with self.assertRaises(ValueError):
            profile.align_synthetic(self.plan)

    def test_foreign_optional_item_is_not_silently_removed(self):
        item = self.plan["milestones"][2]["index_items"][2]
        item["item_id"] = "OTHER"
        fixed, _ = profile.align_synthetic(self.plan)
        self.assertFalse(profile.check(fixed)["aligned_with_bound_proposed_terms"])
        self.assertEqual(fixed["milestones"][2]["index_items"][-1]["item_id"], "OTHER")

    def test_cli_exit_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "copy"
            command = [sys.executable, str(HERE / "proposal_profile.py"), str(self.source), "--output-dir", str(out)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(first.returncode, 1, first.stderr)
            self.assertEqual(profile.blob(self.source.read_bytes()), profile.UPSTREAM_BLOB)
            fixed = subprocess.run([sys.executable, str(HERE / "proposal_profile.py"), str(out / "aligned-engagement.json")], capture_output=True, text=True, timeout=10)
            self.assertEqual(fixed.returncode, 0, fixed.stderr)
            second = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(second.returncode, 2)
            self.assertIn("output exists", second.stderr)

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "invalid.json"
            for value in ('{"synthetic":true,"synthetic":false}', '{"x":NaN}'):
                p.write_text(value)
                with self.assertRaises(ValueError):
                    profile.read(p)


if __name__ == "__main__":
    unittest.main()
