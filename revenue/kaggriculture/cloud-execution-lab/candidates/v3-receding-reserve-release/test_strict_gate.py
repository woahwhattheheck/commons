# SPDX-License-Identifier: Apache-2.0
"""Synthetic contracts for the independent own-cash admission gate."""
from __future__ import annotations

import copy
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import strict_gate as gate


def row(*, seat: int, own: float, margin: float, changed: bool = True) -> dict:
    return {
        "opponent": "arlene",
        "seed": 7,
        "seat": seat,
        "own_delta": own,
        "margin_delta": margin,
        "trace_changed": changed,
    }


def report(*rows: dict, verdict: str = "ADVANCE") -> dict:
    return {
        "schema_version": 1,
        "operation": gate.OPERATION,
        "verdict": verdict,
        "cells": len(rows),
        "rows": list(rows),
    }


class StrictOwnCashGateTests(unittest.TestCase):
    def test_positive_own_cash_and_margin_advances(self):
        result = gate.evaluate(
            report(
                row(seat=0, own=5, margin=5),
                row(seat=1, own=5, margin=5),
            )
        )
        self.assertEqual(result["verdict"], "ADVANCE")
        self.assertEqual(result["summary"]["negative_own_cells"], 0)
        self.assertEqual(result["summary"]["mean_own_delta"], 5)

    def test_margin_gain_by_harming_rival_cannot_hide_own_loss(self):
        result = gate.evaluate(
            report(
                row(seat=0, own=-1, margin=9),
                row(seat=1, own=-1, margin=9),
            )
        )
        self.assertEqual(result["verdict"], "HOLD")
        self.assertEqual(result["summary"]["negative_own_cells"], 2)
        self.assertGreater(result["summary"]["mean_margin_delta"], 0)

    def test_trace_only_change_without_cash_signal_holds(self):
        result = gate.evaluate(
            report(
                row(seat=0, own=0, margin=0),
                row(seat=1, own=0, margin=0),
            )
        )
        self.assertEqual(result["verdict"], "HOLD")
        self.assertEqual(result["reason"], "mean paired own cash did not improve")

    def test_no_signal_passes_through_only_with_unchanged_traces(self):
        clean = gate.evaluate(
            report(
                row(seat=0, own=0, margin=0, changed=False),
                row(seat=1, own=0, margin=0, changed=False),
                verdict="NO_SIGNAL",
            )
        )
        self.assertEqual(clean["verdict"], "NO_SIGNAL")

        with self.assertRaisesRegex(gate.StrictGateError, "changed traces"):
            gate.evaluate(
                report(
                    row(seat=0, own=0, margin=0, changed=True),
                    verdict="NO_SIGNAL",
                )
            )

    def test_malformed_duplicate_and_nonfinite_rows_fail_closed(self):
        valid = report(
            row(seat=0, own=1, margin=1),
            row(seat=1, own=1, margin=1),
        )
        variants = []

        missing = copy.deepcopy(valid)
        del missing["rows"][0]["own_delta"]
        variants.append(missing)

        duplicate = copy.deepcopy(valid)
        duplicate["rows"][1]["seat"] = 0
        variants.append(duplicate)

        nonfinite = copy.deepcopy(valid)
        nonfinite["rows"][0]["own_delta"] = math.inf
        variants.append(nonfinite)

        wrong_count = copy.deepcopy(valid)
        wrong_count["cells"] = 99
        variants.append(wrong_count)

        for candidate in variants:
            with self.subTest(candidate=candidate):
                with self.assertRaises(gate.StrictGateError):
                    gate.evaluate(candidate)


if __name__ == "__main__":
    unittest.main()
