#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("gate", HERE / "champion_gate.py")
assert SPEC and SPEC.loader
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)

INC = "v5c:" + "1" * 64
CAND = "v5c:" + "2" * 64


def report(candidate_delta_v31=10, candidate_delta_inc=20):
    cells = []
    for opp in ("opp:a", "opp:b"):
        for seed in range(10, 14):
            for seat in (0, 1):
                champ_own = 1000 + seed + seat
                champ_rival = 900 + seed
                inc_own = champ_own - (candidate_delta_inc - candidate_delta_v31)
                inc_rival = champ_rival
                cand_own = champ_own + candidate_delta_v31
                cand_rival = champ_rival
                cells.append({
                    "opponent_id": opp, "seed": seed, "seat": seat,
                    "incumbent_own": inc_own, "incumbent_rival": inc_rival,
                    "champion_own": champ_own, "champion_rival": champ_rival,
                    "candidate_own": cand_own, "candidate_rival": cand_rival,
                })
    return {
        "schema": G.SCHEMA,
        "incumbent_id": INC,
        "candidate_id": CAND,
        "engine_id": "engine:pinned",
        "opponent_pack_id": "pack:frontier",
        "incumbent_archive_sha256": "a" * 64,
        "champion_archive_sha256": G.V31_ARCHIVE_SHA256,
        "candidate_archive_sha256": "b" * 64,
        "cells": cells,
    }


class Tests(unittest.TestCase):
    def test_passes_only_when_candidate_clears_both(self):
        r = G.validate_report(report())
        self.assertTrue(r["champion_ready"])
        self.assertEqual(160, r["own_sum_delta_vs_v31"])
        self.assertEqual(320, r["own_sum_delta_vs_incumbent"])
        self.assertEqual(4, r["seed_count"])
        self.assertEqual(2, r["opponent_count"])
        self.assertEqual(4, len(r["strata"]))

    def test_exact_v31_tie_is_not_outperformance(self):
        with self.assertRaisesRegex(G.ChampionError, "strictly beat V3.1"):
            G.validate_report(report(candidate_delta_v31=0, candidate_delta_inc=10))

    def test_better_than_v31_but_worse_than_incumbent_fails(self):
        with self.assertRaisesRegex(G.ChampionError, "regresses incumbent own score"):
            G.validate_report(report(candidate_delta_v31=10, candidate_delta_inc=-1))

    def test_margin_regression_fails_even_with_own_score_gain(self):
        x = report()
        for c in x["cells"]:
            c["candidate_rival"] += 1000
        with self.assertRaisesRegex(G.ChampionError, "margin"):
            G.validate_report(x)

    def test_margin_can_improve_every_cell_while_own_score_loses_and_must_reject(self):
        x = report()
        for c in x["cells"]:
            c["candidate_own"] = c["champion_own"] - 1
            c["candidate_rival"] = c["champion_rival"] - 100
            c["incumbent_own"] = c["champion_own"] - 2
            c["incumbent_rival"] = c["champion_rival"]
        with self.assertRaisesRegex(G.ChampionError, "strictly beat V3.1"):
            G.validate_report(x)

    def test_new_loss_fails(self):
        x = report()
        c = x["cells"][0]
        c["candidate_own"] = c["candidate_rival"] - 1
        x["cells"][1]["candidate_own"] += 2000
        with self.assertRaisesRegex(G.ChampionError, "new losses"):
            G.validate_report(x)

    def test_negative_opponent_seat_stratum_fails_despite_positive_total(self):
        x = report()
        for c in x["cells"]:
            if c["opponent_id"] == "opp:a" and c["seat"] == 0:
                c["candidate_own"] = c["champion_own"] - 1
            elif c["opponent_id"] == "opp:b" and c["seat"] == 0:
                c["candidate_own"] += 50
        with self.assertRaisesRegex(G.ChampionError, "negative own-score stratum"):
            G.validate_report(x)

    def test_wrong_v31_archive_fails(self):
        x = report()
        x["champion_archive_sha256"] = "c" * 64
        with self.assertRaisesRegex(G.ChampionError, "exact submitted V3.1"):
            G.validate_report(x)

    def test_unbalanced_or_duplicate_panel_fails(self):
        x = report()
        x["cells"].pop()
        with self.assertRaises(G.ChampionError):
            G.validate_report(x)
        y = report()
        y["cells"][1] = copy.deepcopy(y["cells"][0])
        with self.assertRaisesRegex(G.ChampionError, "unique"):
            G.validate_report(y)

    def test_noncanonical_order_fails(self):
        x = report()
        x["cells"][0], x["cells"][1] = x["cells"][1], x["cells"][0]
        with self.assertRaisesRegex(G.ChampionError, "sorted"):
            G.validate_report(x)

    def test_closed_shapes_and_plain_ints(self):
        x = report()
        x["claimed_win"] = True
        with self.assertRaisesRegex(G.ChampionError, "keys mismatch"):
            G.validate_report(x)
        y = report()
        y["cells"][0]["candidate_own"] = True
        with self.assertRaisesRegex(G.ChampionError, "plain int"):
            G.validate_report(y)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(G.ChampionError, "duplicate JSON"):
            G._loads('{"a":1,"a":2}')


if __name__ == "__main__":
    unittest.main()
