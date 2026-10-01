#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from gemini_market_certificate import (
    public_supply_certificate,
    rival_net_supply_lower_bound,
    sell_deferral_replay_certificate,
)


class RivalSupplyCertificateTests(unittest.TestCase):
    def test_positive_lower_bound_proves_prior_rival_supply(self):
        # delta inventory +15, known town drain +5, our requested SELL upper +10
        # => rival SELL - rival BUY >= +10.
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
