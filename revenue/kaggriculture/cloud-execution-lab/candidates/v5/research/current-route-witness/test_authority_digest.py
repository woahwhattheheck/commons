# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from current_route_witness import SCHEMA, bind_current_route_window


COMMITTED_ROUTE = "main"


class Controller:
    def __init__(self):
        self.cur = COMMITTED_ROUTE
        self.R = {
            COMMITTED_ROUTE: [
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
                {"farmer": ["MOVE", "EAST"], "hands": [["WATER"]], "market": []},
                {"farmer": ["HARVEST"], "hands": [["PASS"]], "market": [["SELL", "CARROT", 1]]},
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
            ]
        }


def observation(step: int, *, hands: int = 1):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"farmer": [0, 0], "hands": [[1, 0] for _ in range(hands)]},
            {"farmer": [9, 9], "hands": []},
        ],
        "private": {"inventories": [{} for _ in range(1 + hands)]},
    }


class AlternateController(Controller):
    pass


class AuthorityDigestTests(unittest.TestCase):
    def bind(self, controller, obs, *, lookahead):
        return bind_current_route_window(
            controller,
            obs,
            completed_route_id=COMMITTED_ROUTE,
            lookahead=lookahead,
        )

    def test_schema_is_full_authority_v2(self):
        self.assertEqual(SCHEMA, "titan-v5-current-route-window-v2")

    def test_current_worker_authority_changes_window_digest(self):
        route = Controller()
        a = self.bind(route, observation(0, hands=1), lookahead=1)
        b = self.bind(route, observation(0, hands=2), lookahead=1)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual(a.route_sha256, b.route_sha256)
        self.assertEqual(a.rows[0].action_sha256, b.rows[0].action_sha256)
        self.assertNotEqual(a.current_worker_cardinality, b.current_worker_cardinality)
        self.assertNotEqual(a.window_sha256, b.window_sha256)

    def test_requested_lookahead_changes_digest_even_when_rows_truncate_equal(self):
        route = Controller()
        a = self.bind(route, observation(2), lookahead=1)
        b = self.bind(route, observation(2), lookahead=72)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual([row.receipt() for row in a.rows], [row.receipt() for row in b.rows])
        self.assertEqual(a.route_sha256, b.route_sha256)
        self.assertNotEqual(a.lookahead, b.lookahead)
        self.assertNotEqual(a.window_sha256, b.window_sha256)

    def test_controller_identity_changes_digest_for_identical_route_bytes(self):
        a_controller = Controller()
        b_controller = AlternateController()
        b_controller.R = copy.deepcopy(a_controller.R)
        a = self.bind(a_controller, observation(0), lookahead=2)
        b = self.bind(b_controller, observation(0), lookahead=2)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual(a.route_sha256, b.route_sha256)
        self.assertEqual([row.receipt() for row in a.rows], [row.receipt() for row in b.rows])
        self.assertNotEqual(a.controller_type, b.controller_type)
        self.assertNotEqual(a.window_sha256, b.window_sha256)


if __name__ == "__main__":
    unittest.main()
