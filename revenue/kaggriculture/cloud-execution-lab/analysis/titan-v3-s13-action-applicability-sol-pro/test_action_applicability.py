# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from action_applicability import (
    AuditError,
    RouteRow,
    audit_rows,
    certificate_matches,
    load_pinned_engine,
    prestate_certificate,
    strict_json_bytes,
    structural_signature,
)


def tile_grid(tile=None):
    grid = [[None for _ in range(10)] for _ in range(10)]
    grid[4][4] = copy.deepcopy(tile)
    return grid


def farm(tile=None, money=100.0):
    return {
        "farmer": [4, 4],
        "hands": [[4, 4], [5, 4], [4, 5], [5, 5]],
        "hires_today": 4,
        "money": money,
        "tiles": tile_grid(tile),
        "unlocked_quadrants": ["NW"],
    }


def observation(*, wheat_in_hand: int, wheat_in_shed: int, money=100.0):
    cow = {
        "animal": "COW",
        "cared_today": False,
        "consecutive_unfed": 0,
        "fed_today": False,
        "fertilizer_available": True,
        "kind": "PASTURE",
        "pending_care_bonus": 2,
        "placed_day": 0,
        "yield_units": 0,
    }
    inventories = [{"WHEAT": wheat_in_hand} if wheat_in_hand else {}, {}, {}, {}, {}]
    return {
        "day": 2,
        "hour": 1,
        "step": 49,
        "player": 0,
        "remainingOverageTime": 59.5,
        "farms": [farm(cow, money), farm(None, 200.0)],
        "private": {
            "inventories": inventories,
            "seeds": {"WHEAT": 0},
            "shed": {"WHEAT": wheat_in_shed, "FERTILIZER": 0},
        },
        "market": {
            "inventory": {"WHEAT": 10000, "FERTILIZER": 10000},
            "prices": {"WHEAT": 25, "FERTILIZER": 100},
        },
        "town": {"unlocked_shops": []},
    }


CFG = {
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
}

SOURCE_ACTION = {
    "farmer": ["FEED"],
    "hands": [["PASS"], ["PASS"], ["PASS"], ["PASS"]],
    "market": [],
}
TARGET_ACTION = {
    "farmer": ["PICKUP", "WHEAT", 4],
    "hands": [["PASS"], ["PASS"], ["PASS"], ["PASS"]],
    "market": [],
}


class TinyPinnedEngine:
    @staticmethod
    def _apply_unit_action(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity):
        del day, turns_per_day, shed_capacity
        if idx == 0:
            position = farm["farmer"]
        else:
            position = farm["hands"][idx - 1]
        inventory = private["inventories"][idx]
        op = action[0] if isinstance(action, list) and action else None
        if op == "PASS":
            return
        if op == "FEED":
            x, y = position
            tile = farm["tiles"][y][x]
            if not isinstance(tile, dict) or "animal" not in tile or tile.get("fed_today"):
                return
            if inventory.get("WHEAT", 0) <= 0:
                return
            inventory["WHEAT"] -= 1
            if inventory["WHEAT"] == 0:
                del inventory["WHEAT"]
            tile["fed_today"] = True
            return
        if op == "PICKUP":
            if tuple(position) not in {(4, 4), (5, 4), (4, 5), (5, 5)}:
                return
            item = action[1]
            quantity = int(action[2]) if len(action) >= 3 else 1
            quantity = min(quantity, private["shed"].get(item, 0))
            if quantity <= 0:
                return
            private["shed"][item] -= quantity
            inventory[item] = inventory.get(item, 0) + quantity


class ApplicabilityTests(unittest.TestCase):
    def test_structural_signature_aliases_engine_incompatible_states(self):
        source_obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        target_obs = observation(wheat_in_hand=0, wheat_in_shed=4)
        self.assertEqual(structural_signature(source_obs, 0), {"hands": 4, "quadrants": 1})
        self.assertEqual(structural_signature(source_obs, 0), structural_signature(target_obs, 0))
        source_cert = prestate_certificate(source_obs, CFG, SOURCE_ACTION, seat=0, mode="units")
        target_cert = prestate_certificate(target_obs, CFG, SOURCE_ACTION, seat=0, mode="units")
        self.assertNotEqual(source_cert, target_cert)

    def test_corpus_auditor_reproduces_feed_pickup_predecessor(self):
        source_obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        target_obs = observation(wheat_in_hand=0, wheat_in_shed=4)
        source = RouteRow(
            episode="1", seat=0, team="Source", frame=49, step=49,
            signature=(4, 1), action=SOURCE_ACTION, observation=source_obs,
            configuration=CFG,
        )
        target = RouteRow(
            episode="2", seat=0, team="Target", frame=49, step=49,
            signature=(4, 1), action=TARGET_ACTION, observation=target_obs,
            configuration=CFG,
        )
        result = audit_rows([source, target], TinyPinnedEngine())
        self.assertEqual(result["unit_false_applicability_witnesses"], 2)
        self.assertEqual(result["certificate_failures"], 0)
        witness = result["first_witness"]
        self.assertEqual(witness["source_component"], ["FEED"])
        self.assertEqual(witness["target_component"], ["PICKUP", "WHEAT", 4])

    def test_certificate_matches_exact_and_rejects_changed_own_state(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        cert = prestate_certificate(obs, CFG, SOURCE_ACTION, seat=0, mode="full")
        self.assertTrue(certificate_matches(cert, obs, CFG, SOURCE_ACTION, seat=0))
        changed = copy.deepcopy(obs)
        changed["private"]["inventories"][0].clear()
        self.assertFalse(certificate_matches(cert, changed, CFG, SOURCE_ACTION, seat=0))

    def test_volatile_step_and_budget_are_excluded(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        changed = copy.deepcopy(obs)
        changed["step"] = 500
        changed["remainingOverageTime"] = 0.01
        self.assertEqual(
            prestate_certificate(obs, CFG, SOURCE_ACTION, seat=0, mode="full"),
            prestate_certificate(changed, CFG, SOURCE_ACTION, seat=0, mode="full"),
        )

    def test_rival_farm_is_outside_own_prestate_certificate(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        changed = copy.deepcopy(obs)
        changed["farms"][1]["money"] = -999999
        changed["farms"][1]["farmer"] = [0, 0]
        for mode in ("units", "market", "full"):
            self.assertEqual(
                prestate_certificate(obs, CFG, SOURCE_ACTION, seat=0, mode=mode),
                prestate_certificate(changed, CFG, SOURCE_ACTION, seat=0, mode=mode),
            )

    def test_day_is_bound_for_unit_execution(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        changed = copy.deepcopy(obs)
        changed["day"] += 1
        self.assertNotEqual(
            prestate_certificate(obs, CFG, SOURCE_ACTION, seat=0, mode="units"),
            prestate_certificate(changed, CFG, SOURCE_ACTION, seat=0, mode="units"),
        )

    def test_market_money_inventory_and_shed_are_bound(self):
        action = {
            "farmer": ["PASS"],
            "hands": [["PASS"]] * 4,
            "market": [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "FERTILIZER", 1]],
        }
        obs = observation(wheat_in_hand=0, wheat_in_shed=2)
        base = prestate_certificate(obs, CFG, action, seat=0, mode="market")
        for mutation in ("money", "market", "shed"):
            changed = copy.deepcopy(obs)
            if mutation == "money":
                changed["farms"][0]["money"] += 1
            elif mutation == "market":
                changed["market"]["inventory"]["FERTILIZER"] -= 1
            else:
                changed["private"]["shed"]["WHEAT"] -= 1
            self.assertNotEqual(base, prestate_certificate(changed, CFG, action, seat=0, mode="market"))

    def test_action_identity_is_bound(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        self.assertNotEqual(
            prestate_certificate(obs, CFG, SOURCE_ACTION, seat=0, mode="units"),
            prestate_certificate(obs, CFG, TARGET_ACTION, seat=0, mode="units"),
        )

    def test_empty_market_placeholders_are_accepted_but_malformed_rows_fail(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        action = copy.deepcopy(SOURCE_ACTION)
        action["market"] = [[], ["HIRE"]]
        prestate_certificate(obs, CFG, action, seat=0, mode="market")
        action["market"] = [123]
        with self.assertRaisesRegex(AuditError, "action.market"):
            prestate_certificate(obs, CFG, action, seat=0, mode="market")

    def test_player_orientation_is_fail_closed(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        obs["player"] = 1
        with self.assertRaisesRegex(AuditError, "does not bind seat"):
            prestate_certificate(obs, CFG, SOURCE_ACTION, seat=0, mode="units")

    def test_boolean_or_fractional_engine_configuration_is_rejected(self):
        obs = observation(wheat_in_hand=1, wheat_in_shed=0)
        for key, value in (("boardSize", True), ("turnsPerDay", 24.5)):
            cfg = dict(CFG)
            cfg[key] = value
            with self.assertRaisesRegex(AuditError, "expected integer"):
                prestate_certificate(obs, cfg, SOURCE_ACTION, seat=0, mode="units")

    def test_duplicate_and_nonfinite_json_are_rejected(self):
        with self.assertRaisesRegex(AuditError, "duplicate JSON key"):
            strict_json_bytes(b'{"x":1,"x":2}', "fixture")
        with self.assertRaisesRegex(AuditError, "non-finite JSON constant"):
            strict_json_bytes(b'{"x":NaN}', "fixture")

    def test_engine_digest_is_verified_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.py"
            path.write_text("VALUE = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(AuditError, "engine SHA-256 mismatch"):
                load_pinned_engine(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
