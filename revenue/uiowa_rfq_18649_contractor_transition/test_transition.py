#!/usr/bin/env python3
"""UIOWA-108 -- tests for the contractor-transition demonstration.

Run:
    python3 -m unittest -v test_transition

The order's completion condition is the spec: the example must distinguish
completed access changes, unresolved ownership and missing evidence
"without inserting real account data". Both halves are asserted here.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

import scenario
import transition

HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(HERE, "fixtures", "contractor_transition.json")
UNSAFE = os.path.join(HERE, "fixtures", "contractor_transition_unsafe.json")


def load(path):
    return transition.load(path)


def report_for(packet):
    report, _issues = transition.build(packet)
    return report


def item(report, item_id):
    rows = [i for i in report.items if i["item_id"] == item_id]
    assert rows, "no item %s" % item_id
    return rows[0]


def minimal_closed_packet():
    """The smallest packet where every item is genuinely complete."""
    return {
        "packet_id": "TEST-CLOSED",
        "transition": {"departing_ref": "SYN-PERSON-001"},
        "people": [
            {"id": "SYN-PERSON-001", "role": "contractor", "employment_type": "contractor",
             "service": "ESS", "account_name": "syn-c-1", "synthetic": True},
            {"id": "SYN-PERSON-002", "role": "lead", "employment_type": "staff",
             "service": "ESS", "account_name": "syn-s-2", "synthetic": True},
        ],
        "applications": [
            {"id": "SYN-APP-001", "name": "App", "service": "ESS",
             "owner_ref": "SYN-PERSON-001", "successor_ref": "SYN-PERSON-002", "synthetic": True},
        ],
        "service_identities": [],
        "runbooks": [],
        "access_changes": [
            {"id": "SYN-CHG-001", "subject_ref": "SYN-PERSON-001", "target_ref": "SYN-APP-001",
             "action": "REASSIGN_OWNER", "status": "COMPLETED", "completed_at": "2026-09-15",
             "evidence_ref": "synthetic://test/evidence-1", "synthetic": True},
        ],
    }


class TestTheThreeStatesStaySeparate(unittest.TestCase):
    """A careless handoff report collapses completed, unresolved and unknown
    into one green checkmark. These four cases are the ones that get
    collapsed."""

    def setUp(self):
        self.report = report_for(load(CLEAN))

    def test_completed_needs_a_dated_record_and_an_evidence_locator(self):
        row = item(self.report, "SYN-APP-001")
        self.assertEqual(row["state"], "COMPLETED")
        self.assertTrue(row["evidence_refs"])

    def test_no_successor_is_unresolved_ownership_not_missing_evidence(self):
        """We know exactly what is wrong: the contractor still owns it and
        nobody has picked it up. That is a live gap, not an absence of
        information."""
        row = item(self.report, "SYN-APP-002")
        self.assertEqual(row["state"], "UNRESOLVED_OWNERSHIP")
        self.assertIsNone(row["successor_ref"])
        self.assertIn("no successor", " ".join(row["reasons"]))

    def test_a_named_successor_is_a_plan_not_evidence(self):
        """SYN-SVC-002 has a successor named and a request raised. Nothing
        shows the handoff happened, so it cannot read as complete."""
        row = item(self.report, "SYN-SVC-002")
        self.assertEqual(row["state"], "NO_EVIDENCE")
        self.assertEqual(row["successor_ref"], "SYN-PERSON-003")
        self.assertIn("a plan, not evidence", " ".join(row["reasons"]))

    def test_status_completed_without_a_locator_is_not_completed(self):
        """Somebody typing COMPLETED into a field is not evidence. This is
        the single most common way a handoff report lies."""
        row = item(self.report, "SYN-RB-001")
        self.assertEqual(row["state"], "NO_EVIDENCE")
        self.assertIn("no evidence locator", " ".join(row["reasons"]))

    def test_the_three_states_account_for_every_item(self):
        counts = self.report.counts()
        self.assertEqual(sum(counts.values()), len(self.report.items))
        self.assertEqual(sorted(counts), sorted(transition.STATES))

    def test_the_scenario_shows_both_a_strength_and_real_gaps(self):
        counts = self.report.counts()
        self.assertEqual(counts["COMPLETED"], 2)
        self.assertEqual(counts["UNRESOLVED_OWNERSHIP"], 2)
        self.assertEqual(counts["NO_EVIDENCE"], 2)


class TestClosureIsFailClosed(unittest.TestCase):
    def test_one_open_item_keeps_the_transition_open(self):
        report = report_for(load(CLEAN))
        self.assertFalse(report.transition_closed())
        self.assertEqual(len(report.open_items()), 4)

    def test_all_completed_closes_it(self):
        report = report_for(minimal_closed_packet())
        self.assertTrue(report.transition_closed())

    def test_an_empty_packet_is_not_closed_by_vacuous_truth(self):
        """Nothing to check is not the same as everything checked. A packet
        with no items must not report a closed transition."""
        packet = minimal_closed_packet()
        packet["applications"] = []
        packet["access_changes"] = []
        report = report_for(packet)
        self.assertEqual(report.items, [])
        self.assertFalse(report.transition_closed())

    def test_no_completion_percentage_or_score_is_produced(self):
        """A percentage here would average an unresolved service identity
        against a completed one and produce a reassuring number."""
        report = report_for(load(CLEAN))
        payload = json.dumps(report.as_dict()).lower()
        for banned in ("percent", "score", "maturity", "rating", "grade"):
            self.assertNotIn(banned, payload, "found %r in the report" % banned)


class TestRealismGuard(unittest.TestCase):
    """"without inserting real account data" -- enforced, not conventional."""

    def setUp(self):
        self.issues, _ = scenario.validate_packet(load(UNSAFE))
        self.codes = set(i.code for i in self.issues)

    def test_a_resolvable_address_is_refused(self):
        self.assertIn("REAL_LOOKING_EMAIL", self.codes)

    def test_a_bare_account_name_is_refused(self):
        self.assertIn("REAL_LOOKING_ACCOUNT_NAME", self.codes)

    def test_an_identifier_that_does_not_announce_itself_is_refused(self):
        self.assertIn("IDENTIFIER_NOT_MARKED_SYNTHETIC", self.codes)

    def test_a_record_not_declaring_itself_fictional_is_refused(self):
        self.assertIn("RECORD_NOT_MARKED_SYNTHETIC", self.codes)

    def test_a_nine_digit_run_is_refused_anywhere_in_the_record(self):
        self.assertIn("POSSIBLE_REAL_ID_NUMBER", self.codes)

    def test_an_unsafe_packet_is_not_deliverable(self):
        self.assertFalse(scenario.is_deliverable(self.issues))

    def test_the_clean_packet_passes_the_guard(self):
        """A guard that fires on everything gets switched off. The clean
        packet must come through with zero safety issues."""
        issues, _ = scenario.validate_packet(load(CLEAN))
        safety = [i.as_dict() for i in issues if i.is_safety]
        self.assertEqual(safety, [])
        self.assertTrue(scenario.is_deliverable(issues))

    def test_the_guard_proves_it_can_fail(self):
        """Take the packet that passes, inject one real-looking address, and
        assert it flips. A guard that has never gone red is worth nothing."""
        packet = copy.deepcopy(load(CLEAN))
        issues, _ = scenario.validate_packet(packet)
        self.assertTrue(scenario.is_deliverable(issues))

        packet["people"][1]["email"] = "j.doe@uiowa.edu"
        issues, _ = scenario.validate_packet(packet)
        self.assertFalse(scenario.is_deliverable(issues))
        self.assertIn("REAL_LOOKING_EMAIL", [i.code for i in issues])

    def test_reserved_invalid_tld_is_the_only_safe_address_shape(self):
        for unsafe in ("a@b.com", "a@uiowa.edu", "a@example.org", "a@localhost.test"):
            self.assertIsNone(scenario.SAFE_EMAIL.match(unsafe), unsafe)
        for safe in ("syn-1@example.invalid", "syn-svc-2@fictional.invalid"):
            self.assertIsNotNone(scenario.SAFE_EMAIL.match(safe), safe)


class TestReferentialIntegrity(unittest.TestCase):
    def setUp(self):
        self.issues, _ = scenario.validate_packet(load(UNSAFE))
        self.codes = [i.code for i in self.issues]

    def test_a_dangling_reference_is_reported(self):
        self.assertIn("DANGLING_REFERENCE", self.codes)

    def test_a_duplicate_record_id_is_reported(self):
        self.assertIn("DUPLICATE_RECORD_ID", self.codes)

    def test_out_of_vocabulary_action_and_status_are_reported(self):
        fields = [i.field for i in self.issues if i.code == "UNKNOWN_VOCABULARY_VALUE"]
        self.assertIn("action", fields)
        self.assertIn("status", fields)

    def test_a_broken_reference_cannot_read_as_completed(self):
        """A report that says 'done' about a record pointing at nothing is
        worse than silence."""
        packet = minimal_closed_packet()
        packet["applications"][0]["successor_ref"] = "SYN-PERSON-999"
        report = report_for(packet)
        self.assertEqual(item(report, "SYN-APP-001")["state"], "NO_EVIDENCE")
        self.assertIn("broken reference", " ".join(item(report, "SYN-APP-001")["reasons"]))

    def test_a_packet_with_no_departing_person_is_reported(self):
        packet = minimal_closed_packet()
        packet["transition"] = {}
        issues, _ = scenario.validate_packet(packet)
        self.assertIn("MISSING_REQUIRED_FIELD",
                      [i.code for i in issues if i.record_id == "transition"])

    def test_integrity_problems_still_render_a_report(self):
        """A broken reference is a finding. The report must still be produced
        so somebody can see it -- unlike unsafe data, which is refused."""
        packet = minimal_closed_packet()
        packet["applications"][0]["owner_ref"] = "SYN-PERSON-001"
        packet["applications"][0]["successor_ref"] = "SYN-PERSON-999"
        report, issues = transition.build(packet)
        self.assertTrue(scenario.is_deliverable(issues))
        self.assertIn("NO_EVIDENCE", transition.render_markdown(report))


class TestCliContract(unittest.TestCase):
    """Exit codes carry meaning: 0 closed, 1 open items, 2 bad input,
    3 refused for unsafe content."""

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "transition.py")] + list(args),
            cwd=HERE, capture_output=True, text=True,
        )

    def test_open_transition_exits_one_and_writes_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_cli("--input", CLEAN, "--outdir", tmp)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            for name in ("transition_items.csv", "transition_report.json", "transition_report.md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, name)), name)
            self.assertIn("closed=False", proc.stderr)

    def test_unsafe_packet_exits_three_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_cli("--input", UNSAFE, "--outdir", tmp)
            self.assertEqual(proc.returncode, 3, proc.stdout)
            self.assertIn("REFUSED", proc.stderr)
            self.assertEqual(os.listdir(tmp), [],
                             "a refused packet must not leave artifacts behind")

    def test_malformed_json_exits_two_without_a_traceback(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{ nope")
            path = fh.name
        try:
            proc = self.run_cli("--input", path)
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn("not valid JSON", proc.stderr)
        finally:
            os.unlink(path)

    def test_a_missing_file_exits_two_without_a_traceback(self):
        proc = self.run_cli("--input", os.path.join(HERE, "nope.json"))
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stderr)


class TestFictionIsLabelled(unittest.TestCase):
    def test_the_report_says_it_is_fictional_on_the_first_screen(self):
        text = transition.render_markdown(report_for(load(CLEAN)))
        self.assertIn("fictional", text.lower())
        self.assertIn("not a", text.lower())
        self.assertIn("Still UNKNOWN", text)

    def test_the_report_carries_the_prohibited_interpretations(self):
        payload = report_for(load(CLEAN)).as_dict()
        prohibited = payload["meta"]["prohibited_interpretation"]
        self.assertIn("University of Iowa finding", prohibited)
        self.assertIn("employee performance assessment", prohibited)
        self.assertEqual(payload["meta"]["authority"], "FICTIONAL_REHEARSAL_ONLY")

    def test_join_keys_match_the_landed_synthetic_collection(self):
        payload = report_for(load(CLEAN)).as_dict()
        self.assertTrue(payload["meta"]["synthetic"])
        for row in payload["items"]:
            self.assertIn(row["service"], scenario.SERVICES)


class TestCommittedSampleIsNotStale(unittest.TestCase):
    """A checked-in artifact that has drifted from the code that made it
    reads as current and is not. The render is deterministic, so this is an
    exact comparison."""

    def test_sample_markdown_matches_a_fresh_render(self):
        path = os.path.join(HERE, "sample_output", "transition_report.md")
        with open(path, encoding="utf-8") as fh:
            committed = fh.read()
        self.assertEqual(
            committed, transition.render_markdown(report_for(load(CLEAN))),
            "sample_output/ is stale -- regenerate with: "
            "python3 transition.py --input fixtures/contractor_transition.json --outdir sample_output",
        )

    def test_sample_json_matches_a_fresh_build(self):
        path = os.path.join(HERE, "sample_output", "transition_report.json")
        with open(path, encoding="utf-8") as fh:
            committed = json.load(fh)
        fresh = json.loads(json.dumps(report_for(load(CLEAN)).as_dict(), sort_keys=True))
        self.assertEqual(committed, fresh)


if __name__ == "__main__":
    unittest.main(verbosity=2)
