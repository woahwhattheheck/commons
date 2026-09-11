from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("a6_report_tested", HERE / "report.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def valid_report(regime="selfplay", candidate_entry="baseline.py"):
    expected = m.EXPECTED_REGIMES[regime]
    opponent = expected["opponent"]
    games = []
    for seed in m.EXPECTED_SEEDS:
        for seat in (0, 1):
            games.append({
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "status": "complete",
                "scores": [100 + seat, 90 - seat],
                "failure": None,
                "trace_sha256": ("a" if seat == 0 else "b") * 64,
            })
    return {
        "schema_version": 1,
        "engine_ref": m.ENGINE_REF,
        "agent_rng_seed": m.EXPECTED_RNG_SEED,
        "candidate": {"entry": candidate_entry, "callable": "agent", "sha256": "d" * 64},
        "opponents": {
            opponent: {"entry": expected["opponent_entry"], "callable": "agent", "sha256": "c" * 64}
        },
        "seeds": list(m.EXPECTED_SEEDS),
        "games": games,
        "reproducibility": {"checked": True, "same_trace_and_scores": True},
    }


class StrictReceiptTests(unittest.TestCase):
    def validate(self, report, regime="selfplay", candidate_entry="baseline.py"):
        expected = m.EXPECTED_REGIMES[regime]
        return m.validate_report(report, "test", expected["opponent"], expected["opponent_entry"], candidate_entry)

    def test_exact_eight_cell_panel_is_accepted_for_each_regime(self):
        for regime in m.EXPECTED_REGIMES:
            with self.subTest(regime=regime):
                indexed = self.validate(valid_report(regime), regime)
                self.assertEqual(len(indexed), 8)

    def test_duplicate_cell_is_rejected_not_collapsed(self):
        report = valid_report()
        report["games"].append(copy.deepcopy(report["games"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate paired cell"):
            self.validate(report)

    def test_missing_and_substituted_cells_are_rejected(self):
        report = valid_report()
        report["games"].pop()
        with self.assertRaisesRegex(ValueError, "exact paired cell set mismatch"):
            self.validate(report)
        report = valid_report()
        report["games"][0]["seed"] = 2611151999
        with self.assertRaisesRegex(ValueError, "invalid seed"):
            self.validate(report)
        report = valid_report()
        report["games"][0]["opponent"] = "other"
        with self.assertRaisesRegex(ValueError, "wrong opponent"):
            self.validate(report)

    def test_seed_and_seat_aliases_are_rejected(self):
        for field, value in (
            ("seed", True), ("seed", str(m.EXPECTED_SEEDS[0])), ("seed", float(m.EXPECTED_SEEDS[0])),
            ("candidate_seat", True), ("candidate_seat", "0"), ("candidate_seat", 0.0),
        ):
            with self.subTest(field=field, value=value):
                report = valid_report()
                report["games"][0][field] = value
                with self.assertRaises(ValueError):
                    self.validate(report)

    def test_top_level_seed_panel_and_rng_are_exact(self):
        report = valid_report()
        report["seeds"][0] = str(m.EXPECTED_SEEDS[0])
        with self.assertRaisesRegex(ValueError, "seed panel mismatch"):
            self.validate(report)
        for value in (True, str(m.EXPECTED_RNG_SEED), m.EXPECTED_RNG_SEED + 1):
            with self.subTest(value=value):
                report = valid_report()
                report["agent_rng_seed"] = value
                with self.assertRaisesRegex(ValueError, "agent_rng_seed"):
                    self.validate(report)

    def test_bool_string_nan_and_infinite_scores_are_rejected(self):
        for value in (True, "100", float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                report = valid_report()
                report["games"][0]["scores"][0] = value
                with self.assertRaisesRegex(ValueError, "finite JSON number"):
                    self.validate(report)

    def test_trace_status_failure_and_reproducibility_are_exact(self):
        report = valid_report()
        report["games"][0]["trace_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "trace_sha256"):
            self.validate(report)
        report = valid_report()
        report["games"][0]["status"] = True
        with self.assertRaisesRegex(ValueError, "status"):
            self.validate(report)
        report = valid_report()
        report["games"][0]["failure"] = {"kind": "poison"}
        with self.assertRaisesRegex(ValueError, "failure"):
            self.validate(report)
        report = valid_report()
        report["reproducibility"]["same_trace_and_scores"] = False
        with self.assertRaisesRegex(ValueError, "reproducibility"):
            self.validate(report)

    def test_opponent_and_candidate_fingerprints_are_bound(self):
        report = valid_report()
        report["opponents"] = {"other": next(iter(report["opponents"].values()))}
        with self.assertRaisesRegex(ValueError, "opponent metadata"):
            self.validate(report)
        report = valid_report()
        report["opponents"]["a612"]["entry"] = "other.py"
        with self.assertRaisesRegex(ValueError, "wrong entry"):
            self.validate(report)
        report = valid_report()
        report["candidate"]["entry"] = "other.py"
        with self.assertRaisesRegex(ValueError, "wrong entry"):
            self.validate(report)
        report = valid_report()
        report["candidate"]["sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "sha256"):
            self.validate(report)

    def test_candidate_report_requires_candidate_entry(self):
        report = valid_report(candidate_entry="candidate.py")
        indexed = self.validate(report, candidate_entry="candidate.py")
        self.assertEqual(len(indexed), 8)

    def test_pair_scores_preserves_candidate_relative_seat_math(self):
        report = valid_report()
        self.assertEqual(m.pair_scores(report["games"][0]), (100, 90))
        self.assertEqual(m.pair_scores(report["games"][1]), (89, 101))


if __name__ == "__main__":
    unittest.main()
