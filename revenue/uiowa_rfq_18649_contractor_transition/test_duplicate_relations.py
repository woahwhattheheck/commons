#!/usr/bin/env python3
"""Regression for Trellis review 5256147892: do not erase duplicate edges.

ZZ-KESTREL-R9V6 implements the repair; ZZ-Trellis found and executed the original
cross-target witness. All records are fictional; no network or account action.
Run with: python -B -m unittest test_duplicate_relations (also with -O).
"""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import transition
from test_completion_integrity import packet

HERE = Path(__file__).resolve().parent


def three_completed():
    data = packet()
    for number in (2, 3):
        application = copy.deepcopy(data["applications"][0])
        application.update(id="SYN-APP-%03d" % number,
                           name="Fictional application %d" % number)
        data["applications"].append(application)
        change = copy.deepcopy(data["access_changes"][0])
        change.update(id="SYN-CHG-%03d" % number,
                      target_ref=application["id"],
                      evidence_ref="synthetic://duplicate-review/change-%03d" % number)
        data["access_changes"].append(change)
    return data


def cross_target_duplicate(status="REQUESTED"):
    data = three_completed()
    duplicate = copy.deepcopy(data["access_changes"][0])
    duplicate.update(target_ref="SYN-APP-002", status=status)
    if status != "COMPLETED":
        duplicate.update(evidence_ref=None, completed_at=None)
    data["access_changes"].append(duplicate)
    return data


def states(report):
    return {item["item_id"]: item["state"] for item in report.items}


class DuplicateRelationships(unittest.TestCase):
    def test_valid_three_item_control_is_closed_in_every_order(self):
        data = three_completed()
        before = copy.deepcopy(data)
        for order in itertools.permutations(data["access_changes"]):
            candidate = copy.deepcopy(data); candidate["access_changes"] = list(order)
            report, issues = transition.build(candidate)
            self.assertEqual(issues, [])
            self.assertTrue(report.transition_closed())
            self.assertEqual(set(states(report).values()), {"COMPLETED"})
        self.assertEqual(data, before)

    def test_both_targets_invalid_in_all_72_status_and_order_cases(self):
        expected = {"SYN-APP-001": "NO_EVIDENCE", "SYN-APP-002": "NO_EVIDENCE",
                    "SYN-APP-003": "COMPLETED"}
        cases = 0
        for status in ("REQUESTED", "IN_PROGRESS", "COMPLETED"):
            data = cross_target_duplicate(status)
            for order in itertools.permutations(data["access_changes"]):
                candidate = copy.deepcopy(data); candidate["access_changes"] = list(order)
                with self.subTest(status=status, order=[(r["id"], r["target_ref"]) for r in order]):
                    report, issues = transition.build(candidate)
                    self.assertFalse(report.transition_closed())
                    self.assertEqual(states(report), expected)
                    self.assertIn("DUPLICATE_RECORD_ID", [i.code for i in issues])
                    for item in report.items:
                        self.assertEqual(bool(item["evidence_refs"]), item["item_id"] == "SYN-APP-003")
                cases += 1
        self.assertEqual(cases, 72)

    def test_relationships_for_each_subject_survive_duplicate_order(self):
        data = cross_target_duplicate()
        data["applications"][1]["owner_ref"] = "SYN-PERSON-002"
        data["access_changes"][1]["subject_ref"] = "SYN-PERSON-002"
        data["access_changes"][-1]["subject_ref"] = "SYN-PERSON-002"
        for departing, expected in (
            ("SYN-PERSON-001", {"SYN-APP-001": "NO_EVIDENCE", "SYN-APP-003": "COMPLETED"}),
            ("SYN-PERSON-002", {"SYN-APP-002": "NO_EVIDENCE"}),
        ):
            for order in itertools.permutations(data["access_changes"]):
                candidate = copy.deepcopy(data); candidate["access_changes"] = list(order)
                candidate["transition"]["departing_ref"] = departing
                with self.subTest(departing=departing, order=[r["subject_ref"] for r in order]):
                    report, _ = transition.build(candidate)
                    self.assertFalse(report.transition_closed())
                    self.assertEqual(states(report), expected)

    def test_duplicate_for_another_subject_does_not_taint_unrelated_item(self):
        # The invalid ID affects every occurrence, but it is not a reason to
        # invalidate every record owned by any person named in those changes.
        data = cross_target_duplicate()
        data["access_changes"][-1]["subject_ref"] = "SYN-PERSON-002"
        report, _ = transition.build(data)
        self.assertEqual(states(report), {"SYN-APP-001": "NO_EVIDENCE",
            "SYN-APP-002": "COMPLETED", "SYN-APP-003": "COMPLETED"})
        self.assertFalse(report.transition_closed())

    def test_secondary_duplicate_with_no_successor_still_has_no_evidence(self):
        data = cross_target_duplicate()
        data["applications"][1].pop("successor_ref")
        for order in (data["access_changes"], list(reversed(data["access_changes"]))):
            candidate = copy.deepcopy(data); candidate["access_changes"] = order
            report, _ = transition.build(candidate)
            self.assertEqual(states(report)["SYN-APP-002"], "NO_EVIDENCE")
            self.assertEqual(states(report)["SYN-APP-003"], "COMPLETED")

    def test_duplicate_build_preserves_input_and_report_is_order_invariant(self):
        data = cross_target_duplicate(); before = copy.deepcopy(data)
        forward, _ = transition.build(data)
        self.assertEqual(data, before)
        reverse = copy.deepcopy(data); reverse["access_changes"].reverse()
        backward, _ = transition.build(reverse)
        self.assertEqual(forward.as_dict(), backward.as_dict())
        self.assertEqual(transition.render_markdown(forward), transition.render_markdown(backward))

    def test_cli_preserves_same_three_reports_when_duplicate_order_reverses(self):
        with tempfile.TemporaryDirectory(prefix="duplicate-relations-") as temporary:
            root = Path(temporary); outputs = []
            for number, data in enumerate((cross_target_duplicate(), cross_target_duplicate())):
                if number:
                    data["access_changes"].reverse()
                source = root / ("input-%d.json" % number)
                out = root / ("report-%d" % number)
                source.write_text(json.dumps(data), encoding="utf-8")
                flags = ["-O"] if sys.flags.optimize else []
                result = subprocess.run([sys.executable, "-B", *flags,
                    str(HERE / "transition.py"), "--input", str(source), "--outdir", str(out)],
                    text=True, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                outputs.append({p.name: p.read_bytes() for p in out.iterdir()})
            self.assertEqual(len(outputs[0]), 3)
            self.assertEqual(outputs[0], outputs[1])
            parsed = json.loads(outputs[0]["transition_report.json"])
            self.assertFalse(parsed["transition_closed"])
            self.assertEqual({i["item_id"]: i["state"] for i in parsed["items"]},
                {"SYN-APP-001": "NO_EVIDENCE", "SYN-APP-002": "NO_EVIDENCE", "SYN-APP-003": "COMPLETED"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
