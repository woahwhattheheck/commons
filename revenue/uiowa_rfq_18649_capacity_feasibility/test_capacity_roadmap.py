#!/usr/bin/env python3
"""Tests for the capacity-aware roadmap engine (UIOWA-116).

The hostile cases here are the ways a roadmap lies: a prerequisite scheduled
after the thing that needs it, a cycle nobody noticed, an unestimated item
counted as free, work pushed off the end of the horizon and quietly forgotten,
and a "role" that is really a person's name.

Run: python3 -m unittest -v test_capacity_roadmap
"""

import contextlib
import copy
import io
import json
import os
import shutil
import tempfile
import unittest

import capacity_roadmap as cr

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "data", "roadmap-items.json")
CAPACITY = os.path.join(HERE, "data", "capacity-assumptions.json")


def run_cli(argv):
    """Invoke the CLI with its chatter captured, so a test run reads cleanly."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cr.main(argv)
    return rc


def codes(findings):
    return set(f.code for f in findings)


def err_codes(findings):
    return set(f.code for f in cr.errors(findings))


class Base(unittest.TestCase):
    def setUp(self):
        self.items = cr.load_items(ITEMS)
        self.capacity = cr.load_capacity(CAPACITY)

    def item(self, doc, item_id):
        for it in doc["items"]:
            if it["id"] == item_id:
                return it
        raise AssertionError("no item %s" % item_id)

    def static(self):
        return cr.static_checks(self.items, self.capacity)


class TestDependencyGraph(Base):
    def test_fixture_graph_is_acyclic(self):
        graph = cr.DependencyGraph(self.items["items"])
        self.assertIsNone(graph.find_cycle())

    def test_topological_order_respects_every_edge(self):
        graph = cr.DependencyGraph(self.items["items"])
        order = graph.topological_order()
        self.assertEqual(len(order), len(self.items["items"]))
        pos = dict((n, i) for i, n in enumerate(order))
        for node, prereqs in graph.prereqs.items():
            for p in prereqs:
                self.assertLess(pos[p], pos[node], "%s must come before %s" % (p, node))

    def test_topological_order_is_stable(self):
        a = cr.DependencyGraph(self.items["items"]).topological_order()
        shuffled = copy.deepcopy(self.items)
        shuffled["items"] = list(reversed(shuffled["items"]))
        b = cr.DependencyGraph(shuffled["items"]).topological_order()
        self.assertEqual(a, b, "order must not depend on how the file was written")

    def test_cycle_is_detected_and_reported_as_a_path(self):
        # RM-01 -> RM-02 -> RM-08 ... make RM-01 depend on RM-02.
        self.item(self.items, "RM-01")["prerequisites"] = ["RM-02"]
        graph = cr.DependencyGraph(self.items["items"])
        cycle = graph.find_cycle()
        self.assertIsNotNone(cycle)
        self.assertIn("RM-01", cycle)
        self.assertIn("RM-02", cycle)
        self.assertEqual(cycle[0], cycle[-1], "a cycle path returns to where it started")

    def test_cycle_refuses_to_schedule(self):
        self.item(self.items, "RM-01")["prerequisites"] = ["RM-02"]
        static, graph, results = cr.run(self.items, self.capacity)
        self.assertIn("D004_PREREQUISITE_CYCLE", err_codes(static))
        self.assertEqual([], results, "no schedule may be produced for a cyclic graph")

    def test_topological_order_raises_on_a_cycle(self):
        self.item(self.items, "RM-01")["prerequisites"] = ["RM-02"]
        graph = cr.DependencyGraph(self.items["items"])
        with self.assertRaises(cr.InputError):
            graph.topological_order()

    def test_self_prerequisite_is_caught(self):
        self.item(self.items, "RM-03")["prerequisites"] = ["RM-03"]
        static, _graph = self.static()
        self.assertIn("D003_SELF_PREREQUISITE", err_codes(static))

    def test_missing_prerequisite_is_caught(self):
        self.item(self.items, "RM-03")["prerequisites"] = ["RM-99"]
        static, _graph = self.static()
        self.assertIn("D002_MISSING_PREREQUISITE", err_codes(static))

    def test_duplicate_item_id_is_caught(self):
        self.items["items"].append(copy.deepcopy(self.item(self.items, "RM-03")))
        static, _graph = self.static()
        self.assertIn("D001_DUPLICATE_ITEM_ID", err_codes(static))


class TestPhaseOrdering(Base):
    def test_prerequisite_scheduled_after_its_dependent_is_caught(self):
        # THE phase-ordering violation: RM-02 needs RM-01, so RM-01 in a LATER
        # window than RM-02 is impossible. A static table would render it happily.
        self.item(self.items, "RM-01")["proposed_phase"] = "90-180"
        self.item(self.items, "RM-02")["proposed_phase"] = "0-90"
        static, _graph = self.static()
        self.assertIn("D005_PREREQ_AFTER_DEPENDENT", err_codes(static))
        detail = " ".join(f.detail for f in cr.errors(static))
        self.assertIn("RM-01", detail)
        self.assertIn("RM-02", detail)
        self.assertIn("90-180", detail)

    def test_transitive_ordering_violation_is_caught(self):
        # RM-09 depends on RM-08; put RM-08 last and RM-09 first.
        self.item(self.items, "RM-09")["proposed_phase"] = "0-90"
        static, _graph = self.static()
        self.assertIn("D005_PREREQ_AFTER_DEPENDENT", err_codes(static))

    def test_prerequisite_in_the_same_phase_is_allowed(self):
        # Sequencing inside a 90-day window is normal and must not be an error.
        self.item(self.items, "RM-04")["proposed_phase"] = "0-90"
        static, _graph = self.static()
        self.assertNotIn("D005_PREREQ_AFTER_DEPENDENT", err_codes(static))

    def test_clean_fixture_has_no_ordering_violation(self):
        static, _graph = self.static()
        self.assertNotIn("D005_PREREQ_AFTER_DEPENDENT", err_codes(static))

    def test_phase_outside_the_horizon_is_caught(self):
        self.item(self.items, "RM-03")["proposed_phase"] = "someday"
        static, _graph = self.static()
        self.assertIn("D006_PHASE_NOT_IN_HORIZON", err_codes(static))

    def test_resequencing_never_breaks_prerequisite_order(self):
        # The invariant that matters: whatever capacity forces, a prerequisite is
        # never scheduled after the item that depends on it.
        phases = self.items["meta"]["horizon_phases"]
        idx = dict((p, i) for i, p in enumerate(phases))
        idx[cr.BEYOND_HORIZON] = len(phases)
        _static, graph, results = cr.run(self.items, self.capacity)
        self.assertTrue(results)
        for sc, _prop, feas in results:
            for item_id, phase in feas["assignments"].items():
                for p in graph.prereqs[item_id]:
                    self.assertLessEqual(
                        idx[feas["assignments"][p]], idx[phase],
                        "scenario %s put prerequisite %s after %s" % (sc["id"], p, item_id))

    def test_resequencing_never_pulls_work_earlier_than_proposed(self):
        phases = self.items["meta"]["horizon_phases"]
        idx = dict((p, i) for i, p in enumerate(phases))
        idx[cr.BEYOND_HORIZON] = len(phases)
        _static, graph, results = cr.run(self.items, self.capacity)
        for sc, _prop, feas in results:
            for item_id, phase in feas["assignments"].items():
                proposed = graph.items[item_id]["proposed_phase"]
                self.assertGreaterEqual(idx[phase], idx[proposed],
                                        "scenario %s pulled %s earlier than proposed"
                                        % (sc["id"], item_id))


class TestParallelism(Base):
    def test_independent_roots_are_reported_parallel(self):
        graph = cr.DependencyGraph(self.items["items"])
        groups = graph.parallel_groups()
        self.assertEqual(["RM-01", "RM-03", "RM-05"], groups[0]["fully_independent"])

    def test_same_level_is_not_enough_to_be_parallel(self):
        # Force two items onto one level while one still reaches the other, and
        # assert neither is reported as fully independent.
        items = [
            {"id": "A", "title": "a", "proposed_phase": "0-90", "prerequisites": [],
             "effort": {"r": {"low": 1, "likely": 1, "high": 1}}},
            {"id": "B", "title": "b", "proposed_phase": "0-90", "prerequisites": ["A"],
             "effort": {"r": {"low": 1, "likely": 1, "high": 1}}},
            {"id": "C", "title": "c", "proposed_phase": "0-90", "prerequisites": ["A"],
             "effort": {"r": {"low": 1, "likely": 1, "high": 1}}},
            {"id": "D", "title": "d", "proposed_phase": "0-90", "prerequisites": ["B"],
             "effort": {"r": {"low": 1, "likely": 1, "high": 1}}},
        ]
        graph = cr.DependencyGraph(items)
        groups = graph.parallel_groups()
        self.assertEqual(["B", "C"], groups[1]["fully_independent"])
        self.assertIn("D", groups[2]["members"])

    def test_tracks_separate_chains_that_never_touch(self):
        graph = cr.DependencyGraph(self.items["items"])
        tracks = graph.tracks()
        self.assertIn(["RM-03", "RM-04"], tracks)
        self.assertEqual(2, len(tracks))


class TestUnknownEffort(Base):
    def test_unknown_effort_is_not_read_as_zero(self):
        self.assertEqual(cr.UNKNOWN,
                         cr.effort_for(self.item(self.items, "RM-06"), "infra_operations", "likely"))

    def test_unknown_and_zero_produce_different_outcomes(self):
        _s, _g, unknown_results = cr.run(self.items, self.capacity)
        zeroed = copy.deepcopy(self.items)
        for it in zeroed["items"]:
            if it["id"] == "RM-06":
                it["effort"]["infra_operations"] = {"low": 0, "likely": 0, "high": 0}
        _s2, _g2, zero_results = cr.run(zeroed, self.capacity)
        sc = "expected"
        unk = next(f for s, _p, f in unknown_results if s["id"] == sc)
        zer = next(f for s, _p, f in zero_results if s["id"] == sc)
        self.assertEqual(cr.UNVERIFIABLE, cr.verdict_of(unk["rows"], unk["assignments"]))
        self.assertEqual(cr.FEASIBLE, cr.verdict_of(zer["rows"], zer["assignments"]),
                         "a literal zero is a claim that the work is free; UNKNOWN is not")

    def test_a_phase_carrying_an_unknown_is_never_reported_feasible(self):
        _s, _g, results = cr.run(self.items, self.capacity)
        for sc, _prop, feas in results:
            rows = [r for r in feas["rows"] if r["unknown_items"]]
            self.assertTrue(rows, "scenario %s should carry the UNKNOWN item" % sc["id"])
            for r in rows:
                self.assertEqual(cr.UNVERIFIABLE, r["verdict"])
                self.assertIsNone(r["shortfall"])
                self.assertIsNone(r["headroom"])

    def test_unknown_item_still_appears_in_the_schedule(self):
        # It must not be dropped for being unestimated -- the sequence needs it.
        _s, _g, results = cr.run(self.items, self.capacity)
        for _sc, _prop, feas in results:
            self.assertIn("RM-06", feas["assignments"])

    def test_unknown_is_named_in_the_findings(self):
        _s, _g, results = cr.run(self.items, self.capacity)
        found = []
        for _sc, prop, feas in results:
            found.extend(prop["findings"] + feas["findings"])
        self.assertIn("C002_CAPACITY_UNVERIFIABLE", codes(found))


class TestCapacity(Base):
    def test_unmet_capacity_is_reported_on_the_plan_as_proposed(self):
        _s, _g, results = cr.run(self.items, self.capacity)
        prop = next(p for s, p, _f in results if s["id"] == "expected")
        short = [r for r in prop["rows"] if r["verdict"] == cr.INFEASIBLE]
        self.assertTrue(short, "the expected scenario over-subscribes a role as proposed")
        for r in short:
            self.assertGreater(r["shortfall"], 0)

    def test_shortfall_is_a_number_not_a_clamp(self):
        _s, _g, results = cr.run(self.items, self.capacity)
        prop = next(p for s, p, _f in results if s["id"] == "constrained")
        r = next(r for r in prop["rows"]
                 if r["role"] == "pipeline_engineer" and r["phase"] == "0-90")
        self.assertEqual(cr.INFEASIBLE, r["verdict"])
        self.assertAlmostEqual(r["demand_known"] - r["capacity"], r["shortfall"], places=1)

    def test_resequencing_resolves_the_expected_shortfall(self):
        _s, _g, results = cr.run(self.items, self.capacity)
        sc, prop, feas = next(t for t in results if t[0]["id"] == "expected")
        self.assertEqual(cr.INFEASIBLE, cr.verdict_of(prop["rows"], prop["assignments"]))
        self.assertEqual(cr.UNVERIFIABLE, cr.verdict_of(feas["rows"], feas["assignments"]))
        self.assertTrue(feas["moves"], "something had to move to resolve it")
        self.assertEqual("role capacity", feas["moves"][0]["reason"])
        _ = sc

    def test_work_that_fits_nowhere_is_reported_not_dropped(self):
        _s, graph, results = cr.run(self.items, self.capacity)
        _sc, _prop, feas = next(t for t in results if t[0]["id"] == "constrained")
        beyond = [i for i, p in feas["assignments"].items() if p == cr.BEYOND_HORIZON]
        self.assertTrue(beyond, "the constrained scenario should push something off the horizon")
        self.assertEqual(len(graph.items), len(feas["assignments"]),
                         "every item is accounted for, including the ones that did not fit")
        self.assertIn("C003_BEYOND_HORIZON", err_codes(feas["findings"]))

    def test_a_plan_with_beyond_horizon_work_is_never_feasible(self):
        # The absorption bug this guards against: beyond-horizon items stop
        # contributing demand, so the capacity table reads clean.
        _s, _g, results = cr.run(self.items, self.capacity)
        for sc, _prop, feas in results:
            if any(p == cr.BEYOND_HORIZON for p in feas["assignments"].values()):
                self.assertEqual(cr.INFEASIBLE,
                                 cr.verdict_of(feas["rows"], feas["assignments"]),
                                 "scenario %s dropped work and still read feasible" % sc["id"])

    def test_changing_the_resource_range_changes_the_sequence(self):
        _s, _g, results = cr.run(self.items, self.capacity)
        moves = dict((sc["id"], len(feas["moves"])) for sc, _p, feas in results)
        self.assertGreater(moves["constrained"], moves["invested"],
                           "a tighter resource range must disturb the sequence more")
        self.assertEqual(0, moves["invested"],
                         "with the resources invested, the proposed sequence should hold")

    def test_an_item_needing_an_unbudgeted_role_is_caught(self):
        self.item(self.items, "RM-03")["effort"]["data_steward"] = {"low": 1, "likely": 2, "high": 3}
        static, _graph = self.static()
        self.assertIn("C004_UNKNOWN_ROLE", err_codes(static))

    def test_capacity_multiplier_actually_scales_capacity(self):
        sc = next(s for s in self.capacity["scenarios"] if s["id"] == "invested")
        cap = cr.scenario_capacity(self.capacity, sc)
        base = self.capacity["roles"]["monitoring_owner"]["0-90"]
        self.assertAlmostEqual(base * sc["capacity_multiplier"], cap["monitoring_owner"]["0-90"])


class TestNoPersonalCommitments(Base):
    def test_a_capacity_record_naming_a_person_is_rejected(self):
        tmp = tempfile.mkdtemp()
        try:
            doc = copy.deepcopy(self.capacity)
            doc["roles"]["monitoring_owner"] = {"name": "J. Rivera", "0-90": 24,
                                                "90-180": 24, "180+": 16}
            p = os.path.join(tmp, "cap.json")
            with open(p, "w") as fh:
                json.dump(doc, fh)
            with self.assertRaises(cr.InputError) as cm:
                cr.load_capacity(p)
            self.assertIn("per ROLE", str(cm.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_personal_name_as_a_role_id_is_rejected(self):
        tmp = tempfile.mkdtemp()
        try:
            doc = copy.deepcopy(self.capacity)
            doc["roles"]["Jane Smith"] = {"0-90": 20, "90-180": 20, "180+": 10}
            p = os.path.join(tmp, "cap.json")
            with open(p, "w") as fh:
                json.dump(doc, fh)
            with self.assertRaises(cr.InputError) as cm:
                cr.load_capacity(p)
            self.assertIn("role-shaped", str(cm.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_nested_person_field_is_found(self):
        tmp = tempfile.mkdtemp()
        try:
            doc = copy.deepcopy(self.capacity)
            doc["scenarios"][0]["staffing"] = {"details": [{"email": "x@example.org"}]}
            p = os.path.join(tmp, "cap.json")
            with open(p, "w") as fh:
                json.dump(doc, fh)
            with self.assertRaises(cr.InputError):
                cr.load_capacity(p)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_generated_output_contains_a_calendar_date(self):
        tmp = tempfile.mkdtemp()
        try:
            rc = run_cli(["plan", "--items", ITEMS, "--capacity", CAPACITY, "--outdir", tmp])
            self.assertIn(rc, (0, 1))
            for name in sorted(os.listdir(tmp)):
                with open(os.path.join(tmp, name), "r", encoding="utf-8") as fh:
                    text = fh.read()
                hit = cr.DATE_SHAPED.search(text)
                self.assertIsNone(hit, "%s contains a calendar date %r; phases are relative windows"
                                  % (name, hit.group(0) if hit else ""))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestHostileInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p

    def test_missing_file_is_a_readable_error(self):
        with self.assertRaises(cr.InputError) as cm:
            cr.load_items(os.path.join(self.tmp, "nope.json"))
        self.assertIn("file not found", str(cm.exception))

    def test_malformed_json_is_a_readable_error(self):
        p = self.write("bad.json", '{"meta": {"horizon_phases": ["0-90"],}')
        with self.assertRaises(cr.InputError) as cm:
            cr.load_items(p)
        self.assertIn("not valid JSON", str(cm.exception))

    def test_item_missing_required_keys_names_them(self):
        p = self.write("thin.json", json.dumps(
            {"meta": {"horizon_phases": ["0-90"]}, "items": [{"id": "X"}]}))
        with self.assertRaises(cr.InputError) as cm:
            cr.load_items(p)
        for key in ("title", "proposed_phase", "prerequisites", "effort"):
            self.assertIn(key, str(cm.exception))

    def test_prerequisites_of_the_wrong_type_is_a_readable_error(self):
        p = self.write("t.json", json.dumps({
            "meta": {"horizon_phases": ["0-90"]},
            "items": [{"id": "X", "title": "t", "proposed_phase": "0-90",
                       "prerequisites": "RM-01", "effort": {}}]}))
        with self.assertRaises(cr.InputError) as cm:
            cr.load_items(p)
        self.assertIn("must be a list", str(cm.exception))

    def test_bad_effort_point_is_rejected(self):
        p = self.write("c.json", json.dumps({
            "meta": {}, "roles": {"r": {"0-90": 10}},
            "scenarios": [{"id": "s", "effort_point": "medium", "capacity_multiplier": 1}]}))
        with self.assertRaises(cr.InputError) as cm:
            cr.load_capacity(p)
        self.assertIn("low|likely|high", str(cm.exception))

    def test_an_item_with_no_effort_at_all_does_not_crash(self):
        items = {"meta": {"horizon_phases": ["0-90", "90-180"]},
                 "items": [{"id": "X", "title": "t", "proposed_phase": "0-90",
                            "prerequisites": [], "effort": {}}]}
        cap = {"meta": {}, "roles": {"r": {"0-90": 10, "90-180": 10}},
               "scenarios": [{"id": "s", "effort_point": "likely", "capacity_multiplier": 1.0}]}
        static, _graph, results = cr.run(items, cap)
        self.assertEqual(set(), err_codes(static))
        self.assertEqual("0-90", results[0][2]["assignments"]["X"])

    def test_cli_reports_unreadable_input_without_a_traceback(self):
        self.assertEqual(2, run_cli(["check", "--items", "/nonexistent.json",
                                     "--capacity", "/nonexistent.json"]))


class TestOutputs(Base):
    def test_ascii_is_pure_ascii_uniform_width_and_colourless(self):
        static, graph, results = cr.run(self.items, self.capacity)
        text = cr.render_graph_ascii(graph, self.items)
        for sc, prop, feas in results:
            text += cr.render_scenario_ascii(self.items, graph, sc, prop, feas)
        self.assertTrue(all(ord(c) < 128 for c in text))
        self.assertNotIn("\x1b[", text)
        self.assertEqual({cr.W}, set(len(l) for l in text.split("\n") if l))
        for mark in ("=", "!", "|", "."):
            self.assertIn(mark, text)

    def test_ascii_names_the_legend_so_marks_are_readable_without_colour(self):
        static, graph, results = cr.run(self.items, self.capacity)
        sc, prop, feas = results[0]
        text = cr.render_scenario_ascii(self.items, graph, sc, prop, feas)
        self.assertIn("LEGEND", text)
        self.assertIn("no colour", text)

    def test_bar_marks_overflow_distinctly(self):
        over = cr.bar(150.0, 100.0)
        under = cr.bar(50.0, 100.0)
        self.assertIn("!", over)
        self.assertNotIn("!", under)
        self.assertEqual(len(over), len(under))

    def test_planning_table_covers_every_item_in_every_scenario(self):
        tmp = tempfile.mkdtemp()
        try:
            run_cli(["plan", "--items", ITEMS, "--capacity", CAPACITY, "--outdir", tmp])
            import csv as _csv
            with open(os.path.join(tmp, "roadmap-planning-table.csv"), encoding="utf-8") as fh:
                rows = list(_csv.DictReader(fh))
            self.assertEqual(len(self.items["items"]) * len(self.capacity["scenarios"]), len(rows))
            self.assertTrue(any(r["scheduled_phase"] == cr.BEYOND_HORIZON for r in rows))
            self.assertTrue(any(r["effort_unknown"] for r in rows))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_render_is_byte_identical_across_runs(self):
        tmp = tempfile.mkdtemp()
        try:
            a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            for out in (a, b):
                run_cli(["plan", "--items", ITEMS, "--capacity", CAPACITY, "--outdir", out])
            for name in sorted(os.listdir(a)):
                with open(os.path.join(a, name), "rb") as fh:
                    one = fh.read()
                with open(os.path.join(b, name), "rb") as fh:
                    two = fh.read()
                self.assertEqual(one, two, "%s differs between runs" % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_exits_nonzero_when_something_is_wrong(self):
        self.assertEqual(1, run_cli(["check", "--items", ITEMS, "--capacity", CAPACITY]))

    def test_a_clean_plan_exits_zero(self):
        # Remove the two sources of error: the UNKNOWN is a warning, so only the
        # capacity shortfalls need resolving. Give every role plenty of room.
        tmp = tempfile.mkdtemp()
        try:
            cap = copy.deepcopy(self.capacity)
            for role in cap["roles"]:
                for phase in cap["roles"][role]:
                    cap["roles"][role][phase] = 10000
            cap["scenarios"] = [s for s in cap["scenarios"] if s["id"] == "expected"]
            p = os.path.join(tmp, "cap.json")
            with open(p, "w") as fh:
                json.dump(cap, fh)
            self.assertEqual(0, run_cli(["check", "--items", ITEMS, "--capacity", p]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_every_emitted_code_is_documented(self):
        static, _graph, results = cr.run(self.items, self.capacity)
        used = codes(cr.all_findings(static, results))
        self.assertTrue(used <= set(cr.RULES), "undocumented codes: %s" % (used - set(cr.RULES)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
