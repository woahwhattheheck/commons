#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Literal predecessor killer for PR #12153's swallowed-L01 composition failure.

The predecessor fixture is loaded from the exact reviewed old Git commit rather
than retyped here.  The paired successor probe reuses the current carrier's own
executable helpers, so one test file proves the old fail-open state and the new
fail-closed state with the same injected L01 failure class.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[5]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_apply_repair as successor  # noqa: E402

PREDECESSOR_HEAD = "abb32c2bc8b6f5907b218b8febe273ccd7c65002"
PREDECESSOR_CARRIER_BLOB = "3613982a364fee67b9fbfbebb81c0e66c9f37934"
CARRIER_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/repairs/"
    "titan-v3-l01-r02-composition-preservation/apply_repair.py"
)


def _git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _predecessor_source() -> str:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{PREDECESSOR_HEAD}:{CARRIER_PATH}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    self_bytes = proc.stdout
    actual = _git_blob_sha(self_bytes)
    if actual != PREDECESSOR_CARRIER_BLOB:
        raise AssertionError(f"predecessor carrier drift: {actual}")
    return self_bytes.decode("utf-8")


def _decode(fragment: str) -> str:
    tree = ast.parse("VALUE = (\n" + fragment + ")\n")
    return ast.literal_eval(tree.body[0].value)


def _predecessor_probe_class():
    source = _predecessor_source()
    namespace = {"__name__": "pr12153_predecessor_apply_repair"}
    exec(compile(source, f"{PREDECESSOR_HEAD}:{CARRIER_PATH}", "exec"), namespace)
    method = _decode(namespace["R02_METHOD_NEW"])
    generated = {}
    exec("class Probe:\n" + method, generated)
    return generated["Probe"]


class _OldFeatures:
    r02_route_bank = True
    l01_land = True
    l01_sheep = False
    l01_day0buy = False
    l01_leanplant = False


class _OldController:
    def __init__(self):
        self.R = {"MAIN": [{"tag": "l01_patched"}]}


class ExactPredecessorKillerTests(unittest.TestCase):
    def test_exact_old_head_fails_open_but_successor_rolls_back(self):
        # Exact reviewed predecessor: R02 commits raw tail; swallowed L01 error
        # returns normally; old caller then records l01_reapplied=True.
        old_probe = _predecessor_probe_class()
        old = old_probe()
        old.features = _OldFeatures()
        old.controller = _OldController()
        old.diagnostics = {}
        old._v3_r02 = {"plan": 0, "endgame": False, "replaced": 10}

        def swallowed_l01_error():
            old.diagnostics["v3_l01"] = {
                "activations": {},
                "reasons": ["V3_L01_ERROR_RuntimeError"],
            }
            return None

        old._v3_l01_install = swallowed_l01_error
        r02 = types.ModuleType("r02_route_bank")

        def predecessor_step(agent, _obs, enabled):
            self.assertTrue(enabled)
            agent.controller.R["MAIN"][:] = [{"tag": "raw_r02_tail"}]
            agent._v3_r02 = {"plan": 1, "endgame": False, "replaced": 15}
            return agent._v3_r02

        r02.step = predecessor_step
        with patch.dict(sys.modules, {"r02_route_bank": r02}):
            old._v3_r02_step({"step": 144})

        self.assertEqual(old.controller.R["MAIN"], [{"tag": "raw_r02_tail"}])
        self.assertEqual(old.diagnostics["v3_l01"]["reasons"], ["V3_L01_ERROR_RuntimeError"])
        self.assertEqual(old.diagnostics["v3_r02_step"]["replaced"], 15)
        self.assertTrue(old.diagnostics["v3_r02_step"]["l01_reapplied"])

        # Current successor: the same L01 failure is inside the transaction,
        # so R02 is never installed and rollback/fallback truth is explicit.
        new = successor._agent()
        modules, calls = successor._fake_modules(fail_l01=True)
        with patch.dict(sys.modules, modules):
            new._v3_route_install()

        self.assertEqual(calls, ["patch_tapes", "install_l01"])
        self.assertIsNone(new._v3_r02)
        self.assertEqual(new.controller.R["MAIN"][0]["tag"], "canonical")
        self.assertTrue(new.controller.R["MAIN"][0]["fallback_l01"])
        report = new.diagnostics["v3_l01_r02"]
        self.assertFalse(report["composed"])
        self.assertTrue(report["rolled_back"])
        self.assertFalse(report["r02_installed"])
        self.assertEqual(report["error"], "RuntimeError")


if __name__ == "__main__":
    unittest.main(verbosity=2)
