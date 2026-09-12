# SPDX-License-Identifier: Apache-2.0
"""Replay/reset regression for the pinned terminal composition entrypoint."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "reference" / "titan-current" / "terminal_composition.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_terminal_composition_replay", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeTerminalSell:
    next_identity = 0
    failures = set()

    def __init__(self):
        type(self).next_identity += 1
        self.identity = type(self).next_identity

    def act(self, observation, configuration=None):
        del configuration
        step = int(observation.get("step", 0))
        key = (self.identity, step)
        if key in type(self).failures:
            type(self).failures.remove(key)
            raise RuntimeError("synthetic terminal failure")
        return {"instance": self.identity, "step": step}


class TerminalCompositionReplayTest(unittest.TestCase):
    def setUp(self):
        _FakeTerminalSell.next_identity = 0
        _FakeTerminalSell.failures = set()

    def test_same_step_replay_reuses_completed_instance_and_rewind_resets(self):
        module = _load_module()
        module.TerminalSell = _FakeTerminalSell
        module._INSTANCE = None
        module._LAST_STEP = None

        self.assertEqual(module.agent({"step": 0}), {"instance": 1, "step": 0})
        self.assertEqual(module.agent({"step": 0}), {"instance": 1, "step": 0})
        self.assertEqual(module.agent({"step": 2}), {"instance": 1, "step": 2})
        self.assertEqual(module.agent({"step": 2}), {"instance": 1, "step": 2})

        self.assertEqual(module.agent({"step": 1}), {"instance": 2, "step": 1})
        self.assertEqual(module.agent({"step": 1}), {"instance": 2, "step": 1})

    def test_failed_rewind_does_not_publish_replay_boundary(self):
        module = _load_module()
        module.TerminalSell = _FakeTerminalSell
        module._INSTANCE = None
        module._LAST_STEP = None

        self.assertEqual(module.agent({"step": 1}), {"instance": 1, "step": 1})
        _FakeTerminalSell.failures.add((2, 0))
        with self.assertRaisesRegex(RuntimeError, "synthetic terminal failure"):
            module.agent({"step": 0})

        self.assertEqual(module._LAST_STEP, 1)
        self.assertEqual(module.agent({"step": 0}), {"instance": 3, "step": 0})


if __name__ == "__main__":
    unittest.main()
