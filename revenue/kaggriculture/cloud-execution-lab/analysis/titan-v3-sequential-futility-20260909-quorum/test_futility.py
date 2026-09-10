# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import futility
import metrics as canonical_metrics
from gate_common import CellKey, Game

H0, H1, H2, H3 = (character * 64 for character in "0123")
G0, G1 = "a" * 40, "b" * 40


def policy(**overrides):
    value = {
        "min_mean_own_delta": 1.0,
        "min_median_own_delta": 1.0,
        "min_mean_margin_delta": 1.0,
        "min_positive_cell_fraction": 0.5,
        "min_positive_pair_fraction": 0.5,
        "max_result_regressions": 0,
        "max_baseline_win_regressions": 0,
        "max_new_losses": 0,
        "max_negative_opponent_strata": 0,
        "max_negative_seat_strata": 0,
        "min_worst_cell_own_delta": -20.0,
        "require_any_change": True,
    }
    value.update(overrides)
    return value


def permissive_policy(**overrides):
    value = policy(
        min_mean_own_delta=-1_000_000.0,
        min_median_own_delta=-1_000_000.0,
        min_mean_margin_delta=-1_000_000.0,
        min_positive_cell_fraction=0.0,
        min_positive_pair_fraction=0.0,
        max_result_regressions=8,
        max_baseline_win_regressions=8,
        max_new_losses=8,
        max_negative_opponent_strata=2,
        max_negative_seat_strata=2,
        min_worst_cell_own_delta=None,
        require_any_change=False,
    )
    value.update(overrides)
    return value


def contract_value(*, policy_value=None, **overrides):
    value = {
        "schema_version": 1,
        "panel_id": "quorum-panel-1",
        "baseline_name": "canonical",
        "candidate_name": "challenger",
        "seeds": [101, 102],
        "opponents": ["arlene", "apex"],
        "seats": [0, 1],
        "expected_cells": 8,
        "provenance": {
            "engine_commit": G0,
            "engine_sha256": H0,
            "runner_commit": G1,
            "runner_sha256": H1,
            "baseline_artifact_sha256": H2,
            "candidate_artifact_sha256": H3,
        },
        "policy": policy_value or policy(),
    }
    value.update(overrides)
    return value


def evidence_value(provenance=None, **overrides):
    value = {
        "schema_version": 1,
        "panel_id": "quorum-panel-1",
        "provenance": deepcopy(provenance or contract_value()["provenance"]),
        "exact_command": "python official_runner.py --immutable-grid quorum-panel-1",
    }
    value.update(overrides)
    return value


def rows(delta=10.0):
    baseline, candidate = [], []
    for opponent in ("arlene", "apex"):
        for seed in (101, 102):
            for seat in (0, 1):
                before = [100.0, 80.0] if seat == 0 else [80.0, 100.0]
                after = list(before)
                after[seat] += delta
                common = {
                    "opponent": opponent,
                    "seed": seed,
                    "candidate_seat": seat,
                    "status": "complete",
                }
                baseline.append({**common, "scores": before})
                candidate.append({**common, "scores": after})
    return baseline, candidate


def identity_rows():
    baseline, _ = rows()
    return baseline, deepcopy(baseline)


def mutate_delta(values, indices, *, own=0.0, rival=0.0):
    result = deepcopy(values)
    for index in indices:
        seat = result[index]["candidate_seat"]
        result[index]["scores"][seat] += own
        result[index]["scores"][1 - seat] += rival
    return result


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, allow_nan=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values) -> None:
    path.write_text(
        "".join(json.dumps(value, allow_nan=True) + "\n" for value in values),
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Harness:
    def __init__(
        self,
        root: Path,
        *,
        contract_obj=None,
        evidence_obj=None,
        baseline=None,
        candidate=None,
    ):
        self.contract = root / "CONTRACT.json"
        self.evidence = root / "PROVENANCE.json"
        self.baseline = root / "canonical.GAMES.jsonl"
        self.candidate = root / "challenger.GAMES.jsonl"
        self.envelope = root / "ENVELOPE.json"
        self.certificate = root / "BOUND-CERTIFICATE.md"
        baseline_rows, candidate_rows = rows()
        selected_contract = contract_obj or contract_value()
        write_json(self.contract, selected_contract)
        write_json(
            self.evidence,
            evidence_obj or evidence_value(selected_contract["provenance"]),
        )
        write_jsonl(self.baseline, baseline if baseline is not None else baseline_rows)
        write_jsonl(self.candidate, candidate if candidate is not None else candidate_rows)

    def add_envelope(self, lower: float, upper: float, **overrides) -> None:
        self.certificate.write_text(
            "Synthetic test-only terminal score bound.\n", encoding="utf-8"
        )
        value = {
            "schema_version": 1,
            "panel_id": "quorum-panel-1",
            "contract_sha256": digest(self.contract),
            "terminal_score_min": lower,
            "terminal_score_max": upper,
            "certificate_sha256": digest(self.certificate),
        }
        value.update(overrides)
        write_json(self.envelope, value)

    def run(self, *, bounded=False):
        return futility.run_futility(
            contract_path=self.contract,
            evidence_path=self.evidence,
            baseline_path=self.baseline,
            candidate_path=self.candidate,
            envelope_path=self.envelope if bounded else None,
            certificate_path=self.certificate if bounded else None,
        )


class PartialValidationTests(unittest.TestCase):
    def test_empty_candidate_is_continue_and_never_promote(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(Path(directory), candidate=[])
            report, code = harness.run()
            self.assertEqual(code, 4)
            self.assertEqual(report["verdict"], "CONTINUE")
            self.assertFalse(report["partial_panel_can_promote"])
            self.assertEqual(report["analysis"]["coverage"]["candidate_cells"], 0)

    def test_partial_positive_panel_never_promotes(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate[:4])
            report, code = harness.run()
            self.assertEqual(code, 4)
            self.assertEqual(report["verdict"], "CONTINUE")
            self.assertEqual(report["mode"], "partial-futility-only")

    def test_noncomplete_row_is_invalid_not_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            candidate[0]["status"] = "timeout"
            candidate[0]["error"] = "deadline"
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate[:1])
            with self.assertRaisesRegex(futility.GateError, "non-complete"):
                harness.run()

    def test_duplicate_cell_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            harness = Harness(
                Path(directory), baseline=baseline, candidate=[candidate[0], candidate[0]]
            )
            with self.assertRaisesRegex(futility.GateError, "duplicate cell"):
                harness.run()

    def test_extra_cell_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            candidate[0]["seed"] = 999
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate[:1])
            with self.assertRaisesRegex(futility.GateError, "extra cell"):
                harness.run()

    def test_candidate_without_baseline_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            harness = Harness(
                Path(directory), baseline=baseline[1:], candidate=candidate[:1]
            )
            with self.assertRaisesRegex(futility.GateError, "missing matching baseline"):
                harness.run()

    def test_duplicate_json_key_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, _ = rows()
            harness = Harness(Path(directory), baseline=baseline, candidate=[])
            harness.candidate.write_text(
                '{"opponent":"arlene","seed":101,"seed":102,'
                '"candidate_seat":0,"status":"complete","scores":[100,80]}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(futility.GateError, "duplicate JSON"):
                harness.run()

    @unittest.skipIf(os.name == "nt", "symlink permissions vary on Windows")
    def test_symlink_input_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = Harness(root, candidate=[])
            target = root / "candidate-target.jsonl"
            target.write_text("", encoding="utf-8")
            harness.candidate.unlink()
            harness.candidate.symlink_to(target)
            with self.assertRaisesRegex(futility.GateError, "symbolic links"):
                harness.run()

    def test_source_replacement_after_snapshot_cannot_change_evaluated_panel(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, full_candidate = rows()
            harness = Harness(Path(directory), baseline=baseline, candidate=[])
            original_loader = futility.load_partial_games
            calls = 0

            def replacing_loader(path, *, label, expected):
                nonlocal calls
                calls += 1
                if calls == 1:
                    # All outer inputs were already snapshotted. Replacing the
                    # source pathname now must not populate the private candidate
                    # snapshot used by this decision.
                    write_jsonl(harness.candidate, full_candidate)
                return original_loader(path, label=label, expected=expected)

            with mock.patch.object(futility, "load_partial_games", replacing_loader):
                report, code = harness.run()
            self.assertEqual(code, 4)
            self.assertEqual(report["analysis"]["coverage"]["candidate_cells"], 0)
            self.assertEqual(report["verdict"], "CONTINUE")


class CombinatorialFutilityTests(unittest.TestCase):
    def test_observed_result_regression_is_irreversible(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            candidate = mutate_delta(candidate, [0], own=-40.0)
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate[:1])
            report, code = harness.run()
            self.assertEqual(code, 3)
            self.assertEqual(report["verdict"], "FUTILE")
            reasons = set(report["analysis"]["futility_reasons"])
            self.assertIn("result_regressions", reasons)
            self.assertIn("baseline_win_regressions", reasons)
            self.assertIn("new_losses", reasons)

    def test_positive_cell_fraction_uses_best_possible_remainder(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            contract_obj = contract_value(
                policy_value=permissive_policy(min_positive_cell_fraction=0.75)
            )
            harness = Harness(
                Path(directory),
                contract_obj=contract_obj,
                baseline=baseline,
                candidate=candidate[:3],
            )
            report, code = harness.run()
            self.assertEqual(code, 3)
            check = next(
                item
                for item in report["analysis"]["checks"]
                if item["name"] == "positive_cell_fraction"
            )
            self.assertEqual(check["optimistic_final"], 5 / 8)
            self.assertTrue(check["futility_proven"])

    def test_positive_pair_fraction_counts_incomplete_pairs_optimistically(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            contract_obj = contract_value(
                policy_value=permissive_policy(min_positive_pair_fraction=0.75)
            )
            harness = Harness(
                Path(directory),
                contract_obj=contract_obj,
                baseline=baseline,
                candidate=candidate[:4],
            )
            report, code = harness.run()
            self.assertEqual(code, 3)
            check = next(
                item
                for item in report["analysis"]["checks"]
                if item["name"] == "positive_pair_fraction"
            )
            self.assertEqual(check["optimistic_final"], 0.5)

    def test_median_can_be_futile_without_numeric_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            contract_obj = contract_value(
                policy_value=permissive_policy(min_median_own_delta=1.0)
            )
            harness = Harness(
                Path(directory),
                contract_obj=contract_obj,
                baseline=baseline,
                candidate=candidate[:5],
            )
            report, code = harness.run()
            self.assertEqual(code, 3)
            check = next(
                item
                for item in report["analysis"]["checks"]
                if item["name"] == "median_own_delta"
            )
            self.assertEqual(check["optimistic_final"], 0.0)

    def test_median_does_not_prune_when_missing_values_can_move_middle(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            contract_obj = contract_value(
                policy_value=permissive_policy(min_median_own_delta=1.0)
            )
            harness = Harness(
                Path(directory),
                contract_obj=contract_obj,
                baseline=baseline,
                candidate=candidate[:4],
            )
            report, code = harness.run()
            self.assertEqual(code, 4)
            check = next(
                item
                for item in report["analysis"]["checks"]
                if item["name"] == "median_own_delta"
            )
            self.assertTrue(check["optimistic_final_unbounded"])

    def test_complete_negative_opponent_stratum_is_irreversible(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            candidate = mutate_delta(candidate, range(4), own=-1.0)
            contract_obj = contract_value(policy_value=permissive_policy(max_negative_opponent_strata=0))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=candidate[:4]
            )
            report, code = harness.run()
            self.assertEqual(code, 3)
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "negative_opponent_strata")
            self.assertEqual(check["forced_keys"], ["arlene"])

    def test_complete_negative_seat_stratum_is_irreversible(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            seat_zero_indices = [0, 2, 4, 6]
            candidate = mutate_delta(candidate, seat_zero_indices, own=-1.0)
            selected = [candidate[index] for index in seat_zero_indices]
            contract_obj = contract_value(policy_value=permissive_policy(max_negative_seat_strata=0))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=selected
            )
            report, code = harness.run()
            self.assertEqual(code, 3)
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "negative_seat_strata")
            self.assertEqual(check["forced_keys"], [0])

    def test_observed_worst_cell_violation_is_irreversible(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            candidate = mutate_delta(candidate, [0], own=-16.0)
            contract_obj = contract_value(policy_value=permissive_policy(min_worst_cell_own_delta=-5.0))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=candidate[:1]
            )
            report, code = harness.run()
            self.assertEqual(code, 3)
            self.assertIn("worst_cell_own_delta", report["analysis"]["futility_reasons"])

    def test_identity_partial_panel_must_continue_when_change_remains_possible(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            contract_obj = contract_value(policy_value=permissive_policy(require_any_change=True))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=candidate[:7]
            )
            report, code = harness.run()
            self.assertEqual(code, 4)
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "any_score_change")
            self.assertEqual(check["optimistic_final"], 1)


class EnvelopeTests(unittest.TestCase):
    def test_envelope_proves_mean_own_delta_futile(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            candidate = mutate_delta(candidate, range(4), own=-5.0)
            contract_obj = contract_value(policy_value=permissive_policy(min_mean_own_delta=0.0))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=candidate[:4]
            )
            harness.add_envelope(0.0, 101.0)
            report, code = harness.run(bounded=True)
            self.assertEqual(code, 3)
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "mean_own_delta")
            self.assertEqual(check["optimistic_final"], -2.0)
            self.assertTrue(check["futility_proven"])

    def test_envelope_proves_mean_margin_delta_futile(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            candidate = mutate_delta(candidate, range(4), rival=5.0)
            contract_obj = contract_value(policy_value=permissive_policy(min_mean_margin_delta=0.0))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=candidate[:4]
            )
            harness.add_envelope(79.0, 101.0)
            report, code = harness.run(bounded=True)
            self.assertEqual(code, 3)
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "mean_margin_delta")
            self.assertEqual(check["optimistic_final"], -1.5)

    def test_envelope_can_prove_unrun_cell_violates_worst_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            # The observed cell reaches the +2 floor, while every still-unrun
            # ordinary cell starts at 100 and can reach at most 101.
            baseline[0]["scores"][0] = 90.0
            candidate[0]["scores"][0] = 92.0
            contract_obj = contract_value(policy_value=permissive_policy(min_worst_cell_own_delta=2.0))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=candidate[:1]
            )
            harness.add_envelope(0.0, 101.0)
            report, code = harness.run(bounded=True)
            self.assertEqual(code, 3)
            self.assertIn("worst_cell_own_delta", report["analysis"]["futility_reasons"])
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "worst_cell_own_delta")
            self.assertEqual(check["observed"], 2.0)
            self.assertEqual(check["optimistic_final"], 1.0)

    def test_envelope_tightens_positive_cell_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, _ = identity_rows()
            contract_obj = contract_value(policy_value=permissive_policy(min_positive_cell_fraction=0.1))
            harness = Harness(
                Path(directory), contract_obj=contract_obj, baseline=baseline, candidate=[]
            )
            harness.add_envelope(0.0, 100.0)
            report, code = harness.run(bounded=True)
            self.assertEqual(code, 3)
            check = next(item for item in report["analysis"]["checks"] if item["name"] == "positive_cell_fraction")
            self.assertEqual(check["optimistic_final"], 0.0)

    def test_score_outside_envelope_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate[:1])
            harness.add_envelope(0.0, 99.0)
            with self.assertRaisesRegex(futility.GateError, "outside certified envelope"):
                harness.run(bounded=True)

    def test_contract_digest_mismatch_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(Path(directory), candidate=[])
            harness.add_envelope(0.0, 101.0, contract_sha256="f" * 64)
            with self.assertRaisesRegex(futility.GateError, "contract_sha256"):
                harness.run(bounded=True)

    def test_certificate_digest_mismatch_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(Path(directory), candidate=[])
            harness.add_envelope(0.0, 101.0, certificate_sha256="f" * 64)
            with self.assertRaisesRegex(futility.GateError, "certificate_sha256"):
                harness.run(bounded=True)

    def test_envelope_requires_certificate(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(Path(directory), candidate=[])
            harness.add_envelope(0.0, 101.0)
            with self.assertRaisesRegex(futility.GateError, "supplied together"):
                futility.run_futility(
                    contract_path=harness.contract,
                    evidence_path=harness.evidence,
                    baseline_path=harness.baseline,
                    candidate_path=harness.candidate,
                    envelope_path=harness.envelope,
                )


class SoundnessPropertyTests(unittest.TestCase):
    def test_every_bounded_futile_verdict_has_no_passing_completion(self):
        rng = random.Random(20260909)
        score_domain = (0.0, 1.0, 2.0, 3.0)
        keys = [CellKey("arlene", 101, 0), CellKey("arlene", 101, 1)]
        baseline = {
            keys[0]: Game(keys[0], (2.0, 1.0), 1),
            keys[1]: Game(keys[1], (1.0, 2.0), 2),
        }
        envelope = {
            "terminal_score_min": 0.0,
            "terminal_score_max": 3.0,
            "terminal_score_span": 3.0,
        }

        for trial in range(250):
            selected_policy = policy(
                min_mean_own_delta=rng.choice((-2.0, -1.0, 0.0, 0.5, 1.0, 2.0, 3.0)),
                min_median_own_delta=rng.choice((-2.0, -1.0, 0.0, 0.5, 1.0, 2.0, 3.0)),
                min_mean_margin_delta=rng.choice((-4.0, -2.0, 0.0, 1.0, 2.0, 4.0)),
                min_positive_cell_fraction=rng.choice((0.0, 0.5, 1.0)),
                min_positive_pair_fraction=rng.choice((0.0, 1.0)),
                max_result_regressions=rng.randrange(3),
                max_baseline_win_regressions=rng.randrange(3),
                max_new_losses=rng.randrange(3),
                max_negative_opponent_strata=rng.randrange(2),
                max_negative_seat_strata=rng.randrange(3),
                min_worst_cell_own_delta=rng.choice((None, -2.0, -1.0, 0.0, 1.0, 2.0)),
                require_any_change=bool(rng.randrange(2)),
            )
            raw_contract = {
                "schema_version": 1,
                "panel_id": f"property-{trial}",
                "baseline_name": "canonical",
                "candidate_name": "challenger",
                "seeds": [101],
                "opponents": ["arlene"],
                "seats": [0, 1],
                "expected_cells": 2,
                "provenance": contract_value()["provenance"],
                "policy": selected_policy,
            }
            validated = futility.validate_contract(raw_contract)

            observed_count = rng.randrange(3)
            observed_keys = keys[:observed_count]
            partial = {}
            for line, key in enumerate(observed_keys, 1):
                scores = (rng.choice(score_domain), rng.choice(score_domain))
                partial[key] = Game(key, scores, line)

            analysis = futility.analyze_futility(
                contract=validated,
                baseline=baseline,
                candidate=partial,
                envelope=envelope,
            )
            if not analysis["futility_reasons"]:
                continue

            missing = [key for key in keys if key not in partial]
            completion_vectors = itertools.product(
                itertools.product(score_domain, repeat=2), repeat=len(missing)
            )
            for completion in completion_vectors:
                full = dict(partial)
                for line, (key, scores) in enumerate(zip(missing, completion), 10):
                    full[key] = Game(key, tuple(scores), line)
                metrics = canonical_metrics.analyze(baseline, full)
                passes = all(
                    check["pass"]
                    for check in canonical_metrics.evaluate_policy(
                        metrics, validated["policy"]
                    )
                )
                self.assertFalse(
                    passes,
                    msg=(
                        f"false FUTILE on trial {trial}; reasons="
                        f"{analysis['futility_reasons']}; completion={completion}; "
                        f"policy={selected_policy}; partial={partial}"
                    ),
                )


class DelegationAndDeterminismTests(unittest.TestCase):
    def test_complete_positive_panel_delegates_and_promotes(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(Path(directory))
            report, code = harness.run()
            self.assertEqual(code, 0)
            self.assertEqual(report["verdict"], "PROMOTE")
            self.assertEqual(report["mode"], "complete-delegation")
            self.assertEqual(report["delegated_gate"]["verdict"], "PROMOTE")

    def test_complete_identity_panel_delegates_and_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = identity_rows()
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate)
            report, code = harness.run()
            self.assertEqual(code, 3)
            self.assertEqual(report["verdict"], "REJECT")
            self.assertEqual(report["mode"], "complete-delegation")

    def test_partial_reports_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate = rows()
            harness = Harness(Path(directory), baseline=baseline, candidate=candidate[:3])
            first, first_code = harness.run()
            second, second_code = harness.run()
            self.assertEqual(first_code, second_code)
            self.assertEqual(first, second)

    def test_cli_writes_invalid_report_and_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = Harness(root, candidate=[])
            harness.evidence.write_text("{bad json\n", encoding="utf-8")
            output = root / "REPORT.json"
            code = futility.main(
                [
                    "--contract", str(harness.contract),
                    "--evidence", str(harness.evidence),
                    "--baseline", str(harness.baseline),
                    "--candidate", str(harness.candidate),
                    "--report", str(output),
                    "--quiet",
                ]
            )
            self.assertEqual(code, 2)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["verdict"], "INVALID")

    def test_cli_continue_exit_four(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = Harness(root, candidate=[])
            output = root / "REPORT.json"
            code = futility.main(
                [
                    "--contract", str(harness.contract),
                    "--evidence", str(harness.evidence),
                    "--baseline", str(harness.baseline),
                    "--candidate", str(harness.candidate),
                    "--report", str(output),
                    "--quiet",
                ]
            )
            self.assertEqual(code, 4)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["verdict"], "CONTINUE")


if __name__ == "__main__":
    unittest.main()
