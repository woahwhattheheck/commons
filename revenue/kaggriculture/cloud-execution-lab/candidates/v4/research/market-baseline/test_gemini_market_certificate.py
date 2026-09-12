#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from gemini_market_certificate import (
    executable_own_sell_requested_upper,
    public_supply_certificate,
    rival_net_supply_lower_bound,
    sell_deferral_replay_certificate,
    source_bound_public_supply_certificate,
)


class FakeEngine:
    PRODUCTS = ["WHEAT", "WOOL", "MILK"]
    SHOPS = {
        "YARN_STORE": ["WOOL"],
        "PIZZA_SHOP": ["MILK", "WHEAT"],
    }
    TOWN_CENTER_PRODUCTS = list(PRODUCTS)
    MAX_SHOP_INSTANCES = 8

    @staticmethod
    def _parse_order(order):
        if not isinstance(order, list) or not order:
            return None
        op = order[0]
        if op in ("HIRE", "BUY_LAND"):
            return {"type": op}
        if op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"):
            if len(order) < 3:
                return None
            try:
                n = int(order[2])
            except (TypeError, ValueError):
                return None
            if n <= 0:
                return None
            return {"type": op, "item": order[1], "remaining": n}
        return None


def observation(step, item="WOOL", inventory=100, shops=()):
    return {
        "step": step,
        "market": {"inventory": {item: inventory}},
        "town": {"unlocked_shops": list(shops)},
    }


class RivalSupplyCertificateTests(unittest.TestCase):
    def test_positive_lower_bound_proves_prior_rival_supply(self):
        self.assertEqual(
            rival_net_supply_lower_bound(
                previous_inventory=100,
                current_inventory=115,
                previous_town_consume=5,
                previous_own_sell_requested_upper=10,
            ),
            10,
        )
        cert = public_supply_certificate(
            item="WOOL",
            previous_inventory=100,
            current_inventory=115,
            previous_town_consume=5,
            previous_own_sell_requested_upper=10,
        )
        self.assertTrue(cert["proved_prior_rival_net_supply"])
        self.assertEqual(cert["status"], "PROVED_PRIOR_RIVAL_NET_SUPPLY")

    def test_nonpositive_bound_does_not_claim_absence(self):
        cert = public_supply_certificate(
            item="MILK",
            previous_inventory=100,
            current_inventory=90,
            previous_town_consume=5,
            previous_own_sell_requested_upper=0,
        )
        self.assertEqual(cert["rival_net_supply_lower_bound"], -5)
        self.assertFalse(cert["proved_prior_rival_net_supply"])
        self.assertEqual(cert["status"], "NO_POSITIVE_RIVAL_SUPPLY_PROOF")
        self.assertIn(
            "non-positive lower bound does not prove zero rival flow",
            cert["limits"],
        )

    def test_bool_is_rejected_as_market_integer(self):
        with self.assertRaises(ValueError):
            rival_net_supply_lower_bound(
                previous_inventory=True,
                current_inventory=100,
                previous_town_consume=0,
                previous_own_sell_requested_upper=0,
            )


class SourceBoundTransitionTests(unittest.TestCase):
    engine = FakeEngine()

    def test_adjacent_public_transition_derives_town_and_own_sell(self):
        previous = observation(4, inventory=100, shops=("YARN_STORE",))
        current = observation(5, inventory=115, shops=("YARN_STORE",))
        cert = source_bound_public_supply_certificate(
            self.engine,
            item="WOOL",
            previous_observation=previous,
            current_observation=current,
            previous_own_action={"market": [["SELL", "WOOL", 10]]},
        )
        # step4 YARN_STORE consumes 2 WOOL after market. 15 + 2 - 10 = 7.
        self.assertEqual(cert["derived_town_consume"], 2)
        self.assertEqual(cert["derived_own_sell_requested_upper"], 10)
        self.assertEqual(cert["rival_net_supply_lower_bound"], 7)
        self.assertTrue(cert["proved_prior_rival_net_supply"])
        self.assertEqual(
            cert["input_custody"],
            "ADJACENT_PUBLIC_STATE_PLUS_OFFICIAL_MARKET_PREFIX",
        )

    def test_nonadjacent_observations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "adjacent"):
            source_bound_public_supply_certificate(
                self.engine,
                item="WOOL",
                previous_observation=observation(4),
                current_observation=observation(6),
                previous_own_action={},
            )

    def test_sell_outside_executable_market_cap_is_not_charged_to_us(self):
        action = {"market": [["SELL", "WOOL", 2], ["SELL", "WOOL", 999]]}
        self.assertEqual(
            executable_own_sell_requested_upper(
                self.engine,
                action,
                item="WOOL",
                config={"maxMarketOrdersPerTurn": 1},
            ),
            2,
        )

    def test_official_parser_coercible_in_prefix_sell_is_counted(self):
        action = {"market": [["SELL", "WOOL", "7"]]}
        self.assertEqual(
            executable_own_sell_requested_upper(self.engine, action, item="WOOL"),
            7,
        )

    def test_zero_config_cap_still_exposes_row_zero_like_engine(self):
        action = {"market": [["SELL", "WOOL", 3], ["SELL", "WOOL", 9]]}
        self.assertEqual(
            executable_own_sell_requested_upper(
                self.engine,
                action,
                item="WOOL",
                config={"maxMarketOrdersPerTurn": 0},
            ),
            3,
        )

    def test_day_boundary_uses_previous_town_not_newly_unlocked_shop(self):
        previous = observation(71, inventory=100, shops=())
        current = observation(72, inventory=100, shops=("YARN_STORE",))
        cert = source_bound_public_supply_certificate(
            self.engine,
            item="WOOL",
            previous_observation=previous,
            current_observation=current,
            previous_own_action={},
        )
        self.assertEqual(cert["derived_town_consume"], 0)
        self.assertEqual(cert["rival_net_supply_lower_bound"], 0)
        self.assertFalse(cert["proved_prior_rival_net_supply"])

    def test_unknown_product_rejected_before_evidence(self):
        with self.assertRaises(ValueError):
            source_bound_public_supply_certificate(
                self.engine,
                item="BOGUS",
                previous_observation=observation(4),
                current_observation=observation(5),
                previous_own_action={},
            )


class SellDeferralReplayTests(unittest.TestCase):
    def _certificate(self, **overrides):
        args = dict(
            item="WOOL",
            has_existing_sell=True,
            town_drain_units=2,
            deterministic_post_drain_premium=4,
            rival_supply_lower_bound=0,
            queue_safe=True,
            custody_safe=True,
            financing_safe=True,
            row_budget_safe=True,
            horizon_safe=True,
            evidence_complete=True,
        )
        args.update(overrides)
        return sell_deferral_replay_certificate(**args)

    def test_all_guards_only_yields_replay_candidate_not_policy(self):
        cert = self._certificate()
        self.assertEqual(cert["status"], "CANDIDATE_FOR_OWNER_REPLAY")
        self.assertFalse(cert["policy_authorized"])

    def test_proved_prior_rival_supply_vetoes_generic_deferral(self):
        cert = self._certificate(rival_supply_lower_bound=1)
        self.assertEqual(cert["status"], "VETO_PROVED_PRIOR_RIVAL_SUPPLY")
        self.assertFalse(cert["policy_authorized"])

    def test_each_owner_guard_fails_closed(self):
        for guard in (
            "queue_safe",
            "custody_safe",
            "financing_safe",
            "row_budget_safe",
            "horizon_safe",
        ):
            with self.subTest(guard=guard):
                cert = self._certificate(**{guard: False})
                self.assertEqual(cert["status"], "FAIL_CLOSED_OWNER_CONSTRAINT")
                self.assertFalse(cert["policy_authorized"])

    def test_missing_evidence_fails_closed_before_other_economics(self):
        cert = self._certificate(
            evidence_complete=False,
            deterministic_post_drain_premium=1000,
        )
        self.assertEqual(cert["status"], "FAIL_CLOSED_MISSING_EVIDENCE")

    def test_never_retimes_without_existing_sell(self):
        cert = self._certificate(has_existing_sell=False)
        self.assertEqual(cert["status"], "NO_EXISTING_SELL_TO_RETIME")

    def test_requires_positive_town_premium(self):
        self.assertEqual(
            self._certificate(town_drain_units=0)["status"],
            "NO_DETERMINISTIC_POST_DRAIN_PREMIUM",
        )
        self.assertEqual(
            self._certificate(deterministic_post_drain_premium=0)["status"],
            "NO_DETERMINISTIC_POST_DRAIN_PREMIUM",
        )

    def test_boolean_guards_are_strict(self):
        with self.assertRaises(ValueError):
            self._certificate(queue_safe=1)


if __name__ == "__main__":
    unittest.main()
