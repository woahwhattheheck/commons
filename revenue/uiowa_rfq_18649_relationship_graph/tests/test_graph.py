import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("graph_builder", HERE / "build_graph.py")
graph_builder = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(graph_builder)

class RelationshipGraphTests(unittest.TestCase):
    def canonical(self):
        return graph_builder.build_graph(ROOT, HERE / "graph_annotations.json", None)

    def demo(self):
        return graph_builder.build_graph(
            ROOT,
            HERE / "graph_annotations.json",
            HERE / "demo_unsupported_links.json",
        )

    def test_canonical_graph_has_no_integrity_errors(self):
        graph = self.canonical()
        self.assertEqual(graph_builder.validate_graph(graph), [])
        self.assertEqual(graph["summary"]["node_types"]["recommendation"], 2)
        self.assertEqual(graph["summary"]["node_types"]["finding"], 3)
        self.assertEqual(graph["summary"]["node_types"]["observation"], 8)
        self.assertEqual(graph["summary"]["node_types"]["evidence"], 8)
        self.assertEqual(graph["summary"]["node_types"]["source"], 8)
        self.assertNotIn("missing", graph["summary"]["node_types"])

    def test_recommendation_chain_reaches_exact_source_locator(self):
        graph = self.canonical()
        nodes = {n["id"]: n for n in graph["nodes"]}
        edges = {(e["from"], e["to"], e["relation"], e["state"]) for e in graph["edges"]}
        self.assertIn(("REC:R-001", "FND:F-002", "recommendation_to_finding", "supported"), edges)
        self.assertIn(("FND:F-002", "OBS:E-004", "finding_to_observation", "supporting"), edges)
        self.assertIn(("OBS:E-004", "EV:E-004", "observation_to_evidence", "supported"), edges)
        self.assertIn(("EV:E-004", "SRC:E-004", "evidence_to_source", "supported"), edges)
        self.assertEqual(nodes["SRC:E-004"]["details"]["locator"], "interface section 4")

    def test_counter_evidence_is_explicit(self):
        graph = self.canonical()
        edges = [e for e in graph["edges"] if e["from"] == "FND:F-002" and e["to"] == "OBS:E-006"]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["state"], "counter_evidence")

    def test_shared_report_references_survive(self):
        graph = self.canonical()
        nodes = {n["id"]: n for n in graph["nodes"]}
        refs = nodes["FND:F-002"]["details"]["report_references"]
        self.assertEqual({r["statement_id"] for r in refs}, {"S-002", "S-004"})
        self.assertEqual(
            {r["report_location"] for r in refs},
            {"executive-summary.md#material-gap", "final-report.md#recommendation-1"},
        )

    def test_demo_unsupported_reference_remains_visible(self):
        graph = self.demo()
        nodes = {n["id"]: n for n in graph["nodes"]}
        self.assertIn("MISSING:F-DEMO-999", nodes)
        self.assertEqual(nodes["MISSING:F-DEMO-999"]["state"], "unsupported_reference")
        unsupported = [e for e in graph["edges"] if e["state"] == "unsupported"]
        self.assertEqual(len(unsupported), 1)
        self.assertEqual(graph_builder.validate_graph(graph), [])

    def test_static_example_matches_builder(self):
        built = self.demo()
        checked = json.loads((HERE / "examples" / "graph.json").read_text(encoding="utf-8"))
        self.assertEqual(checked, built)
        html = (HERE / "examples" / "graph.html").read_text(encoding="utf-8")
        self.assertIn("const GRAPH=", html)
        self.assertIn("SYNTHETIC rehearsal only", html)
        self.assertNotIn('src="http', html)
        self.assertNotIn('href="http', html)

if __name__ == "__main__":
    unittest.main()
