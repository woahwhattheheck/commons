from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

import compare as subject


def valid_receipt() -> dict:
    return {
        "schema_version": 1,
        "operation": subject.OPERATION,
        "source": {
            "scheduler_git_blob_sha1": "7c068b7078c3d7c09bb3836590ad42b0af934cdf",
            "closure_sha256": "1" * 64,
        },
        "ablation": {
            "kind": subject.EXPECTED_KIND,
            "changed_files": ["scheduler.py"],
            "scheduler_git_blob_sha1": "3" * 40,
            "closure_sha256": "2" * 64,
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1,
            "removed_scenario_names": list(subject.EXPECTED_REMOVED_SCENARIOS),
            "preserved_v2_markers": {
                name: True for name in subject.EXPECTED_MARKERS
            },
        },
    }


def valid_report() -> dict:
    report = copy.deepcopy(subject.expected_report_custody())
    report["games"] = [
        {
            "opponent": "arlene",
            "seed": subject.EXPECTED_SEEDS[0],
            "candidate_seat": 0,
        }
    ]
    return report


class ComparatorAdapterContracts(unittest.TestCase):
    def test_valid_receipt_reuses_strict_closure_gate(self):
        identity = subject.validate_receipt(valid_receipt())
        self.assertEqual(identity["source_closure_sha256"], "1" * 64)
        self.assertEqual(identity["ablation_closure_sha256"], "2" * 64)
        self.assertNotEqual(
            identity["source_closure_sha256"],
            identity["ablation_closure_sha256"],
        )

    def test_wrong_operation_is_rejected(self):
        receipt = valid_receipt()
        receipt["operation"] = "other"
        with self.assertRaises(subject.CompareError):
            subject.validate_receipt(receipt)

    def test_removed_scenario_identity_is_exact(self):
        for mutation in ("missing", "reordered", "extra"):
            with self.subTest(mutation=mutation):
                receipt = valid_receipt()
                names = receipt["ablation"]["removed_scenario_names"]
                if mutation == "missing":
                    names.pop()
                elif mutation == "reordered":
                    names.reverse()
                else:
                    names.append("invented")
                with self.assertRaises(subject.CompareError):
                    subject.validate_receipt(receipt)

    def test_missing_or_false_preserved_marker_is_rejected(self):
        for mutation in ("missing", "false"):
            with self.subTest(mutation=mutation):
                receipt = valid_receipt()
                marker = next(iter(subject.EXPECTED_MARKERS))
                if mutation == "missing":
                    del receipt["ablation"]["preserved_v2_markers"][marker]
                else:
                    receipt["ablation"]["preserved_v2_markers"][marker] = False
                with self.assertRaises(subject.CompareError):
                    subject.validate_receipt(receipt)

    def test_report_custody_requires_literal_workflow_seed_grid(self):
        report = valid_report()
        subject.validate_report_custody(report, "control")
        report["seeds"] = list(subject.EXPECTED_SEEDS[:-1])
        with self.assertRaises(subject.CompareError):
            subject.validate_report_custody(report, "control")

    def test_boolean_candidate_seat_is_not_integer_identity(self):
        report = valid_report()
        report["games"][0]["candidate_seat"] = True
        with self.assertRaises(subject.CompareError):
            subject.validate_report_custody(report, "control")

    def test_report_custody_binds_on_disk_evaluator_and_opponent_bytes(self):
        for mutation in ("loader", "evaluator", "opponent"):
            with self.subTest(mutation=mutation):
                report = valid_report()
                if mutation == "loader":
                    report["loader_sha256"] = "0" * 64
                elif mutation == "evaluator":
                    report["evaluator_sha256"] = "0" * 64
                else:
                    report["opponents"]["arlene"]["sha256"] = "0" * 64
                with self.assertRaises(subject.CompareError):
                    subject.validate_report_custody(report, "control")

    def test_duplicate_and_nonfinite_json_remain_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text('{"x": 1, "x": 2}\n', encoding="utf-8")
            with self.assertRaises(subject.CompareError):
                subject.strict_object(path)
            path.write_text('{"x": NaN}\n', encoding="utf-8")
            with self.assertRaises(subject.CompareError):
                subject.strict_object(path)

    def test_markdown_and_reason_name_the_actual_ablation(self):
        report = {
            "verdict": "NO_ACTION_SIGNAL",
            "reason": "the target-domain ablation never changed a returned action trace",
            "exit_code": 4,
        }
        rendered = subject.markdown(copy.deepcopy(report))
        self.assertIn(
            "# TITAN V2 delayed-rival stress-scenario ablation",
            rendered,
        )
        self.assertIn("delayed-rival stress-scenario ablation", rendered)
        self.assertNotIn("target-domain ablation", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
