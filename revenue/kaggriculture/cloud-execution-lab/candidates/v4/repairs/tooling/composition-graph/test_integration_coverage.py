import copy
import importlib.util
import pathlib
import unittest

SPEC = importlib.util.spec_from_file_location(
    "integration_coverage",
    pathlib.Path(__file__).with_name("check_integration_coverage.py"),
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.integration = {
            "schema": mod.INTEGRATION_SCHEMA,
            "landed": [
                {"lane": "A", "repair_path": "repairs/a", "status": "tested"},
                {"lane": "B", "repair_path": "repairs/b", "composition_state": "blocked", "status": "tested"},
                {"lane": "No path", "status": "evidence"},
            ],
        }
        self.composition = {
            "schema": mod.COMPOSITION_SCHEMA,
            "components": [
                {"id": "b", "package": "repairs/b", "state": "blocked"},
            ],
        }
        self.coverage = {
            "schema": mod.COVERAGE_SCHEMA,
            "mode": "fail_closed",
            "entries": [
                {
                    "repair_path": "repairs/a",
                    "lane": "A",
                    "disposition": "evidence_only",
                    "graph_component": None,
                    "reason": "not wired",
                },
                {
                    "repair_path": "repairs/b",
                    "lane": "B",
                    "disposition": "blocked",
                    "graph_component": "b",
                    "reason": "waiting",
                },
            ],
        }

    def audit(self):
        return mod.audit_ledgers(self.integration, self.composition, self.coverage)

    def codes(self):
        return {e["code"] for e in self.audit()["errors"]}

    def test_valid_current_shape(self):
        out = self.audit()
        self.assertTrue(out["ok"])
        self.assertEqual(out["classified_count"], 2)
        self.assertEqual([x["repair_path"] for x in out["action_required"]], ["repairs/a"])
        self.assertEqual(out["graph_bound"][0]["component"], "b")
        self.assertEqual(len(out["coverage_digest"]), 64)

    def test_new_integration_path_must_be_classified(self):
        self.integration["landed"].append({"lane": "C", "repair_path": "repairs/c"})
        self.assertIn("unclassified_integration_path", self.codes())

    def test_extra_coverage_path_rejected(self):
        self.coverage["entries"].append(
            {"repair_path": "repairs/c", "lane": "C", "disposition": "blocked", "reason": "x"}
        )
        self.assertIn("coverage_path_not_in_integration", self.codes())

    def test_duplicate_integration_path_rejected(self):
        self.integration["landed"].append({"lane": "A2", "repair_path": "repairs/a"})
        self.assertIn("duplicate_integration_repair_path", self.codes())

    def test_duplicate_coverage_path_rejected(self):
        self.coverage["entries"].append(copy.deepcopy(self.coverage["entries"][0]))
        self.assertIn("duplicate_coverage_repair_path", self.codes())

    def test_lane_mismatch_rejected(self):
        self.coverage["entries"][0]["lane"] = "wrong"
        self.assertIn("lane_mismatch", self.codes())

    def test_unsafe_path_rejected(self):
        self.integration["landed"][0]["repair_path"] = "../escape"
        self.assertIn("unsafe_integration_repair_path", self.codes())

    def test_bad_disposition_rejected(self):
        self.coverage["entries"][0]["disposition"] = "ready-ish"
        self.assertIn("bad_disposition", self.codes())

    def test_compose_requires_graph_component(self):
        self.coverage["entries"][0]["disposition"] = "compose"
        self.coverage["entries"][0].pop("reason")
        self.assertIn("compose_without_graph_component", self.codes())

    def test_unknown_graph_component_rejected(self):
        self.coverage["entries"][1]["graph_component"] = "missing"
        self.assertIn("unknown_graph_component", self.codes())

    def test_graph_package_mismatch_rejected(self):
        self.composition["components"][0]["package"] = "repairs/other"
        self.assertIn("graph_package_mismatch", self.codes())

    def test_graph_state_mismatch_rejected(self):
        self.composition["components"][0]["state"] = "compose"
        self.assertIn("graph_state_mismatch", self.codes())

    def test_graph_component_must_be_coverage_bound(self):
        self.coverage["entries"][1]["graph_component"] = None
        self.assertIn("graph_component_not_bound_to_coverage", self.codes())

    def test_integration_composition_state_mismatch_rejected(self):
        self.coverage["entries"][1]["disposition"] = "evidence_only"
        self.assertIn("integration_composition_state_mismatch", self.codes())

    def test_non_applicable_cannot_bind_graph(self):
        self.coverage["entries"][0].update(
            {"disposition": "non_applicable", "graph_component": "b", "reason": "not a transform"}
        )
        self.assertIn("non_applicable_has_graph_component", self.codes())

    def test_blocked_requires_reason(self):
        self.coverage["entries"][0]["disposition"] = "blocked"
        self.coverage["entries"][0].pop("reason")
        self.assertIn("disposition_without_reason", self.codes())


if __name__ == "__main__":
    unittest.main()
