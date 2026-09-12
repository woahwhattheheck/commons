# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest

from current_route_full_snapshot import bind_current_full_route
from v233_v234_current_safe import V233V234SixSheepCurrentSafeABI
from test_v233_v234_current import action, obs


class Controller:
    def __init__(self):
        self.cur = "proposal-not-authority"
        self.R = {
            "committed": [action() for _ in range(719)],
            "proposal-not-authority": [action() for _ in range(719)],
        }


def receipt(observation, route="committed", **updates):
    value = {
        "route_step": observation["step"],
        "last_step": observation["step"],
        "player": observation["player"],
        "route": route,
    }
    value.update(updates)
    return value


class SnapshotIntegrationTests(unittest.TestCase):
    def test_real_receipt_bound_full_snapshot_drives_exact_day12_request(self):
        observation = obs()
        snapshot = bind_current_full_route(
            Controller(),
            observation,
            completed_route_receipt=receipt(observation),
        )
        self.assertIsNotNone(snapshot)
        out = V233V234SixSheepCurrentSafeABI(enabled=True).transform(
            observation, action(), route_snapshot=snapshot
        )
        self.assertEqual(
            out["market"],
            [
                ["BUY_LAND"],
                ["BUY_ANIMAL", "SHEEP", 6],
                ["BUY_PRODUCT", "WHEAT", 6],
                ["HIRE"],
                ["HIRE"],
            ],
        )

    def test_raw_cur_is_not_authority(self):
        self.assertIsNone(bind_current_full_route(Controller(), obs()))

    def test_forged_receipt_fields_fail_closed_at_safe_surface(self):
        observation = obs()
        snapshot = bind_current_full_route(
            Controller(),
            observation,
            completed_route_receipt=receipt(observation),
        )
        self.assertIsNotNone(snapshot)
        baseline = action()
        for field, value in (
            ("route_step", observation["step"] - 1),
            ("last_step", observation["step"] + 1),
            ("player", 1),
            ("route_id", "proposal-not-authority"),
        ):
            with self.subTest(field=field):
                forged = replace(snapshot, **{field: value})
                out = V233V234SixSheepCurrentSafeABI(enabled=True).transform(
                    observation, baseline, route_snapshot=forged
                )
                self.assertEqual(out, baseline)

    def test_stale_or_cross_player_receipt_never_binds_snapshot(self):
        observation = obs()
        controller = Controller()
        for bad in (
            receipt(observation, route_step=observation["step"] - 1, last_step=observation["step"] - 1),
            receipt(observation, route_step=observation["step"], last_step=observation["step"] + 1),
            receipt(observation, player=1),
        ):
            with self.subTest(receipt=bad):
                self.assertIsNone(
                    bind_current_full_route(
                        controller,
                        observation,
                        completed_route_receipt=bad,
                    )
                )


if __name__ == "__main__":
    unittest.main()
