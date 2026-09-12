#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("_economics_gate_under_test", HERE / "economics_gate.py")
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


CONTROL = "v5c:" + "1" * 64
CANDIDATE = "v5c:" + "2" * 64


def report(*, delta: int = 10):
    cells = []
    for seed in range(100, 104):
        for seat in (0, 1):
            control_own = 1000 + seed + seat
            control_rival = 900 + seed
            # Preserve rival score and move own score by delta so paired margin
            # delta is exactly `delta` in every cell.
            cells.append(
                {
                    "seed": seed,
                    "seat": seat,
                    "control_own": control_own,
                    "control_rival": control_rival,
                    "candidate_own": control_own + delta,
                    "candidate_rival": control_rival,
                }
            )
    return {
        "schema": gate.SCHEMA,
        "control_id": CONTROL,
        "candidate_id": CANDIDATE,
        "cells": cells,
    }


class EconomicsGateTests(unittest.TestCase):
    def test_positive_panel_passes_and_recomputes_raw_margins(self):
        receipt = gate.validate_report(
            report(delta=10), candidate_id=CANDIDATE, control_id=CONTROL
        )
        self.assertEqual("PASS", receipt["classification"])
        self.assertTrue(receipt["promotion_ready"])
        self.assertEqual(8, receipt["cell_count"])
        self.assertEqual(4, receipt["seed_count"])
        self.assertEqual(80, receipt["sum_margin_delta"])
        self.assertEqual(10.0, receipt["mean_margin_delta"])
        self.assertEqual(8, receipt["positive_cells"])
        self.assertEqual(0, receipt["negative_cells"])
        self.assertRegex(receipt["panel_sha256"], r"^[0-9a-f]{64}$")

    def test_exact_zero_mean_is_no_regression_pass(self):
        receipt = gate.validate_report(
            report(delta=0), candidate_id=CANDIDATE, control_id=CONTROL
        )
        self.assertEqual(0, receipt["sum_margin_delta"])
        self.assertEqual(8, receipt["tied_cells"])

    def test_negative_mean_is_rejected(self):
        with self.assertRaisesRegex(gate.EconomicsError, "mean margin regresses"):
            gate.validate_report(
                report(delta=-1), candidate_id=CANDIDATE, control_id=CONTROL
            )

    def test_reported_summary_cannot_be_smuggled(self):
        value = report()
        value["mean_margin_delta"] = 999999
        with self.assertRaisesRegex(gate.EconomicsError, "keys mismatch"):
            gate.validate_report(value, candidate_id=CANDIDATE, control_id=CONTROL)

    def test_cross_build_candidate_is_rejected(self):
        with self.assertRaisesRegex(gate.EconomicsError, "does not match promotion candidate"):
            gate.validate_report(
                report(), candidate_id="v5c:" + "3" * 64, control_id=CONTROL
            )

    def test_cross_build_control_is_rejected(self):
        with self.assertRaisesRegex(gate.EconomicsError, "does not match promotion control"):
            gate.validate_report(
                report(), candidate_id=CANDIDATE, control_id="v5c:" + "4" * 64
            )

    def test_same_control_and_candidate_is_rejected(self):
        value = report()
        value["candidate_id"] = value["control_id"]
        with self.assertRaisesRegex(gate.EconomicsError, "must differ"):
            gate.validate_report(value)

    def test_duplicate_seed_seat_is_rejected(self):
        value = report()
        value["cells"][1] = copy.deepcopy(value["cells"][0])
        with self.assertRaisesRegex(gate.EconomicsError, "must be unique"):
            gate.validate_report(value)

    def test_unbalanced_seat_panel_is_rejected(self):
        value = report()
        # Keep eight unique cells but replace the final seat-1 cell by a new
        # seed that has only seat 0.  Both affected seeds are incomplete.
        value["cells"][-1] = {
            **value["cells"][-1],
            "seed": 104,
            "seat": 0,
        }
        value["cells"] = sorted(value["cells"], key=lambda cell: (cell["seed"], cell["seat"]))
        with self.assertRaisesRegex(gate.EconomicsError, "exactly both seats"):
            gate.validate_report(value)

    def test_too_small_panel_is_rejected(self):
        value = report()
        value["cells"] = value["cells"][:6]
        with self.assertRaisesRegex(gate.EconomicsError, "at least 8 cells"):
            gate.validate_report(value)

    def test_noncanonical_cell_order_is_rejected(self):
        value = report()
        value["cells"][0], value["cells"][1] = value["cells"][1], value["cells"][0]
        with self.assertRaisesRegex(gate.EconomicsError, "canonically sorted"):
            gate.validate_report(value)

    def test_bool_and_noninteger_scores_are_rejected(self):
        for bad in (True, 10.0, "10"):
            with self.subTest(bad=bad):
                value = report()
                value["cells"][0]["candidate_own"] = bad
                with self.assertRaisesRegex(gate.EconomicsError, "plain int"):
                    gate.validate_report(value)

    def test_cell_shape_is_closed(self):
        value = report()
        value["cells"][0]["claimed_delta"] = 1000000
        with self.assertRaisesRegex(gate.EconomicsError, "exact raw score keys"):
            gate.validate_report(value)

    def test_mixed_sign_panel_uses_recomputed_aggregate(self):
        value = report(delta=0)
        adjustments = (100, -20, -20, -20, -20, -20, -20, 20)
        for cell, adjustment in zip(value["cells"], adjustments):
            cell["candidate_own"] += adjustment
        receipt = gate.validate_report(value)
        self.assertEqual(0, receipt["sum_margin_delta"])
        self.assertEqual(2, receipt["positive_cells"])
        self.assertEqual(6, receipt["negative_cells"])

    def test_json_loader_rejects_duplicate_keys_and_nonfinite_constants(self):
        with self.assertRaisesRegex(gate.EconomicsError, "duplicate JSON object key"):
            gate._loads_strict('{"a":1,"a":2}')
        with self.assertRaisesRegex(gate.EconomicsError, "non-finite JSON constant"):
            gate._loads_strict('{"a":NaN}')


if __name__ == "__main__":
    unittest.main()
