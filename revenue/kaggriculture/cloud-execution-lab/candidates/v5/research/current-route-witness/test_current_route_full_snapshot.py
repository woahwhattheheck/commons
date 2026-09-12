# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from current_route_full_snapshot import FULL_SCHEMA, bind_current_full_route
from current_route_witness import bind_current_route_window


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


def observation(step=0):
    return {
        "step": step,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [[5, 4]]}],
        "private": {"inventories": [{}, {}]},
    }


class FullRouteSnapshotTests(unittest.TestCase):
    def test_snapshot_derives_exact_existing_window_receipt(self):
        controller = Controller()
        snap = bind_current_full_route(
            controller, observation(), completed_route_id="committed"
        )
        direct = bind_current_route_window(
            controller, observation(), completed_route_id="committed", lookahead=3
        )
        self.assertIsNotNone(snap)
        self.assertEqual(snap.schema, FULL_SCHEMA)
        self.assertEqual(snap.route_id, "committed")
        self.assertEqual(snap.window(3).receipt(), direct.receipt())

    def test_snapshot_is_detached_from_later_controller_mutation(self):
        controller = Controller()
        snap = bind_current_full_route(
            controller, observation(), completed_route_id="committed"
        )
        before = snap.route_actions()
        controller.R["committed"][1]["farmer"] = ["TAMPERED"]
        self.assertEqual(snap.route_actions(), before)
        self.assertEqual(snap.route_actions()[1]["farmer"], ["EAST"])

    def test_explicit_committed_route_beats_raw_cur(self):
        controller = Controller()
        self.assertEqual(controller.cur, "later-proposal")
        snap = bind_current_full_route(
            controller, observation(), completed_route_id="committed"
        )
        self.assertEqual(snap.route_id, "committed")
        self.assertEqual(snap.route_actions()[1]["farmer"], ["EAST"])

    def test_missing_or_bad_authority_fails_closed(self):
        controller = Controller()
        self.assertIsNone(bind_current_full_route(controller, observation()))
        self.assertIsNone(
            bind_current_full_route(
                controller, observation(), completed_route_id="missing"
            )
        )
        bad = copy.deepcopy(observation())
        bad["private"]["inventories"] = [{}]
        self.assertIsNone(
            bind_current_full_route(
                controller, bad, completed_route_id="committed"
            )
        )

    def test_invalid_window_length_fails_closed(self):
        snap = bind_current_full_route(
            Controller(), observation(), completed_route_id="committed"
        )
        self.assertIsNone(snap.window(0))
        self.assertIsNone(snap.window(73))


if __name__ == "__main__":
    unittest.main()
