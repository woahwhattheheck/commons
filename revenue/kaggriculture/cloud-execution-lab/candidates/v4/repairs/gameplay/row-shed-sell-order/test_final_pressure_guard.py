# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for STRATUM survival through canonical final pressure."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]
LARK = LAB.parent / "cloud-opponent-league" / "lark-responsive"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import mechanics
from novel_rank_guard import NovelRankGuard


def action(rows, farmer=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [],
        "market": copy.deepcopy(rows),
    }


def _leading_sort(action_in, key):
    out = copy.deepcopy(action_in)
    rows = out["market"]
    lead = 0
    while lead < len(rows) and rows[lead] and rows[lead][0] == "SELL":
        lead += 1
    rows[:lead] = sorted(rows[:lead], key=key)
    return out


def identity_pressure(action_in, _observation, _configuration, *, quote):
    assert callable(quote)
    return copy.deepcopy(action_in)


def alphabetical_pressure(action_in, _observation, _configuration, *, quote):
    assert callable(quote)
    return _leading_sort(action_in, key=lambda row: row[1])


class FinalPressureAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.obs = {
            "market": {
                "inventory": {"WOOL": 10000, "MILK": 10000, "EGG": 10000},
                "prices": {
                    "WOOL": mechanics.market_price("WOOL", 10000, None),
                    "MILK": mechanics.market_price("MILK", 10000, None),
                    "EGG": mechanics.market_price("EGG", 10000, None),
                },
                "params": None,
            }
        }
        self.cfg = {"maxMarketOrdersPerTurn": 10}
        self.base = action([
            ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4],
            ["HIRE"],
        ])
        self.row = action([
            ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5],
            ["HIRE"],
        ])

    def choose(self, transform, *, base=None, row=None, obs=None, cfg=None, quote=None):
        guard = NovelRankGuard()
        result = guard.choose_after_pressure(
            self.base if base is None else base,
            self.row if row is None else row,
            self.obs if obs is None else obs,
            self.cfg if cfg is None else cfg,
            pressure_transform=transform,
            quote=mechanics.market_price if quote is None else quote,
        )
        return guard, result

    def test_distinct_intermediate_rank_collapsing_after_pressure_is_identity(self):
        guard, got = self.choose(alphabetical_pressure)
        self.assertEqual(got, self.base)
        self.assertEqual(guard.diagnostics["reason"], "collapsed_after_final_pressure")
        self.assertTrue(guard.diagnostics["parent_pressure_changed"])
        self.assertFalse(guard.diagnostics["row_shed_pressure_changed"])

    def test_stable_pressure_tie_preserves_surviving_stratum_order(self):
        guard, got = self.choose(identity_pressure)
        self.assertEqual(got, self.row)
        self.assertEqual(guard.diagnostics["status"], "applied")
        self.assertEqual(guard.diagnostics["reason"], "survives_final_pressure")

    def test_legal_empty_slot_compaction_is_valid_pressure_evidence(self):
        base = action([
            ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4],
            [],
            ["SELL", "EGG", 3],
        ])
        row = action([
            ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5],
            [],
            ["SELL", "EGG", 3],
        ])

        def compact(action_in, _obs, _cfg, *, quote):
            assert callable(quote)
            out = copy.deepcopy(action_in)
            positive = [r for r in out["market"] if r]
            empty = [r for r in out["market"] if not r]
            out["market"] = positive + empty
            return out

        guard, got = self.choose(compact, base=base, row=row)
        self.assertEqual(got, row)
        self.assertEqual(guard.diagnostics["reason"], "survives_final_pressure")
        self.assertEqual(guard.diagnostics["parent_final_market"][-1], [])

    def test_pressure_quantity_mutation_fails_closed(self):
        def mutate(action_in, _obs, _cfg, *, quote):
            out = copy.deepcopy(action_in)
            out["market"][0][2] += 1
            return out

        guard, got = self.choose(mutate)
        self.assertEqual(got, self.base)
        self.assertIn("row multiset", guard.diagnostics["reason"])

    def test_pressure_non_market_mutation_fails_closed(self):
        def mutate(action_in, _obs, _cfg, *, quote):
            out = copy.deepcopy(action_in)
            out["farmer"] = ["LEFT"]
            return out

        guard, got = self.choose(mutate)
        self.assertEqual(got, self.base)
        self.assertIn("non-market", guard.diagnostics["reason"])

    def test_pressure_top_level_key_mutation_fails_closed(self):
        def mutate(action_in, _obs, _cfg, *, quote):
            out = copy.deepcopy(action_in)
            out["extra"] = True
            return out

        guard, got = self.choose(mutate)
        self.assertEqual(got, self.base)
        self.assertIn("top-level", guard.diagnostics["reason"])

    def test_missing_or_throwing_pressure_fails_closed(self):
        guard, got = self.choose(None)
        self.assertEqual(got, self.base)
        self.assertIn("missing", guard.diagnostics["reason"])

        def boom(*_args, **_kwargs):
            raise RuntimeError("pressure boom")

        guard, got = self.choose(boom)
        self.assertEqual(got, self.base)
        self.assertEqual(guard.diagnostics["reason"], "pressure boom")

    def test_missing_quote_fails_closed(self):
        guard = NovelRankGuard()
        got = guard.choose_after_pressure(
            self.base,
            self.row,
            self.obs,
            self.cfg,
            pressure_transform=identity_pressure,
            quote=None,
        )
        self.assertEqual(got, self.base)
        self.assertIn("quote", guard.diagnostics["reason"])

    def test_malformed_pressure_output_fails_closed(self):
        def bad(_action, _obs, _cfg, *, quote):
            return None

        guard, got = self.choose(bad)
        self.assertEqual(got, self.base)
        self.assertIn("dict", guard.diagnostics["reason"])

    def test_callback_mutation_cannot_escape_evidence_copies(self):
        obs = copy.deepcopy(self.obs)
        cfg = copy.deepcopy(self.cfg)
        before_obs = copy.deepcopy(obs)
        before_cfg = copy.deepcopy(cfg)

        def invasive(action_in, local_obs, local_cfg, *, quote):
            local_obs["mutated"] = True
            local_cfg["mutated"] = True
            action_in.setdefault("market", [])
            return action_in

        guard, got = self.choose(invasive, obs=obs, cfg=cfg)
        self.assertEqual(got, self.row)
        self.assertEqual(obs, before_obs)
        self.assertEqual(cfg, before_cfg)
        self.assertEqual(guard.diagnostics["reason"], "survives_final_pressure")

    def test_invalid_row_shed_candidate_still_fails_before_callback(self):
        row = action([
            ["SELL", "MILK", 99],
            ["SELL", "WOOL", 5],
            ["HIRE"],
        ])
        calls = []

        def counted(action_in, _obs, _cfg, *, quote):
            calls.append(copy.deepcopy(action_in))
            return copy.deepcopy(action_in)

        guard, got = self.choose(counted, row=row)
        self.assertEqual(got, self.base)
        self.assertFalse(calls)
        self.assertIn("leading SELL multiset", guard.diagnostics["reason"])

    def test_exact_current_lark_callback_is_api_compatible(self):
        sell_spec = importlib.util.spec_from_file_location(
            "sell_priority", LARK / "sell_priority.py")
        sell = importlib.util.module_from_spec(sell_spec)
        prior_sell = sys.modules.get("sell_priority")
        try:
            sys.modules["sell_priority"] = sell
            sell_spec.loader.exec_module(sell)
            pressure_spec = importlib.util.spec_from_file_location(
                "_row_shed_exact_pressure", LARK / "pressure_priority.py")
            pressure = importlib.util.module_from_spec(pressure_spec)
            pressure_spec.loader.exec_module(pressure)
            guard, got = self.choose(pressure.transform)
        finally:
            if prior_sell is None:
                sys.modules.pop("sell_priority", None)
            else:
                sys.modules["sell_priority"] = prior_sell

        self.assertIn(got, (self.base, self.row))
        self.assertIn(
            guard.diagnostics["reason"],
            ("collapsed_after_final_pressure", "survives_final_pressure"),
        )
        self.assertEqual(guard.diagnostics["mode"], "final_pressure_output")


if __name__ == "__main__":
    unittest.main()
