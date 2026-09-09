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


def _seller_public(step, player=0, marker=1):
    farms = [{"tiles": []}, {"tiles": []}]
    farms[1 - int(player)] = {
        "tiles": [[{"kind": "PLANT", "crop": "MILK", "yield_units": marker}]]
    }
    return {"step": int(step), "player": int(player), "farms": farms}


class _Features:
    def __init__(self, budget_seconds=0.04, reserve_seconds=0.015):
        self.budget_seconds = budget_seconds
        self.reserve_seconds = reserve_seconds
        self.consumer = "frozen"


class _Instance:
    def __init__(self, *, duration, route=None, ready=True, commit_before_delay=False):
        self.features = _Features()
        self.duration = duration
        self.commit_before_delay = commit_before_delay
        self.ready = ready
        self.controller_cur = route or "MAIN"
        self._completed_route = route
        self._completed_seller_state = {
            "planned": {"MILK": [[361, 2]]},
            "pending": {"MILK": 2},
            "previous": _seller_public(359, marker=360),
            "observed_harvests": {"MILK": [[359, 1]]},
        } if route else None
        self._seller_fallback_observations = []
        self.replayed = []
        self.remember_calls = 0
        self.selected = None
        self.post = None
        self.diagnostics = {}

    def _remember_seller_fallback(self, observation):
        self.remember_calls += 1
        row = _seller_public(
            int(observation["step"]), int(observation.get("player", 0)),
            marker=int(observation["step"]) + 1,
        )
        if self._seller_fallback_observations and int(self._seller_fallback_observations[-1]["step"]) == row["step"]:
            self._seller_fallback_observations[-1] = row
        else:
            self._seller_fallback_observations.append(row)

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
        if self.commit_before_delay:
            step = int(observation["step"])
            self._completed_route = self.controller_cur
            self._completed_seller_state = {
                "planned": {"MILK": [[step + 1, 2]]},
                "pending": {"MILK": 2},
                "previous": _seller_public(step, marker=step + 1),
                "observed_harvests": {"MILK": [[step, 1]]},
            }
            self._seller_fallback_observations = []
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
        "farms": [{"hands": [], "tiles": []}, {"hands": [], "tiles": [[{"kind": "PLANT"}]]}],
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

    def test_real_entrypoint_does_not_requeue_a_completed_current_checkpoint(self):
        main = _load_main("checkpointed")
        old = _Instance(
            duration=0.08, route="YARN_CARROT", commit_before_delay=True
        )
        fresh = _Instance(duration=0, ready=False)
        main._INSTANCE = old
        main._new_instance = lambda _root, _features: fresh
        carrier = RECOVERY.RecoveryCarrier(main)

        first = carrier.agent(_obs(360), {"episodeSteps": 720})
        self.assertEqual(first["market"][0][1], "YARN_CARROT")
        self.assertIsNone(main._INSTANCE)
        self.assertEqual(carrier.last_report["status"], "captured")
        self.assertEqual(carrier.last_report["public_observation"], "checkpointed")
        self.assertEqual(old.remember_calls, 0)

        second = carrier.agent(_obs(361), {"episodeSteps": 720})
        self.assertEqual(second["market"][0][1], "YARN_CARROT")
        self.assertEqual(fresh.replayed, [])
        self.assertEqual(fresh._completed_seller_state["previous"]["step"], 360)

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
