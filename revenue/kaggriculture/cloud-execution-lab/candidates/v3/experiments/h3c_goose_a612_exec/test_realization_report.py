from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("h3c_realization_report_tested", HERE / "realization_report.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def valid_report():
    games = []
    for seed in m.EXPECTED_SEEDS:
        for seat in (0, 1):
            games.append({
                "opponent": m.EXPECTED_OPPONENT,
                "seed": seed,
                "candidate_seat": seat,
                "status": "complete",
                "scores": [100 + seat, 90 - seat],
                "trace_sha256": ("a" if seat == 0 else "b") * 64,
                "daily_bank": [],
            })
    return {
        "engine_ref": m.EXPECTED_ENGINE_REF,
        "seeds": list(m.EXPECTED_SEEDS),
        "opponents": [{"name": m.EXPECTED_OPPONENT}],
        "games": games,
    }


class StrictReceiptTests(unittest.TestCase):
    def test_exact_eight_cell_panel_is_accepted(self):
        indexed = m.validate_report(valid_report(), "valid")
        self.assertEqual(frozenset(indexed), m.EXPECTED_CELLS)
        self.assertEqual(len(indexed), 8)

    def test_duplicate_cell_is_rejected_not_silently_collapsed(self):
        report = valid_report()
        report["games"].append(copy.deepcopy(report["games"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate paired cell"):
            m.validate_report(report, "dup")

    def test_missing_cell_is_rejected(self):
        report = valid_report()
        report["games"].pop()
        with self.assertRaisesRegex(ValueError, "exact paired cell set mismatch"):
            m.validate_report(report, "missing")

    def test_extra_or_wrong_seed_is_rejected(self):
        report = valid_report()
        report["games"][0]["seed"] = 2611151999
        with self.assertRaisesRegex(ValueError, "invalid seed"):
            m.validate_report(report, "extra")

    def test_seed_and_seat_bool_string_float_aliases_are_rejected(self):
        poisons = (
            ("seed", True),
            ("seed", str(m.EXPECTED_SEEDS[0])),
            ("seed", float(m.EXPECTED_SEEDS[0])),
            ("candidate_seat", True),
            ("candidate_seat", "0"),
            ("candidate_seat", 0.0),
        )
        for field, value in poisons:
            with self.subTest(field=field, value=value):
                report = valid_report()
                report["games"][0][field] = value
                with self.assertRaises(ValueError):
                    m.validate_report(report, "typed")

    def test_top_level_seed_panel_types_are_strict(self):
        for value in (True, str(m.EXPECTED_SEEDS[0]), float(m.EXPECTED_SEEDS[0])):
            with self.subTest(value=value):
                report = valid_report()
                report["seeds"][0] = value
                with self.assertRaisesRegex(ValueError, "seed panel mismatch"):
                    m.validate_report(report, "top")

    def test_bool_string_nan_and_infinite_scores_are_rejected(self):
        for value in (True, "100", float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                report = valid_report()
                report["games"][0]["scores"][0] = value
                with self.assertRaisesRegex(ValueError, "finite JSON number"):
                    m.validate_report(report, "score")

    def test_score_pair_preserves_candidate_relative_seat_math(self):
        game0 = valid_report()["games"][0]
        self.assertEqual(m.score_pair(game0), (100, 90))
        game1 = valid_report()["games"][1]
        self.assertEqual(m.score_pair(game1), (89, 101))

    def test_trace_and_status_must_be_exact(self):
        report = valid_report()
        report["games"][0]["trace_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "invalid trace_sha256"):
            m.validate_report(report, "trace")
        report = valid_report()
        report["games"][0]["status"] = True
        with self.assertRaises(ValueError):
            m.validate_report(report, "status")


if __name__ == "__main__":
    unittest.main()
