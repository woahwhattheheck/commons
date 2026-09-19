#!/usr/bin/env python3
"""Tests for the UIOWA-115 roadmap dependency consistency checker.

The two that matter most are `ParallelismTests` (valid parallel work must stay
parallel, and same-level items must be provably independent) and
`RepairRehearsalTests` (the named repairs must actually clear the errors, on a
copy, without touching what needs a planner).

Run:  python3 -m unittest -v test_depcheck
"""

import copy
import csv
import json
import os
import tempfile
import unittest

import depcheck as D

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, "fixtures", name), "r", encoding="utf-8") as handle:
        return json.load(handle)


CONSISTENT = load("roadmap_consistent.json")
INCONSISTENT = load("roadmap_inconsistent.json")
HOSTILE = load("hostile_roadmap.json")

PHASES = [{"phase_id": "0-90", "order": 0, "label": "0-90 days"},
          {"phase_id": "90-180", "order": 1, "label": "90-180 days"},
          {"phase_id": "180+", "order": 2, "label": "180+ days"}]


def run(roadmap, **kwargs):
    return D.check(copy.deepcopy(roadmap), **kwargs)


def codes(result, severity=None):
    return sorted(f["code"] for f in result["findings"]
                  if severity is None or f["severity"] == severity)


def by_code(result, code):
    return [f for f in result["findings"] if f["code"] == code]


def node(result, item_id):
    for entry in result["nodes"]:
        if entry["item_id"] == item_id:
            return entry
    raise AssertionError("node %s missing" % item_id)


def successors(result):
    graph = {}
    for edge in result["edges"]:
        graph.setdefault(edge["prerequisite_id"], []).append(edge["dependent_id"])
    return graph


def roadmap(items, phases=None, roadmap_id="RM-TEST"):
    return {"roadmap_id": roadmap_id, "fiction_notice": "SYNTHETIC test input.",
            "phases": phases if phases is not None else PHASES, "items": items}


# --------------------------------------------------------------------------

class ConsistentRoadmapTests(unittest.TestCase):

    def test_a_coherent_roadmap_reports_no_errors(self):
        result = run(CONSISTENT)
        self.assertEqual(0, result["counts"]["errors"], codes(result, D.ERROR))
        self.assertEqual(0, result["counts"]["unknowns"])

    def test_levels_respect_every_prerequisite_edge(self):
        result = run(CONSISTENT)
        levels = {n["item_id"]: n["level"] for n in result["nodes"]}
        for edge in result["edges"]:
            self.assertLess(levels[edge["prerequisite_id"]], levels[edge["dependent_id"]],
                            "%s -> %s" % (edge["prerequisite_id"], edge["dependent_id"]))

    def test_exit_code_is_zero_when_clean_and_one_when_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(0, D.main([
                "--roadmap", os.path.join(HERE, "fixtures", "roadmap_consistent.json"),
                "--outdir", tmp]))
            self.assertEqual(1, D.main([
                "--roadmap", os.path.join(HERE, "fixtures", "roadmap_inconsistent.json"),
                "--outdir", tmp]))


class ParallelismTests(unittest.TestCase):

    def test_independent_work_is_reported_as_one_parallel_group(self):
        result = run(CONSISTENT)
        groups = {(g["phase_id"], g["level"]): g["items"] for g in result["parallel_groups"]}
        self.assertEqual(["R-01", "R-02", "R-03"], groups[("0-90", 0)])
        self.assertEqual(["R-04", "R-05", "R-06", "R-09", "R-11"], groups[("90-180", 1)])
        self.assertEqual(["R-07", "R-08", "R-10"], groups[("180+", 2)])

    def test_items_in_a_parallel_group_have_no_path_between_them(self):
        result = run(CONSISTENT)
        graph = successors(result)
        reach = {n["item_id"]: D.reachable_from(n["item_id"], graph)
                 for n in result["nodes"]}
        for group in result["parallel_groups"]:
            for left in group["items"]:
                for right in group["items"]:
                    if left == right:
                        continue
                    self.assertNotIn(right, reach[left],
                                     "%s reaches %s but they were called parallel"
                                     % (left, right))

    def test_the_checker_emits_no_linear_execution_order(self):
        # A topological sort would be correct and would destroy the information
        # above, so no such field exists to be misread.
        result = run(CONSISTENT)
        for banned in ("topological_order", "execution_order", "sequence",
                       "schedule", "order"):
            self.assertNotIn(banned, result)

    def test_repairing_a_broken_roadmap_does_not_serialise_parallel_work(self):
        rehearsal = D.rehearse(copy.deepcopy(INCONSISTENT))
        before = {tuple(g["items"]) for g in rehearsal["before"]["parallel_groups"]
                  if g["size"] > 1}
        after = {tuple(g["items"]) for g in rehearsal["after"]["parallel_groups"]
                 if g["size"] > 1}
        self.assertTrue(before)
        for group in before:
            self.assertTrue(any(set(group) <= set(other) for other in after),
                            "parallel group %s was lost by the repairs" % (group,))


class CycleTests(unittest.TestCase):

    def test_cycle_is_found_with_every_member(self):
        entries = by_code(run(INCONSISTENT), "dependency_cycle")
        self.assertEqual(1, len(entries))
        self.assertEqual(["X-06", "X-07", "X-08"], entries[0]["items"])
        self.assertEqual(D.ERROR, entries[0]["severity"])

    def test_every_edge_in_the_cycle_is_offered_as_a_cut(self):
        entry = by_code(run(INCONSISTENT), "dependency_cycle")[0]
        offered = sorted((r["prerequisite_id"], r["item_id"]) for r in entry["repairs"])
        self.assertEqual([("X-06", "X-08"), ("X-07", "X-06"), ("X-08", "X-07")], offered)
        self.assertEqual({entry["repairs"][0]["choice_group"]},
                         {r["choice_group"] for r in entry["repairs"]})

    def test_a_two_item_loop_is_still_a_loop(self):
        result = run(roadmap([
            {"item_id": "A", "phase": "0-90", "prerequisites": ["B"]},
            {"item_id": "B", "phase": "0-90", "prerequisites": ["A"]},
        ]))
        self.assertEqual(["A", "B"], by_code(result, "dependency_cycle")[0]["items"])

    def test_self_dependency_is_reported_with_its_edge(self):
        entry = by_code(run(INCONSISTENT), "self_dependency")[0]
        self.assertEqual({"prerequisite_id": "X-05", "dependent_id": "X-05"},
                         entry["edge"])

    def test_items_in_a_cycle_get_no_invented_level(self):
        result = run(INCONSISTENT)
        for item_id in ("X-06", "X-07", "X-08"):
            self.assertEqual(D.UNKNOWN, node(result, item_id)["level"])
            self.assertTrue(node(result, item_id)["in_cycle"])


class MissingPrerequisiteTests(unittest.TestCase):

    def test_dangling_reference_names_the_exact_edge(self):
        entry = by_code(run(INCONSISTENT), "missing_prerequisite")[0]
        self.assertEqual({"prerequisite_id": "X-99", "dependent_id": "X-04"},
                         entry["edge"])
        self.assertEqual(D.ERROR, entry["severity"])

    def test_an_unresolvable_reference_is_not_treated_as_satisfied(self):
        result = run(INCONSISTENT)
        self.assertNotIn({"prerequisite_id": "X-99", "dependent_id": "X-04"},
                         result["edges"])
        # and the item it broke is UNKNOWN, not quietly fine
        self.assertEqual(D.UNKNOWN, node(result, "X-04")["earliest_feasible_phase"])
        unknown = [f for f in by_code(result, "feasibility_unknown")
                   if f["items"] == ["X-04"]]
        self.assertTrue(unknown)

    def test_both_repairs_are_offered_and_only_one_is_mechanical(self):
        entry = by_code(run(INCONSISTENT), "missing_prerequisite")[0]
        ops = {r["op"]: r["mechanical"] for r in entry["repairs"]}
        self.assertEqual({"define_item": False, "remove_prerequisite": True}, ops)


class PhaseTests(unittest.TestCase):

    def test_inversion_names_the_edge_and_both_repairs(self):
        entry = by_code(run(INCONSISTENT), "phase_inversion")[0]
        self.assertEqual({"prerequisite_id": "X-02", "dependent_id": "X-03"},
                         entry["edge"])
        mechanical = [r for r in entry["repairs"] if r["mechanical"]]
        manual = [r for r in entry["repairs"] if not r["mechanical"]]
        self.assertEqual(1, len(mechanical))
        self.assertEqual("X-03", mechanical[0]["item_id"])
        self.assertEqual("90-180", mechanical[0]["phase_id"])
        self.assertEqual(1, len(manual))
        self.assertEqual("X-02", manual[0]["item_id"])

    def test_inversion_cascades_through_a_misplaced_prerequisite(self):
        # C looks fine against B's STATED phase. It is not fine, because B
        # itself cannot happen until 180+. Checking only the stated phase of a
        # direct prerequisite misses exactly this.
        result = run(roadmap([
            {"item_id": "A", "phase": "180+", "prerequisites": []},
            {"item_id": "B", "phase": "0-90", "prerequisites": ["A"]},
            {"item_id": "C", "phase": "90-180", "prerequisites": ["B"]},
        ]))
        inverted = {f["edge"]["dependent_id"] for f in by_code(result, "phase_inversion")}
        self.assertEqual({"B", "C"}, inverted)

    def test_a_prerequisite_in_the_same_phase_is_an_open_question_not_an_error(self):
        result = run(roadmap([
            {"item_id": "A", "phase": "0-90", "prerequisites": []},
            {"item_id": "B", "phase": "0-90", "prerequisites": ["A"]},
        ]))
        self.assertEqual(0, result["counts"]["errors"])
        entry = by_code(result, "same_phase_dependency")[0]
        self.assertEqual(D.OPEN_QUESTION, entry["severity"])

    def test_slack_is_reported_as_float_not_as_a_fault(self):
        entry = [f for f in by_code(run(CONSISTENT), "schedule_slack")
                 if f["items"] == ["R-08"]]
        self.assertTrue(entry)
        self.assertEqual(D.INFO, entry[0]["severity"])

    def test_unassigned_phase_is_never_defaulted(self):
        result = run(INCONSISTENT)
        self.assertEqual(D.UNASSIGNED, node(result, "X-09")["phase"])
        entry = [f for f in by_code(result, "unassigned_phase") if f["items"] == ["X-09"]]
        self.assertEqual(D.UNKNOWN_SEV, entry[0]["severity"])
        self.assertFalse(entry[0]["repairs"][0]["mechanical"])

    def test_dependent_of_an_unassigned_item_is_unknown_not_a_pass(self):
        result = run(INCONSISTENT)
        entry = [f for f in by_code(result, "feasibility_unknown") if f["items"] == ["X-10"]]
        self.assertTrue(entry)
        self.assertEqual(D.UNKNOWN_SEV, entry[0]["severity"])
        self.assertEqual(D.UNKNOWN, node(result, "X-10")["earliest_feasible_phase"])


class SharedDependencyTests(unittest.TestCase):

    def test_chokepoint_names_every_dependent(self):
        entry = by_code(run(CONSISTENT), "shared_prerequisite")[0]
        self.assertEqual(["R-03", "R-06", "R-09", "R-11"], entry["items"])
        self.assertIn("chokepoint", entry["message"])

    def test_the_fan_in_threshold_is_a_parameter_not_a_hidden_constant(self):
        self.assertEqual([], by_code(run(CONSISTENT, fanin_threshold=4),
                                     "shared_prerequisite"))
        self.assertTrue(by_code(run(CONSISTENT, fanin_threshold=2),
                                "shared_prerequisite"))

    def test_redundant_edge_is_information_not_an_error(self):
        entry = [f for f in by_code(run(INCONSISTENT), "redundant_edge")
                 if f["edge"] == {"prerequisite_id": "X-01", "dependent_id": "X-11"}]
        self.assertTrue(entry)
        self.assertEqual(D.INFO, entry[0]["severity"])
        self.assertFalse(entry[0]["repairs"][0]["mechanical"])

    def test_duplicate_prerequisite_is_deduplicated_and_reported(self):
        result = run(INCONSISTENT)
        self.assertTrue(by_code(result, "duplicate_prerequisite"))
        pairs = [e for e in result["edges"]
                 if e == {"prerequisite_id": "X-01", "dependent_id": "X-11"}]
        self.assertEqual(1, len(pairs))


class RepairRehearsalTests(unittest.TestCase):

    def test_the_named_repairs_actually_clear_every_error(self):
        rehearsal = D.rehearse(copy.deepcopy(INCONSISTENT))
        self.assertEqual(4, rehearsal["before"]["counts"]["errors"])
        self.assertEqual(0, rehearsal["after"]["counts"]["errors"],
                         codes(rehearsal["after"], D.ERROR))

    def test_unknowns_survive_the_rehearsal_because_a_planner_is_required(self):
        rehearsal = D.rehearse(copy.deepcopy(INCONSISTENT))
        self.assertGreater(rehearsal["after"]["counts"]["unknowns"], 0)
        self.assertIn("unassigned_phase", codes(rehearsal["after"], D.UNKNOWN_SEV))
        self.assertTrue(rehearsal["needs_a_planner"])

    def test_the_input_roadmap_is_never_modified(self):
        original = copy.deepcopy(INCONSISTENT)
        supplied = copy.deepcopy(INCONSISTENT)
        D.rehearse(supplied)
        self.assertEqual(original, supplied)

    def test_the_proposal_is_labelled_a_proposal(self):
        rehearsal = D.rehearse(copy.deepcopy(INCONSISTENT))
        self.assertIn("PROPOSAL", rehearsal["proposed_roadmap"]["proposal_notice"])
        self.assertIn("proposed-repairs", rehearsal["proposed_roadmap"]["roadmap_id"])

    def test_exactly_one_cut_per_loop_is_taken(self):
        rehearsal = D.rehearse(copy.deepcopy(INCONSISTENT))
        cuts = [r for r in rehearsal["applied_repairs"] if r.get("choice_group")]
        self.assertEqual(1, len(cuts))
        self.assertTrue(rehearsal["alternative_cuts_not_taken"])

    def test_no_repair_needing_a_planner_is_ever_applied(self):
        rehearsal = D.rehearse(copy.deepcopy(INCONSISTENT))
        for item in rehearsal["applied_repairs"]:
            self.assertTrue(item["mechanical"])
        applied_ids = {i["item_id"] for i in rehearsal["applied_repairs"]}
        self.assertNotIn("X-09", applied_ids)

    def test_rehearsing_a_clean_roadmap_changes_nothing(self):
        rehearsal = D.rehearse(copy.deepcopy(CONSISTENT))
        self.assertEqual([], rehearsal["applied_repairs"])
        self.assertEqual(rehearsal["before"]["counts"], rehearsal["after"]["counts"])


class HostileInputTests(unittest.TestCase):

    def test_malformed_records_are_each_named(self):
        found = set(codes(run(HOSTILE), D.ERROR))
        for expected in ("item_missing_id", "item_duplicate_id",
                         "prerequisites_not_a_list", "prerequisite_not_an_id",
                         "phase_undefined", "phase_order_duplicate"):
            self.assertIn(expected, found)

    def test_unreadable_prerequisites_do_not_become_no_prerequisites(self):
        result = run(HOSTILE)
        entry = [f for f in by_code(result, "feasibility_unknown") if f["items"] == ["H-03"]]
        self.assertTrue(entry)
        self.assertIn("could not be fully read", entry[0]["message"])

    def test_a_blank_phase_is_unassigned_not_the_first_phase(self):
        result = run(HOSTILE)
        self.assertEqual(D.UNASSIGNED, node(result, "H-06")["phase"])

    def test_an_undefined_phase_reference_is_not_silently_accepted(self):
        result = run(HOSTILE)
        self.assertEqual(D.UNASSIGNED, node(result, "H-04")["phase"])
        self.assertTrue(by_code(result, "phase_undefined"))

    def test_an_empty_roadmap_does_not_crash(self):
        result = D.check({"roadmap_id": "RM-EMPTY", "phases": [], "items": []})
        self.assertIn("no_phases_defined", codes(result, D.ERROR))
        self.assertEqual(0, result["counts"]["items"])
        self.assertTrue(result["content_digest"])

    def test_a_roadmap_with_items_but_no_phases_reports_unknown_not_pass(self):
        result = D.check(roadmap([{"item_id": "A", "phase": "0-90",
                                   "prerequisites": []}], phases=[]))
        self.assertIn("no_phases_defined", codes(result, D.ERROR))
        self.assertEqual(D.UNASSIGNED, node(result, "A")["phase"])

    def test_non_integer_phase_order_is_rejected_rather_than_guessed(self):
        result = D.check(roadmap(
            [{"item_id": "A", "phase": "first", "prerequisites": []}],
            phases=[{"phase_id": "first", "order": "one"}]))
        self.assertIn("phase_order_invalid", codes(result, D.ERROR))


class OutputTests(unittest.TestCase):

    def test_the_same_roadmap_digests_identically(self):
        self.assertEqual(run(CONSISTENT)["content_digest"],
                         run(CONSISTENT)["content_digest"])

    def test_moving_one_item_changes_the_digest(self):
        moved = copy.deepcopy(CONSISTENT)
        moved["items"][0]["phase"] = "90-180"
        self.assertNotEqual(run(CONSISTENT)["content_digest"], run(moved)["content_digest"])

    def test_dot_and_mermaid_contain_every_node_and_edge(self):
        result = run(CONSISTENT)
        dot, mermaid = D.render_dot(result), D.render_mermaid(result)
        for entry in result["nodes"]:
            self.assertIn(D._safe_node(entry["item_id"]), dot)
            self.assertIn(entry["item_id"], mermaid)
        for edge in result["edges"]:
            arrow = "%s -> %s" % (D._safe_node(edge["prerequisite_id"]),
                                  D._safe_node(edge["dependent_id"]))
            self.assertIn(arrow, dot)

    def test_graph_subgraphs_follow_phase_order_not_alphabetical_order(self):
        mermaid = D.render_mermaid(run(CONSISTENT))
        self.assertLess(mermaid.index('["90-180"]'), mermaid.index('["180+"]'))

    def test_findings_csv_carries_the_exact_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "findings.csv")
            D.write_findings_csv(path, run(INCONSISTENT))
            with open(path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        inversion = [r for r in rows if r["code"] == "phase_inversion"]
        self.assertEqual(1, len(inversion))
        self.assertEqual("X-02", inversion[0]["prerequisite_id"])
        self.assertEqual("X-03", inversion[0]["dependent_id"])

    def test_csv_cells_that_look_like_formulas_stay_text(self):
        self.assertEqual("'=cmd()", D._csv_cell("=cmd()"))
        self.assertEqual("plain", D._csv_cell("plain"))

    def test_report_states_that_unknown_is_neither_pass_nor_fail(self):
        report = D.render_report(run(INCONSISTENT))
        self.assertIn("it is not a pass and it is not a", report)
        self.assertIn("may run at the same time", report)

    def test_cli_writes_every_artifact_including_the_rehearsal(self):
        with tempfile.TemporaryDirectory() as tmp:
            D.main(["--roadmap", os.path.join(HERE, "fixtures",
                                              "roadmap_inconsistent.json"),
                    "--outdir", tmp, "--rehearse-repairs"])
            for name in ("graph.json", "graph.dot", "dependency_report.md",
                         "findings.csv", "proposed_roadmap.json",
                         "rehearsal_report.md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, name)), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
