# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import unittest
from unittest import mock

import build_route_matrix as builder


ROUTER = b'''ROUTE_STEP = 144
FINAL_PLAN_STEP = 648
SHOP_PLANS = {("A", "B"): 3}

class State:
    plan = 0

def choose(state, observation, step):
    if step == ROUTE_STEP:
        shops = observation["town"]["unlocked_shops"]
        state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)
    if step == FINAL_PLAN_STEP:
        state.plan = 2
    return state.plan
'''


class BuildRouteMatrixTests(unittest.TestCase):
    def _build(
        self,
        plan_index=7,
        *,
        selection_step=builder.ROUTE_STEP,
        candidate_sha=None,
        router_sha=None,
    ):
        baseline = {
            "main.py": b"entry\n",
            "r04_full_router.py": ROUTER,
            "TITAN-CONFIG.json": b"{}\n",
        }
        expected_candidate = builder.digest(builder.archive_bytes(baseline))
        expected_router = builder.digest(ROUTER)
        if candidate_sha is None:
            candidate_sha = expected_candidate
        if router_sha is None:
            router_sha = expected_router
        with (
            mock.patch.object(builder, "members", side_effect=({"v31": b"x"}, {"delivery": b"y"})),
            mock.patch.object(builder, "compose", return_value=dict(baseline)),
            mock.patch.object(builder.Path, "read_bytes", return_value=b"overlay\n"),
            mock.patch.object(builder, "CANDIDATE_SHA", candidate_sha),
            mock.patch.object(builder, "ROUTER_SHA256", router_sha),
        ):
            result = builder.build(
                Path("v31.tar.gz"),
                Path("delivery.tar.gz"),
                plan_index,
                selection_step,
            )
        return baseline, result

    def test_exact_baseline_changes_only_router(self):
        baseline, (files, before, after) = self._build(9)
        self.assertEqual(before, ROUTER)
        self.assertNotEqual(after, before)
        self.assertEqual(set(files), set(baseline))
        self.assertEqual(files["main.py"], baseline["main.py"])
        self.assertEqual(files["TITAN-CONFIG.json"], baseline["TITAN-CONFIG.json"])
        self.assertEqual(files["r04_full_router.py"], after)
        self.assertIn(b"state.plan = 9\n", after)
        self.assertIn(b"if step == FINAL_PLAN_STEP:\n        state.plan = 2", after)

    def test_terminal_matrix_changes_only_terminal_rhs(self):
        baseline, (files, before, after) = self._build(
            9, selection_step=builder.FINAL_PLAN_STEP
        )
        self.assertEqual(before, ROUTER)
        self.assertNotEqual(after, before)
        self.assertEqual(set(files), set(baseline))
        self.assertEqual(files["main.py"], baseline["main.py"])
        self.assertIn(
            b'state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)',
            after,
        )
        self.assertIn(
            b"if step == FINAL_PLAN_STEP:\n        state.plan = 9",
            after,
        )

    def test_terminal_plan2_is_exact_production_control(self):
        baseline, (files, before, after) = self._build(
            builder.TERMINAL_PLAN,
            selection_step=builder.FINAL_PLAN_STEP,
        )
        self.assertEqual(before, ROUTER)
        self.assertEqual(after, ROUTER)
        self.assertEqual(files, baseline)

    def test_rejects_invalid_selection_step(self):
        with self.assertRaisesRegex(ValueError, "selection_step"):
            self._build(9, selection_step=647)

    def test_rejects_production_v3_archive_drift(self):
        with self.assertRaisesRegex(ValueError, "baseline identity drift"):
            self._build(candidate_sha="0" * 64)

    def test_rejects_router_identity_drift(self):
        with self.assertRaisesRegex(ValueError, "router identity drift"):
            self._build(router_sha="0" * 64)


if __name__ == "__main__":
    unittest.main()
