"""Tests for the fiction-labeling screen.

The load-bearing test in here is `test_a_real_measurement_is_not_required_to
_claim_it_is_synthetic`. The first version of this screen asked "does the file
say SYNTHETIC", and it flagged a generated report of a real scan -- for which
"SYNTHETIC" would have been a false statement. The requirement is that a
record-shaped artifact says WHICH it is. Getting that wrong would have had the
screen recommending people write falsehoods into their own outputs.
"""
from __future__ import annotations

import ast
import hashlib
import os
import shutil
import tempfile
import unittest

import label_scan
import labelcheck
from labelcheck import (
    DISCLOSED, LABEL_BURIED, NOT_EVIDENCE, UNDISCLOSED_PROVENANCE,
    UNLABELED_CONFIG_SHAPED, UNREADABLE,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
PRODUCTION_MODULES = ("labelcheck.py", "label_scan.py")

RECORDS = (
    "finding_id,service,area,state,statement\n"
    "F-SYN-001,ESS,software_delivery,DEMONSTRATED_STRENGTH,Reviews cover changes\n"
    "F-SYN-002,RIS,deployment,OBSERVED_GAP,No rebuild evidence supplied\n"
)


def hash_tree(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            with open(full, "rb") as fh:
                out[os.path.relpath(full, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


class TestFixtures(unittest.TestCase):
    def setUp(self):
        self.by_path = {r.path: r for r in labelcheck.scan_tree(FIXTURES)}

    def test_records_without_any_statement_are_the_finding(self):
        r = self.by_path[os.path.join("lane_records_unlabeled", "findings.csv")]
        self.assertEqual(r.status, UNDISCLOSED_PROVENANCE)
        self.assertEqual(r.shape, "RECORDS")

    def test_records_with_a_synthetic_header_are_disclosed(self):
        r = self.by_path[os.path.join("lane_records_labeled", "findings.csv")]
        self.assertEqual(r.status, DISCLOSED)
        self.assertEqual(r.label_offset, 0)

    def test_a_real_measurement_is_not_required_to_claim_it_is_synthetic(self):
        """The reframing test. A real scan output carrying a provenance
        statement is DISCLOSED. Demanding the word SYNTHETIC here would be
        demanding a false statement."""
        r = self.by_path[os.path.join("lane_real", "scan_results.csv")]
        self.assertEqual(r.status, DISCLOSED)
        with open(os.path.join(FIXTURES, "lane_real", "scan_results.csv"),
                  encoding="utf-8") as fh:
            text = fh.read()
        # The file must make no affirmative claim to be synthetic -- it says
        # the opposite. (Asserting the word is absent fails on the denial
        # itself, which is the same trap as the disclaimer checks elsewhere.)
        self.assertIn("not synthetic", text.lower())
        self.assertIn("REAL -", text)
        self.assertIn("provenance", text)

    def test_configuration_is_not_counted_as_a_finding(self):
        r = self.by_path[os.path.join("lane_config", "weights.json")]
        self.assertEqual(r.status, UNLABELED_CONFIG_SHAPED)
        summary = labelcheck.summarize(list(self.by_path.values()))
        self.assertNotIn("lane_config", summary["lanes_needing_a_label"])

    def test_a_buried_disclosure_is_its_own_class_not_a_pass(self):
        r = self.by_path[os.path.join("lane_buried", "report.md")]
        self.assertEqual(r.status, LABEL_BURIED)
        self.assertGreater(r.label_offset, labelcheck.DEFAULT_HEADER_BYTES)
        self.assertNotEqual(r.status, DISCLOSED)


class TestClassification(unittest.TestCase):
    def test_header_bytes_is_configurable_and_changes_the_verdict(self):
        text = ("x" * 900) + "\nF-SYN-001 ESS finding assessed\n" + "SYNTHETIC\n"
        strict = labelcheck.check_text(text, "l", "a.md", header_bytes=10)
        lenient = labelcheck.check_text(text, "l", "a.md", header_bytes=5000)
        self.assertEqual(strict.status, LABEL_BURIED)
        self.assertEqual(lenient.status, DISCLOSED)

    def test_documentation_is_not_required_to_disclose(self):
        r = labelcheck.check_text(
            "This README explains the ESS assessment findings format.", "l", "README.md")
        self.assertEqual(r.shape, "DOCUMENTATION")
        self.assertIn(r.status, (NOT_EVIDENCE, DISCLOSED))

    def test_for_example_is_not_a_disclosure(self):
        """'example' alone must not count -- 'for example' is ordinary prose."""
        r = labelcheck.check_text(
            RECORDS + "\nfor example, the ESS finding above\n", "l", "f.csv")
        self.assertEqual(r.status, UNDISCLOSED_PROVENANCE)

    def test_generic_data_without_engagement_subjects_is_not_flagged(self):
        r = labelcheck.check_text(
            "id,value\nA-001,3\nA-002,4\nA-003,5\n", "l", "d.csv")
        self.assertNotEqual(r.status, UNDISCLOSED_PROVENANCE)

    def test_unreadable_artifact_is_never_disclosed(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "lane_x")
            os.makedirs(lane)
            with open(os.path.join(lane, "bad.csv"), "wb") as fh:
                fh.write(b"\xff\xfe\x00 not utf-8 \xff" * 8)
            results = labelcheck.scan_tree(tmp)
            self.assertEqual(results[0].status, UNREADABLE)
            self.assertNotEqual(results[0].status, DISCLOSED)

    def test_tiny_files_are_skipped_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "lane_x")
            os.makedirs(lane)
            with open(os.path.join(lane, "stub.md"), "w", encoding="utf-8") as fh:
                fh.write("ESS\n")
            self.assertEqual(labelcheck.scan_tree(tmp), [])


class TestSummary(unittest.TestCase):
    def test_counts_sum_and_worst_status_per_lane(self):
        results = labelcheck.scan_tree(FIXTURES)
        s = labelcheck.summarize(results)
        self.assertEqual(sum(s["by_status"].values()), s["artifacts_examined"])
        self.assertEqual(s["lanes_by_worst_status"]["lane_records_unlabeled"],
                         UNDISCLOSED_PROVENANCE)
        self.assertEqual(s["lanes_by_worst_status"]["lane_buried"], LABEL_BURIED)
        self.assertEqual(sorted(s["lanes_needing_a_label"]),
                         ["lane_buried", "lane_records_unlabeled"])

    def test_needs_a_label_excludes_config_and_disclosed(self):
        s = labelcheck.summarize(labelcheck.scan_tree(FIXTURES))
        self.assertEqual(s["needs_a_label"], 2)


class TestScreenIsItselfNonDestructive(unittest.TestCase):
    DESTRUCTIVE_LEAF = {"rmtree", "removedirs", "unlink", "rmdir", "truncate"}
    DESTRUCTIVE_DOTTED = {"os.remove", "os.rename", "os.replace", "os.system",
                          "shutil.move", "subprocess.run", "subprocess.Popen"}

    @staticmethod
    def _dotted(node):
        parts, cur = [], node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts)) if parts else None

    def test_no_destructive_calls_in_the_screen(self):
        offenders = []
        for name in PRODUCTION_MODULES:
            with open(os.path.join(HERE, name), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    d = self._dotted(node.func)
                    if not d:
                        continue
                    if d.rsplit(".", 1)[-1] in self.DESTRUCTIVE_LEAF or d in self.DESTRUCTIVE_DOTTED:
                        offenders.append(f"{name}:{node.lineno} {d}")
        self.assertEqual(offenders, [])

    def test_only_the_approved_writer_opens_for_writing(self):
        offenders = []
        for name in PRODUCTION_MODULES:
            with open(os.path.join(HERE, name), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            enclosing = {}
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(fn):
                        enclosing.setdefault(child, fn.name)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "open"):
                    continue
                mode = ""
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = str(node.args[1].value)
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = str(kw.value.value)
                if set(mode) & set("wax+") and enclosing.get(node) != "write_output":
                    offenders.append(f"{name}:{node.lineno}")
        self.assertEqual(offenders, [])

    def test_scanning_leaves_the_tree_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_root = os.path.join(tmp, "scanned")
            shutil.copytree(FIXTURES, copy_root)
            before = hash_tree(copy_root)
            self.assertGreater(len(before), 0)
            labelcheck.scan_tree(copy_root)
            self.assertEqual(before, hash_tree(copy_root))

    def test_writer_refuses_to_escape_the_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            os.makedirs(out)
            for bad in ("../x.md", "a/../../x.md", "/tmp/x.md"):
                with self.assertRaises(ValueError, msg=bad):
                    label_scan.write_output(out, bad, "x")
            self.assertFalse(os.path.exists(os.path.join(tmp, "x.md")))


class TestCli(unittest.TestCase):
    def test_exit_1_and_outputs_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = label_scan.main(["--root", FIXTURES, "--output-dir", tmp])
            self.assertEqual(rc, 1)
            for name in ("FICTION_LABELING_SCREEN.md", "artifacts.csv", "screen.json"):
                self.assertTrue(os.path.isfile(os.path.join(tmp, name)), name)

    def test_generated_csv_states_its_own_provenance(self):
        """The screen flagged this tool's own CSV; the fix travels with the file."""
        with tempfile.TemporaryDirectory() as tmp:
            label_scan.main(["--root", FIXTURES, "--output-dir", tmp])
            with open(os.path.join(tmp, "artifacts.csv"), encoding="utf-8") as fh:
                text = fh.read()
        self.assertTrue(text.startswith("provenance,"))
        self.assertIn("not synthetic", text)
        result = labelcheck.check_text(text, "self", "artifacts.csv")
        self.assertNotEqual(result.status, UNDISCLOSED_PROVENANCE)

    def test_exit_0_on_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "src", "lane_ok")
            os.makedirs(lane)
            with open(os.path.join(lane, "f.csv"), "w", encoding="utf-8") as fh:
                fh.write("provenance,finding_id,service\nSYNTHETIC,F-1,ESS\n"
                         "SYNTHETIC,F-2,RIS\nSYNTHETIC,F-3,IAM\n")
            self.assertEqual(
                label_scan.main(["--root", os.path.join(tmp, "src"),
                                 "--output-dir", os.path.join(tmp, "o")]), 0)

    def test_exit_2_on_a_bad_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                label_scan.main(["--root", os.path.join(tmp, "nope"),
                                 "--output-dir", os.path.join(tmp, "o")]), 2)

    def test_report_awards_no_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            label_scan.main(["--root", FIXTURES, "--output-dir", tmp])
            with open(os.path.join(tmp, "FICTION_LABELING_SCREEN.md"),
                      encoding="utf-8") as fh:
                text = fh.read()
        body = text.replace(label_scan.DISCLAIMER, "").upper()
        for verdict in ("CERTIFIED", "COMPLIANT", "LABELING SCORE", "% LABELED"):
            self.assertNotIn(verdict, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
