# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from current_route_full_snapshot import FULL_SCHEMA, bind_current_full_route
from current_route_witness import ROUTE_SOURCE, SCHEMA, bind_current_route_window


def selected(move="PASS"):
    return {"farmer": [move], "hands": [["PASS"]], "market": []}


class Controller:
    def __init__(self):
        self.cur = "later-proposal"
        self.R = {
            "committed": [selected() for _ in range(8)],
            "later-proposal": [selected("WEST") for _ in range(8)],
        }
        self.R["committed"][1] = selected("EAST")


def observation(step=0, player=0):
    return {
        "step": step,
        "player": player,
        "farms": [
            {"farmer": [4, 4], "hands": [[5, 4]]},
            {"farmer": [9, 9], "hands": [[8, 9]]},
        ],
        "private": {"inventories": [{}, {}]},
    }


def receipt(obs, route="committed", **updates):
    value = {
        "route_step": obs["step"],
        "last_step": obs["step"],
        "player": obs["player"],
        "route": route,
    }
    value.update(updates)
    return value


class FullRouteSnapshotTests(unittest.TestCase):
    def test_snapshot_derives_exact_canonical_v3_window_receipt(self):
        controller = Controller()
        obs = observation()
        committed = receipt(obs)
        snap = bind_current_full_route(
            controller, obs, completed_route_receipt=committed
        )
        direct = bind_current_route_window(
            controller,
            obs,
            completed_route_receipt=committed,
            lookahead=3,
        )
        self.assertIsNotNone(snap)
        self.assertIsNotNone(direct)
        self.assertEqual(snap.schema, FULL_SCHEMA)
        self.assertEqual(snap.route_source, ROUTE_SOURCE)
        self.assertEqual(snap.route_id, "committed")
        self.assertEqual(snap.route_step, 0)
        self.assertEqual(snap.last_step, 0)
        self.assertEqual(snap.player, 0)
        derived = snap.window(3)
        self.assertIsNotNone(derived)
        self.assertEqual(derived.schema, SCHEMA)
        self.assertEqual(derived.receipt(), direct.receipt())

    def test_snapshot_is_detached_from_later_controller_mutation(self):
        controller = Controller()
        obs = observation()
        snap = bind_current_full_route(
            controller, obs, completed_route_receipt=receipt(obs)
        )
        self.assertIsNotNone(snap)
        before = snap.route_actions()
        controller.R["committed"][1]["farmer"] = ["TAMPERED"]
        self.assertEqual(snap.route_actions(), before)
        self.assertEqual(snap.route_actions()[1]["farmer"], ["EAST"])

    def test_receipt_route_beats_raw_cur(self):
        controller = Controller()
        self.assertEqual(controller.cur, "later-proposal")
        obs = observation()
        snap = bind_current_full_route(
            controller, obs, completed_route_receipt=receipt(obs)
        )
        self.assertIsNotNone(snap)
        self.assertEqual(snap.route_id, "committed")
        self.assertEqual(snap.route_actions()[1]["farmer"], ["EAST"])

    def test_missing_stale_carried_cross_player_or_wrong_route_fails_closed(self):
        controller = Controller()
        obs = observation()
        self.assertIsNone(bind_current_full_route(controller, obs))
        bad_receipts = (
            receipt(obs, route="missing"),
            receipt(obs, route_step=1, last_step=1),
            receipt(obs, route_step=0, last_step=1),
            receipt(obs, player=1),
        )
        for bad_receipt in bad_receipts:
            with self.subTest(receipt=bad_receipt):
                self.assertIsNone(
                    bind_current_full_route(
                        controller,
                        obs,
                        completed_route_receipt=bad_receipt,
                    )
                )

    def test_malformed_observation_fails_closed(self):
        controller = Controller()
        obs = observation()
        bad = copy.deepcopy(obs)
        bad["private"]["inventories"] = [{}]
        self.assertIsNone(
            bind_current_full_route(
                controller,
                bad,
                completed_route_receipt=receipt(obs),
            )
        )

    def test_nonfinite_route_anywhere_fails_closed(self):
        controller = Controller()
        controller.R["committed"][7]["market"] = [["SELL", "WHEAT", float("inf")]]
        obs = observation()
        self.assertIsNone(
            bind_current_full_route(
                controller,
                obs,
                completed_route_receipt=receipt(obs),
            )
        )

    def test_invalid_window_length_fails_closed(self):
        obs = observation()
        snap = bind_current_full_route(
            Controller(), obs, completed_route_receipt=receipt(obs)
        )
        self.assertIsNotNone(snap)
        self.assertIsNone(snap.window(0))
        self.assertIsNone(snap.window(73))


if __name__ == "__main__":
    unittest.main()
