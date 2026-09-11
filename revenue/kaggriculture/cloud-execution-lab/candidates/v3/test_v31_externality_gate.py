from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v31_externality_gate", HERE / "v31_externality_gate.py"
)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


def cell(seat=0, baseline=(100, 90), candidate=(110, 85), opponent="opp", seed=1):
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "baseline": {"scores": list(baseline)},
        "candidate": {"scores": list(candidate)},
    }


def document(rows=None, *, complete=True, events=None):
    return {
        "cells": list(rows or [cell()]),
        "externality_complete": complete,
        "externality_events": list(events or []),
    }


def event(
    *,
    event_id="e1",
    seat=0,
    opponent="opp",
    seed=1,
    product="WOOL",
    price_delta=0,
    rival_long_units=0,
):
    return {
        "event_id": event_id,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "product": product,
        "source": "official_replay",
        "price_delta": price_delta,
        "rival_long_units": rival_long_units,
    }


class ExternalityGateTests(unittest.TestCase):
    def test_clean_complete_trace_passes(self):
        report = gate.evaluate(document())
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["terminal"]["mean_delta_own"], 10.0)
        self.assertEqual(report["terminal"]["mean_delta_rival"], -5.0)
        self.assertEqual(report["terminal"]["mean_delta_m"], 15.0)

    def test_seat1_uses_official_player_order(self):
        row = cell(seat=1, baseline=(90, 100), candidate=(85, 110))
        report = gate.evaluate(document([row]))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["terminal"]["mean_delta_own"], 10.0)
        self.assertEqual(report["terminal"]["mean_delta_rival"], -5.0)
        self.assertEqual(report["terminal"]["mean_delta_m"], 15.0)

    def test_positive_rival_terminal_delta_blocks_even_when_margin_improves(self):
        row = cell(baseline=(100, 90), candidate=(110, 95))
        report = gate.evaluate(document([row]))
        self.assertEqual(report["terminal"]["mean_delta_m"], 5.0)
        self.assertEqual(report["terminal"]["mean_delta_rival"], 5.0)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertTrue(any("mean rival delta" in reason for reason in report["reasons"]))

    def test_measured_price_uplift_to_rival_long_inventory_blocks(self):
        doc = document(events=[event(price_delta=2, rival_long_units=4)])
        report = gate.evaluate(doc)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["product_externality"]["estimated_rival_price_uplift"], 8.0
        )
        self.assertEqual(
            report["product_externality"]["by_product"]["WOOL"]["positive_price_events"], 1
        )

    def test_price_increase_without_rival_exposure_is_not_harm(self):
        doc = document(events=[event(price_delta=3, rival_long_units=0)])
        report = gate.evaluate(doc)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(
            report["product_externality"]["estimated_rival_price_uplift"], 0.0
        )

    def test_incomplete_or_missing_trace_can_never_pass(self):
        hold = gate.evaluate(document(complete=False))
        self.assertEqual(hold["verdict"], "HOLD")

        raw = {"cells": [cell()]}
        hold = gate.evaluate(raw)
        self.assertEqual(hold["verdict"], "HOLD")

    def test_negative_margin_blocks_independently_of_trace(self):
        row = cell(baseline=(100, 90), candidate=(101, 95))
        report = gate.evaluate(document([row]))
        self.assertEqual(report["terminal"]["mean_delta_m"], -4.0)
        self.assertEqual(report["verdict"], "BLOCK")

    def test_unknown_cell_and_duplicate_event_id_fail_closed(self):
        with self.assertRaisesRegex(gate.ExternalityError, "unknown paired cell"):
            gate.evaluate(
                document(events=[event(seed=999, price_delta=1, rival_long_units=1)])
            )

        dup = event(price_delta=0, rival_long_units=0)
        with self.assertRaisesRegex(gate.ExternalityError, "duplicate externality event_id"):
            gate.evaluate(document(events=[dup, copy.deepcopy(dup)]))

    def test_event_numbers_are_finite_json_numbers_not_bools(self):
        with self.assertRaisesRegex(gate.ExternalityError, "JSON number"):
            gate.evaluate(document(events=[event(price_delta=True)]))
        with self.assertRaisesRegex(gate.ExternalityError, "finite"):
            gate.evaluate(document(events=[event(price_delta=float("inf"))]))
        with self.assertRaisesRegex(gate.ExternalityError, "non-negative"):
            gate.evaluate(document(events=[event(rival_long_units=-1)]))

    def test_complete_flag_is_strict_boolean(self):
        doc = document()
        doc["externality_complete"] = 1
        with self.assertRaisesRegex(gate.ExternalityError, "JSON boolean"):
            gate.evaluate(doc)

    def test_parent_alias_conflicts_remain_fail_closed(self):
        row = cell()
        row["seat"] = 1
        with self.assertRaisesRegex(gate.delta_report.DataError, "conflicting seat aliases"):
            gate.evaluate(document([row]))

    def test_cli_distinguishes_pass_policy_and_data_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            path.write_text(json.dumps(document()), encoding="utf-8")
            self.assertEqual(gate.main([str(path)]), 0)

            blocked = document([cell(baseline=(100, 90), candidate=(110, 95))])
            path.write_text(json.dumps(blocked), encoding="utf-8")
            self.assertEqual(gate.main([str(path)]), 3)

            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(gate.main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
