# SPDX-License-Identifier: Apache-2.0
"""Contracts for the league Elo/lean ledger."""
import json
import os
import tempfile
import unittest

from ledger import (
    DEFAULT_ELO,
    LedgerError,
    expected_score,
    load_ledger,
    new_ledger,
    record_results,
    save_ledger,
    standings,
    update_elo,
)


class EloMathTest(unittest.TestCase):
    def test_equal_ratings_expected_half(self):
        self.assertAlmostEqual(expected_score(1500.0, 1500.0), 0.5)

    def test_400_point_gap_expected_ten_to_one(self):
        self.assertAlmostEqual(expected_score(1900.0, 1500.0), 10 / 11, places=6)

    def test_win_moves_ratings_toward_each_other(self):
        players = {}
        update_elo(players, [("a", "b", 1.0)], k=24.0)
        self.assertGreater(players["a"]["elo"], DEFAULT_ELO)
        self.assertLess(players["b"]["elo"], DEFAULT_ELO)
        self.assertAlmostEqual(
            (players["a"]["elo"] - DEFAULT_ELO) + (players["b"]["elo"] - DEFAULT_ELO),
            0.0, places=9)

    def test_tie_leaves_equal_ratings_unchanged(self):
        players = {}
        update_elo(players, [("a", "b", 0.5)], k=24.0)
        self.assertEqual(players["a"]["elo"], DEFAULT_ELO)
        self.assertEqual(players["b"]["elo"], DEFAULT_ELO)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(LedgerError):
            update_elo({}, [("a", "b", 0.7)])
        with self.assertRaises(LedgerError):
            update_elo({}, [("a", "b", 1.0)], k=-1.0)


class RecordResultsTest(unittest.TestCase):
    def test_win_loss_folds_both_sides(self):
        players = {}
        record_results(players, [
            {"contestant": "c", "opponent": "o", "margin": 100.0},
            {"contestant": "c", "opponent": "o", "margin": -50.0},
        ])
        self.assertEqual(players["c"]["wins"], 1)
        self.assertEqual(players["c"]["losses"], 1)
        self.assertEqual(players["o"]["wins"], 1)
        self.assertEqual(players["o"]["losses"], 1)
        self.assertEqual(players["c"]["games"], 2)
        self.assertAlmostEqual(players["c"]["margin_sum"], 50.0)

    def test_tie_counts_half(self):
        players = {}
        before = dict(players)
        record_results(players, [{"contestant": "c", "opponent": "o", "margin": 0.0}])
        self.assertEqual(players["c"]["ties"], 1)
        self.assertEqual(players["o"]["ties"], 1)
        self.assertEqual(players["c"]["elo"], before.get("c", {}).get("elo", DEFAULT_ELO)
                         if before else DEFAULT_ELO)

    def test_malformed_games_fail_closed(self):
        for bad in ({"contestant": "", "opponent": "o", "margin": 1.0},
                    {"contestant": "c", "opponent": "o", "margin": float("nan")},
                    {"contestant": "c", "opponent": "o"}):
            with self.assertRaises(LedgerError):
                record_results({}, [bad])


class StandingsTest(unittest.TestCase):
    def test_sorted_by_elo_desc_with_lean(self):
        players = {}
        record_results(players, [{"contestant": "strong", "opponent": "weak", "margin": 10.0}])
        rows = standings(players)
        self.assertEqual([r["name"] for r in rows], ["strong", "weak"])
        self.assertEqual(rows[0]["mean_margin"], 10.0)
        self.assertEqual(rows[1]["mean_margin"], -10.0)

    def test_new_player_has_no_mean_margin(self):
        rows = standings({"fresh": {"elo": DEFAULT_ELO, "games": 0, "wins": 0,
                                    "ties": 0, "losses": 0, "margin_sum": 0.0}})
        self.assertIsNone(rows[0]["mean_margin"])


class PersistenceTest(unittest.TestCase):
    def test_roundtrip(self):
        ledger = new_ledger()
        record_results(ledger["players"],
                       [{"contestant": "c", "opponent": "o", "margin": 5.0}])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            save_ledger(path, ledger)
            reloaded = load_ledger(path)
        self.assertEqual(reloaded["players"], ledger["players"])

    def test_missing_path_gives_fresh_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = load_ledger(os.path.join(tmp, "nope.json"))
        self.assertEqual(ledger["schema"], "titan.league-ledger.v1")
        self.assertEqual(ledger["players"], {})

    def test_wrong_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            with open(path, "w") as handle:
                json.dump({"schema": "other"}, handle)
            with self.assertRaises(LedgerError):
                load_ledger(path)


if __name__ == "__main__":
    unittest.main()
