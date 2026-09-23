"""Exercise the real twelve-case operator rehearsal, not a second compiler."""
import copy
from decimal import Decimal
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.revenue_collection_desk import core, rehearsal


class CollectionRehearsalTests(unittest.TestCase):
    def test_twelve_unique_expected_outcomes(self):
        result = rehearsal.run()
        self.assertEqual(len(result["cases"]), 12)
        self.assertEqual(len({case["id"] for case in result["cases"]}), 12)
        self.assertTrue(result["all_passed"])
        self.assertTrue(all(case["context_invariant"] for case in result["cases"]))

    def test_actual_outputs_replay_and_reject_tampering(self):
        result = rehearsal.run()
        for case in result["cases"]:
            with self.subTest(case=case["id"]):
                if "report" in case["actual"]:
                    self.assertTrue(core.verify_ledger(case["ledger"], case["actual"]["report"]))
                    self.assertTrue(case["replay_verified"])
                    self.assertTrue(case["tampered_report_rejected"])
                else:
                    with self.assertRaisesRegex(core.ContractError, case["expected_error"]):
                        core.compile_ledger(case["ledger"])

    def test_fixture_inputs_are_not_mutated(self):
        cases = rehearsal.cases()
        before = copy.deepcopy(cases)
        with patch.object(rehearsal, "cases", return_value=cases):
            rehearsal.run()
        self.assertEqual(cases, before)

    def test_zeroed_total_mutant_fails_rehearsal(self):
        with patch.object(core, "_sum_exact", return_value=Decimal(0)):
            result = rehearsal.run()
        self.assertFalse(result["all_passed"])
        exact = next(case for case in result["cases"] if case["id"] == "exact-money-across-contexts")
        self.assertFalse(exact["passed"])

    def test_rehearsal_receipt_covers_actual_inputs_and_outputs(self):
        result = rehearsal.run()
        receipt = result.pop("rehearsal_receipt_sha256")
        self.assertEqual(core.sha256_value(result), receipt)
        result["cases"][0]["ledger"]["claims"][0]["amount"] = "99"
        self.assertNotEqual(core.sha256_value(result), receipt)

    def test_readable_cli_contains_all_cases_and_limits(self):
        run = subprocess.run([sys.executable, "-m", "tools.revenue_collection_desk.rehearsal"], capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("fictional", run.stdout)
        self.assertIn("not real collection", run.stdout)
        self.assertIn("1234567890123456789012345678.1", run.stdout)
        for case in rehearsal.cases():
            self.assertIn("## " + case["id"], run.stdout)

    def test_real_normal_and_optimized_json_cli_are_identical(self):
        outputs = []
        for mode in ([], ["-O"]):
            run = subprocess.run([sys.executable, *mode, "-m", "tools.revenue_collection_desk.rehearsal", "--json"], capture_output=True, timeout=30, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            outputs.append(run.stdout)
        self.assertEqual(outputs[0], outputs[1])
        result = json.loads(outputs[0])
        self.assertTrue(result["synthetic"])
        self.assertTrue(result["all_passed"])
        self.assertEqual(result["precisions_exercised"], [3, 28, 80])

    def test_unexpected_compile_failure_is_not_reported_as_success(self):
        with patch.object(core, "compile_ledger", side_effect=core.ContractError("unexpected defect")):
            result = rehearsal.run()
        self.assertFalse(result["all_passed"])
        self.assertFalse(any(case["passed"] for case in result["cases"]))


if __name__ == "__main__":
    unittest.main()
