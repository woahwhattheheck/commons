# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

import paired_cell_tail_admission as target


EVALUATOR = "e" * 64


def h(label: str) -> str:
    import hashlib

    return hashlib.sha256(label.encode()).hexdigest()


def game(
    *,
    opponent: str,
    seed: int,
    seat: int,
    own: float,
    rival: float,
    action: str,
    trace: str,
) -> dict:
    scores = [own, rival] if seat == 0 else [rival, own]
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "episode_steps": 720,
        "steps": 719,
        "candidate_action_count": 719,
        "candidate_action_sha256": h(action),
        "trace_sha256": h(trace),
        "scores": scores,
        "bank_snapshot": list(scores),
    }


def report(
    games: list[dict],
    *,
    evaluator: str = EVALUATOR,
    include_grid_descriptors: bool = False,
) -> dict:
    value = {
        "evaluator_sha256": evaluator,
        "progress": {
            "state": "complete",
            "planned_games": len(games),
            "recorded_games": len(games),
        },
        "engine": {"ref": "engine-pin"},
        "games": games,
    }
    if include_grid_descriptors:
        value["seeds"] = sorted({row["seed"] for row in games})
        value["opponents"] = {
            name: f"{name}.py::agent"
            for name in sorted({row["opponent"] for row in games})
        }
    return value


def paired(
    rows: list[tuple[int, int, float, float, float, float]],
    *,
    opponent: str = "arlene",
    changed: bool = True,
    include_grid_descriptors: bool = False,
) -> tuple[dict, dict]:
    left: list[dict] = []
    right: list[dict] = []
    for seed, seat, control_own, control_rival, candidate_own, candidate_rival in rows:
        left.append(
            game(
                opponent=opponent,
                seed=seed,
                seat=seat,
                own=control_own,
                rival=control_rival,
                action=f"control-action-{seed}-{seat}",
                trace=f"control-trace-{seed}-{seat}",
            )
        )
        right.append(
            game(
                opponent=opponent,
                seed=seed,
                seat=seat,
                own=candidate_own,
                rival=candidate_rival,
                action=(
                    f"candidate-action-{seed}-{seat}"
                    if changed
                    else f"control-action-{seed}-{seat}"
                ),
                trace=(
                    f"candidate-trace-{seed}-{seat}"
                    if changed
                    else f"control-trace-{seed}-{seat}"
                ),
            )
        )
    return (
        report(left, include_grid_descriptors=include_grid_descriptors),
        report(right, include_grid_descriptors=include_grid_descriptors),
    )


class PairedCellTailAdmissionTests(unittest.TestCase):
    def test_safe_frontier_admits(self) -> None:
        control, candidate = paired(
            [(1, 0, 100, 90, 110, 85), (1, 1, 100, 90, 102, 89)]
        )
        result = target.assess(control, candidate)
        self.assertEqual(result["verdict"], "ADMIT")
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual(result["changed_cells"]["min_own_cash_delta"], 2)
        self.assertFalse(result["promotion_authorized"])

    def test_descriptor_grid_binds_complete_cross_product(self) -> None:
        control, candidate = paired(
            [(1, 0, 100, 90, 110, 85), (1, 1, 100, 90, 102, 89)],
            include_grid_descriptors=True,
        )
        result = target.assess(control, candidate)
        self.assertTrue(result["descriptor_grid"]["bound"])
        self.assertEqual(result["descriptor_grid"]["expected_cells"], 2)
        self.assertEqual(result["descriptor_grid"]["candidate_seats"], [0, 1])

    def test_descriptor_grid_incomplete_fails_closed(self) -> None:
        control, candidate = paired(
            [(1, 0, 100, 90, 110, 85)],
            include_grid_descriptors=True,
        )
        with self.assertRaisesRegex(target.EvidenceError, "descriptor opponent×seed×seat grid"):
            target.assess(control, candidate)

    def test_margin_only_false_positive_rejects(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 95, 80)])
        result = target.assess(control, candidate)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["overall"]["mean_margin_delta"], 5)
        self.assertEqual(result["overall"]["mean_own_cash_delta"], -5)
        self.assertFalse(result["gates"]["nonnegative_own_every_changed_cell"])

    def test_aggregate_masked_catastrophic_tail_rejects(self) -> None:
        rows = [(seed, 0, 100, 90, 110, 90) for seed in range(1, 8)]
        # Still a win; rival falls harder. Legacy aggregate gates see mean own
        # +2.5, median +10, 7 positive vs 1 negative, positive mean margin,
        # and no outcome regression, yet one TITAN cell loses 50 cash.
        rows.append((8, 0, 100, 90, 50, 0))
        control, candidate = paired(rows)
        result = target.assess(control, candidate)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["overall"]["mean_own_cash_delta"], 2.5)
        self.assertEqual(result["overall"]["median_own_cash_delta"], 10)
        self.assertEqual(result["overall"]["positive_own_cells"], 7)
        self.assertEqual(result["overall"]["negative_own_cells"], 1)
        self.assertEqual(result["overall"]["new_losses"], 0)
        self.assertEqual(result["overall"]["lost_wins"], 0)
        self.assertEqual(len(result["negative_own_changed_cells"]), 1)
        self.assertEqual(result["negative_own_changed_cells"][0]["seed"], 8)

    def test_new_loss_rejects_even_with_own_gain(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 120)])
        result = target.assess(control, candidate)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(result["gates"]["zero_new_losses"])
        self.assertFalse(result["gates"]["zero_lost_wins"])

    def test_margin_tail_rejects_even_with_own_gain(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 105)])
        result = target.assess(control, candidate)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["changed_cells"]["min_own_cash_delta"], 10)
        self.assertEqual(result["changed_cells"]["min_margin_delta"], -5)

    def test_inactive_exact_parity(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 100, 90)], changed=False)
        result = target.assess(control, candidate)
        self.assertEqual(result["verdict"], "INACTIVE")
        self.assertFalse(result["gates"]["candidate_action_activation"])

    def test_score_change_without_action_change_is_detached(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 101, 90)], changed=False)
        with self.assertRaisesRegex(target.EvidenceError, "score changed without"):
            target.assess(control, candidate)

    def test_trace_change_without_action_change_is_detached(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 100, 90)], changed=False)
        candidate["games"][0]["trace_sha256"] = h("detached-trace")
        with self.assertRaisesRegex(target.EvidenceError, "trace changed without"):
            target.assess(control, candidate)

    def test_grid_mismatch_fails_closed(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 85), (2, 0, 100, 90, 110, 85)])
        candidate["games"].pop()
        candidate["progress"]["planned_games"] = 1
        candidate["progress"]["recorded_games"] = 1
        with self.assertRaisesRegex(target.EvidenceError, "paired grid mismatch"):
            target.assess(control, candidate)

    def test_duplicate_cell_fails_closed(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 85)])
        control["games"].append(copy.deepcopy(control["games"][0]))
        control["progress"]["planned_games"] = 2
        control["progress"]["recorded_games"] = 2
        with self.assertRaisesRegex(target.EvidenceError, "duplicate paired cell"):
            target.assess(control, candidate)

    def test_evaluator_mismatch_fails_closed(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 85)])
        candidate["evaluator_sha256"] = "f" * 64
        with self.assertRaisesRegex(target.EvidenceError, "evaluator SHA-256 mismatch"):
            target.assess(control, candidate)

    def test_optional_panel_descriptor_mismatch_fails_closed(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 85)])
        candidate["engine"] = {"ref": "other-engine"}
        with self.assertRaisesRegex(target.EvidenceError, "engine mismatch"):
            target.assess(control, candidate)

    def test_incomplete_lifecycle_fails_closed(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 85)])
        candidate["games"][0]["steps"] = 718
        candidate["games"][0]["candidate_action_count"] = 718
        with self.assertRaisesRegex(target.EvidenceError, "lacks full"):
            target.assess(control, candidate)

    def test_seat_one_orientation(self) -> None:
        control, candidate = paired([(1, 1, 100, 90, 103, 89)])
        result = target.assess(control, candidate)
        row = result["cells"][0]
        self.assertEqual(row["control_own_cash"], 100)
        self.assertEqual(row["candidate_own_cash"], 103)
        self.assertEqual(row["own_cash_delta"], 3)
        self.assertEqual(result["verdict"], "ADMIT")

    def test_receipt_is_deterministic_and_self_excluding(self) -> None:
        control, candidate = paired([(1, 0, 100, 90, 110, 85)])
        first = target.assess(control, candidate)
        second = target.assess(copy.deepcopy(control), copy.deepcopy(candidate))
        self.assertEqual(first, second)
        unsigned = dict(first)
        seal = unsigned.pop("receipt_sha256")
        self.assertEqual(seal, target.canonical_sha256(unsigned))

    def test_markdown_exposes_regression_cell(self) -> None:
        control, candidate = paired([(7, 0, 100, 90, 95, 80)])
        text = target.render_markdown(target.assess(control, candidate))
        self.assertIn("REJECT", text)
        self.assertIn("| `arlene` | 7 | 0 | -5.000 | 5.000 |", text)
        self.assertIn("does not authorize promotion", text)

    def test_strict_load_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(target.EvidenceError, "duplicate key"):
                target.strict_load(path, "bad")


if __name__ == "__main__":
    unittest.main()
