# SPDX-License-Identifier: Apache-2.0
"""Exercise the candidate through the repository's real canonical main.py."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

SPEC = importlib.util.spec_from_file_location("_mnemosyne_recovery_integration", HERE / "recovery_main.py")
RECOVERY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RECOVERY)


class _Features:
    def __init__(self, budget_seconds=0.04, reserve_seconds=0.015):
        self.budget_seconds = budget_seconds
        self.reserve_seconds = reserve_seconds
        self.consumer = "frozen"


class _Instance:
    def __init__(self, *, duration, route=None, ready=True):
        self.features = _Features()
        self.duration = duration
        self.ready = ready
        self.controller_cur = route or "MAIN"
        self._completed_route = route
        self._completed_seller_state = {
            "planned": {"MILK": [[361, 2]]},
            "pending": {"MILK": 2},
            "previous": {"step": 359},
            "observed_harvests": {"MILK": [[359, 1]]},
        } if route else None
        self._seller_fallback_observations = []
        self.replayed = []
        self.selected = None
        self.post = None
        self.diagnostics = {}

    def _remember_seller_fallback(self, observation):
        self._seller_fallback_observations.append(deepcopy(dict(observation)))

    def act(self, observation, _configuration=None, *, entry_started=None):
        if not self.ready:
            self.controller_cur = self._completed_route or "MAIN"
            self.replayed = [int(row["step"]) for row in self._seller_fallback_observations]
            self.ready = True
        self.selected = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["ROUTE", self.controller_cur, int(observation["step"])]],
        }
        end = time.perf_counter() + self.duration
        while time.perf_counter() < end:
            pass
        return deepcopy(self.selected)


def _load_main(label):
    name = f"_mnemosyne_current_main_{label}"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _obs(step):
    return {
        "step": step,
        "player": 0,
        "farms": [{"hands": []}, {"hands": []}],
        "private": {},
    }


@unittest.skipUnless((ROOT / "main.py").is_file() and (ROOT / "titan_runtime.py").is_file(),
                     "repository canonical source is not present in standalone staging")
class CurrentEntrypointIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

    def test_real_predecessor_discards_route_and_public_fallback(self):
        main = _load_main("predecessor")
        old = _Instance(duration=0.08, route="YARN_CARROT")
        fresh = _Instance(duration=0, ready=False)
        main._INSTANCE = old
        main._new_instance = lambda _root, _features: fresh

        first = main.agent(_obs(360), {"episodeSteps": 720})
        self.assertEqual(first["market"][0][1], "YARN_CARROT")
        self.assertIsNone(main._INSTANCE)
        self.assertEqual(old._seller_fallback_observations, [])

        second = main.agent(_obs(361), {"episodeSteps": 720})
        self.assertEqual(second["market"][0][1], "MAIN")
        self.assertEqual(fresh.replayed, [])

    def test_real_entrypoint_with_carrier_restores_only_committed_state(self):
        main = _load_main("candidate")
        old = _Instance(duration=0.08, route="YARN_CARROT")
        fresh = _Instance(duration=0, ready=False)
        fresh.history = {"unsafe": "fresh"}
        main._INSTANCE = old
        main._new_instance = lambda _root, _features: fresh
        carrier = RECOVERY.RecoveryCarrier(main)

        first = carrier.agent(_obs(360), {"episodeSteps": 720})
        self.assertEqual(first["market"][0][1], "YARN_CARROT")
        self.assertIsNone(main._INSTANCE)
        self.assertEqual(carrier.last_report["status"], "captured")

        # This uncommitted field must not cross the discarded-object boundary.
        old.history = {"unsafe": "corrupt"}
        second = carrier.agent(_obs(361), {"episodeSteps": 720})
        self.assertEqual(second["market"][0][1], "YARN_CARROT")
        self.assertEqual(fresh.replayed, [360])
        self.assertEqual(fresh._completed_seller_state["pending"], {"MILK": 2})
        self.assertEqual(fresh.history, {"unsafe": "fresh"})
        self.assertEqual(carrier.last_report["status"], "restored")


if __name__ == "__main__":
    unittest.main()
