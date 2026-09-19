#!/usr/bin/env python3
"""HERON's source-pinned consumer challenges; not a production 023 adapter.

Run with three local published inputs. No network, input writes, or fixture repair.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

PINS = {
    "core": "ec35cbd8317ccd1fe93dcb8a05458c9e40f4121a",
    "adapter": "e3a7dfdaee58a453ffb5bd208e9f0e6bbac64cb8",
    "register": "fc2ef567e3f9b3f5a5031c74994e62c62b1d9c7e",
}
SCOPE = {"synthetic": True, "collection": "published-uiowa-023-register"}
IAM_POLICY = "EV-SYN-IAM-DEP-POL-004"
IAM_CHANGES = "EV-SYN-IAM-DEP-CHG-005"


def blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def challenge_suite(core, adapter, raw):
    """Project a *test-only* register view; never claim original document text."""
    index = adapter.build_index(raw)
    graph = {k: copy.deepcopy(index[k]) for k in ("schema", "namespace", "coverage", "provenance")}
    graph["scope"] = copy.deepcopy(SCOPE)
    graph["artifacts"] = []
    for artifact in index["artifacts"]:
        projected = {k: copy.deepcopy(artifact[k]) for k in ("id", "kind", "locator", "depends_on")}
        projected["notes"] = artifact["dependency_basis"]
        graph["artifacts"].append(projected)
    before = {"schema": core.MANIFEST, "namespace": adapter.NAMESPACE,
              "snapshot_id": "HERON-SYNTHETIC-REGISTER-BEFORE", "captured_at": "2026-09-19T13:00:00Z",
              "scope": copy.deepcopy(SCOPE), "coverage": "complete", "sources": []}
    for record in index["register_records"]:
        before["sources"].append({"id": record["source_id"], "revision": adapter.REGISTER_BLOB,
          "text": core.canonical(record["fields"]), "metadata": {"locator": record["locator"],
            "representation_notice": "Canonical register record, NOT original referenced document text."},
          "interpretation": {}})

    class ConsumerChallenges(unittest.TestCase):
        def setUp(self):
            self.before = copy.deepcopy(before)
            self.after = copy.deepcopy(before)
            self.after.update(snapshot_id="HERON-SYNTHETIC-REGISTER-AFTER", captured_at="2026-09-19T13:01:00Z")
            self.graph = copy.deepcopy(graph)

        def source(self, sid, collection=None):
            return next(s for s in (collection or self.after)["sources"] if s["id"] == sid)

        def report(self):
            return core.analyze(self.before, self.after, self.graph)

        def test_actual_seven_records_fourteen_nodes(self):
            result = self.report()
            self.assertEqual(result["counts"], {"unchanged": 7})
            self.assertEqual(len(result["artifacts"]), 14)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual([d["code"] for d in result["diagnostics"]], ["partial_dependency_coverage"])

        def test_rich_inventory_is_not_silently_a_core_graph(self):
            with self.assertRaisesRegex(core.InputError, "unknown fields"):
                core.analyze(self.before, self.after, index)
            self.assertTrue(all(a["notes"] for a in self.graph["artifacts"]))

        def test_both_iam_causes_reach_shared_finding_and_narrative(self):
            for sid in (IAM_POLICY, IAM_CHANGES):
                self.source(sid)["text"] += " Synthetic review amendment."
            result = self.report()
            for target in ("FND-SYN-IAM-DEP-001", "UIOWA-023-CASE-D", "UIOWA-023-REGISTER"):
                row = next(a for a in result["artifacts"] if a["artifact_id"] == target)
                self.assertEqual({c["source_id"] for c in row["causes"]}, {IAM_POLICY, IAM_CHANGES})
            narrative = next(a for a in result["artifacts"] if a["artifact_id"] == "UIOWA-023-CASE-D")
            paths = [c["path"] for c in narrative["causes"]]
            self.assertIn("artifact:OBS-SYN-IAM-DEP-001", paths[1])
            self.assertIn("artifact:OBS-SYN-IAM-DEP-002", paths[0])

        def test_unknown_and_known_cause_coexist_without_false_resolution(self):
            self.source(IAM_POLICY)["text"] += " Synthetic exception wording."
            self.source(IAM_CHANGES)["text"] = None
            narrative = next(a for a in self.report()["artifacts"] if a["artifact_id"] == "UIOWA-023-CASE-D")
            self.assertEqual(narrative["action"], "resolve_comparison_or_mapping")
            self.assertEqual({c["change_type"] for c in narrative["causes"]}, {"text_changed", "comparison_unavailable"})

        def test_register_text_must_not_be_treated_as_underlying_evidence(self):
            for manifest in (self.before, self.after):
                for source in manifest["sources"]:
                    source["interpretation"]["register_record"] = json.loads(source.pop("text"))
                    source["unavailable_reason"] = "Referenced document bytes and fingerprints were not supplied."
            self.source(IAM_POLICY)["interpretation"]["register_record"]["claim"] += " Synthetic amendment."
            result = self.report()
            self.assertEqual(result["counts"], {"comparison_unavailable": 7})
            row = next(s for s in result["source_changes"] if s["source_id"] == IAM_POLICY)
            self.assertIn("register_record", row["interpretation_changes"])
            self.assertIsNone(row["text_change"])

        def test_graph_scope_missing_is_visible_not_defaulted(self):
            self.graph.pop("scope")
            result = self.report()
            self.assertTrue(all(a["mapping_incomplete"] for a in result["artifacts"]))
            self.assertIn("unbound_dependency_scope", [d["code"] for d in result["diagnostics"]])

        def test_cross_engagement_graph_refused(self):
            self.graph["scope"]["collection"] = "a different engagement"
            with self.assertRaisesRegex(core.InputError, "dependency scope mismatch"):
                self.report()

        def test_projection_preserves_notes_and_physical_source_locators(self):
            self.assertEqual([s["metadata"]["locator"] for s in self.before["sources"]],
                             [r["locator"] for r in index["register_records"]])
            for original, projected in zip(index["artifacts"], self.graph["artifacts"]):
                self.assertEqual(original["dependency_basis"], projected["notes"])
                self.assertEqual(original["depends_on"], projected["depends_on"])

        def test_partial_source_inventory_cannot_fabricate_removal(self):
            self.after["sources"] = [s for s in self.after["sources"] if s["id"] != IAM_POLICY]
            self.after["coverage"] = "partial"
            result = self.report()
            self.assertEqual(result["counts"], {"unchanged": 6, "comparison_unavailable": 1})
            narrative = next(a for a in result["artifacts"] if a["artifact_id"] == "UIOWA-023-CASE-D")
            self.assertEqual(narrative["action"], "resolve_comparison_or_mapping")

        def test_inputs_and_rich_inventory_remain_unchanged(self):
            saved = core.canonical([index, self.before, self.after, self.graph])
            self.report()
            self.assertEqual(core.canonical([index, self.before, self.after, self.graph]), saved)

    return unittest.defaultTestLoader.loadTestsFromTestCase(ConsumerChallenges)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in PINS:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in PINS}
    observed = {name: blob(path) for name, path in paths.items()}
    if observed != PINS:
        parser.exit(2, "Source binding mismatch; reconcile before re-running: " + json.dumps(observed) + "\n")
    core = load("heron_exact_core", paths["core"])
    adapter = load("heron_exact_peer_adapter", paths["adapter"])
    result = unittest.TextTestRunner(verbosity=2).run(challenge_suite(core, adapter, paths["register"].read_bytes()))
    unchanged = all(blob(path) == PINS[name] for name, path in paths.items())
    print(json.dumps({"source_blobs": observed, "tests_run": result.testsRun,
                      "successful": result.wasSuccessful(), "inputs_unchanged": unchanged}, sort_keys=True))
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
