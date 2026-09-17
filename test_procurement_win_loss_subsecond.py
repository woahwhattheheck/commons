#!/usr/bin/env python3
"""Regression tests for whole-second procurement chronology."""
from __future__ import annotations

import copy
import subprocess
import sys
import unittest
from pathlib import Path

from test_procurement_win_loss import FIXTURES
from tools.procurement_win_loss.compiler import OutcomeError, compile_record


ROOT = Path(__file__).resolve().parent


def _fractional(text: str, digits: str) -> str:
    if text.endswith("Z"):
        return f"{text[:-1]}.{digits}Z"
    if len(text) >= 6 and text[-6] in {"+", "-"} and text[-3] == ":":
        return f"{text[:-6]}.{digits}{text[-6:]}"
    raise AssertionError(f"fixture timestamp has unsupported spelling: {text}")


class ProcurementWinLossSubsecondTests(unittest.TestCase):
    def test_false_promotion_predecessor_is_rejected_before_truncation(self):
        row = copy.deepcopy(
            next(
                item["record"]
                for item in FIXTURES["valid"]
                if item["name"] == "later_pending_after_terminal_fails_closed"
            )
        )
        terminal = next(
            item for item in row["evidence"] if item["decision_signal"] in {"SELECTED", "AWARDED"}
        )
        pending = next(item for item in row["evidence"] if item["decision_signal"] == "PENDING")
        terminal_second = terminal["observed_at"]
        pending["observed_at"] = _fractional(terminal_second, "900")
        terminal["observed_at"] = _fractional(terminal_second, "100")
        with self.assertRaisesRegex(OutcomeError, "must be second-aligned"):
            compile_record(row)

    def test_fractional_compiled_at_rejected(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        row["compiled_at"] = _fractional(row["compiled_at"], "001")
        with self.assertRaisesRegex(OutcomeError, "record.compiled_at must be second-aligned"):
            compile_record(row)

    def test_fractional_observed_at_rejected(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        row["evidence"][0]["observed_at"] = _fractional(row["evidence"][0]["observed_at"], "500")
        with self.assertRaisesRegex(OutcomeError, "observed_at must be second-aligned"):
            compile_record(row)

    def test_fractional_captured_at_rejected(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        row["evidence"][0]["captured_at"] = _fractional(row["evidence"][0]["captured_at"], "999999")
        with self.assertRaisesRegex(OutcomeError, "captured_at must be second-aligned"):
            compile_record(row)

    def test_zero_fraction_is_second_aligned_and_canonicalized(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        original = row["compiled_at"]
        row["compiled_at"] = _fractional(original, "000")
        receipt = compile_record(row)
        self.assertEqual(receipt["compiled_at"], original)

    def test_optimized_mode_keeps_subsecond_guard(self):
        code = (
            "import copy\n"
            "from test_procurement_win_loss import FIXTURES\n"
            "from tools.procurement_win_loss.compiler import OutcomeError, compile_record\n"
            "row=copy.deepcopy(FIXTURES['valid'][0]['record'])\n"
            "stamp=row['compiled_at']\n"
            "row['compiled_at']=stamp[:-1]+'.123Z'\n"
            "try:\n"
            "    compile_record(row)\n"
            "except OutcomeError as exc:\n"
            "    raise SystemExit(0 if 'second-aligned' in str(exc) else 8)\n"
            "raise SystemExit(9)\n"
        )
        completed = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
