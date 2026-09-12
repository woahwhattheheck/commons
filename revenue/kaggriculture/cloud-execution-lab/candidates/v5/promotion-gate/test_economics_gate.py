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
ENGINE = "engine:official-pinned"
OPPONENT_PACK = "frontier:top30-union"
OPPONENTS = ("opponent:alpha", "opponent:beta")
CONTROL_ARCHIVE = "a" * 64
CANDIDATE_ARCHIVE = "b" * 64


def report(*, delta: int = 10, opponents=OPPONENTS, seeds=range(100, 104)):
    cells = []
    for opponent_id in opponents:
        for seed in seeds:
            for seat in (0, 1):
                control_own = 1000 + seed + seat
                control_rival = 900 + seed
                cells.append(
                    {
                        "opponent_id": opponent_id,
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
        "engine_id": ENGINE,
        "opponent_pack_id": OPPONENT_PACK,
        "control_archive_sha256": CONTROL_ARCHIVE,
        "candidate_archive_sha256": CANDIDATE_ARCHIVE,
        "cells": cells,
    }


def validate(value=None, **overrides):
    expected = dict(
        candidate_id=CANDIDATE,
        control_id=CONTROL,
        engine_id=ENGINE,
        opponent_pack_id=OPPONENT_PACK,
        control_archive_sha256=CONTROL_ARCHIVE,
        candidate_archive_sha256=CANDIDATE_ARCHIVE,
    )
    expected.update(overrides)
    return gate.validate_report(report() if value is None else value, **expected)


class EconomicsGateTests(unittest.TestCase):
    def test_positive_panel_passes_and_recomputes_raw_margins(self):
        receipt = validate(report(delta=10))
        self.assertEqual("PASS", receipt["classification"])
        self.assertTrue(receipt["promotion_ready"])
        self.assertEqual(16, receipt["cell_count"])
        self.assertEqual(4, receipt["seed_count"])
        self.assertEqual(2, receipt["opponent_count"])
        self.assertEqual(list(OPPONENTS), receipt["opponent_ids"])
        self.assertEqual(160, receipt["sum_margin_delta"])
        self.assertEqual(10.0, receipt["mean_margin_delta"])
        self.assertEqual(16, receipt["positive_cells"])
        self.assertEqual(0, receipt["negative_cells"])
        self.assertEqual(ENGINE, receipt["engine_id"])
        self.assertEqual(OPPONENT_PACK, receipt["opponent_pack_id"])
        self.assertEqual(CONTROL_ARCHIVE, receipt["control_archive_sha256"])
        self.assertEqual(CANDIDATE_ARCHIVE, receipt["candidate_archive_sha256"])
        self.assertRegex(receipt["panel_sha256"], r"^[0-9a-f]{64}$")

    def test_exact_zero_mean_is_no_regression_pass(self):
        receipt = validate(report(delta=0))
        self.assertEqual(0, receipt["sum_margin_delta"])
        self.assertEqual(16, receipt["tied_cells"])

    def test_negative_mean_is_rejected(self):
        with self.assertRaisesRegex(gate.EconomicsError, "mean margin regresses"):
            validate(report(delta=-1))

    def test_reported_summary_cannot_be_smuggled(self):
        value = report()
        value["mean_margin_delta"] = 999999
        with self.assertRaisesRegex(gate.EconomicsError, "keys mismatch"):
            validate(value)

    def test_cross_build_candidate_is_rejected(self):
        with self.assertRaisesRegex(gate.EconomicsError, "does not match promotion candidate"):
            validate(candidate_id="v5c:" + "3" * 64)

    def test_cross_build_control_is_rejected(self):
        with self.assertRaisesRegex(gate.EconomicsError, "does not match promotion control"):
            validate(control_id="v5c:" + "4" * 64)

    def test_same_control_and_candidate_is_rejected(self):
        value = report()
        value["candidate_id"] = value["control_id"]
        with self.assertRaisesRegex(gate.EconomicsError, "must differ"):
            gate.validate_report(value)

    def test_execution_authority_must_match(self):
        cases = [
            ("engine", {"engine_id": "engine:other"}, "engine_id does not match"),
            (
                "opponent-pack",
                {"opponent_pack_id": "frontier:other"},
                "opponent_pack_id does not match",
            ),
            (
                "control-archive",
                {"control_archive_sha256": "c" * 64},
                "control archive does not match",
            ),
            (
                "candidate-archive",
                {"candidate_archive_sha256": "d" * 64},
                "candidate archive does not match",
            ),
        ]
        for label, expected, message in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(gate.EconomicsError, message):
                    validate(**expected)

    def test_none_opponent_pack_can_be_bound_exactly(self):
        value = report()
        value["opponent_pack_id"] = None
        receipt = gate.validate_report(
            value,
            candidate_id=CANDIDATE,
            control_id=CONTROL,
            engine_id=ENGINE,
            opponent_pack_id=None,
            control_archive_sha256=CONTROL_ARCHIVE,
            candidate_archive_sha256=CANDIDATE_ARCHIVE,
        )
        self.assertIsNone(receipt["opponent_pack_id"])

    def test_control_and_candidate_archives_must_differ(self):
        value = report()
        value["candidate_archive_sha256"] = value["control_archive_sha256"]
        with self.assertRaisesRegex(gate.EconomicsError, "archive hashes must differ"):
            gate.validate_report(value)

    def test_single_opponent_panel_is_rejected_even_with_enough_cells(self):
        value = report(opponents=("opponent:alpha",), seeds=range(100, 108))
        with self.assertRaisesRegex(gate.EconomicsError, "at least 2 distinct opponents"):
            validate(value)

    def test_opponents_must_cover_identical_seed_sets(self):
        value = report()
        for cell in value["cells"]:
            if cell["opponent_id"] == "opponent:beta" and cell["seed"] == 103:
                cell["seed"] = 104
        value["cells"].sort(key=lambda cell: (cell["opponent_id"], cell["seed"], cell["seat"]))
        with self.assertRaisesRegex(gate.EconomicsError, "identical seed sets"):
            validate(value)

    def test_every_opponent_seed_requires_both_seats(self):
        value = report(seeds=range(100, 105))
        value["cells"] = [
            cell for cell in value["cells"]
            if not (
                cell["opponent_id"] == "opponent:beta"
                and cell["seed"] == 104
                and cell["seat"] == 1
            )
        ]
        with self.assertRaisesRegex(gate.EconomicsError, "exactly both seats"):
            validate(value)

    def test_duplicate_opponent_seed_seat_is_rejected(self):
        value = report()
        value["cells"][1] = copy.deepcopy(value["cells"][0])
        with self.assertRaisesRegex(gate.EconomicsError, "must be unique"):
            validate(value)

    def test_too_small_panel_is_rejected(self):
        value = report()
        value["cells"] = value["cells"][:14]
        with self.assertRaisesRegex(gate.EconomicsError, "at least 16 cells"):
            validate(value)

    def test_noncanonical_cell_order_is_rejected(self):
        value = report()
        value["cells"][0], value["cells"][1] = value["cells"][1], value["cells"][0]
        with self.assertRaisesRegex(gate.EconomicsError, "canonically sorted"):
            validate(value)

    def test_empty_opponent_id_is_rejected(self):
        value = report()
        value["cells"][0]["opponent_id"] = ""
        with self.assertRaisesRegex(gate.EconomicsError, "non-empty string"):
            validate(value)

    def test_bool_and_noninteger_scores_are_rejected(self):
        for bad in (True, 10.0, "10"):
            with self.subTest(bad=bad):
                value = report()
                value["cells"][0]["candidate_own"] = bad
                with self.assertRaisesRegex(gate.EconomicsError, "plain int"):
                    validate(value)

    def test_oversized_scores_and_seeds_are_rejected(self):
        for field in ("candidate_own", "seed"):
            with self.subTest(field=field):
                value = report()
                value["cells"][0][field] = 1 << 100
                with self.assertRaisesRegex(gate.EconomicsError, "plain int"):
                    validate(value)

    def test_cell_shape_is_closed(self):
        value = report()
        value["cells"][0]["claimed_delta"] = 1000000
        with self.assertRaisesRegex(gate.EconomicsError, "exact raw score keys"):
            validate(value)

    def test_mixed_sign_panel_uses_recomputed_aggregate(self):
        value = report(delta=0)
        adjustments = [100] + [-10] * 10 + [0] * 5
        for cell, adjustment in zip(value["cells"], adjustments):
            cell["candidate_own"] += adjustment
        receipt = validate(value)
        self.assertEqual(0, receipt["sum_margin_delta"])
        self.assertEqual(1, receipt["positive_cells"])
        self.assertEqual(10, receipt["negative_cells"])
        self.assertEqual(5, receipt["tied_cells"])

    def test_json_loader_rejects_duplicate_keys_and_nonfinite_constants(self):
        with self.assertRaisesRegex(gate.EconomicsError, "duplicate JSON object key"):
            gate._loads_strict('{"a":1,"a":2}')
        with self.assertRaisesRegex(gate.EconomicsError, "non-finite JSON constant"):
            gate._loads_strict('{"a":NaN}')


if __name__ == "__main__":
    unittest.main()
