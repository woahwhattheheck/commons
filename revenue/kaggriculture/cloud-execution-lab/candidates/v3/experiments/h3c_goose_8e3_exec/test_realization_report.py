from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("h3c_realization_report_tested", HERE / "realization_report.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load realization_report.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


BASELINE_SHA = "c" * 64
CANDIDATE_SHA = "d" * 64
EVALUATOR_SHA = "5" * 64


def valid_report(candidate_entry="baseline.py", candidate_sha=BASELINE_SHA):
    games = []
    for seed in m.EXPECTED_SEEDS:
        for seat in (0, 1):
            games.append({
                "opponent": m.EXPECTED_OPPONENT,
                "seed": seed,
                "candidate_seat": seat,
                "status": "complete",
                "scores": [100 + seat, 90 - seat],
                "failure": None,
                "trace_sha256": ("a" if seat == 0 else "b") * 64,
                "daily_bank": [],
            })
    baseline_fp = {"entry": "baseline.py", "callable": "agent", "sha256": BASELINE_SHA}
    return {
        "schema_version": 1,
        "engine_ref": m.EXPECTED_ENGINE_REF,
        "engine_sha256": {
            "kaggriculture.py": "1" * 64,
            "kaggriculture.json": "2" * 64,
            "utils.py": "3" * 64,
        },
        "loader_sha256": "4" * 64,
        "evaluator_sha256": EVALUATOR_SHA,
        "candidate": {"entry": candidate_entry, "callable": "agent", "sha256": candidate_sha},
        "seeds": list(m.EXPECTED_SEEDS),
        "agent_rng_seed": m.EXPECTED_AGENT_RNG_SEED,
        "limits": {"action_rpc_seconds": 1.0},
        "opponents": {m.EXPECTED_OPPONENT: baseline_fp},
        "reproducibility": {
            "checked": True,
            "same_trace_and_scores": True,
            "original_trace": "a" * 64,
            "replay_trace": "a" * 64,
        },
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
            ("seed", True), ("seed", str(m.EXPECTED_SEEDS[0])), ("seed", float(m.EXPECTED_SEEDS[0])),
            ("candidate_seat", True), ("candidate_seat", "0"), ("candidate_seat", 0.0),
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

    def test_trace_status_and_failure_must_be_exact(self):
        report = valid_report()
        report["games"][0]["trace_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "invalid trace_sha256"):
            m.validate_report(report, "trace")
        report = valid_report()
        report["games"][0]["status"] = True
        with self.assertRaises(ValueError):
            m.validate_report(report, "status")
        report = valid_report()
        report["games"][0]["failure"] = {"kind": "timeout"}
        with self.assertRaisesRegex(ValueError, "non-null failure"):
            m.validate_report(report, "failure")

    def test_opponent_metadata_must_match_exact_evaluator_shape(self):
        poisons = []
        report = valid_report(); report["opponents"] = [{"name": m.EXPECTED_OPPONENT}]; poisons.append(report)
        report = valid_report(); report["opponents"] = {"other": report["opponents"][m.EXPECTED_OPPONENT]}; poisons.append(report)
        report = valid_report(); report["opponents"][m.EXPECTED_OPPONENT]["entry"] = "other.py"; poisons.append(report)
        report = valid_report(); report["opponents"][m.EXPECTED_OPPONENT]["callable"] = "other"; poisons.append(report)
        report = valid_report(); report["opponents"][m.EXPECTED_OPPONENT]["sha256"] = "not-a-hash"; poisons.append(report)
        for index, poisoned in enumerate(poisons):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    m.validate_report(poisoned, "opponent-meta")

    def test_candidate_fingerprint_entry_and_hash_are_bound(self):
        report = valid_report()
        report["candidate"]["entry"] = "candidate.py"
        with self.assertRaisesRegex(ValueError, "wrong fingerprint entry"):
            m.validate_report(report, "candidate-entry")
        report = valid_report()
        report["candidate"]["sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "invalid fingerprint sha256"):
            m.validate_report(report, "candidate-hash")
        candidate = valid_report("candidate.py", CANDIDATE_SHA)
        m.validate_report(candidate, "candidate", "candidate.py")

    def test_rng_and_source_metadata_are_fail_closed(self):
        for value in (True, "20260911", 20260912):
            with self.subTest(rng=value):
                report = valid_report()
                report["agent_rng_seed"] = value
                with self.assertRaisesRegex(ValueError, "wrong agent_rng_seed"):
                    m.validate_report(report, "rng")
        report = valid_report(); report["evaluator_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "invalid evaluator_sha256"):
            m.validate_report(report, "eval")
        report = valid_report(); report["engine_sha256"].pop("utils.py")
        with self.assertRaisesRegex(ValueError, "engine_sha256 shape mismatch"):
            m.validate_report(report, "engine")

    def test_reproducibility_must_be_checked_and_trace_identical(self):
        report = valid_report(); report["reproducibility"]["same_trace_and_scores"] = False
        with self.assertRaisesRegex(ValueError, "did not pass"):
            m.validate_report(report, "repro")
        report = valid_report(); report["reproducibility"]["replay_trace"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "trace mismatch"):
            m.validate_report(report, "repro-trace")

    def test_pair_metadata_binds_same_baseline_and_evaluator(self):
        control = valid_report()
        candidate = valid_report("candidate.py", CANDIDATE_SHA)
        m.validate_report(control, "control", "baseline.py")
        m.validate_report(candidate, "candidate", "candidate.py")
        m.validate_pair_metadata(control, candidate)

        poisoned = copy.deepcopy(candidate)
        poisoned["opponents"][m.EXPECTED_OPPONENT]["sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "metadata drift: opponents"):
            m.validate_pair_metadata(control, poisoned)

        poisoned = copy.deepcopy(candidate)
        poisoned["evaluator_sha256"] = "6" * 64
        with self.assertRaisesRegex(ValueError, "metadata drift: evaluator_sha256"):
            m.validate_pair_metadata(control, poisoned)

        poisoned = copy.deepcopy(candidate)
        poisoned["candidate"]["sha256"] = BASELINE_SHA
        with self.assertRaisesRegex(ValueError, "unexpectedly equals baseline"):
            m.validate_pair_metadata(control, poisoned)

    def test_actual_byte_fingerprints_bind_checked_out_sources(self):
        control = valid_report()
        candidate = valid_report("candidate.py", CANDIDATE_SHA)
        m.validate_actual_byte_fingerprints(
            control, candidate, BASELINE_SHA, CANDIDATE_SHA, EVALUATOR_SHA
        )

        poison_cases = (
            ("control candidate", lambda c, h: c["candidate"].__setitem__("sha256", "e" * 64)),
            ("control opponent", lambda c, h: c["opponents"][m.EXPECTED_OPPONENT].__setitem__("sha256", "e" * 64)),
            ("candidate opponent", lambda c, h: h["opponents"][m.EXPECTED_OPPONENT].__setitem__("sha256", "e" * 64)),
            ("H3c candidate", lambda c, h: h["candidate"].__setitem__("sha256", "e" * 64)),
            ("control evaluator", lambda c, h: c.__setitem__("evaluator_sha256", "e" * 64)),
            ("candidate evaluator", lambda c, h: h.__setitem__("evaluator_sha256", "e" * 64)),
        )
        for label, mutate in poison_cases:
            with self.subTest(label=label):
                c = valid_report()
                h = valid_report("candidate.py", CANDIDATE_SHA)
                mutate(c, h)
                with self.assertRaisesRegex(ValueError, label):
                    m.validate_actual_byte_fingerprints(
                        c, h, BASELINE_SHA, CANDIDATE_SHA, EVALUATOR_SHA
                    )

    def test_expected_source_hashes_must_be_canonical_sha256(self):
        control = valid_report()
        candidate = valid_report("candidate.py", CANDIDATE_SHA)
        for baseline, treatment, evaluator in (
            ("bad", CANDIDATE_SHA, EVALUATOR_SHA),
            (BASELINE_SHA, "D" * 64, EVALUATOR_SHA),
            (BASELINE_SHA, CANDIDATE_SHA, True),
        ):
            with self.subTest(baseline=baseline, treatment=treatment, evaluator=evaluator):
                with self.assertRaisesRegex(ValueError, "expected source sha256"):
                    m.validate_actual_byte_fingerprints(
                        control, candidate, baseline, treatment, evaluator
                    )


if __name__ == "__main__":
    unittest.main()
