#!/usr/bin/env python3
"""Tests for the register projection and its conformance harness.

Run:
    python3 -m unittest -v test_conformance

These exist because field-shape conformance is not semantic conformance. The
integration test runs the register's real validator; the rest assert the
mapping does not quietly make a record read stronger than its source.
"""

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

import conformance
import project

HERE = os.path.dirname(os.path.abspath(__file__))
# In the repository this lane sits directly under revenue/, so "..'" is the
# right root. UIOWA_REVENUE_ROOT overrides it so the suite can be run in full
# from a staging checkout instead of skipping its integration tests there.
REVENUE = os.path.abspath(os.environ.get("UIOWA_REVENUE_ROOT")
                          or os.path.join(HERE, ".."))
DECLARED = os.path.join(HERE, "divergences.json")
VALIDATOR = os.path.join(REVENUE, conformance.VALIDATOR_REL)

# The register's own contract, restated here so these tests fail if the
# projection drifts even when the sibling lane is not present to run.
EV_RE = re.compile(r"^EV-SYN-(ESS|RIS|IAM)-(SD|SEC|DEP|AI)-[A-Z]+-[0-9]{3}$")
OBS_RE = re.compile(r"^OBS-SYN-(ESS|RIS|IAM)-(SD|SEC|DEP|AI)-[0-9]{3}$")
FND_RE = re.compile(r"^FND-SYN-(ESS|RIS|IAM)-(SD|SEC|DEP|AI)-[0-9]{3}$")
STATES = {"SUPPORTING", "CONFLICTING", "EVIDENCE_OF_ABSENCE", "NO_EVIDENCE_OBSERVED"}
CONFIDENCE = {"HIGH", "MODERATE", "LOW", "UNRESOLVED", "NOT_EVIDENCED"}


def projected():
    return project.project_all(REVENUE)


class TestTheProjectionSatisfiesTheRegisterContract(unittest.TestCase):
    def setUp(self):
        self.rows, self.skipped, self.absent = projected()
        if not self.rows:
            self.skipTest("no sibling lane outputs present to project")

    def test_identifiers_match_the_registers_patterns(self):
        for row in self.rows:
            self.assertRegex(row["evidence_id"], EV_RE)
            self.assertRegex(row["observation_id"], OBS_RE)
            self.assertRegex(row["finding_id"], FND_RE)

    def test_identifiers_carry_the_group_and_area_scope_marker(self):
        for row in self.rows:
            marker = "-%s-%s-" % (row["group"], row["area"])
            for field in ("evidence_id", "observation_id", "finding_id"):
                self.assertIn(marker, row[field], row[field])

    def test_evidence_ids_are_unique(self):
        ids = [r["evidence_id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_enums_are_inside_the_registers_vocabulary(self):
        for row in self.rows:
            self.assertIn(row["evidence_state"], STATES)
            self.assertIn(row["confidence"], CONFIDENCE)

    def test_the_registers_conditional_rules_are_satisfied(self):
        for row in self.rows:
            if row["evidence_state"] == "NO_EVIDENCE_OBSERVED":
                self.assertEqual(row["confidence"], "NOT_EVIDENCED")
            if row["evidence_state"] == "CONFLICTING":
                self.assertEqual(row["confidence"], "UNRESOLVED")
                self.assertTrue(row["conflict_group"].strip())
            if row["evidence_state"] == "EVIDENCE_OF_ABSENCE":
                for field in ("universe_definition", "enumerator_authority",
                              "completeness_basis"):
                    self.assertTrue(row[field].strip(), field)

    def test_no_required_free_text_field_is_blank(self):
        for field in ("source_type", "source_ref", "captured_at",
                      "represented_period", "claim", "scope_limit", "follow_up"):
            for row in self.rows:
                self.assertTrue(row[field].strip(), "%s blank in %s" % (field, row["evidence_id"]))

    def test_the_csv_carries_exactly_the_registers_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.csv")
            conformance.write_register_csv(self.rows, path)
            with open(path, encoding="utf-8") as fh:
                header = fh.readline().strip().split(",")
            self.assertEqual(header, project.REGISTER_COLUMNS)


class TestTheProjectionNeverReadsStrongerThanItsSource(unittest.TestCase):
    def test_an_unevidenced_source_value_never_projects_to_supporting(self):
        self.assertEqual(conformance.favourability_problems(), [])

    def test_the_check_proves_it_can_fail(self):
        """A checker that has never gone red is worth nothing."""
        original = conformance.MAPPINGS["inventory"]
        try:
            bad = dict(original)
            bad["UNSUPPORTED_CLAIM"] = ("SUPPORTING", "HIGH")
            conformance.MAPPINGS["inventory"] = bad
            problems = conformance.favourability_problems()
            self.assertTrue(problems)
            self.assertEqual(problems[0]["source_value"], "UNSUPPORTED_CLAIM")
        finally:
            conformance.MAPPINGS["inventory"] = original

    def test_the_source_classification_survives_in_the_row(self):
        """The enum cannot hold it, so it is written verbatim into
        scope_limit. Losing it is the failure this projection exists to
        avoid."""
        rows, _s, _a = projected()
        if not rows:
            self.skipTest("no sibling lane outputs present")
        inventory = [r for r in rows if r.get("_order") == "UIOWA-071"]
        self.assertTrue(inventory)
        for row in inventory:
            self.assertIn("source classification", row["scope_limit"])


class TestDivergencesAreDeclared(unittest.TestCase):
    def setUp(self):
        self.declared = conformance.load_declared(DECLARED)

    def test_there_are_no_undeclared_collapses(self):
        self.assertEqual(conformance.undeclared_collapses(self.declared), [])

    def test_every_declared_divergence_is_real(self):
        """A declaration for a collapse that does not happen is noise; it
        would also let a real one hide behind it."""
        for d in self.declared["declared"]:
            table = None
            for name, mapping in conformance.MAPPINGS.items():
                if all(v in mapping for v in d["source_values"]):
                    table = mapping
                    break
            self.assertIsNotNone(table, d["id"])
            targets = set(tuple(table[v]) for v in d["source_values"])
            self.assertEqual(len(targets), 1,
                             "%s declares a collapse that does not occur" % d["id"])
            self.assertEqual(list(targets)[0], tuple(d["register_target"]), d["id"])

    def test_the_collapse_detector_proves_it_can_fail(self):
        original = conformance.MAPPINGS["transition"]
        try:
            bad = dict(original)
            bad["COMPLETED"] = ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED")
            conformance.MAPPINGS["transition"] = bad
            problems = conformance.undeclared_collapses(self.declared)
            self.assertTrue(problems)
            self.assertEqual(problems[0]["table"], "transition")
        finally:
            conformance.MAPPINGS["transition"] = original

    def test_the_transition_distinction_is_recorded_as_surviving(self):
        ids = [s["id"] for s in self.declared["verified_survivals"]]
        self.assertIn("SURV-108-01", ids)

    def test_unresolved_ownership_and_missing_evidence_do_not_collapse(self):
        table = conformance.MAPPINGS["transition"]
        self.assertNotEqual(table["UNRESOLVED_OWNERSHIP"], table["NO_EVIDENCE"])


class TestNothingSyntheticIsLaundered(unittest.TestCase):
    def test_every_row_declares_itself_fictional(self):
        rows, _s, _a = projected()
        if not rows:
            self.skipTest("no sibling lane outputs present")
        for row in rows:
            self.assertIn("FICTIONAL", row["scope_limit"], row["evidence_id"])

    def test_every_source_locator_is_unmistakably_synthetic(self):
        rows, _s, _a = projected()
        if not rows:
            self.skipTest("no sibling lane outputs present")
        for row in rows:
            self.assertTrue(row["source_ref"].startswith("synthetic://"), row["source_ref"])


class TestAbsentSiblingIsReportedNotPassed(unittest.TestCase):
    def test_a_missing_lane_output_is_recorded_as_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows, skipped, absent = project.project_all(tmp)
            self.assertEqual(rows, [])
            self.assertEqual(len(absent), len(project.SOURCES))
            for a in absent:
                self.assertIn("not present", a["reason"])

    def test_a_missing_validator_does_not_report_conformant(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = os.path.join(tmp, "out")
            code = conformance.main(["--revenue-root", tmp, "--outdir", outdir])
            self.assertEqual(code, 3, "an unverifiable run must not exit 0")
            with open(os.path.join(outdir, "conformance.json"), encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertNotEqual(payload["status"], "CONFORMANT")

    def test_a_bad_root_exits_two(self):
        self.assertEqual(
            conformance.main(["--revenue-root", os.path.join(HERE, "nope")]), 2)


class TestAgainstTheRealValidator(unittest.TestCase):
    """The integration test. Skipped with a stated reason if the sibling lane
    is not checked out -- never silently passed."""

    def setUp(self):
        if not os.path.exists(VALIDATOR):
            self.skipTest("register validator absent at %s; conformance NOT verified"
                          % conformance.VALIDATOR_REL)

    def test_the_register_validator_accepts_every_projected_row(self):
        rows, _s, _a = projected()
        if not rows:
            self.skipTest("no sibling lane outputs present to project")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "projected.csv")
            conformance.write_register_csv(rows, path)
            code, out, err = conformance.run_validator(VALIDATOR, path)
            self.assertEqual(code, 0, "register rejected the projection:\n%s" % err)
            self.assertIn("OK rows=%d" % len(rows), out)

    def test_the_validator_rejects_a_deliberately_broken_row(self):
        """Proves the integration test is actually exercising the validator
        and not passing on an empty file."""
        rows, _s, _a = projected()
        if not rows:
            self.skipTest("no sibling lane outputs present to project")
        broken = copy.deepcopy(rows)
        broken[0]["evidence_state"] = "NO_EVIDENCE_OBSERVED"
        broken[0]["confidence"] = "HIGH"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "broken.csv")
            conformance.write_register_csv(broken, path)
            code, _out, err = conformance.run_validator(VALIDATOR, path)
            self.assertEqual(code, 1)
            self.assertIn("NOT_EVIDENCED", err)

    def test_the_cli_reports_conformant_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, os.path.join(HERE, "conformance.py"),
                 "--revenue-root", REVENUE, "--outdir", tmp],
                cwd=HERE, capture_output=True, text=True,
            )
            self.assertIn("status=", proc.stderr)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("validator_exit=0", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
