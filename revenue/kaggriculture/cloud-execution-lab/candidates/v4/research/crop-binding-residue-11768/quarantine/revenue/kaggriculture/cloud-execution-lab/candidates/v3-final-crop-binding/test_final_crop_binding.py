# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating contracts for final crop repair binding."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from candidate_runtime import FinalCropBindingAgent
from crop_release import commit_input_repair, units
from early_capital import order_early_capital
from spatial_tempo import SpatialTempo
from titan_runtime import TitanAgent


def action(market, *, farmer=None, hands=None):
    return {
        "farmer": deepcopy(["PASS"] if farmer is None else farmer),
        "hands": deepcopy([["PASS"]] if hands is None else hands),
        "market": deepcopy(market),
    }


def buy_case(*, farmer=None):
    inherited = [
        ["SELL", "CARROT", 1],
        ["BUY_LAND"],
        ["SELL", "STRAWBERRY", 2],
    ]
    expected = action(
        inherited + [["BUY_PRODUCT", "WHEAT", 3]],
        farmer=farmer,
    )
    obs = {"step": 455, "player": 0, "private": {"seeds": {}}}
    post = {"step": 455, "player": 0}
    proposal = {
        "step": 455,
        "player": 0,
        "slot": len(inherited),
        "units": 3,
        "kind": "buy",
        "unit_binding": deepcopy(units(expected)),
        "inherited_market": deepcopy(inherited),
        "expected_market": deepcopy(expected["market"]),
        "shared_stock_upper": 100,
        "funding_through": 457,
        "spending_upper": 99,
    }
    intent = {
        "status": "awaiting_observed_deposit",
        "player": 0,
        "input_repair_remaining": 3,
        "wheat_reserve_required": 3,
    }
    return intent, proposal, obs, post, expected


class LateQueueOwnershipTests(unittest.TestCase):
    def bare_agent(self, *, owner, repair=None, status="completed"):
        agent = object.__new__(FinalCropBindingAgent)
        agent.features = SimpleNamespace(
            early_capital=True,
            market_pressure=True,
        )
        agent.spatial = SimpleNamespace(_crop_repair=repair)
        agent.diagnostics = {"status": status}
        agent._crop_repair_live = owner
        return agent

    @contextmanager
    def patched_late_mutators(self):
        with patch.object(
            TitanAgent,
            "_feed_stock_selected",
            side_effect=lambda obs, cfg, selected: action(
                selected["market"] + [["SELL", "MILK", 1]]
            ),
        ) as feed, patch.object(
            TitanAgent,
            "_early_capital_selected",
            side_effect=lambda obs, cfg, selected: action(
                [["BUY_LAND"], ["SELL", "CARROT", 1]]
            ),
        ) as early, patch.object(
            TitanAgent,
            "_market_pressure_selected",
            side_effect=lambda obs, cfg, selected: selected,
        ) as pressure:
            yield feed, early, pressure

    def test_validated_owner_blocks_feed_capital_and_final_pressure(self):
        selected = action(
            [
                ["SELL", "CARROT", 1],
                ["BUY_LAND"],
                ["BUY_PRODUCT", "WHEAT", 3],
            ]
        )
        agent = self.bare_agent(owner=True, repair={"kind": "buy"})

        with self.patched_late_mutators() as (feed, early, pressure):
            after_feed = agent._feed_stock_selected({}, {}, selected)
            returned = agent._early_capital_selected({}, {}, after_feed)

        self.assertIs(returned, selected)
        feed.assert_not_called()
        early.assert_not_called()
        pressure.assert_not_called()
        self.assertEqual(
            agent.diagnostics["feed_stock"]["reason"],
            "crop_input_repair_owns_current_queue",
        )
        self.assertEqual(
            agent.diagnostics["early_capital"]["reason"],
            "crop_input_repair_owns_current_queue",
        )
        self.assertEqual(
            agent.diagnostics["market_pressure"]["reason"],
            "crop_input_repair_owns_current_queue",
        )

    def test_raw_stale_proposal_without_validated_owner_runs_late_transforms(self):
        selected = action([["BUY_LAND"], ["SELL", "CARROT", 1]])
        agent = self.bare_agent(owner=False, repair={"kind": "buy"})

        with self.patched_late_mutators() as (feed, early, pressure):
            after_feed = agent._feed_stock_selected({}, {}, selected)
            returned = agent._early_capital_selected({}, {}, after_feed)

        feed.assert_called_once()
        early.assert_called_once()
        pressure.assert_called_once()
        self.assertEqual(
            returned["market"],
            [["BUY_LAND"], ["SELL", "CARROT", 1]],
        )
        self.assertFalse(agent._crop_repair_owns_market())
        self.assertFalse(getattr(agent, "_final_pressure_boundary", False))

    def test_deadline_runs_capital_but_does_not_start_optional_pressure(self):
        selected = action([["BUY_LAND"], ["SELL", "CARROT", 1]])
        agent = self.bare_agent(
            owner=False,
            repair=None,
            status="deadline_fallback",
        )

        with self.patched_late_mutators() as (_, early, pressure):
            agent._early_capital_selected({}, {}, selected)

        early.assert_called_once()
        pressure.assert_not_called()


class History:
    def __init__(self, events):
        self.events = events
        self.fill_result = None
        self.diagnostics = {"remembered": False}

    def remember(self, obs, cfg, returned, post):
        self.events.append("history")
        self.diagnostics = {
            "remembered": True,
            "post_bound": post is not None,
        }


class LifecycleSpatial:
    def __init__(self, events, intent, proposal, *, guarded_farmer=None):
        self.events_log = events
        self.events = []
        self.receipt_events = []
        self.sale_obligation = None
        self.crop_intent = deepcopy(intent)
        self.crop_report = {"changed": True, "reason": "proposal_created"}
        self._crop_repair = deepcopy(proposal)
        self.guarded_farmer = guarded_farmer

    def observe_crop_receipts(self, *args):
        self.events_log.append("observe_crop_receipts")

    def guard_returned(self, obs, returned, **kwargs):
        self.events_log.append(
            ("guard_returned", bool(kwargs.get("repair_fallback")))
        )
        if self.guarded_farmer is None:
            return returned
        out = deepcopy(returned)
        out["farmer"] = deepcopy(self.guarded_farmer)
        return out

    def guard_crop_returned(self, obs, returned, post):
        self.events_log.append(
            (
                "guard_crop",
                self._crop_repair is not None,
                deepcopy(returned.get("market", [])),
            )
        )
        return SpatialTempo.guard_crop_returned(self, obs, returned, post)

    def finish(self, *args):
        self.events_log.append("finish")

    def finish_crop(self, obs, returned, post, route, **kwargs):
        self.events_log.append("finish_crop")
        self.crop_intent = commit_input_repair(
            self.crop_intent,
            self._crop_repair,
            obs,
            returned,
            post,
        )
        self._crop_repair = None


class LifecycleHarness(FinalCropBindingAgent):
    def _selected_snapshot(self, obs, returned=None):
        if returned is not None and units(returned) != self.expected_units:
            return None
        return deepcopy(self.snapshot)


def make_lifecycle_agent(
    intent,
    proposal,
    post,
    *,
    status="completed",
    guarded_farmer=None,
):
    events = []
    agent = object.__new__(LifecycleHarness)
    agent.lifecycle_events = events
    agent.expected_units = deepcopy(proposal["unit_binding"])
    agent.snapshot = deepcopy(post)
    agent.spatial = LifecycleSpatial(
        events,
        intent,
        proposal,
        guarded_farmer=guarded_farmer,
    )
    agent.history = History(events)
    agent.quadrant = None
    agent._quadrant_admission = None
    agent.controller = SimpleNamespace(cur="MAIN")
    agent.features = SimpleNamespace(
        crop_release=True,
        terminal_history=False,
        market_pressure=True,
    )
    agent.diagnostics = {"status": status}
    return agent, events


@contextmanager
def lifecycle_late_mutators():
    def feed(agent, obs, cfg, selected):
        agent.lifecycle_events.append(
            ("feed_base", getattr(agent.spatial, "_crop_repair", None) is not None)
        )
        out = deepcopy(selected)
        out["market"].append(["SELL", "MILK", 1])
        return out

    def capital(agent, obs, cfg, selected):
        agent.lifecycle_events.append("capital")
        out = deepcopy(selected)
        out["market"].append(["SELL", "WOOL", 1])
        return out

    def pressure(agent, obs, cfg, selected):
        agent.lifecycle_events.append("pressure")
        out = deepcopy(selected)
        out["market"].append(["SELL", "EGG", 1])
        return out

    with patch.object(
        TitanAgent,
        "_feed_stock_selected",
        new=feed,
    ), patch.object(
        TitanAgent,
        "_early_capital_selected",
        new=capital,
    ), patch.object(
        TitanAgent,
        "_market_pressure_selected",
        new=pressure,
    ):
        yield


class FinalizerLifecycleTests(unittest.TestCase):
    def test_exact_post_guard_proposal_alone_owns_final_queue(self):
        intent, proposal, obs, post, expected = buy_case()
        agent, events = make_lifecycle_agent(intent, proposal, post)

        with lifecycle_late_mutators():
            returned = agent._finish_production(obs, expected, {})

        self.assertEqual(returned, expected)
        self.assertFalse(any(
            isinstance(row, tuple) and row[0] == "feed_base" for row in events
        ))
        self.assertNotIn("capital", events)
        self.assertNotIn("pressure", events)
        self.assertEqual(
            [row[0] for row in events if isinstance(row, tuple)],
            ["guard_returned", "guard_crop"],
        )
        binding = agent.diagnostics["crop_repair_binding"]
        self.assertTrue(binding["bound_after_return_guard"])
        self.assertFalse(binding["retired_before_late_market"])
        self.assertIn("input_repair_pending", agent.spatial.crop_intent)
        self.assertNotIn("input_repair_unknown", agent.spatial.crop_intent)
        self.assertIsNone(agent.spatial._crop_repair)
        self.assertFalse(agent._crop_repair_owns_market())

    def test_deadline_after_proposal_retires_stale_owner_before_late_transforms(self):
        intent, proposal, obs, post, expected = buy_case()
        fallback = action(proposal["inherited_market"])
        agent, events = make_lifecycle_agent(
            intent,
            proposal,
            post,
            status="deadline_fallback",
        )

        with lifecycle_late_mutators():
            returned = agent._finish_production(obs, fallback, {})

        self.assertNotIn(["BUY_PRODUCT", "WHEAT", 3], returned["market"])
        feed_rows = [
            row for row in events
            if isinstance(row, tuple) and row[0] == "feed_base"
        ]
        self.assertEqual(feed_rows, [("feed_base", False)])
        self.assertIn("capital", events)
        self.assertNotIn("pressure", events)
        binding = agent.diagnostics["crop_repair_binding"]
        self.assertFalse(binding["bound_after_return_guard"])
        self.assertTrue(binding["retired_before_late_market"])
        self.assertFalse(binding["repair_residue_after_retirement"])
        self.assertEqual(
            agent.spatial.crop_report["reason"],
            "pre_transform_unbound_repair_retired",
        )
        self.assertNotIn("input_repair_pending", agent.spatial.crop_intent)
        self.assertNotIn("input_repair_unknown", agent.spatial.crop_intent)
        self.assertIsNone(agent.spatial._crop_repair)
        self.assertFalse(agent._crop_repair_owns_market())

    def test_guard_induced_unit_mismatch_cancels_buy_then_releases_queue(self):
        intent, proposal, obs, post, expected = buy_case(farmer=["HARVEST"])
        agent, events = make_lifecycle_agent(
            intent,
            proposal,
            post,
            guarded_farmer=["PASS"],
        )

        with lifecycle_late_mutators():
            returned = agent._finish_production(obs, expected, {})

        self.assertEqual(returned["farmer"], ["PASS"])
        self.assertNotIn(["BUY_PRODUCT", "WHEAT", 3], returned["market"])
        feed_rows = [
            row for row in events
            if isinstance(row, tuple) and row[0] == "feed_base"
        ]
        self.assertEqual(feed_rows, [("feed_base", False)])
        self.assertIn("capital", events)
        self.assertIn("pressure", events)
        self.assertEqual(
            agent.spatial.crop_report["reason"],
            "final_unit_guard_canceled_unbound_repair",
        )
        self.assertNotIn("input_repair_pending", agent.spatial.crop_intent)
        self.assertNotIn("input_repair_unknown", agent.spatial.crop_intent)
        self.assertIsNone(agent.spatial._crop_repair)
        self.assertFalse(agent._crop_repair_owns_market())

    def test_unremovable_repair_residue_remains_fail_closed(self):
        intent, proposal, obs, post, expected = buy_case()
        moved = action(
            [
                ["SELL", "CARROT", 1],
                ["BUY_PRODUCT", "WHEAT", 3],
                ["BUY_LAND"],
                ["SELL", "STRAWBERRY", 2],
            ]
        )
        agent, events = make_lifecycle_agent(intent, proposal, post)

        with lifecycle_late_mutators():
            returned = agent._finish_production(obs, moved, {})

        self.assertIn(["BUY_PRODUCT", "WHEAT", 3], returned["market"][:10])
        feed_rows = [
            row for row in events
            if isinstance(row, tuple) and row[0] == "feed_base"
        ]
        self.assertEqual(feed_rows, [("feed_base", False)])
        self.assertIn("capital", events)
        self.assertIn("pressure", events)
        binding = agent.diagnostics["crop_repair_binding"]
        self.assertTrue(binding["retired_before_late_market"])
        self.assertTrue(binding["repair_residue_after_retirement"])
        self.assertTrue(agent.spatial.crop_intent["input_repair_unknown"])
        self.assertNotIn("input_repair_pending", agent.spatial.crop_intent)
        self.assertIsNone(agent.spatial._crop_repair)
        self.assertFalse(agent._crop_repair_owns_market())


class PredecessorOrderingSpatial:
    def __init__(self, events):
        self.events_log = events
        self.events = []
        self.receipt_events = []
        self.sale_obligation = None
        self.crop_intent = None
        self.crop_report = {}
        self._crop_repair = None

    def observe_crop_receipts(self, *args):
        self.events_log.append("observe_crop_receipts")

    def guard_returned(self, obs, returned, **kwargs):
        self.events_log.append("guard_returned")
        return returned

    def guard_crop_returned(self, obs, returned, post):
        self.events_log.append("guard_crop")
        return returned

    def finish(self, *args):
        self.events_log.append("finish")

    def finish_crop(self, *args, **kwargs):
        self.events_log.append("finish_crop")


class PredecessorHarness(TitanAgent):
    def _feed_stock_selected(self, obs, cfg, selected):
        self.order_events.append("feed")
        return selected

    def _early_capital_selected(self, obs, cfg, selected):
        self.order_events.append("capital_pressure")
        return selected


class PredecessorOrderingTests(unittest.TestCase):
    def test_current_predecessor_guards_before_late_market_mutators(self):
        events = []
        agent = object.__new__(PredecessorHarness)
        agent.order_events = events
        agent.spatial = PredecessorOrderingSpatial(events)
        agent.history = None
        agent.quadrant = None
        agent._quadrant_admission = None
        agent.controller = SimpleNamespace(cur="MAIN")
        agent.features = SimpleNamespace(
            crop_release=False,
            terminal_history=False,
        )
        agent.diagnostics = {"status": "completed"}

        TitanAgent._finish_production(
            agent,
            {"step": 455, "player": 0},
            action([["BUY_PRODUCT", "WHEAT", 3]]),
            {},
        )

        self.assertLess(events.index("guard_crop"), events.index("feed"))
        self.assertLess(events.index("guard_crop"), events.index("capital_pressure"))


class ReceiptBindingRegressionTests(unittest.TestCase):
    def test_real_early_capital_sort_can_poison_accepted_buy_binding(self):
        intent, proposal, obs, post, expected = buy_case()
        owner = SpatialTempo.__new__(SpatialTempo)
        owner._crop_repair = proposal
        owner.crop_report = {}

        # Current ordering accepts the repair first. The real v2 stable ranker
        # then moves the second SELL ahead of BUY_LAND while leaving the appended
        # WHEAT repair executable in its final slot.
        guarded_too_early = owner.guard_crop_returned(obs, expected, post)
        moved, report = order_early_capital(
            object(),
            obs,
            {"episodeSteps": 720, "turnsPerDay": 24},
            guarded_too_early,
            [],
            (),
        )
        predecessor = commit_input_repair(intent, proposal, obs, moved, post)

        self.assertTrue(report["changed"])
        self.assertEqual(
            moved["market"],
            [
                ["SELL", "CARROT", 1],
                ["SELL", "STRAWBERRY", 2],
                ["BUY_LAND"],
                ["BUY_PRODUCT", "WHEAT", 3],
            ],
        )
        self.assertIn(["BUY_PRODUCT", "WHEAT", 3], moved["market"][:10])
        self.assertTrue(predecessor["input_repair_unknown"])
        self.assertNotIn("input_repair_pending", predecessor)

        final_guarded = owner.guard_crop_returned(obs, expected, post)
        candidate = commit_input_repair(
            intent,
            proposal,
            obs,
            final_guarded,
            post,
        )
        self.assertNotIn("input_repair_unknown", candidate)
        self.assertEqual(
            candidate["input_repair_pending"]["expected_market"],
            expected["market"],
        )

    def test_withheld_sale_indices_are_equally_receipt_critical(self):
        inherited = [
            ["SELL", "WHEAT", 2],
            ["BUY_SEED", "WHEAT", 1],
            ["SELL", "WHEAT", 2],
            ["SELL", "STRAWBERRY", 1],
        ]
        expected = action(
            [
                [],
                ["BUY_SEED", "WHEAT", 1],
                [],
                ["SELL", "STRAWBERRY", 1],
            ]
        )
        obs = {"step": 457, "player": 0}
        post = {"step": 457, "player": 0}
        proposal = {
            "step": 457,
            "player": 0,
            "slot": len(inherited),
            "units": 3,
            "kind": "withhold",
            "unit_binding": deepcopy(units(expected)),
            "inherited_market": deepcopy(inherited),
            "expected_market": deepcopy(expected["market"]),
            "original_sale_slots": [0, 2],
            "sale_slots": [],
            "expected_sale_units": 0,
            "expected_shed_wheat": 3,
        }
        intent = {
            "player": 0,
            "input_repair_remaining": 3,
            "wheat_reserve_required": 3,
        }
        moved = deepcopy(expected)
        moved["market"] = [
            ["SELL", "STRAWBERRY", 1],
            [],
            ["BUY_SEED", "WHEAT", 1],
            [],
        ]

        predecessor = commit_input_repair(intent, proposal, obs, moved, post)
        candidate = commit_input_repair(intent, proposal, obs, expected, post)

        self.assertTrue(predecessor["input_repair_unknown"])
        self.assertIn("input_repair_pending", candidate)


if __name__ == "__main__":
    unittest.main()
