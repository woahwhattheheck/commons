# SPDX-License-Identifier: Apache-2.0
"""Contracts for the league own-cash regression alarm.

Includes the #11907 witness: a joint (opponent, seat) stratum with
negative own-cash on every seed must alarm even when the global mean and
every per-opponent / per-seat marginal are nonnegative.
"""
import unittest

from alarms import (
    AlarmData,
    alarms_to_markdown,
    check_own_cash_regressions,
    joint_strata,
)


def witness_cells():
    """#11907 witness table, one cell per seed per joint stratum."""
    table = {
        ("arlene", 0): [-10.0] * 8,
        ("arlene", 1): [+30.0] * 8,
        ("apex", 0): [+30.0] * 8,
        ("apex", 1): [+10.0] * 8,
        ("public_bt12", 0): [+30.0] * 8,
        ("public_bt12", 1): [+10.0] * 8,
        ("v1", 0): [+30.0] * 8,
        ("v1", 1): [+10.0] * 8,
    }
    cells = []
    for (opponent, seat), values in table.items():
        for seed, own_cash in enumerate(values):
            cells.append({"opponent": opponent, "candidate_seat": seat,
                          "seed": seed, "own_cash": own_cash})
    return cells


class JointStrataTest(unittest.TestCase):
    def test_groups_by_opponent_and_seat(self):
        strata = joint_strata(witness_cells())
        self.assertEqual(set(strata), {
            ("arlene", 0), ("arlene", 1), ("apex", 0), ("apex", 1),
            ("public_bt12", 0), ("public_bt12", 1), ("v1", 0), ("v1", 1)})
        self.assertEqual(len(strata[("arlene", 0)]), 8)

    def test_malformed_cells_fail_closed(self):
        with self.assertRaises(AlarmData):
            joint_strata([{"opponent": "", "candidate_seat": 0, "own_cash": 1.0}])
        with self.assertRaises(AlarmData):
            joint_strata([{"opponent": "x", "candidate_seat": 2, "own_cash": 1.0}])
        with self.assertRaises(AlarmData):
            joint_strata([{"opponent": "x", "candidate_seat": 0,
                           "own_cash": float("nan")}])


class OwnCashAlarmTest(unittest.TestCase):
    def test_witness_alarms_despite_positive_marginals(self):
        cells = witness_cells()
        alarms = check_own_cash_regressions(cells)
        kinds = {(a["kind"], a["opponent"], a["candidate_seat"]) for a in alarms}
        self.assertIn(("negative_own_cash", "arlene", 0), kinds)
        # No other stratum alarms: every other joint mean is nonnegative.
        self.assertEqual(len(alarms), 1)

    def test_no_alarms_when_all_nonnegative(self):
        cells = [dict(c, own_cash=abs(c["own_cash"]) + 1.0) for c in witness_cells()]
        self.assertEqual(check_own_cash_regressions(cells), [])

    def test_regression_against_baseline(self):
        cells = witness_cells()
        # Baseline: every stratum used to average +30.
        baseline = {(opp, seat): 30.0 for opp, seat in {
            ("arlene", 0), ("arlene", 1), ("apex", 0), ("apex", 1)}}
        alarms = check_own_cash_regressions(cells, baseline=baseline,
                                            drop_tolerance=5.0)
        by_kind = {}
        for alarm in alarms:
            by_kind.setdefault(alarm["kind"], []).append(
                (alarm["opponent"], alarm["candidate_seat"]))
        # arlene x seat 1: 30 vs 30 -> no regression; apex x seat 1: 10 vs 30 -> regression.
        self.assertIn(("apex", 1), by_kind.get("own_cash_regression", []))
        self.assertNotIn(("arlene", 1), by_kind.get("own_cash_regression", []))

    def test_first_week_without_baseline_only_checks_floor(self):
        cells = [dict(c, own_cash=25.0) for c in witness_cells()
                 if not (c["opponent"] == "arlene" and c["candidate_seat"] == 0)]
        alarms = check_own_cash_regressions(cells, baseline=None)
        self.assertEqual(alarms, [])

    def test_incomplete_stratum_alarms(self):
        cells = [{"opponent": "x", "candidate_seat": 0, "own_cash": 5.0}]
        alarms = check_own_cash_regressions(cells, min_cells_per_stratum=4)
        self.assertEqual(len(alarms), 1)
        self.assertEqual(alarms[0]["kind"], "incomplete_stratum")

    def test_bad_thresholds_fail_closed(self):
        with self.assertRaises(AlarmData):
            check_own_cash_regressions(witness_cells(), floor=float("inf"))
        with self.assertRaises(AlarmData):
            check_own_cash_regressions(witness_cells(), drop_tolerance=-1.0)

    def test_markdown_renders_alarm_kinds(self):
        alarms = check_own_cash_regressions(witness_cells())
        text = alarms_to_markdown("witness", alarms)
        self.assertIn("NEGATIVE_OWN_CASH", text)
        self.assertIn("arlene x seat 0", text)
        clean = alarms_to_markdown("clean", [])
        self.assertIn("No own-cash alarms", clean)


if __name__ == "__main__":
    unittest.main()
