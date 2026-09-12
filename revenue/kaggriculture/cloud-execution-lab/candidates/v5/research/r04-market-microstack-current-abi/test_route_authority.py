# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import unittest

from market_route_authority import (
    CURRENT_CONTROLLER_AUTHORITY_BLOB,
    CURRENT_CONTROLLER_AUTHORITY_PATH,
    CURRENT_ROUTE_AUTHORITY_BLOB,
    CURRENT_ROUTE_AUTHORITY_COMMIT,
    CURRENT_ROUTE_AUTHORITY_PATH,
    EXPECTED_CONTROLLER_STATE_KEYS,
    NO_QUEUE_MODEL,
    bind_market_route_authority,
    validate_market_route_authority,
)
from test_support import action, authority, controller_with_route, observation


class MarketRouteAuthorityTests(unittest.TestCase):
    def test_exact_merged_route_and_controller_sources_are_pinned(self):
        root = Path(__file__).resolve().parent
        route_blob = subprocess.check_output(
            [
                "git",
                "rev-parse",
                f"{CURRENT_ROUTE_AUTHORITY_COMMIT}:{CURRENT_ROUTE_AUTHORITY_PATH}",
            ],
            cwd=root,
            text=True,
        ).strip()
        controller_blob = subprocess.check_output(
            [
                "git",
                "rev-parse",
                f"{CURRENT_ROUTE_AUTHORITY_COMMIT}:{CURRENT_CONTROLLER_AUTHORITY_PATH}",
            ],
            cwd=root,
            text=True,
        ).strip()
        self.assertEqual(route_blob, CURRENT_ROUTE_AUTHORITY_BLOB)
        self.assertEqual(controller_blob, CURRENT_CONTROLLER_AUTHORITY_BLOB)

    def test_binder_consumes_real_current_route_window_and_proves_no_queue(self):
        obs = observation(300)
        future = {301: action(market=[["SELL", "CARROT", 2]])}
        bound = authority(obs, future)
        self.assertEqual(bound.queue_model, NO_QUEUE_MODEL)
        self.assertEqual(bound.controller_state_keys, EXPECTED_CONTROLLER_STATE_KEYS)
        self.assertEqual(bound.queued_commands(), ())
        validated = validate_market_route_authority(
            bound, obs, required_end_step=308
        )
        self.assertIsNotNone(validated)
        actions, receipt = validated
        self.assertEqual(actions[301]["market"], [["SELL", "CARROT", 2]])
        self.assertEqual(receipt["authority_sha256"], bound.authority_sha256)
        self.assertEqual(receipt["window"]["current_step"], 300)
        self.assertEqual(receipt["window"]["route_source"], "installed_controller.R[cur]")

    def test_any_new_controller_instance_state_fails_closed_until_queue_authority_exists(self):
        obs = observation(300)
        controller = controller_with_route()
        controller.pending_commands = []
        self.assertIsNone(bind_market_route_authority(controller, obs, lookahead=8))

    def test_wrong_controller_type_fails_closed(self):
        class OtherAgent:
            pass

        controller = OtherAgent()
        controller.R = {"test-route": [action() for _ in range(720)]}
        controller.cur = "test-route"
        controller._fs = None
        controller._fs_for = None
        self.assertIsNone(bind_market_route_authority(controller, observation(300), lookahead=8))

    def test_nonfinite_data_anywhere_in_full_route_fails_closed(self):
        obs = observation(300)
        controller = controller_with_route()
        controller.R[controller.cur][500]["diagnostic"] = float("inf")
        # The consumer strictly re-verifies the full route even if an older
        # canonical-window producer happens to accept non-finite JSON itself.
        self.assertIsNone(bind_market_route_authority(controller, obs, lookahead=8))

    def test_digest_tamper_is_not_authority(self):
        obs = observation(300)
        bound = authority(obs)
        tampered = replace(bound, authority_sha256="0" * 64)
        self.assertIsNone(
            validate_market_route_authority(tampered, obs, required_end_step=308)
        )

    def test_authority_is_bound_to_public_step_and_worker_cardinality(self):
        obs = observation(300)
        bound = authority(obs)
        self.assertIsNone(
            validate_market_route_authority(bound, observation(301), required_end_step=309)
        )
        changed_workers = observation(300, hands=1, inventories=[{}, {}])
        self.assertIsNone(
            validate_market_route_authority(bound, changed_workers, required_end_step=308)
        )

    def test_route_change_changes_market_authority_digest(self):
        obs = observation(300)
        first = authority(obs, {301: action(market=[["SELL", "CARROT", 2]])})
        second = authority(obs, {301: action(market=[["SELL", "CARROT", 3]])})
        self.assertNotEqual(first.authority_sha256, second.authority_sha256)
        self.assertNotEqual(first.window.route_sha256, second.window.route_sha256)
        self.assertNotEqual(first.window.window_sha256, second.window.window_sha256)


if __name__ == "__main__":
    unittest.main()
