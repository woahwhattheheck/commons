"""Normal and optimized regression tests; no provider/network access."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
PACKAGE = "uiowa103_halyard_graph_checks"
if PACKAGE not in sys.modules:
    spec = importlib.util.spec_from_file_location(PACKAGE, HERE / "__init__.py",
                                                submodule_search_locations=[str(HERE)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = package
    spec.loader.exec_module(package)
from uiowa103_halyard_graph_checks import graph_cases as gc
from uiowa103_halyard_graph_checks import equivalence_trace as et

MAPPER = Path(os.environ.get("UIOWA_IDENTITY_MAP_PATH", HERE.parent / "uiowa_rfq_18649_identity_map" / "identity_map.py"))


class GraphChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapper, cls.source = gc.load_mapper(MAPPER)

    def report(self, records, decisions=()):
        return self.mapper.reconcile(gc.packet(records, decisions))

    def test_actual_mapper_targeted_contract(self):
        result = gc.run_suite(self.mapper, exhaustive=False)
        self.assertEqual(result["summary"]["failed"], 0, result)
        self.assertEqual(result["summary"]["checks"], 32)

    def test_all_five_vertex_graphs(self):
        result = gc.run_suite(self.mapper, exhaustive=True)
        self.assertEqual(result["summary"]["failed"], 0, result)
        self.assertEqual(result["summary"]["exhaustive_graphs_executed"], 1024)

    def test_witness_exact_provenance_and_shortest_path(self):
        a, b, c = [gc.record(x) for x in "ABC"]
        ds = [gc.decision("AB", a, b), gc.decision("BC", b, c)]
        graph = et.ReportGraph(self.report([a, b, c], ds))
        ids = {n["original"]["payload"]["case_label"]: oid for oid, n in graph.nodes.items()}
        trace = graph.explain(ids["A"], ids["C"])
        self.assertEqual([s["decision"]["decision_id"] for s in trace["steps"]], ["AB", "BC"])
        self.assertEqual([n["original"] for n in trace["occurrences"]], [a, b, c])
        self.assertEqual(trace["supporting_decisions"], ds)
        reverse = graph.explain(ids["C"], ids["A"])
        self.assertEqual([s["decision"]["decision_id"] for s in reverse["steps"]], ["BC", "AB"])
        # A triangle retains three reasons but the shortest A->C trail has one edge.
        ds += [gc.decision("CA", c, a)]
        graph = et.ReportGraph(self.report([a, b, c], ds))
        trace = graph.explain(ids["A"], ids["C"])
        self.assertEqual(len(trace["steps"]), 1)
        self.assertEqual(len(trace["supporting_decisions"]), 3)

    def test_unknown_path_is_not_a_negative_conclusion(self):
        a, b = gc.record("A"), gc.record("B")
        graph = et.ReportGraph(self.report([a, b]))
        ids = sorted(graph.nodes)
        trace = graph.explain(*ids)
        self.assertEqual(trace["status"], "no_equivalence_path")
        self.assertEqual(trace["negative_constraints"], [])
        self.assertIn("does not establish", trace["interpretation"])

    def test_negative_constraint_retained_but_never_walked(self):
        a, b, c = [gc.record(x) for x in "ABC"]
        negative = gc.decision("NOT-BC", b, c, "different_entity")
        graph = et.ReportGraph(self.report([a, b, c], [gc.decision("AB", a, b), negative]))
        ids = {n["original"]["payload"]["case_label"]: oid for oid, n in graph.nodes.items()}
        trace = graph.explain(ids["A"], ids["C"])
        self.assertEqual(trace["status"], "no_equivalence_path")
        self.assertEqual(trace["steps"], [])
        self.assertEqual(trace["negative_constraints"], [negative])

    def test_trace_inputs_and_outputs_do_not_alias_internal_state(self):
        a, b = gc.record("A"), gc.record("B")
        report = self.report([a, b], [gc.decision("AB", a, b)])
        graph = et.ReportGraph(report)
        ids = sorted(graph.nodes)
        first = graph.explain(*ids)
        retained = deepcopy(first)
        report["records"][0]["original"]["payload"]["case_label"] = "changed"
        first["steps"][0]["decision"]["reason"] = "changed"
        self.assertEqual(graph.explain(*ids), retained)

    def test_digest_mutation_is_not_silently_accepted(self):
        report = self.report([gc.record("A")])
        report["records"][0]["original"]["source_locators"] = ["synthetic://substituted"]
        with self.assertRaisesRegex(et.TraceError, "digest mismatch"):
            et.ReportGraph(report)

    def test_rehashed_unexplained_union_is_rejected(self):
        report = self.report([gc.record("A"), gc.record("B")])
        group = {"group_id": "forged-group", "members": [r["occurrence_id"] for r in report["records"]]}
        report["equivalence_groups"] = [group]
        for row in report["records"]:
            row["equivalence_group"] = group["group_id"]
        report["snapshot_sha256"] = et.snapshot_digest(report)
        with self.assertRaisesRegex(et.TraceError, "closure"):
            et.ReportGraph(report)

    def test_rehashed_missing_reason_is_rejected(self):
        a, b = gc.record("A"), gc.record("B")
        report = self.report([a, b], [gc.decision("AB", a, b)])
        report["equivalences"][0]["evidence_locators"] = []
        report["snapshot_sha256"] = et.snapshot_digest(report)
        with self.assertRaisesRegex(et.TraceError, "provenance"):
            et.ReportGraph(report)

    def test_rehashed_cross_scope_graph_is_rejected(self):
        a, b = gc.record("A"), gc.record("B")
        report = self.report([a, b], [gc.decision("AB", a, b)])
        report["records"][0]["original"]["synthetic"] = False
        report["snapshot_sha256"] = et.snapshot_digest(report)
        with self.assertRaisesRegex(et.TraceError, "synthetic scopes"):
            et.ReportGraph(report)

    def test_rehashed_negative_cycle_is_rejected(self):
        a, b, c = [gc.record(x) for x in "ABC"]
        report = self.report([a, b, c], [gc.decision("AB", a, b), gc.decision("BC", b, c)])
        report["equivalences"].append(gc.decision("NOT-AC", a, c, "different_entity"))
        report["snapshot_sha256"] = et.snapshot_digest(report)
        with self.assertRaisesRegex(et.TraceError, "contradicts positive closure"):
            et.ReportGraph(report)

    def test_missing_occurrence_is_explicit(self):
        graph = et.ReportGraph(self.report([gc.record("A")]))
        with self.assertRaisesRegex(et.TraceError, "absent"):
            graph.explain(next(iter(graph.nodes)), "not-present")

    def test_reject_everything_control_cannot_pass(self):
        def reject(document):
            raise self.mapper.MappingError("control rejects all inputs")
        target = SimpleNamespace(MappingError=self.mapper.MappingError, reconcile=reject)
        result = gc.run_suite(target, exhaustive=False)
        self.assertGreater(result["summary"]["failed"], 0)
        self.assertTrue(any(c["case"] == "explicit_pair" and c["status"] == "FAIL" for c in result["checks"]))

    def test_unexpected_exception_control_cannot_pass_negative_cases(self):
        def crash(document):
            raise RuntimeError("control crash")
        result = gc.run_suite(SimpleNamespace(MappingError=self.mapper.MappingError, reconcile=crash), False)
        self.assertEqual(result["summary"]["failed"], 32)

    def test_ignore_negative_constraints_control_cannot_pass(self):
        def target(document):
            doc = deepcopy(document)
            doc["equivalences"] = [d for d in doc["equivalences"] if d["relation"] != "different_entity"]
            return self.mapper.reconcile(doc)
        result = gc.run_suite(SimpleNamespace(MappingError=self.mapper.MappingError, reconcile=target), False)
        failures = {r["case"] for r in result["checks"] if r["status"] == "FAIL"}
        self.assertTrue(all(f"negative_after_full_closure_order_{n}" in failures for n in range(6)))

    def test_provenance_substitution_control_cannot_pass(self):
        def target(document):
            result = self.mapper.reconcile(document)
            for row in result["records"]:
                row["original"]["source_locators"] = ["synthetic://invented-locator"]
            result["snapshot_sha256"] = et.snapshot_digest(result)
            return result
        result = gc.run_suite(SimpleNamespace(MappingError=self.mapper.MappingError, reconcile=target), False)
        self.assertGreater(result["summary"]["failed"], 0)
        self.assertTrue(any(r["case"] == "explicit_pair" and r["status"] == "FAIL" for r in result["checks"]))

    def test_revision_selection_control_cannot_pass(self):
        def target(document):
            result = self.mapper.reconcile(document)
            for row in result["links"]:
                for side in ("from", "to"):
                    endpoint = row[side]
                    if endpoint["status"] == "ambiguous":
                        endpoint["status"] = "resolved"
                        endpoint["resolved_id"] = endpoint["candidate_ids"][0]
                row["status"] = "resolved"
            result["snapshot_sha256"] = et.snapshot_digest(result)
            return result
        result = gc.run_suite(SimpleNamespace(MappingError=self.mapper.MappingError, reconcile=target), False)
        self.assertTrue(any(r["case"] == "equivalence_does_not_pick_revision" and r["status"] == "FAIL" for r in result["checks"]))

    def test_dropped_link_control_cannot_vacuously_pass_revision_check(self):
        def target(document):
            result = self.mapper.reconcile(document)
            result["links"] = []
            result["snapshot_sha256"] = et.snapshot_digest(result)
            return result
        result = gc.run_suite(SimpleNamespace(MappingError=self.mapper.MappingError, reconcile=target), False)
        failures = {r["case"] for r in result["checks"] if r["status"] == "FAIL"}
        self.assertIn("equivalence_does_not_pick_revision", failures)
        self.assertIn("qualified_v1_citation_survives_equivalence", failures)

    def test_long_chain_needs_no_recursive_traversal(self):
        records = [gc.record(str(i)) for i in range(1200)]
        ds = [gc.decision(f"D-{i:04}", records[i], records[i+1]) for i in range(len(records)-1)]
        graph = et.ReportGraph(self.report(records, ds))
        ids = {n["original"]["payload"]["case_label"]: oid for oid, n in graph.nodes.items()}
        trace = graph.explain(ids["0"], ids["1199"])
        self.assertEqual(len(trace["steps"]), 1199)
        self.assertEqual(len(trace["occurrences"]), 1200)

    def test_wrong_blob_is_rejected_before_target_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "target.py"
            path.write_text('raise RuntimeError("must not execute")\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                gc.load_mapper(path, "0" * 40)

    def test_cli_receipt_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "receipt.json"
            cmd = [sys.executable, "-O"] if sys.flags.optimize else [sys.executable]
            cmd += [str(HERE / "graph_cases.py"), "--mapper", str(MAPPER), "--quick", "--out", str(output)]
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            retained = output.read_bytes()
            self.assertEqual(json.loads(retained)["summary"]["passed"], 32)
            repeated = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(output.read_bytes(), retained)

    def test_example_replay_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "example"
            cmd = [sys.executable, "-O"] if sys.flags.optimize else [sys.executable]
            cmd += [str(HERE / "example.py"), "--mapper", str(MAPPER), "--out", str(output)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            self.assertEqual(observed["summary"]["occurrences"], 5)
            self.assertEqual(observed["summary"]["unresolved_links"], 1)
            self.assertEqual(observed["supporting_decisions"], 3)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(len(manifest["files"]), 6)
            for name, expected in manifest["files"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)
            graph = et.ReportGraph(json.loads((output / "report.json").read_text()))
            self.assertEqual(graph.explain(observed["left"], observed["right"]),
                             json.loads((output / "trace.json").read_text()))
            repeated = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(repeated.returncode, 2)

    def test_trace_render_does_not_create_source_supplied_markup(self):
        a = gc.record("A")
        a["id"] = "[bait](https://example.invalid) *bold* | <img src=x>"
        report = self.report([a])
        graph = et.ReportGraph(report)
        oid = next(iter(graph.nodes))
        rendered = et.render_markdown(graph.explain(oid, oid))
        self.assertNotIn("[bait](", rendered)
        self.assertNotIn("*bold*", rendered)
        self.assertNotIn("<img", rendered)
        self.assertIn("&#124;", rendered)


if __name__ == "__main__":
    unittest.main()
