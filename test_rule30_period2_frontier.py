from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "research" / "rule30_nonperiodicity" / "period2_fiber.py"
RECEIPT_PATH = ROOT / "research" / "rule30_nonperiodicity" / "bounded_receipt.json"
spec = importlib.util.spec_from_file_location("period2_fiber", MODULE_PATH)
assert spec and spec.loader
period2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = period2
spec.loader.exec_module(period2)


def reference_step(row: dict[int, int]) -> dict[int, int]:
    lo = min(row, default=0) - 1
    hi = max(row, default=0) + 1
    return {
        i: period2.rule30(row.get(i - 1, 0), row.get(i, 0), row.get(i + 1, 0))
        for i in range(lo, hi + 1)
    }


def reference_trace(row: dict[int, int], steps: int) -> list[int]:
    out = []
    current = dict(row)
    for _ in range(steps + 1):
        out.append(current.get(0, 0))
        current = reference_step(current)
    return out


class Rule30PeriodTwoFrontierTests(unittest.TestCase):
    def test_local_rule_truth_table(self) -> None:
        expected = {
            (1, 1, 1): 0, (1, 1, 0): 0, (1, 0, 1): 0, (1, 0, 0): 1,
            (0, 1, 1): 1, (0, 1, 0): 1, (0, 0, 1): 1, (0, 0, 0): 0,
        }
        self.assertEqual({k: period2.rule30(*k) for k in expected}, expected)

    def test_bitset_engine_matches_independent_dict_oracle(self) -> None:
        radius = 4
        limit = 14
        for phase in (0, 1):
            for right_word in range(1 << radius):
                packed, origin, _ = period2.complete_candidate(radius, phase, right_word, horizon_limit=limit)
                row = {}
                for pos in range(-radius, radius + 1):
                    row[pos] = (packed >> (origin + pos)) & 1
                expected = reference_trace(row, limit)
                current = packed
                actual = []
                for _ in range(limit + 1):
                    actual.append((current >> origin) & 1)
                    current = period2._step(current)
                self.assertEqual(actual, expected)

    def test_first_forced_left_depths(self) -> None:
        radius = 2
        for r1 in (0, 1):
            for r2 in (0, 1):
                right_word = r1 | (r2 << 1)
                _, _, left0 = period2.complete_candidate(radius, 0, right_word, horizon_limit=12)
                l1_0 = left0 & 1
                l2_0 = (left0 >> 1) & 1
                self.assertEqual(l1_0, 1 - r1)
                self.assertEqual(l2_0, r1)

                _, _, left1 = period2.complete_candidate(radius, 1, right_word, horizon_limit=12)
                l1_1 = left1 & 1
                l2_1 = (left1 >> 1) & 1
                self.assertEqual(l1_1, 1)
                self.assertEqual(l2_1, int(not (r1 or r2)))

    def test_completion_matches_alternating_prefix(self) -> None:
        for radius in range(1, 7):
            for phase in (0, 1):
                for right_word in range(1 << radius):
                    row, origin, _ = period2.complete_candidate(radius, phase, right_word, horizon_limit=20)
                    for time in range(radius + 1):
                        self.assertEqual(
                            period2._center_after(row, origin, time),
                            period2.alternating_bit(phase, time),
                        )

    def test_exact_small_radius_frontier(self) -> None:
        expected = {
            1: ((6, 1), (2, 1)),
            2: ((6, 1), (5, 1)),
            3: ((6, 1), (5, 2)),
            4: ((6, 2), (5, 4)),
            5: ((8, 7), (6, 10)),
            6: ((9, 11), (7, 17)),
        }
        for radius, (p0, p1) in expected.items():
            result = period2.enumerate_radius(radius)
            self.assertEqual((result.phase0.horizon, result.phase0.count), p0)
            self.assertEqual((result.phase1.horizon, result.phase1.count), p1)

    def test_committed_receipt_is_bound_to_enumerator_and_truth_boundary(self) -> None:
        receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

        # Recompute the complete retained bounded theorem on every root-battery
        # execution. This covers both phases for radii 1..14 (65,532 exact
        # phase/right-half candidates) and compares the entire canonical object:
        # claim/reduction text, hard-false infinite/prize flags, and every
        # radius/phase horizon, count, phase and witness. No unregenerated tail
        # rows remain available for a hand-edited receipt to drift under green CI.
        regenerated = period2.build_receipt(14)
        self.assertEqual(receipt, regenerated)
        self.assertFalse(regenerated["prize_theorem"])
        self.assertFalse(regenerated["period_two_excluded_for_all_finite_support"])

    def test_optimized_python_regenerates_the_complete_committed_receipt(self) -> None:
        # The retained CI battery invokes root tests under ordinary Python. Make
        # optimized-mode parity a retained predecessor rather than an unwritten
        # local convention by regenerating all 65,532 candidates in a fresh -O
        # interpreter and comparing the complete JSON object byte-semantically.
        completed = subprocess.run(
            [sys.executable, "-O", str(MODULE_PATH), "--max-radius", "14"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        committed = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        regenerated = json.loads(completed.stdout)
        self.assertEqual(committed, regenerated)
        self.assertFalse(regenerated["prize_theorem"])
        self.assertFalse(regenerated["period_two_excluded_for_all_finite_support"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
