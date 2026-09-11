# SPDX-License-Identifier: Apache-2.0
"""R02 diagnostic-truth contracts promised by the V3 release note.

    python -m unittest -v checks/test_v3_r02.py

The route-bank state keeps both a per-call replacement count (``replaced``) for runtime
diagnostics and an explicit cumulative custody count (``replaced_total``).  These tests
prove a real route switch reports a positive current-turn count, while the following
idempotent turn reports zero without changing route bytes or losing the cumulative total.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r02_route_bank as r02  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402


class _Controller:
    def __init__(self, route):
        self.cur = "MAIN"
        self.R = {self.cur: route}
        self._fs_for = object()


def _tapes():
    return [
        [{"marker": "%d:%d" % (plan, step)} for step in range(719)]
        for plan in range(13)
    ]


class R02DiagnosticTruthTests(unittest.TestCase):
    def test_replaced_is_per_call_while_total_remains_cumulative(self):
        route = [{"marker": "canonical:%d" % step} for step in range(719)]
        tapes = _tapes()
        agent = TitanAgent(Features(r02_route_bank=True))
        agent.controller = _Controller(route)
        agent.diagnostics = {}

        state = r02.install(agent, True, tapes=tapes)
        self.assertEqual(state["replaced"], 719)
        self.assertEqual(state["replaced_total"], 719)
        self.assertEqual(route, tapes[0])

        agent._v3_r02_step({
            "step": r02.ROUTE_STEP,
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]},
        })
        first = dict(agent.diagnostics["v3_r02_step"])
        self.assertEqual(first["plan"], 3)
        self.assertEqual(first["replaced"], 719 - r02.ROUTE_STEP)
        total_after_switch = agent._v3_r02["replaced_total"]
        self.assertEqual(total_after_switch, 719 + (719 - r02.ROUTE_STEP))

        before_noop = deepcopy(route)
        agent._v3_r02_step({
            "step": r02.ROUTE_STEP + 1,
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]},
        })
        second = agent.diagnostics["v3_r02_step"]
        self.assertEqual(second["plan"], 3)
        self.assertEqual(second["replaced"], 0)
        self.assertEqual(agent._v3_r02["replaced_total"], total_after_switch)
        self.assertEqual(route, before_noop)


if __name__ == "__main__":
    unittest.main(verbosity=2)
