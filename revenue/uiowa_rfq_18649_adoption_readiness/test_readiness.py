#!/usr/bin/env python3
"""Tests for the UIOWA-077 organizational AI adoption readiness engine.

These assert behaviour, not shape. The hostile cases are the point: an
individual identity, a team below the contributor floor, an option missing its
basis, a phase inversion, a dependency loop, and a record whose observations
are all unusable.

Run:  python3 -m unittest -v test_readiness
"""

import copy
import csv
import json
import os
import tempfile
import unittest

import readiness as R

HERE = os.path.dirname(os.path.abspath(__file__))


def load(*parts):
    with open(os.path.join(HERE, *parts), "r", encoding="utf-8") as handle:
        return json.load(handle)


MODEL_OBJ = load("model", "indicators.json")
CATALOG_OBJ = load("model", "option_catalog.json")
TEAMS_OBJ = load("fixtures", "synthetic_teams.json")
HOSTILE_TEAMS_OBJ = load("fixtures", "hostile_teams.json")
HOSTILE_CATALOG_OBJ = load("fixtures", "hostile_catalog.json")


def run(teams=None, model=None, catalog=None, **kwargs):
    result, _model, _catalog = R.assess(
        copy.deepcopy(teams if teams is not None else TEAMS_OBJ),
        copy.deepcopy(model if model is not None else MODEL_OBJ),
        copy.deepcopy(catalog if catalog is not None else CATALOG_OBJ),
        **kwargs)
    return result


def team_of(result, team_id):
    for team in result["teams"]:
        if team["team_id"] == team_id:
            return team
    raise AssertionError("team %s not in result" % team_id)


def dim_of(team, dimension_id):
    for dim in team["dimensions"]:
        if dim["dimension_id"] == dimension_id:
            return dim
    raise AssertionError("dimension %s not in team %s" % (dimension_id, team["team_id"]))


def walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            for item in walk_keys(value):
                yield item
    elif isinstance(node, list):
        for value in node:
            for item in walk_keys(value):
                yield item


# --------------------------------------------------------------------------
# Rule 1 - this instrument cannot be turned on a person
# --------------------------------------------------------------------------

class IndividualIdentityTests(unittest.TestCase):

    def test_record_naming_an_employee_is_rejected_not_anonymised(self):
        result = run(teams=HOSTILE_TEAMS_OBJ)
        rejected = {r["team_id"]: r for r in result["rejected_teams"]}
        self.assertIn("T-BAD-IDENTITY", rejected)
        self.assertEqual(["individual_identity_present"], rejected["T-BAD-IDENTITY"]["reasons"])
        self.assertIn("T-BAD-IDENTITY.observations[0].employee_id",
                      rejected["T-BAD-IDENTITY"]["detail"])
        # Rejected means absent from the assessment entirely - not stripped and
        # scored anyway.
        assessed = [t["team_id"] for t in result["teams"]]
        self.assertNotIn("T-BAD-IDENTITY", assessed)

    def test_named_roster_at_team_level_is_also_rejected(self):
        result = run(teams=HOSTILE_TEAMS_OBJ)
        rejected = {r["team_id"]: r for r in result["rejected_teams"]}
        self.assertIn("T-BAD-ROSTER", rejected)
        self.assertIn("T-BAD-ROSTER.respondents", rejected["T-BAD-ROSTER"]["detail"])

    def test_identity_scan_reaches_nested_structures(self):
        hits = R.scan_identity_keys({"a": [{"b": {"netid": "x"}}]}, "rec")
        self.assertEqual(["rec.a[0].b.netid"], hits)

    def test_team_scoped_keys_are_not_flagged(self):
        clean = {"team_id": "T", "team_label": "L", "contributor_count": 5, "observations": []}
        self.assertEqual([], R.scan_identity_keys(clean))

    def test_shipped_fixture_carries_no_individual_identity(self):
        self.assertEqual([], R.scan_identity_keys(TEAMS_OBJ))

    def test_no_individual_identity_key_reaches_the_output(self):
        result = run()
        offenders = sorted({k for k in walk_keys(result)
                            if k.strip().lower() in R.FORBIDDEN_IDENTITY_KEYS})
        self.assertEqual([], offenders)


# --------------------------------------------------------------------------
# Rules 2 and 3 - thin signal is UNKNOWN, and UNKNOWN is not a shortfall
# --------------------------------------------------------------------------

class UnknownHandlingTests(unittest.TestCase):

    def test_team_below_contributor_floor_is_unknown_not_absent(self):
        team = team_of(run(), "T-IAM")
        self.assertEqual(2, team["contributor_count"])
        states = {d["state"] for d in team["dimensions"]}
        self.assertEqual({R.UNKNOWN}, states)
        for dim in team["dimensions"]:
            self.assertEqual("insufficient_contributors", dim["reason"])
        self.assertEqual(0, team["coverage"]["dimensions_with_a_state"])
        self.assertEqual(0, team["coverage"]["absent_of_assessed"])

    def test_thin_team_gets_evidence_requests_and_no_options(self):
        team = team_of(run(), "T-IAM")
        self.assertEqual([], team["plan"])
        self.assertEqual(6, len(team["evidence_requests"]))
        for request in team["evidence_requests"]:
            self.assertTrue(request["validating_evidence"].strip())

    def test_dimension_below_indicator_floor_is_unknown(self):
        dim = dim_of(team_of(run(), "T-RIS"), "available_support")
        self.assertEqual(R.UNKNOWN, dim["state"])
        self.assertEqual("insufficient_indicator_coverage", dim["reason"])

    def test_dimension_with_no_evidence_is_unknown_not_absent(self):
        dim = dim_of(team_of(run(), "T-ESS"), "workflow_fit")
        self.assertEqual(R.UNKNOWN, dim["state"])
        self.assertEqual("no_indicator_evidence", dim["reason"])

    def test_unknown_is_excluded_from_every_denominator(self):
        for team in run()["teams"]:
            cov = team["coverage"]
            self.assertEqual(
                cov["dimensions_with_a_state"],
                cov["established_of_assessed"] + cov["emerging_of_assessed"]
                + cov["absent_of_assessed"])
            self.assertEqual(cov["dimensions_defined"],
                             cov["dimensions_with_a_state"] + cov["dimensions_unknown"])

    def test_unknown_never_produces_a_development_option(self):
        for team in run()["teams"]:
            unknown = set(team["unknown"])
            planned = {item["dimension_id"] for item in team["plan"]}
            self.assertEqual(set(), unknown & planned)

    def test_established_dimension_produces_no_option(self):
        team = team_of(run(), "T-ESS")
        planned = {item["dimension_id"] for item in team["plan"]}
        for strength in team["strengths"]:
            self.assertNotIn(strength, planned)

    def test_lowering_the_contributor_floor_lets_the_thin_team_resolve(self):
        team = team_of(run(min_contributors=2), "T-IAM")
        self.assertNotEqual({R.UNKNOWN}, {d["state"] for d in team["dimensions"]})
        # The floor is a declared parameter, not a hidden constant.
        self.assertEqual(2, run(min_contributors=2)["parameters"]["min_contributors"])


# --------------------------------------------------------------------------
# Rule 4 - recollection is not a record
# --------------------------------------------------------------------------

class EvidenceStrengthTests(unittest.TestCase):

    def test_interview_only_established_is_downgraded_with_a_reason(self):
        team = team_of(run(), "T-RIS")
        dim = dim_of(team, "knowledge_sharing")
        self.assertEqual("EMERGING", dim["state"])
        self.assertTrue(any("recollection_only" in note for note in dim["notes"]))

    def test_same_claim_backed_by_an_artifact_is_not_downgraded(self):
        teams = {"teams": [{
            "team_id": "T-X", "team_label": "fiction", "contributor_count": 4,
            "observations": [
                {"indicator_id": "SHR-1", "state": "ESTABLISHED",
                 "evidence_kind": "artifact", "evidence_source": "SYNTHETIC register"},
                {"indicator_id": "SHR-2", "state": "ESTABLISHED",
                 "evidence_kind": "artifact", "evidence_source": "SYNTHETIC review dates"},
            ]}]}
        dim = dim_of(team_of(run(teams=teams), "T-X"), "knowledge_sharing")
        self.assertEqual("ESTABLISHED", dim["state"])
        self.assertEqual([], dim["notes"])

    def test_downgrade_cannot_manufacture_an_absent_finding(self):
        teams = {"teams": [{
            "team_id": "T-Y", "team_label": "fiction", "contributor_count": 4,
            "observations": [
                {"indicator_id": "SHR-1", "state": "ESTABLISHED",
                 "evidence_kind": "interview_statement", "evidence_source": "SYNTHETIC note"},
                {"indicator_id": "SHR-2", "state": "ESTABLISHED",
                 "evidence_kind": "interview_statement", "evidence_source": "SYNTHETIC note"},
            ]}]}
        dim = dim_of(team_of(run(teams=teams), "T-Y"), "knowledge_sharing")
        self.assertEqual("EMERGING", dim["state"])


# --------------------------------------------------------------------------
# Rule 5 - no effort figure without its basis and its validating evidence
# --------------------------------------------------------------------------

class EffortBasisTests(unittest.TestCase):

    def test_every_shipped_option_carries_basis_and_validating_evidence(self):
        for option in CATALOG_OBJ["options"]:
            effort = option["staff_effort"]
            for field in ("assumption_basis", "validating_evidence"):
                self.assertTrue(
                    isinstance(effort.get(field), str) and effort[field].strip(),
                    "%s has no %s" % (option["option_id"], field))

    def test_every_effort_figure_in_the_output_carries_both_fields(self):
        seen = 0
        for team in run()["teams"]:
            for item in team["plan"]:
                effort = item["staff_effort"]
                seen += 1
                self.assertTrue(effort["assumption_basis"].strip())
                self.assertTrue(effort["validating_evidence"].strip())
                self.assertIn(effort["effort_kind"], R.EFFORT_KINDS)
                self.assertLessEqual(effort["value_low"], effort["value_high"])
        self.assertGreater(seen, 0, "no effort figures were exercised")

    def test_option_missing_assumption_basis_cannot_enter_a_plan(self):
        catalog = copy.deepcopy(CATALOG_OBJ)
        for option in catalog["options"]:
            if option["option_id"] == "OPT-EVAL-01":
                del option["staff_effort"]["assumption_basis"]
        result = run(catalog=catalog)
        rejected = {r["option_id"] for r in result["rejected_options"]}
        self.assertIn("OPT-EVAL-01", rejected)
        planned = {i["option_id"] for t in result["teams"] for i in t["plan"]}
        self.assertNotIn("OPT-EVAL-01", planned)

    def test_option_missing_validating_evidence_cannot_enter_a_plan(self):
        catalog = copy.deepcopy(CATALOG_OBJ)
        for option in catalog["options"]:
            if option["option_id"] == "OPT-LIT-01":
                option["staff_effort"]["validating_evidence"] = "   "
        result = run(catalog=catalog)
        self.assertIn("OPT-LIT-01", {r["option_id"] for r in result["rejected_options"]})

    def test_inverted_and_non_numeric_ranges_are_caught(self):
        self.assertTrue(any(d["code"] == "effort_range_inverted" for d in R.validate_effort(
            {"value_low": 9, "value_high": 2, "unit": "person_hours",
             "effort_kind": "one_time", "assumption_basis": "x",
             "validating_evidence": "y"}, "W")))
        self.assertTrue(any(d["code"] == "effort_not_numeric" for d in R.validate_effort(
            {"value_low": "twelve", "value_high": 20, "unit": "person_hours",
             "effort_kind": "one_time", "assumption_basis": "x",
             "validating_evidence": "y"}, "W")))

    def test_one_time_and_recurring_effort_stay_distinguishable(self):
        self.assertTrue(any(d["code"] == "effort_kind_unknown" for d in R.validate_effort(
            {"value_low": 1, "value_high": 2, "unit": "person_hours",
             "effort_kind": "sometimes", "assumption_basis": "x",
             "validating_evidence": "y"}, "W")))
        kinds = {o["staff_effort"]["effort_kind"] for o in CATALOG_OBJ["options"]}
        self.assertEqual({"one_time", "recurring"}, kinds)


# --------------------------------------------------------------------------
# Option completeness and sequencing
# --------------------------------------------------------------------------

class OptionStructureTests(unittest.TestCase):

    def test_every_planned_option_states_all_four_required_things(self):
        for team in run()["teams"]:
            for item in team["plan"]:
                self.assertTrue(item["capability_gained"].strip())
                self.assertTrue(item["observable_indicator"].strip())
                self.assertIsInstance(item["dependencies"], list)
                self.assertIn(item["horizon"], R.HORIZONS)
                self.assertIsInstance(item["staff_effort"], dict)

    def test_option_without_an_observable_indicator_is_rejected(self):
        result = run(catalog=HOSTILE_CATALOG_OBJ)
        self.assertIn("OPT-X-NOOBS", {r["option_id"] for r in result["rejected_options"]})

    def test_option_triggering_off_unknown_is_rejected(self):
        result = run(catalog=HOSTILE_CATALOG_OBJ)
        self.assertIn("OPT-X-UNKNOWNTRIGGER",
                      {r["option_id"] for r in result["rejected_options"]})

    def test_phase_inversion_is_reported_not_published_as_a_plan(self):
        result = run(catalog=HOSTILE_CATALOG_OBJ)
        findings = [f for t in result["teams"] for f in t["dependency_findings"]]
        inversions = [f for f in findings if f["code"] == "phase_inversion"]
        self.assertTrue(inversions)
        self.assertEqual("OPT-X-EARLY", inversions[0]["where"])
        self.assertEqual("error", inversions[0]["severity"])

    def test_dependency_cycle_is_detected(self):
        result = run(catalog=HOSTILE_CATALOG_OBJ)
        cycles = [d for d in result["diagnostics"] if d["code"] == "dependency_cycle"]
        self.assertTrue(cycles)
        self.assertEqual(["OPT-X-LOOP-A", "OPT-X-LOOP-B"], sorted(cycles[0]["detail"]))

    def test_missing_prerequisite_is_reported(self):
        result = run(catalog=HOSTILE_CATALOG_OBJ)
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_prerequisite", codes)

    def test_shipped_catalog_has_no_cycle_and_no_inversion_in_any_plan(self):
        result = run()
        self.assertEqual([], [d for d in result["diagnostics"]
                              if d["code"] in ("dependency_cycle", "missing_prerequisite")])
        errors = [f for t in result["teams"] for f in t["dependency_findings"]
                  if f["severity"] == "error"]
        self.assertEqual([], errors)

    def test_prerequisite_outside_the_plan_is_an_open_question_not_a_silent_pass(self):
        findings = [f for t in run()["teams"] for f in t["dependency_findings"]]
        open_questions = [f for f in findings if f["code"] == "prerequisite_not_in_plan"]
        self.assertTrue(open_questions)
        for finding in open_questions:
            self.assertEqual("open_question", finding["severity"])
            self.assertIn("Confirm", finding["message"])

    def test_shipped_catalog_covers_all_three_horizons(self):
        self.assertEqual(set(R.HORIZONS), {o["horizon"] for o in CATALOG_OBJ["options"]})


# --------------------------------------------------------------------------
# Hostile and missing data
# --------------------------------------------------------------------------

class HostileDataTests(unittest.TestCase):

    def test_unusable_contributor_count_is_rejected_not_defaulted(self):
        rejected = {r["team_id"]: r for r in run(teams=HOSTILE_TEAMS_OBJ)["rejected_teams"]}
        self.assertIn("T-BAD-COUNT", rejected)
        self.assertIn("T-BAD-NOCOUNT", rejected)
        self.assertEqual(["contributor_count_invalid"], rejected["T-BAD-COUNT"]["reasons"])

    def test_boolean_contributor_count_is_not_read_as_one(self):
        teams = {"teams": [{"team_id": "T-B", "team_label": "fiction",
                            "contributor_count": True, "observations": []}]}
        result = run(teams=teams)
        self.assertEqual([], result["teams"])
        self.assertIn("T-B", {r["team_id"] for r in result["rejected_teams"]})

    def test_unusable_observations_are_rejected_and_leave_unknown_behind(self):
        team = team_of(run(teams=HOSTILE_TEAMS_OBJ), "T-PARTIAL")
        reasons = sorted({r for bad in team["rejected_observations"] for r in bad["reasons"]})
        self.assertEqual(["evidence_kind_invalid", "evidence_source_missing",
                          "indicator_unknown", "state_invalid"], reasons)
        # The surviving evidence is below the floor everywhere, so nothing
        # becomes an ABSENT finding on the strength of discarded records.
        self.assertEqual({R.UNKNOWN}, {d["state"] for d in team["dimensions"]})
        self.assertEqual([], team["plan"])

    def test_duplicate_observation_is_rejected_not_merged(self):
        teams = {"teams": [{
            "team_id": "T-D", "team_label": "fiction", "contributor_count": 4,
            "observations": [
                {"indicator_id": "SUP-1", "state": "ESTABLISHED",
                 "evidence_kind": "artifact", "evidence_source": "SYNTHETIC a"},
                {"indicator_id": "SUP-1", "state": "ABSENT",
                 "evidence_kind": "artifact", "evidence_source": "SYNTHETIC b"},
                {"indicator_id": "SUP-2", "state": "ESTABLISHED",
                 "evidence_kind": "artifact", "evidence_source": "SYNTHETIC c"},
            ]}]}
        result = run(teams=teams)
        team = team_of(result, "T-D")
        self.assertIn("observation_duplicate",
                      {r for bad in team["rejected_observations"] for r in bad["reasons"]})
        self.assertEqual("ESTABLISHED", dim_of(team, "available_support")["state"])

    def test_empty_input_produces_an_empty_assessment_not_a_crash(self):
        result = run(teams={"teams": []})
        self.assertEqual([], result["teams"])
        self.assertTrue(result["content_digest"])

    def test_unknown_dimension_in_the_model_does_not_break_the_catalog(self):
        model = copy.deepcopy(MODEL_OBJ)
        model["dimensions"] = [d for d in model["dimensions"]
                               if d["dimension_id"] != "evaluation_capacity"]
        result = run(model=model)
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("option_dimension_unknown", codes)
        planned = {i["option_id"] for t in result["teams"] for i in t["plan"]}
        self.assertNotIn("OPT-EVAL-01", planned)


# --------------------------------------------------------------------------
# What this artifact must never claim
# --------------------------------------------------------------------------

class NoScoringTests(unittest.TestCase):

    def test_output_contains_no_scoring_or_certification_key(self):
        offenders = sorted({k for k in walk_keys(run())
                            if k.strip().lower() in R.BANNED_OUTPUT_KEYS})
        self.assertEqual([], offenders)

    def test_report_states_it_produces_no_score(self):
        result = run()
        report = R.render_report(result, R.load_indicator_model(MODEL_OBJ)[0])
        for phrase in ("composite score", "maturity level", "peer percentile",
                       "individual employee"):
            self.assertIn(phrase, report)

    def test_fixtures_are_labelled_fiction_in_the_output(self):
        self.assertIn("SYNTHETIC", run()["fiction_notice"])

    def test_fixtures_show_both_a_strength_and_a_real_gap(self):
        team = team_of(run(), "T-ESS")
        self.assertIn("practical_training", team["strengths"])
        self.assertIn("evaluation_capacity", team["gaps"])
        self.assertEqual("ABSENT", dim_of(team, "evaluation_capacity")["state"])


# --------------------------------------------------------------------------
# Reproducibility and exports
# --------------------------------------------------------------------------

class OutputTests(unittest.TestCase):

    def test_two_runs_of_the_same_input_agree_byte_for_byte(self):
        self.assertEqual(run()["content_digest"], run()["content_digest"])

    def test_digest_moves_when_the_evidence_moves(self):
        teams = copy.deepcopy(TEAMS_OBJ)
        teams["teams"][0]["contributor_count"] = 8
        self.assertNotEqual(run()["content_digest"], run(teams=teams)["content_digest"])

    def test_csv_export_keeps_basis_columns_populated(self):
        result = run()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "options.csv")
            R.write_options_csv(path, result)
            with open(path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["assumption_basis"].strip())
            self.assertTrue(row["validating_evidence"].strip())
            self.assertIn(row["horizon"], R.HORIZONS)

    def test_csv_cells_that_look_like_formulas_stay_text(self):
        self.assertEqual("'=SUM(A1:A9)", R._csv_cell("=SUM(A1:A9)"))
        self.assertEqual("plain", R._csv_cell("plain"))

    def test_evidence_request_export_lists_the_outstanding_indicator(self):
        result = run()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "requests.csv")
            R.write_requests_csv(path, result)
            with open(path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        thin = [r for r in rows if r["team_id"] == "T-IAM"]
        self.assertTrue(thin)
        for row in thin:
            self.assertEqual("insufficient_contributors", row["reason"])
            self.assertTrue(row["validating_evidence"].strip())

    def test_instrument_renders_every_defined_indicator(self):
        text = R.render_instrument(MODEL_OBJ)
        for dimension in MODEL_OBJ["dimensions"]:
            for indicator in dimension["indicators"]:
                self.assertIn(indicator["indicator_id"], text)
                self.assertIn(indicator["prompt"], text)
        self.assertIn("recollection is not a record", text)

    def test_cli_writes_the_whole_deliverable_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = R.main(["--outdir", tmp])
            self.assertEqual(0, code)
            for name in ("readiness_assessment.json", "readiness_worksheet.csv",
                         "capability_options.csv", "evidence_requests.csv",
                         "readiness_report.md", "interview_instrument.md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, name)), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
