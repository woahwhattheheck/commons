# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from land_admission import BUY_LAND, patch_routes, wrap


def route(length=110):
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(length)]


class PatchRoutesTests(unittest.TestCase):
    def test_adds_only_expected_steps(self):
        routes = {"MAIN": route()}
        before = copy.deepcopy(routes)
        receipt = patch_routes(routes)
        self.assertEqual(receipt["activations"], 2)
        self.assertEqual(routes["MAIN"][74]["market"], [[BUY_LAND]])
        self.assertEqual(routes["MAIN"][98]["market"], [[BUY_LAND]])
        for index, row in enumerate(routes["MAIN"]):
            if index not in (74, 98):
                self.assertEqual(row, before["MAIN"][index])

    def test_idempotent_on_existing_land(self):
        routes = {"MAIN": route()}
        first = patch_routes(routes)
        second = patch_routes(routes)
        self.assertEqual(first["activations"], 2)
        self.assertEqual(second["activations"], 0)
        self.assertEqual(second["existing"], 2)

    def test_preserves_full_market_and_short_route(self):
        routes = {
            "FULL": route(),
            "SHORT": route(20),
        }
        routes["FULL"][74]["market"] = [["SELL", "WHEAT", 1]] * 10
        receipt = patch_routes(routes)
        self.assertEqual(receipt["full"], 1)
        self.assertEqual(receipt["out_of_range"], 2)
        self.assertEqual(receipt["activations"], 1)
        self.assertNotIn([BUY_LAND], routes["FULL"][74]["market"])

    def test_shared_row_converts_once(self):
        shared = {"farmer": ["PASS"], "hands": [], "market": []}
        first = route()
        second = route()
        first[74] = shared
        second[74] = shared
        receipt = patch_routes({"A": first, "B": second}, steps=(74,))
        self.assertEqual(receipt["activations"], 1)
        self.assertEqual(receipt["existing"], 1)
        self.assertEqual(shared["market"], [[BUY_LAND]])

    def test_wrap_installs_after_original_initialize_once(self):
        class Controller:
            R = {"MAIN": route()}

        class Agent:
            def __init__(self):
                self.controller = Controller()
                self.initializations = 0

            def _initialize(self):
                self.initializations += 1

        agent = wrap(Agent())
        self.assertIs(wrap(agent), agent)
        agent._initialize()
        agent._initialize()
        self.assertEqual(agent.initializations, 2)
        self.assertEqual(
            agent._land_admission_state["receipt"]["activations"],
            2,
        )
        self.assertEqual(agent.controller.R["MAIN"][74]["market"], [[BUY_LAND]])


if __name__ == "__main__":
    unittest.main()
