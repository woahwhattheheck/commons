#!/usr/bin/env python3
"""Exact derivation and executable fallback contracts for SOL-TERMINUS."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


patcher = _load("_terminus_candidate_patch", HERE / "terminal_deadline_patch.py")
CONTROL = Path(os.environ["TITAN_TERMINUS_CONTROL"]).resolve()
CANDIDATE = Path(os.environ["TITAN_TERMINUS_CANDIDATE"]).resolve()
MANIFEST = Path(os.environ["TITAN_TERMINUS_MANIFEST"]).resolve()


def _configuration() -> dict[str, int]:
    return {
        "episodeSteps": 720,
        "turnsPerDay": 24,
        "boardSize": 10,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
    }


def _observation(step: int) -> dict[str, object]:
    tiles = [[None for _ in range(10)] for _ in range(10)]
    farm0 = {
        "farmer": [4, 4],
        "hands": [[0, 0]],
        "tiles": copy.deepcopy(tiles),
        "money": 500,
        "hires_today": 1,
        "unlocked_quadrants": ["NW"],
    }
    farm1 = {
        "farmer": [0, 0],
        "hands": [],
        "tiles": copy.deepcopy(tiles),
        "money": 500,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    return {
        "step": step,
        "player": 0,
        "farms": [farm0, farm1],
        "private": {
            "shed": {"WHEAT": 4, "MILK": 1},
            "inventories": [{"CARROT": 2}, {"EGG": 1}],
            "seeds": {},
        },
        "market": {"inventory": {}, "prices": {}, "params": {}},
        "town": {"unlocked_shops": []},
    }


RAW_SELECTED = {
    "farmer": ["EAST"],
    "hands": [["PASS"]],
    "market": [["BUY_SEED", "MELON", 1]],
}


def _sales(action: dict[str, object]) -> dict[str, int]:
    return {
        row[1]: row[2]
        for row in action.get("market", [])
        if isinstance(row, list) and len(row) == 3 and row[0] == "SELL"
    }


class DerivationTests(unittest.TestCase):
    def test_manifest_binds_exact_two_source_preimages(self) -> None:
        receipt = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(receipt["operation"], patcher.OPERATION)
        self.assertEqual(receipt["base_commit"], patcher.BASE_COMMIT)
        self.assertEqual(receipt["changed_paths"], ["main.py", "titan_runtime.py"])
        self.assertEqual(receipt["before_git_blobs"], patcher.EXPECTED_BLOBS)
        self.assertFalse(receipt["canonical_runtime_mutated"])
        self.assertFalse(receipt["provider_or_submission_action"])
        self.assertFalse(receipt["score_or_promotion_claim"])

    def test_candidate_is_exact_one_factor_derivation(self) -> None:
        expected_main = patcher.patch_main(
            (CONTROL / "main.py").read_text(encoding="utf-8")
        )
        expected_runtime = patcher.patch_runtime(
            (CONTROL / "titan_runtime.py").read_text(encoding="utf-8")
        )
        self.assertEqual(
            (CANDIDATE / "main.py").read_text(encoding="utf-8"), expected_main
        )
        self.assertEqual(
            (CANDIDATE / "titan_runtime.py").read_text(encoding="utf-8"),
            expected_runtime,
        )

    def test_wrong_preimage_fails_before_any_second_file_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lab = Path(temporary)
            shutil.copy2(CONTROL / "main.py", lab / "main.py")
            shutil.copy2(CONTROL / "titan_runtime.py", lab / "titan_runtime.py")
            (lab / "main.py").write_bytes((lab / "main.py").read_bytes() + b"# drift\n")
            before_main = (lab / "main.py").read_bytes()
            before_runtime = (lab / "titan_runtime.py").read_bytes()
            with self.assertRaises(patcher.CandidateError):
                patcher.apply_candidate(lab)
            self.assertEqual((lab / "main.py").read_bytes(), before_main)
            self.assertEqual((lab / "titan_runtime.py").read_bytes(), before_runtime)

    def test_reapplication_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lab = Path(temporary)
            shutil.copy2(CANDIDATE / "main.py", lab / "main.py")
            shutil.copy2(CANDIDATE / "titan_runtime.py", lab / "titan_runtime.py")
            with self.assertRaises(patcher.CandidateError):
                patcher.apply_candidate(lab)


class RuntimeFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(CANDIDATE))
        cls.runtime = _load("_terminus_candidate_runtime", CANDIDATE / "titan_runtime.py")
        cls.entrypoint = _load("_terminus_candidate_entrypoint", CANDIDATE / "main.py")

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            sys.path.remove(str(CANDIDATE))
        except ValueError:
            pass

    def _deadline_agent(self, step: int):
        runtime = self.runtime
        expiry = runtime.deadline.DeadlineExceeded("forced selected-transform expiry")

        class FakeTimer:
            def __init__(self, _seconds: float):
                self.expired = expiry

            def __enter__(self):
                return self

            def __exit__(self, _kind, _error, _traceback):
                return False

        original_timer = runtime.deadline._DeadlineTimer
        runtime.deadline._DeadlineTimer = FakeTimer
        self.addCleanup(setattr, runtime.deadline, "_DeadlineTimer", original_timer)

        agent = runtime.TitanAgent(
            runtime.Features(consumer="parent", budget_seconds=1.0, reserve_seconds=0.0)
        )
        agent.ready = True
        agent.consumer = types.SimpleNamespace(
            selected_post_units=None, selected_post_units_binding=None
        )
        agent.controller = types.SimpleNamespace(cur="route-a")
        agent.production = types.SimpleNamespace(act=lambda _obs: copy.deepcopy(RAW_SELECTED))

        def expire_transform(_obs, _cfg, _selected):
            raise expiry

        agent.transform_selected = expire_transform
        return agent.act(_observation(step), _configuration())

    def test_inner_terminal_transform_expiry_keeps_liquidation(self) -> None:
        result = self._deadline_agent(718)
        expected = self.runtime.deadline.terminal_liquidation_fallback(
            _observation(718), _configuration()
        )
        self.assertEqual(result, expected)
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(result["hands"], [["PASS"]])
        self.assertEqual(_sales(result), {"WHEAT": 4, "MILK": 1, "CARROT": 2})
        self.assertNotEqual(result, RAW_SELECTED)

    def test_inner_nonterminal_transform_expiry_keeps_selected_behavior(self) -> None:
        self.assertEqual(self._deadline_agent(717), RAW_SELECTED)

    def test_outer_terminal_finalization_fallback_overrides_selected(self) -> None:
        instance = types.SimpleNamespace(selected=copy.deepcopy(RAW_SELECTED))
        result = self.entrypoint._entrypoint_fallback(
            instance, _observation(718), _configuration(), self.runtime.deadline
        )
        self.assertEqual(
            result,
            self.runtime.deadline.terminal_liquidation_fallback(
                _observation(718), _configuration()
            ),
        )
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(_sales(result), {"WHEAT": 4, "MILK": 1, "CARROT": 2})

    def test_outer_nonterminal_fallback_keeps_deepcopied_selected(self) -> None:
        selected = copy.deepcopy(RAW_SELECTED)
        instance = types.SimpleNamespace(selected=selected)
        result = self.entrypoint._entrypoint_fallback(
            instance, _observation(717), _configuration(), self.runtime.deadline
        )
        self.assertEqual(result, RAW_SELECTED)
        self.assertIsNot(result, selected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
