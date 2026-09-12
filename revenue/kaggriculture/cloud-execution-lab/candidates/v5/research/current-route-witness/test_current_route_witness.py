# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from current_route_witness import (
    MAX_LOOKAHEAD,
    ROUTE_SOURCE,
    SCHEMA,
    bind_b5_kwargs,
    bind_current_route,
    bind_current_route_window,
)


COMMITTED_ROUTE = "main"


class Controller:
    def __init__(self):
        self.cur = "main"
        self.R = {
            "main": [
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
                {"farmer": ["MOVE", "EAST"], "hands": [["WATER"]], "market": []},
                {"farmer": ["HARVEST"], "hands": [["PASS"]], "market": [["SELL", "CARROT", 1]]},
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
            ],
            "alt": [
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
                {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
            ],
        }
        self.calls = 0

    def act(self, _obs):
        self.calls += 1
        raise AssertionError("route witness must not call producer")


def observation(step=0):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"farmer": [0, 0], "hands": [[1, 0]]},
            {"farmer": [9, 9], "hands": []},
        ],
        "private": {"inventories": [{}, {}]},
    }


class CurrentRouteWitnessTests(unittest.TestCase):
    def test_binds_exact_next_row_without_calling_producer(self):
        controller = Controller()
        witness = bind_current_route(
            controller, observation(0), completed_route_id=COMMITTED_ROUTE
        )
        self.assertIsNotNone(witness)
        self.assertEqual(controller.calls, 0)
        self.assertEqual(witness.schema, SCHEMA)
        self.assertEqual(witness.route_source, ROUTE_SOURCE)
        self.assertEqual(witness.route_id, "main")
        self.assertEqual(witness.current_step, 0)
        self.assertEqual(witness.current_index, 0)
        self.assertEqual(witness.next_step, 1)
        self.assertEqual(witness.worker_cardinality, 2)
        self.assertEqual(witness.route_length, 4)
        self.assertEqual(
            witness.next_authored_action(),
            {"farmer": ["MOVE", "EAST"], "hands": [["WATER"]], "market": []},
        )
        self.assertEqual(len(witness.route_sha256), 64)
        self.assertEqual(len(witness.action_sha256), 64)
        self.assertEqual(len(witness.window_sha256), 64)

    def test_window_captures_ordered_rows_from_one_snapshot(self):
        controller = Controller()
        window = bind_current_route_window(
            controller,
            observation(0),
            completed_route_id=COMMITTED_ROUTE,
            lookahead=3,
        )
        self.assertIsNotNone(window)
        self.assertEqual(controller.calls, 0)
        self.assertEqual([row.step for row in window.rows], [1, 2, 3])
        self.assertEqual([row.worker_cardinality for row in window.rows], [2, 2, 2])
        self.assertEqual(window.actions()[1]["market"], [["SELL", "CARROT", 1]])
        self.assertEqual(window.current_index, 0)
        self.assertEqual(window.lookahead, 3)

    def test_window_rows_may_bind_future_worker_cardinality_change(self):
        controller = Controller()
        controller.R["main"][2] = {
            "farmer": ["PASS"],
            "hands": [["PASS"], ["PASS"]],
            "market": [],
        }
        window = bind_current_route_window(
            controller,
            observation(0),
            completed_route_id=COMMITTED_ROUTE,
            lookahead=2,
        )
        self.assertIsNotNone(window)
        self.assertEqual([row.worker_cardinality for row in window.rows], [2, 3])
        # B5 only consumes the immediate row and therefore remains current-cardinality bound.
        self.assertIsNotNone(window.b5_witness())

    def test_b5_rejects_immediate_worker_cardinality_change(self):
        controller = Controller()
        controller.R["main"][1]["hands"] = []
        window = bind_current_route_window(
            controller,
            observation(0),
            completed_route_id=COMMITTED_ROUTE,
            lookahead=2,
        )
        self.assertIsNotNone(window)
        self.assertEqual(window.rows[0].worker_cardinality, 1)
        self.assertIsNone(window.b5_witness())
        self.assertIsNone(
            bind_current_route(
                controller, observation(0), completed_route_id=COMMITTED_ROUTE
            )
        )

    def test_committed_route_authority_is_required(self):
        controller = Controller()
        with self.assertRaises(TypeError):
            bind_current_route(controller, observation(0))
        with self.assertRaises(TypeError):
            bind_current_route_window(controller, observation(0), lookahead=1)
        with self.assertRaises(TypeError):
            bind_b5_kwargs(controller, observation(0))

    def test_uncommitted_live_cur_cannot_override_committed_route(self):
        controller = Controller()
        controller.cur = "alt"
        self.assertIsNone(
            bind_current_route(
                controller, observation(0), completed_route_id=COMMITTED_ROUTE
            )
        )
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=2,
            )
        )

    def test_capture_is_detached_from_later_route_mutation(self):
        controller = Controller()
        window = bind_current_route_window(
            controller,
            observation(0),
            completed_route_id=COMMITTED_ROUTE,
            lookahead=2,
        )
        self.assertIsNotNone(window)
        before_digest = window.route_sha256
        controller.R["main"][1]["farmer"][0] = "BROKEN"
        self.assertEqual(window.actions()[0]["farmer"], ["MOVE", "EAST"])
        self.assertEqual(window.route_sha256, before_digest)

    def test_returned_action_is_detached_from_snapshot(self):
        controller = Controller()
        witness = bind_current_route(
            controller, observation(0), completed_route_id=COMMITTED_ROUTE
        )
        self.assertIsNotNone(witness)
        action = witness.next_authored_action()
        action["farmer"][0] = "BROKEN"
        self.assertEqual(controller.R["main"][1]["farmer"], ["MOVE", "EAST"])
        self.assertEqual(witness.next_authored_action()["farmer"], ["MOVE", "EAST"])

    def test_controller_tape_is_not_mutated(self):
        controller = Controller()
        before = copy.deepcopy(controller.R)
        bind_current_route_window(
            controller,
            observation(0),
            completed_route_id=COMMITTED_ROUTE,
            lookahead=3,
        )
        self.assertEqual(controller.R, before)

    def test_b5_adapter_is_exact(self):
        controller = Controller()
        kwargs = bind_b5_kwargs(
            controller, observation(0), completed_route_id=COMMITTED_ROUTE
        )
        self.assertEqual(
            kwargs,
            {
                "next_authored": {"farmer": ["MOVE", "EAST"], "hands": [["WATER"]], "market": []},
                "next_authored_step": 1,
            },
        )

    def test_route_digest_binds_rows_outside_requested_window(self):
        a = Controller()
        b = Controller()
        b.R["main"][3]["farmer"] = ["MOVE", "WEST"]
        wa = bind_current_route_window(
            a, observation(0), completed_route_id=COMMITTED_ROUTE, lookahead=1
        )
        wb = bind_current_route_window(
            b, observation(0), completed_route_id=COMMITTED_ROUTE, lookahead=1
        )
        self.assertIsNotNone(wa)
        self.assertIsNotNone(wb)
        self.assertNotEqual(wa.route_sha256, wb.route_sha256)
        self.assertEqual(wa.rows[0].action_sha256, wb.rows[0].action_sha256)
        self.assertNotEqual(wa.window_sha256, wb.window_sha256)

    def test_lookahead_is_exact_and_bounded(self):
        controller = Controller()
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=True,
            )
        )
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=0,
            )
        )
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=MAX_LOOKAHEAD + 1,
            )
        )
        self.assertIsNotNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=MAX_LOOKAHEAD,
            )
        )

    def test_rejects_non_plain_step(self):
        class IntLike(int):
            pass

        controller = Controller()
        obs = observation(0)
        obs["step"] = IntLike(0)
        self.assertIsNone(
            bind_current_route(controller, obs, completed_route_id=COMMITTED_ROUTE)
        )
        obs["step"] = True
        self.assertIsNone(
            bind_current_route(controller, obs, completed_route_id=COMMITTED_ROUTE)
        )

    def test_rejects_bad_player_and_private_cardinality(self):
        controller = Controller()
        obs = observation(0)
        obs["player"] = True
        self.assertIsNone(
            bind_current_route(controller, obs, completed_route_id=COMMITTED_ROUTE)
        )
        obs = observation(0)
        obs["private"]["inventories"] = [{}]
        self.assertIsNone(
            bind_current_route(controller, obs, completed_route_id=COMMITTED_ROUTE)
        )

    def test_rejects_unknown_or_malformed_route(self):
        controller = Controller()
        controller.cur = "missing"
        self.assertIsNone(
            bind_current_route(controller, observation(0), completed_route_id="missing")
        )
        controller = Controller()
        controller.R["main"] = {"not": "a route"}
        self.assertIsNone(
            bind_current_route(
                controller, observation(0), completed_route_id=COMMITTED_ROUTE
            )
        )

    def test_rejects_malformed_completed_route_identity(self):
        controller = Controller()
        for route_id in (None, "", True, 0):
            with self.subTest(route_id=route_id):
                self.assertIsNone(
                    bind_current_route(
                        controller, observation(0), completed_route_id=route_id
                    )
                )

    def test_rejects_malformed_window_row(self):
        controller = Controller()
        controller.R["main"][2]["farmer"] = []
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=2,
            )
        )
        controller = Controller()
        controller.R["main"][2]["market"] = None
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=2,
            )
        )

    def test_rejects_end_of_route(self):
        controller = Controller()
        self.assertIsNone(
            bind_current_route(
                controller, observation(3), completed_route_id=COMMITTED_ROUTE
            )
        )
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(3),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=1,
            )
        )

    def test_rejects_non_json_route_anywhere_in_snapshot(self):
        controller = Controller()
        controller.R["main"][3]["market"] = [{"bad": object()}]
        # Even a one-row window cannot claim a whole-route digest over unauthenticated bytes.
        self.assertIsNone(
            bind_current_route_window(
                controller,
                observation(0),
                completed_route_id=COMMITTED_ROUTE,
                lookahead=1,
            )
        )

    def test_receipts_exclude_action_bytes_but_bind_digests(self):
        controller = Controller()
        window = bind_current_route_window(
            controller,
            observation(0),
            completed_route_id=COMMITTED_ROUTE,
            lookahead=2,
        )
        self.assertIsNotNone(window)
        receipt = window.receipt()
        self.assertNotIn("action_json", repr(receipt))
        self.assertEqual(receipt["route_sha256"], window.route_sha256)
        self.assertEqual(receipt["window_sha256"], window.window_sha256)
        self.assertEqual(receipt["rows"][0]["action_sha256"], window.rows[0].action_sha256)
        witness = window.b5_witness()
        self.assertIsNotNone(witness)
        self.assertNotIn("next_authored", witness.receipt())
        self.assertEqual(witness.receipt()["route_sha256"], window.route_sha256)


if __name__ == "__main__":
    unittest.main()
