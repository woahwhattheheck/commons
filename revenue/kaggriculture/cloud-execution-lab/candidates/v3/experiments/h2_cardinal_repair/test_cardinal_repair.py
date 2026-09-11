# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
H2 = V3 / "experiments" / "h2_terminal_last_hop"
OVERLAY = V3 / "overlay"
for path in (H2, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as base  # noqa: E402
import r04_h2_terminal_last_hop as h2  # noqa: E402
import test_h2_terminal_last_hop as parent_tests  # noqa: E402


class H2CardinalRepairTests(unittest.TestCase):
    def test_frozen_walk_returns_literal_cardinal_opcode(self):
        self.assertEqual(base._v219_walk((4, 3), (4, 4)), ["SOUTH"])

    def test_real_cardinal_last_hop_activates(self):
        act = parent_tests.action()
        obs = parent_tests.observation(farmer=(4, 3), inventories=[{"MILK": 3}])
        out, actor, units = h2.rescue_last_hop(
            act, obs, parent_tests.STANDARD_CONFIG, enabled=True
        )
        self.assertEqual(out["farmer"], ["SOUTH"])
        self.assertEqual((actor, units), (0, 3))
        self.assertEqual(act["farmer"], ["PASS"])

    def test_every_real_cardinal_other_worker_move_fails_closed(self):
        for opcode in sorted(h2.CARDINAL_MOVES):
            with self.subTest(opcode=opcode):
                act = parent_tests.action(hands=((opcode,),))
                obs = parent_tests.observation(
                    farmer=(4, 3),
                    hands=((0, 0),),
                    inventories=[{"MILK": 3}, {}],
                )
                out, actor, units = h2.rescue_last_hop(
                    act, obs, parent_tests.STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))


if __name__ == "__main__":
    unittest.main()
