"""Independent missing-frontier regressions; no network or institution records."""
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import lineage as L
import walkthrough as W
from test_lineage import row, manifest, findings


class FrontierRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.a = row(rid="A")
        self.b = row(rid="B", content="b", version="b", supersedes=[L.reference(self.a)])
        self.c = row(rid="C", content="c", version="c", supersedes=[L.reference(self.b)])
        self.d = row(rid="D", content="d", version="d", supersedes=[L.reference(self.a)])

    def report(self, before, after, cited=None):
        return L.compare(manifest(*before), manifest(*after), findings(cited or self.a))

    def impact(self, before, after, cited=None):
        return self.report(before, after, cited)["finding_impacts"][0]

    def test_retained_original_does_not_hide_missing_declared_terminal(self):
        impact = self.impact([self.a, self.b, self.c], [self.a])
        self.assertEqual(impact["status"], "DECLARED_SUCCESSOR_MISSING_REVIEW")
        self.assertEqual(impact["retained_exact_copies"], [L.reference(self.a)])
        self.assertEqual(impact["missing_declared_successors"], [L.reference(self.c)])
        self.assertEqual(impact["declared_successors"], [])

    def test_retained_intermediate_does_not_become_terminal(self):
        impact = self.impact([self.a, self.b, self.c], [self.b])
        self.assertEqual(impact["status"], "DECLARED_SUCCESSOR_MISSING_REVIEW")
        self.assertEqual(impact["missing_declared_successors"], [L.reference(self.c)])
        self.assertNotIn(L.reference(self.b), impact["declared_successors"])

    def test_empty_after_preserves_historical_terminal(self):
        impact = self.impact([self.a, self.b, self.c], [])
        self.assertEqual(impact["status"], "DECLARED_SUCCESSOR_MISSING_REVIEW")
        self.assertEqual(impact["declared_terminal_successors"],
                         [{**L.reference(self.c), "present_in_after": False}])

    def test_one_missing_branch_is_still_a_branch(self):
        impact = self.impact([self.a, self.b, self.d], [self.b])
        self.assertEqual(impact["status"], "BRANCHED_SUCCESSION_REVIEW")
        self.assertEqual(impact["declared_successors"], [L.reference(self.b)])
        self.assertEqual(impact["missing_declared_successors"], [L.reference(self.d)])

    def test_all_branch_tips_missing_remains_branched(self):
        impact = self.impact([self.a, self.b, self.d], [self.a])
        self.assertEqual(impact["status"], "BRANCHED_SUCCESSION_REVIEW")
        self.assertEqual(len(impact["missing_declared_successors"]), 2)
        self.assertFalse(any(r["present_in_after"] for r in impact["declared_terminal_successors"]))

    def test_equal_hash_under_another_id_does_not_hide_missing_record(self):
        copy = {**self.c, "record_id": "copy-C"}
        impact = self.impact([self.a, self.b, self.c], [copy])
        # Both independently declared terminal record identities remain visible.
        self.assertEqual(impact["status"], "BRANCHED_SUCCESSION_REVIEW")
        self.assertEqual(impact["missing_declared_successors"], [L.reference(self.c)])
        self.assertEqual(impact["declared_successors"], [L.reference(copy)])

    def test_changed_bytes_under_same_id_do_not_count_as_present(self):
        changed = {**self.c, "sha256": hashlib.sha256(b"changed").hexdigest(), "supersedes": []}
        impact = self.impact([self.a, self.b, self.c], [changed])
        self.assertEqual(impact["status"], "DECLARED_SUCCESSOR_MISSING_REVIEW")
        self.assertEqual(impact["missing_declared_successors"], [L.reference(self.c)])

    def test_unrelated_missing_history_does_not_contaminate_citation(self):
        unrelated = row(rid="OTHER", document="OTHER", version="x", content="other")
        impact = self.impact([self.a, unrelated], [self.a])
        self.assertEqual(impact["status"], "EXACT_CONTENT_RETAINED")
        self.assertNotIn("missing_declared_successors", impact)

    def test_citation_to_tip_does_not_include_itself_as_successor(self):
        impact = self.impact([self.a, self.b, self.c], [self.c], self.c)
        self.assertEqual(impact["status"], "EXACT_CONTENT_RETAINED")
        self.assertEqual(impact["declared_successors"], [])
        self.assertNotIn("missing_declared_successors", impact)

    def test_convergence_does_not_preserve_obsolete_branch_count(self):
        e = row(rid="E", content="e", version="e", supersedes=[L.reference(self.c), L.reference(self.d)])
        impact = self.impact([self.a, self.b, self.c, self.d], [e])
        self.assertEqual(impact["status"], "DECLARED_SUPERSEDED_REVIEW")
        self.assertEqual(impact["declared_successors"], [L.reference(e)])
        self.assertNotIn("missing_declared_successors", impact)

    def test_dangling_and_cross_document_declarations_stay_diagnostics(self):
        dangling = row(rid="X", content="x", version="x", supersedes=[L.reference(row(rid="UNKNOWN"))])
        cross = row(rid="Y", document="OTHER", content="y", version="y", supersedes=[L.reference(self.a)])
        report = self.report([self.a, self.b, self.c], [self.a, dangling, cross])
        self.assertEqual(report["finding_impacts"][0]["missing_declared_successors"], [L.reference(self.c)])
        self.assertEqual({r["kind"] for r in report["anomalies"]}, {"DANGLING_PREDECESSOR", "CROSS_DOCUMENT_PREDECESSOR"})

    def test_multiple_citations_and_uncited_findings_remain_separate(self):
        f = findings(self.a)
        f["findings"][0]["citations"].append({**L.reference(self.c), "locator": "old conclusion"})
        f["findings"].append({"finding_id": "UNCITED", "citations": []})
        report = L.compare(manifest(self.a, self.b, self.c), manifest(self.a), f)
        self.assertEqual(len(report["finding_impacts"]), 3)
        self.assertEqual(report["input_findings"], f)
        self.assertEqual(report["summary"]["finding_status_counts"],
                         {"DECLARED_SUCCESSOR_MISSING_REVIEW": 1, "CONTENT_CHANGED_REVIEW": 1, "NO_CITATIONS_SUPPLIED": 1})

    def test_inputs_and_new_result_lists_are_isolated(self):
        before, after, f = manifest(self.a, self.b, self.c), manifest(self.a), findings(self.a)
        originals = deepcopy((before, after, f))
        report = L.compare(before, after, f)
        report["finding_impacts"][0]["missing_declared_successors"][0]["record_id"] = "edited"
        self.assertEqual((before, after, f), originals)
        self.assertEqual(report["before"], before)
        self.assertEqual(report["input_findings"], f)

    def test_manifest_permutations_preserve_derived_queue(self):
        baseline = self.impact([self.a, self.b, self.c, self.d], [self.a, self.c])
        for old in itertools.permutations([self.a, self.b, self.c, self.d]):
            for new in itertools.permutations([self.a, self.c]):
                self.assertEqual(self.impact(old, new), baseline)

    def test_markdown_exposes_both_tips_and_exact_presence(self):
        report = self.report([self.a, self.b, self.d], [self.b])
        rendered = L.markdown(report)
        self.assertIn("Declared successor records absent from after collection", rendered)
        self.assertIn("| F1 / A | B | " + self.b["sha256"] + " | Yes |", rendered)
        self.assertIn("| F1 / A | D | " + self.d["sha256"] + " | No -", rendered)
        self.assertIn("Omission is not deletion or approval", rendered)

    def test_markdown_escapes_missing_tip_identifiers(self):
        odd = {**self.c, "record_id": "C|<em>\nnext"}
        report = self.report([self.a, self.b, odd], [self.a])
        rendered = L.markdown(report)
        self.assertIn("C&#124;&lt;em&gt; next", rendered)
        self.assertNotIn("<em>", rendered)

    def test_missing_lineage_adds_no_verification_or_maturity_claim(self):
        report = self.report([self.a, self.b, self.c], [self.a])
        self.assertEqual(report["status"], "DRAFT_NON_AUTHORITATIVE")
        self.assertEqual(report["finding_impacts"][0]["locator_validation"], "NOT_PERFORMED")
        self.assertNotIn("maturity", report["finding_impacts"][0])
        self.assertNotIn("approval", report["finding_impacts"][0])

    def test_all_four_node_dags_and_after_subsets_against_independent_oracle(self):
        # 64 forward DAGs x 16 export subsets x 4 citations = 4096 cases.
        # Compute reachability from integer adjacency, not production helpers.
        possible = [(a, b) for a in range(4) for b in range(a + 1, 4)]
        checked = 0
        for edge_mask in range(1 << len(possible)):
            rows = [row(rid=f"N{i}", content=f"node {i}", version=f"v{i}") for i in range(4)]
            adjacency = {i: set() for i in range(4)}
            for bit, (a, b) in enumerate(possible):
                if edge_mask & (1 << bit):
                    adjacency[a].add(b)
                    rows[b].setdefault("supersedes", []).append(L.reference(rows[a]))
            before = manifest(*rows)
            for subset in range(16):
                after_indices = {i for i in range(4) if subset & (1 << i)}
                after = manifest(*(rows[i] for i in sorted(after_indices)))
                f = {"findings": [{"finding_id": f"F{i}", "citations": [{**L.reference(rows[i]), "locator": "line 1"}]} for i in range(4)]}
                report = L.compare(before, after, f)
                for origin, impact in enumerate(report["finding_impacts"]):
                    reachable = set(adjacency[origin])
                    for _ in range(4):
                        reachable |= {target for item in list(reachable) for target in adjacency[item]}
                    tips = {i for i in reachable if not adjacency[i]}
                    present, absent = tips & after_indices, tips - after_indices
                    expected = ("BRANCHED_SUCCESSION_REVIEW" if len(tips) > 1 else
                                "DECLARED_SUCCESSOR_MISSING_REVIEW" if absent else
                                "DECLARED_SUPERSEDED_REVIEW" if present else
                                "EXACT_CONTENT_RETAINED" if origin in after_indices else
                                "CONTENT_CHANGED_REVIEW" if after_indices else "MISSING_FROM_AFTER")
                    with self.subTest(edges=edge_mask, after=subset, citation=origin):
                        self.assertEqual(impact["status"], expected)
                        self.assertEqual(impact["declared_successors"], [L.reference(rows[i]) for i in sorted(present)])
                        self.assertEqual(impact.get("missing_declared_successors", []), [L.reference(rows[i]) for i in sorted(absent)])
                        if absent:
                            self.assertEqual(impact["declared_terminal_successors"],
                                             [{**L.reference(rows[i]), "present_in_after": i in after_indices} for i in sorted(tips)])
                    checked += 1
        self.assertEqual(checked, 4096)

    def test_long_declared_chain_is_iterative(self):
        rows = []
        for i in range(1200):
            current = row(rid=f"N{i:04}", content=f"data {i}", version=f"v{i}")
            if rows:
                current["supersedes"] = [L.reference(rows[-1])]
            rows.append(current)
        impact = self.impact(rows, [rows[0]], rows[0])
        self.assertEqual(impact["status"], "DECLARED_SUCCESSOR_MISSING_REVIEW")
        self.assertEqual(impact["missing_declared_successors"], [L.reference(rows[-1])])

    def test_cli_json_and_markdown_omit_no_known_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = {"before": manifest(self.a, self.b, self.d), "after": manifest(self.b), "findings": findings(self.a)}
            saved = {}
            for key, value in inputs.items():
                (root / (key + ".json")).write_text(L.encoded(value), encoding="utf-8")
                saved[key] = (root / (key + ".json")).read_bytes()
            command = [sys.executable] + (["-O"] if not __debug__ else []) + [str(Path(L.__file__)), "compare", str(root / "before.json"), str(root / "after.json"), "--findings", str(root / "findings.json")]
            json_run = subprocess.run(command, capture_output=True, text=True, timeout=15)
            text_run = subprocess.run(command + ["--format", "markdown"], capture_output=True, text=True, timeout=15)
            self.assertEqual(json_run.returncode, 0, json_run.stderr)
            self.assertEqual(text_run.returncode, 0, text_run.stderr)
            self.assertEqual(json.loads(json_run.stdout)["finding_impacts"][0]["status"], "BRANCHED_SUCCESSION_REVIEW")
            self.assertIn(self.d["sha256"], text_run.stdout)
            for key in saved:
                self.assertEqual((root / (key + ".json")).read_bytes(), saved[key])


class WalkthroughTests(unittest.TestCase):
    def test_seven_real_reports_have_declared_statuses(self):
        cases = W.scenarios()
        self.assertEqual(len(cases), 7)
        for case in cases:
            with self.subTest(case=case["name"]):
                report = L.compare(case["before"], case["after"], case["findings"])
                self.assertEqual(report["finding_impacts"][0]["status"], case["expected_status"])

    def test_written_bundle_is_reproducible_and_source_files_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            one, two = root / "one", root / "two"
            self.assertEqual(W.build(one), W.build(two))
            first = {p.relative_to(one).as_posix(): p.read_bytes() for p in one.rglob("*") if p.is_file()}
            second = {p.relative_to(two).as_posix(): p.read_bytes() for p in two.rglob("*") if p.is_file()}
            self.assertEqual(first, second)
            for case in W.scenarios():
                for label in ("before", "after"):
                    catalog = case[label]
                    result = L.snapshot(catalog, one / case["name"] / label)
                    self.assertEqual(result["records"], catalog["records"])

    def test_existing_destination_remains_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sentinel = root / "prior.txt"
            sentinel.write_bytes(b"prior review")
            with self.assertRaises(FileExistsError):
                W.build(root)
            self.assertEqual(sentinel.read_bytes(), b"prior review")
            self.assertEqual(list(root.iterdir()), [sentinel])

    def test_failed_semantic_evaluation_creates_no_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "new"
            with patch.object(W.lineage, "compare", side_effect=L.InvalidInput("deliberate evaluation failure")):
                with self.assertRaises(L.InvalidInput):
                    W.build(destination)
            self.assertFalse(destination.exists())

    def test_cli_refuses_reuse_without_reporting_success(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "rehearsal"
            command = [sys.executable] + (["-O"] if not __debug__ else []) + [str(Path(W.__file__)), str(out)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(len(json.loads(first.stdout)["cases"]), 7)
            old = (out / "walkthrough.json").read_bytes()
            again = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(again.stdout, "")
            self.assertEqual((out / "walkthrough.json").read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
