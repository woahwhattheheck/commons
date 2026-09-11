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


def flat_cell(
    seat=0, baseline=(100, 90), candidate=(110, 85), opponent="opp", seed=1
):
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "baseline_scores": list(baseline),
        "candidate_scores": list(candidate),
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


def _row_key(row):
    return (str(row["opponent"]).strip(), str(row["seed"]).strip(), int(row["candidate_seat"]))


def _event_key(raw):
    return (str(raw["opponent"]).strip(), str(raw["seed"]).strip(), int(raw["candidate_seat"]))


def document(rows=None, *, complete=True, events=None):
    rows = list(rows or [cell()])
    events = list(events or [])
    doc = {
        "cells": rows,
        "externality_complete": complete,
        "externality_events": events,
    }
    if complete:
        counts = {_row_key(row): 0 for row in rows}
        for raw in events:
            key = _event_key(raw)
            if key in counts:
                counts[key] += 1
        doc["externality_coverage"] = [
            {
                "opponent": key[0],
                "seed": key[1],
                "candidate_seat": key[2],
                "source": "official_replay",
                "events_observed": counts[key],
            }
            for key in counts
        ]
    return doc


class ExternalityGateTests(unittest.TestCase):
    def test_clean_complete_trace_passes(self):
        report = gate.evaluate(document())
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["schema"], "titan-v31-d3-externality-gate-v2")
        self.assertEqual(report["trace_coverage"]["receipts"], 1)
        self.assertIs(report["trace_coverage"]["all_cells_covered"], True)
        self.assertEqual(report["terminal"]["mean_delta_own"], 10.0)
        self.assertEqual(report["terminal"]["mean_delta_rival"], -5.0)
        self.assertEqual(report["terminal"]["mean_delta_m"], 15.0)

    def test_seat1_nested_scores_use_official_player_order(self):
        row = cell(seat=1, baseline=(90, 100), candidate=(85, 110))
        report = gate.evaluate(document([row]))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["terminal"]["mean_delta_own"], 10.0)
        self.assertEqual(report["terminal"]["mean_delta_rival"], -5.0)
        self.assertEqual(report["terminal"]["mean_delta_m"], 15.0)

    def test_reviewer_seat1_flat_vector_false_green_is_killed(self):
        row = flat_cell(seat=1, baseline=(90, 100), candidate=(110, 100))
        report = gate.evaluate(document([row]))
        self.assertEqual(report["terminal"]["mean_delta_own"], 0.0)
        self.assertEqual(report["terminal"]["mean_delta_rival"], 20.0)
        self.assertEqual(report["terminal"]["mean_delta_m"], -20.0)
        self.assertEqual(report["verdict"], "BLOCK")

    def test_flat_and_nested_score_forms_must_agree_after_seat_normalization(self):
        row = cell(seat=1, baseline=(90, 100), candidate=(85, 110))
        row["baseline_scores"] = [90, 100]
        row["candidate_scores"] = [85, 110]
        report = gate.evaluate(document([row]))
        self.assertEqual(report["verdict"], "PASS")

        poisoned = copy.deepcopy(row)
        poisoned["candidate_scores"] = [999, 110]
        with self.assertRaisesRegex(gate.delta_report.DataError, "conflicting candidate score forms"):
            gate.evaluate(document([poisoned]))

    def test_mixed_arm_pair_and_row_container_representations_fail_closed(self):
        doc = document()
        doc["baseline"] = [
            {"opponent": "opp", "seed": 1, "candidate_seat": 0, "scores": [100, 90]}
        ]
        doc["candidate"] = [
            {"opponent": "opp", "seed": 1, "candidate_seat": 0, "scores": [999, 0]}
        ]
        with self.assertRaisesRegex(
            gate.ExternalityError, "mixed arm-pair and row-container representations"
        ):
            gate.evaluate(doc)

        one_arm = document()
        one_arm["baseline"] = []
        with self.assertRaisesRegex(gate.ExternalityError, "requires both baseline and candidate"):
            gate.evaluate(one_arm)

    def test_multiple_row_container_aliases_reject_bool_int_seat_confusion(self):
        doc = document()
        doc["results"] = copy.deepcopy(doc["cells"])
        doc["results"][0]["candidate_seat"] = False
        # This is the exact trap: JSON-distinct 0/false compare equal in Python.
        self.assertEqual(doc["cells"], doc["results"])
        with self.assertRaisesRegex(
            gate.ExternalityError, "multiple row-container representations are ambiguous"
        ):
            gate.evaluate(doc)

    def test_multiple_row_container_aliases_reject_bool_int_score_confusion(self):
        doc = document([cell(baseline=(1, 90), candidate=(2, 85))])
        doc["games"] = copy.deepcopy(doc["cells"])
        doc["games"][0]["baseline"]["scores"][0] = True
        # Same Python-equality alias class, now in a score scalar rather than seat identity.
        self.assertEqual(doc["cells"], doc["games"])
        with self.assertRaisesRegex(
            gate.ExternalityError, "multiple row-container representations are ambiguous"
        ):
            gate.evaluate(doc)

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
        self.assertIs(hold["trace_coverage"]["all_cells_covered"], False)

        raw = {"cells": [cell()]}
        hold = gate.evaluate(raw)
        self.assertEqual(hold["verdict"], "HOLD")

    def test_complete_trace_requires_exact_per_cell_coverage_receipts(self):
        missing = document()
        del missing["externality_coverage"]
        with self.assertRaisesRegex(gate.ExternalityError, "requires externality_coverage"):
            gate.evaluate(missing)

        mismatch = document(events=[event()])
        mismatch["externality_coverage"][0]["events_observed"] = 0
        with self.assertRaisesRegex(gate.ExternalityError, "event count mismatch"):
            gate.evaluate(mismatch)

        rows = [cell(seed=1), cell(seed=2)]
        incomplete = document(rows)
        incomplete["externality_coverage"] = incomplete["externality_coverage"][:1]
        with self.assertRaisesRegex(gate.ExternalityError, "exactly one receipt per paired cell"):
            gate.evaluate(incomplete)

    def test_coverage_receipts_reject_duplicates_unknown_cells_and_type_confusion(self):
        dup = document()
        dup["externality_coverage"].append(copy.deepcopy(dup["externality_coverage"][0]))
        with self.assertRaisesRegex(gate.ExternalityError, "duplicate externality coverage cell"):
            gate.evaluate(dup)

        unknown = document()
        unknown["externality_coverage"][0]["seed"] = 999
        with self.assertRaisesRegex(gate.ExternalityError, "unknown paired cell"):
            gate.evaluate(unknown)

        confused = document()
        confused["externality_coverage"][0]["events_observed"] = False
        with self.assertRaisesRegex(gate.ExternalityError, "non-negative JSON integer"):
            gate.evaluate(confused)

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
