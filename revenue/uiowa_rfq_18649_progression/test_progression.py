#!/usr/bin/env python3
"""Regression tests for the improvement-path method.

Organized around the order's completion bar:

* `NoAspirationalEndpointTests` -- a target must be earned by the evidence the
  path produces, never claimed. The hard requirement.
* `BaselineTests`               -- an unestablished baseline produces no path and
  never falls back to level 1.
* `ObservableAdvancementTests`  -- a step nobody can check is not a plan.
* `EffortAndSkillTests`         -- costs are stated, and partial totals say so.
* `HostileInputTests`           -- malformed input is refused by name.

Run:  python3 -m unittest -v test_progression.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

import progression
from progression import (
    ASSESSMENT_AREAS,
    BASELINE_UNKNOWN,
    EVIDENCE_KIND_CAPS,
    FEASIBLE,
    MAX_LEVEL_GAIN,
    REFUSED_ASPIRATIONAL_JUMP,
    REFUSED_EVIDENCE_CAP,
    REFUSED_NO_OBSERVABLE,
    REFUSED_UNMET_PREREQUISITE,
    PathProposal,
    Profile,
    ProgressionError,
    evaluate_all,
    evaluate_path,
    load_paths,
    load_profiles,
    read_json,
    render_markdown,
    to_csv_rows,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(HERE, "fixtures", "profiles.json")
PATHS = os.path.join(HERE, "fixtures", "paths.json")


def make_profile(**overrides):
    payload = {
        "profile_id": "PROF-T-01",
        "assessment_area": "security",
        "group": "ESS",
        "practice": "test practice",
        "assessment_status": "assessed",
        "evidence_assumptions": [
            {
                "kind": "policy_document",
                "statement": "a policy exists",
                "basis": "ASSUMED for this test",
            }
        ],
    }
    payload.update(overrides)
    return Profile(payload)


def make_step(**overrides):
    step = {
        "step_id": "S1",
        "capability_change": "do the thing",
        "produces_evidence_kind": "single_observed_instance",
        "observable_advancement": "a dated record exists",
        "effort_person_days": 3,
        "skills_needed": ["a skill"],
        "prerequisites": [],
    }
    step.update(overrides)
    return step


def make_path(**overrides):
    payload = {
        "path_id": "PATH-T-01",
        "profile_id": "PROF-T-01",
        "variant": "direct",
        "target_level": 3,
        "steps": [make_step()],
    }
    payload.update(overrides)
    return PathProposal(payload)


def fixture_result():
    return evaluate_all(
        load_paths(read_json(PATHS)), load_profiles(read_json(PROFILES))
    )


def path_named(result, path_id):
    return next(r for r in result["paths"] if r["path_id"] == path_id)


# ---------------------------------------------------------------------------
# The hard requirement
# ---------------------------------------------------------------------------


class NoAspirationalEndpointTests(unittest.TestCase):
    """A target is earned by the evidence the path produces, or refused."""

    def test_documents_alone_cannot_reach_a_practice_level(self):
        """The single most important assertion in this suite.

        "Write a policy, reach level 4" is the shape of every aspirational
        roadmap. It is refused by arithmetic here: policy and procedure documents
        cap at level 2 whatever effort they carry.
        """
        path = make_path(
            target_level=4,
            steps=[
                make_step(step_id="A", produces_evidence_kind="procedure_document"),
                make_step(step_id="B", produces_evidence_kind="policy_document",
                          effort_person_days=100),
            ],
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], REFUSED_EVIDENCE_CAP)
        self.assertEqual(record["evidence_ceiling_of_this_path"], 2)
        self.assertIn("not its volume", record["reason"])
        # And it names what kind of evidence would actually reach the target.
        self.assertEqual(
            record["evidence_kind_needed"],
            ["repeated_instances", "outcome_measurement"],
        )

    def test_effort_cannot_buy_a_level(self):
        """The same wrong-kind path at 1 day and at 1000 days is refused alike."""
        for days in (1, 1000):
            with self.subTest(days=days):
                path = make_path(
                    target_level=4,
                    steps=[
                        make_step(
                            produces_evidence_kind="policy_document",
                            effort_person_days=days,
                        )
                    ],
                )
                record = evaluate_path(path, make_profile())
                self.assertEqual(record["verdict"], REFUSED_EVIDENCE_CAP)

    def test_the_right_evidence_kind_is_accepted(self):
        """The refusal is about kind, so the correct kind must pass."""
        path = make_path(
            target_level=4,
            steps=[make_step(produces_evidence_kind="repeated_instances")],
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], FEASIBLE)
        self.assertEqual(record["evidence_ceiling_of_this_path"], 4)

    def test_a_jump_beyond_two_levels_is_refused(self):
        path = make_path(
            target_level=5,
            steps=[make_step(produces_evidence_kind="outcome_measurement")],
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], REFUSED_ASPIRATIONAL_JUMP)
        self.assertEqual(record["level_gain"], 3)
        self.assertIn("aspiration, not a path", record["reason"])

    def test_exactly_two_levels_is_allowed(self):
        """The boundary is inclusive: the order asks for one-to-two levels."""
        path = make_path(
            target_level=4,
            steps=[make_step(produces_evidence_kind="repeated_instances")],
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["level_gain"], MAX_LEVEL_GAIN)
        self.assertEqual(record["verdict"], FEASIBLE)

    def test_a_target_at_or_below_the_baseline_is_refused(self):
        for target in (1, 2):
            with self.subTest(target=target):
                path = make_path(target_level=target)
                record = evaluate_path(path, make_profile())
                self.assertEqual(record["verdict"], REFUSED_ASPIRATIONAL_JUMP)
                self.assertIn("nothing to advance", record["reason"])

    def test_level_five_needs_outcome_measurement_specifically(self):
        """Repeated instances reach 4 and stop. Level 5 is about outcomes."""
        profile = make_profile(
            evidence_assumptions=[
                {"kind": "repeated_instances", "statement": "s", "basis": "ASSUMED"}
            ]
        )
        repeated = evaluate_path(
            make_path(
                target_level=5,
                steps=[make_step(produces_evidence_kind="repeated_instances")],
            ),
            profile,
        )
        self.assertEqual(repeated["verdict"], REFUSED_EVIDENCE_CAP)
        measured = evaluate_path(
            make_path(
                target_level=5,
                steps=[make_step(produces_evidence_kind="outcome_measurement")],
            ),
            profile,
        )
        self.assertEqual(measured["verdict"], FEASIBLE)

    def test_no_output_presents_a_baseline_as_observed_fact(self):
        result = fixture_result()
        for record in result["paths"]:
            basis = record["baseline"]["basis"]
            if record["baseline"]["maturity_rank"] is not None:
                self.assertIn("ASSUMED", basis)
                self.assertIn("not an observation", basis)
            self.assertEqual(
                record["content_class"],
                "SYNTHETIC_ASSUMPTION_SET_NOT_A_UNIVERSITY_BASELINE",
            )
        text = render_markdown(result)
        self.assertIn("assumption set", text)
        self.assertIn("None describes the University of Iowa", text)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


class BaselineTests(unittest.TestCase):
    def test_an_unassessed_profile_has_no_level_and_gets_no_path(self):
        """Unassessed is an open question, not a weak result."""
        profile = make_profile(assessment_status="unassessed",
                               evidence_assumptions=[])
        baseline = profile.baseline()
        self.assertIsNone(baseline["maturity_rank"])
        self.assertNotEqual(baseline["maturity_rank"], 1)
        record = evaluate_path(make_path(), profile)
        self.assertEqual(record["verdict"], BASELINE_UNKNOWN)
        self.assertIsNone(record["level_gain"])
        self.assertTrue(record["what_would_unblock_it"])

    def test_no_stated_evidence_is_unknown_not_level_one(self):
        """Absence of stated evidence is not evidence of absence."""
        profile = make_profile(evidence_assumptions=[])
        baseline = profile.baseline()
        self.assertIsNone(baseline["maturity_rank"])
        self.assertIn("Not level 1", baseline["basis"])

    def test_not_applicable_gets_no_level(self):
        profile = make_profile(assessment_status="not_applicable")
        self.assertIsNone(profile.baseline()["maturity_rank"])

    def test_the_baseline_is_the_strongest_evidence_kind(self):
        profile = make_profile(
            evidence_assumptions=[
                {"kind": "policy_document", "statement": "s", "basis": "b"},
                {"kind": "single_observed_instance", "statement": "s", "basis": "b"},
            ]
        )
        self.assertEqual(profile.baseline()["maturity_rank"], 3)

    def test_the_baseline_reports_the_assumptions_it_rests_on(self):
        baseline = make_profile().baseline()
        self.assertEqual(len(baseline["supporting_evidence"]), 1)
        self.assertIn("basis", baseline["supporting_evidence"][0])

    def test_csv_writes_an_unknown_baseline_as_a_word(self):
        """A blank or a 0 here would sort an unassessed practice to the bottom."""
        result = fixture_result()
        rows = to_csv_rows(result)
        header = rows[0]
        baseline_col = header.index("baseline_level")
        verdict_col = header.index("verdict")
        seen = 0
        for row in rows[1:]:
            if row[verdict_col] != BASELINE_UNKNOWN:
                continue
            seen += 1
            self.assertEqual(row[baseline_col], "UNKNOWN")
            self.assertNotEqual(row[baseline_col], "")
            self.assertNotEqual(row[baseline_col], "0")
            self.assertNotEqual(row[baseline_col], "1")
        self.assertEqual(seen, 1)


# ---------------------------------------------------------------------------
# Observable advancement
# ---------------------------------------------------------------------------


class ObservableAdvancementTests(unittest.TestCase):
    def test_a_step_with_no_observable_advancement_is_refused(self):
        path = make_path(
            target_level=3,
            steps=[make_step(observable_advancement="")],
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], REFUSED_NO_OBSERVABLE)
        self.assertIn("not made into one by writing TBD", record["reason"])

    def test_the_refusal_names_the_offending_step(self):
        path = make_path(
            target_level=3,
            steps=[
                make_step(step_id="GOOD"),
                make_step(step_id="BAD", observable_advancement=""),
            ],
        )
        record = evaluate_path(path, make_profile())
        self.assertIn("BAD", record["reason"])
        self.assertNotIn("GOOD", record["reason"])

    def test_every_feasible_path_lists_its_observables(self):
        result = fixture_result()
        feasible = [r for r in result["paths"] if r["verdict"] == FEASIBLE]
        self.assertTrue(feasible)
        for record in feasible:
            self.assertEqual(
                len(record["observable_advancement"]), len(record["steps"])
            )
            for item in record["observable_advancement"]:
                self.assertTrue(item["observable"].strip())


# ---------------------------------------------------------------------------
# Prerequisites, effort, skills
# ---------------------------------------------------------------------------


class EffortAndSkillTests(unittest.TestCase):
    def test_an_unmet_internal_prerequisite_is_refused(self):
        path = make_path(steps=[make_step(prerequisites=["MISSING"])])
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], REFUSED_UNMET_PREREQUISITE)
        self.assertIn("MISSING", record["reason"])

    def test_a_prerequisite_met_by_another_step_is_fine(self):
        path = make_path(
            steps=[
                make_step(step_id="A"),
                make_step(step_id="B", prerequisites=["A"]),
            ]
        )
        self.assertEqual(evaluate_path(path, make_profile())["verdict"], FEASIBLE)

    def test_an_external_prerequisite_is_allowed_and_surfaced(self):
        """Somebody else's dependency is visible, not silently absorbed."""
        path = make_path(
            steps=[make_step(prerequisites=["EXTERNAL:a shared service export"])]
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], FEASIBLE)
        self.assertEqual(
            record["external_prerequisites"], ["EXTERNAL:a shared service export"]
        )

    def test_an_unestimated_step_makes_the_total_a_floor(self):
        """A partial total is never completed to a round number."""
        path = make_path(
            steps=[
                make_step(step_id="A", effort_person_days=3),
                make_step(step_id="B", effort_person_days="UNKNOWN"),
            ]
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(record["verdict"], FEASIBLE)
        self.assertEqual(record["effort_person_days_known"], 3)
        self.assertTrue(record["effort_is_partial"])
        self.assertEqual(record["effort_unestimated_steps"], ["B"])
        self.assertIn("FLOOR, not a total", record["effort_statement"])

    def test_a_fully_estimated_path_is_not_marked_partial(self):
        record = evaluate_path(make_path(), make_profile())
        self.assertFalse(record["effort_is_partial"])
        self.assertNotIn("FLOOR", record["effort_statement"])

    def test_skills_are_collected_across_steps(self):
        path = make_path(
            steps=[
                make_step(step_id="A", skills_needed=["reporting"]),
                make_step(step_id="B", skills_needed=["identity administration",
                                                      "reporting"]),
            ]
        )
        record = evaluate_path(path, make_profile())
        self.assertEqual(
            record["skills_needed"], ["identity administration", "reporting"]
        )

    def test_fixture_carries_an_unestimated_step(self):
        result = fixture_result()
        partial = [
            r for r in result["paths"]
            if r["verdict"] == FEASIBLE and r["effort_is_partial"]
        ]
        self.assertTrue(partial, "fixture should demonstrate a partial total")


# ---------------------------------------------------------------------------
# Variants and coverage
# ---------------------------------------------------------------------------


class VariantAndCoverageTests(unittest.TestCase):
    def test_all_four_assessment_areas_have_a_feasible_path(self):
        """The order asks for synthetic paths in each of the four areas."""
        result = fixture_result()
        self.assertEqual(
            result["coverage"]["areas_with_a_feasible_path"],
            sorted(ASSESSMENT_AREAS),
        )
        self.assertEqual(result["coverage"]["areas_without_a_feasible_path"], [])

    def test_limited_capacity_and_shared_service_variants_are_present(self):
        result = fixture_result()
        variants = {
            r["variant"] for r in result["paths"] if r["verdict"] == FEASIBLE
        }
        self.assertIn("limited_capacity", variants)
        self.assertIn("shared_service", variants)
        self.assertIn("direct", variants)

    def test_a_limited_capacity_variant_reaches_the_same_level_for_less(self):
        """The alternative is a different route, not a lower ambition."""
        result = fixture_result()
        direct = path_named(result, "PATH-SYN-SEC-01")
        limited = path_named(result, "PATH-SYN-SEC-02")
        self.assertEqual(direct["target_level"], limited["target_level"])
        self.assertEqual(direct["verdict"], FEASIBLE)
        self.assertEqual(limited["verdict"], FEASIBLE)
        self.assertLess(
            limited["effort_person_days_known"],
            direct["effort_person_days_known"],
        )

    def test_the_fixture_demonstrates_every_verdict(self):
        result = fixture_result()
        self.assertEqual(
            set(result["counts_by_verdict"]),
            {
                FEASIBLE,
                BASELINE_UNKNOWN,
                REFUSED_EVIDENCE_CAP,
                REFUSED_ASPIRATIONAL_JUMP,
                REFUSED_NO_OBSERVABLE,
                REFUSED_UNMET_PREREQUISITE,
            },
        )


# ---------------------------------------------------------------------------
# Hostile input
# ---------------------------------------------------------------------------


class HostileInputTests(unittest.TestCase):
    def test_an_unrecognized_evidence_kind_is_refused(self):
        """An uncapped kind could buy any level, so it cannot be accepted."""
        with self.assertRaises(ProgressionError) as ctx:
            make_profile(
                evidence_assumptions=[
                    {"kind": "vibes", "statement": "s", "basis": "b"}
                ]
            )
        self.assertIn("vibes", str(ctx.exception))
        self.assertIn("cannot be capped", str(ctx.exception))

    def test_an_evidence_assumption_without_a_basis_is_refused(self):
        with self.assertRaises(ProgressionError) as ctx:
            make_profile(
                evidence_assumptions=[
                    {"kind": "policy_document", "statement": "s"}
                ]
            )
        self.assertIn("indistinguishable from an observation", str(ctx.exception))

    def test_a_step_without_an_evidence_kind_is_refused(self):
        with self.assertRaises(ProgressionError) as ctx:
            make_path(steps=[make_step(produces_evidence_kind=None)])
        self.assertIn("cannot be checked against the target level",
                      str(ctx.exception))

    def test_an_unknown_assessment_area_is_refused(self):
        with self.assertRaises(ProgressionError):
            make_profile(assessment_area="astrology")

    def test_an_out_of_range_target_is_refused(self):
        for target in (0, 6, -1):
            with self.subTest(target=target):
                with self.assertRaises(ProgressionError):
                    make_path(target_level=target)

    def test_a_non_integer_target_is_refused(self):
        for target in ("3", 3.5, True):
            with self.subTest(target=target):
                with self.assertRaises(ProgressionError):
                    make_path(target_level=target)

    def test_an_unknown_variant_is_refused(self):
        with self.assertRaises(ProgressionError):
            make_path(variant="heroic")

    def test_duplicate_ids_are_refused(self):
        with self.assertRaises(ProgressionError):
            load_profiles({"profiles": [
                make_profile().to_dict(), make_profile().to_dict()
            ]})

    def test_a_path_with_no_profile_is_refused(self):
        with self.assertRaises(ProgressionError) as ctx:
            evaluate_all([make_path(profile_id="PROF-MISSING")], [make_profile()])
        self.assertIn("no baseline to plan from", str(ctx.exception))

    def test_malformed_json_names_the_file(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("{nope")
            path = handle.name
        try:
            with self.assertRaises(ProgressionError) as ctx:
                read_json(path)
            self.assertIn(path, str(ctx.exception))
        finally:
            os.unlink(path)

    def test_an_empty_path_set_does_not_crash(self):
        result = evaluate_all([], [make_profile()])
        self.assertEqual(result["paths"], [])
        self.assertEqual(
            result["coverage"]["areas_without_a_feasible_path"],
            list(ASSESSMENT_AREAS),
        )


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


class EndToEndTests(unittest.TestCase):
    def test_output_is_deterministic(self):
        self.assertEqual(
            json.dumps(fixture_result(), sort_keys=True),
            json.dumps(fixture_result(), sort_keys=True),
        )

    def test_cli_writes_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = os.path.join(tmp, "o.json")
            csv_out = os.path.join(tmp, "o.csv")
            md_out = os.path.join(tmp, "o.md")
            code = progression.main(
                ["--profiles", PROFILES, "--paths", PATHS,
                 "--json-out", json_out, "--csv-out", csv_out,
                 "--markdown-out", md_out]
            )
            self.assertEqual(code, 0)
            bundle = read_json(json_out)
            self.assertEqual(bundle["counts_by_verdict"][FEASIBLE], 6)
            self.assertEqual(bundle["counts_by_verdict"][REFUSED_EVIDENCE_CAP], 1)
            with open(md_out, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("REFUSED_EVIDENCE_CAP", text)
            self.assertIn("SYNTHETIC", text)

    def test_method_document_exists_and_matches_the_scale(self):
        """The named deliverable must not drift from the code's caps."""
        path = os.path.join(HERE, "30-progression-method.md")
        self.assertTrue(os.path.exists(path), "30-progression-method.md is required")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for kind, cap in EVIDENCE_KIND_CAPS.items():
            self.assertIn(kind, text, f"method doc must document {kind}")
            self.assertIn(f"`{kind}` | {cap}", text,
                          f"method doc must state {kind} caps at {cap}")

    def test_cli_reports_a_bad_path_without_a_traceback(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "progression.py"),
             "--profiles", "/nonexistent/p.json"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_module_runs_under_python_O(self):
        proc = subprocess.run(
            [sys.executable, "-O", "-m", "unittest",
             "test_progression.NoAspirationalEndpointTests"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
