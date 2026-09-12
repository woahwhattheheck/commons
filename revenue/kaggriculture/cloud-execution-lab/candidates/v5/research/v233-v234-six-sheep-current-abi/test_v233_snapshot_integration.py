# SPDX-License-Identifier: Apache-2.0
import unittest

from current_route_full_snapshot import bind_current_full_route
from v233_v234_current import V233V234SixSheepCurrentABI
from test_v233_v234_current import action, obs


class Controller:
    def __init__(self):
        self.cur = "proposal-not-authority"
        self.R = {
            "committed": [action() for _ in range(719)],
            "proposal-not-authority": [action() for _ in range(719)],
        }


class SnapshotIntegrationTests(unittest.TestCase):
    def test_real_committed_full_snapshot_drives_exact_day12_request(self):
        observation = obs()
        snapshot = bind_current_full_route(
            Controller(), observation, completed_route_id="committed"
        )
        self.assertIsNotNone(snapshot)
        out = V233V234SixSheepCurrentABI(enabled=True).transform(
            observation, action(), route_snapshot=snapshot
        )
        self.assertEqual(
            out["market"],
            [["BUY_LAND"], ["BUY_ANIMAL", "SHEEP", 6], ["BUY_PRODUCT", "WHEAT", 6], ["HIRE"], ["HIRE"]],
        )

    def test_raw_cur_is_not_authority(self):
        self.assertIsNone(bind_current_full_route(Controller(), obs()))


if __name__ == "__main__":
    unittest.main()
