# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zlib

import prefix_route


class PrefixRouteTests(unittest.TestCase):
    def _source_arm(self, root: Path, maximum: int = 30) -> Path:
        tape = {
            str(step): {
                "signature": {"hands": 1, "quadrants": 1},
                "action": {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
            }
            for step in range(maximum + 1)
        }
        raw = json.dumps(tape, sort_keys=True, separators=(",", ":")).encode()
        packed = base64.b85encode(zlib.compress(raw, 9)).decode("ascii")
        source = root / "source.py"
        source.write_text(
            "\n".join([
                "ARM_ID = 'fixture--post24_full'",
                "SOURCE_EPISODE = '1'",
                "SOURCE_TEAM = 'fixture'",
                "SOURCE_SEAT = 0",
                "SOURCE_REWARD = 1.0",
                "SOURCE_SHA256 = 'source'",
                f"TAPE_SHA256 = {hashlib.sha256(raw).hexdigest()!r}",
                f"_PACKED = {packed!r}",
                "",
            ]),
            encoding="utf-8",
        )
        return source

    def _baseline(self, root: Path) -> Path:
        path = root / "baseline.py"
        path.write_text(
            "calls = []\n"
            "def agent(obs, configuration=None):\n"
            "    calls.append(obs['step'])\n"
            "    return {'farmer':['PASS'], 'hands':[['PASS']], 'market':[]}\n",
            encoding="utf-8",
        )
        return path

    def _runtime(self, root: Path) -> Path:
        """Minimal contract fixture; the hosted workflow separately binds the real parent runtime."""
        path = root / "runtime.py"
        path.write_text(
            "class LeaderRoutePolicy:\n"
            "    def __init__(self, baseline_agent, tape, *, mode, start_step=24):\n"
            "        self._baseline_agent = baseline_agent\n"
            "        self._tape = {int(k): v for k, v in tape.items()}\n"
            "        self.mode = mode\n"
            "        self.start_step = start_step\n"
            "        self.active = True\n"
            "        self.handoff_step = None\n"
            "        self.activation_steps = []\n"
            "    def agent(self, obs, configuration=None):\n"
            "        step = obs['step']\n"
            "        if step == 0:\n"
            "            self.active = True\n"
            "            self.handoff_step = None\n"
            "            self.activation_steps = []\n"
            "        base = self._baseline_agent(obs, configuration)\n"
            "        if not self.active or step < self.start_step:\n"
            "            return base\n"
            "        entry = self._tape.get(step)\n"
            "        if entry is None:\n"
            "            self.active = False\n"
            "            if self.handoff_step is None:\n"
            "                self.handoff_step = step\n"
            "            return base\n"
            "        candidate = entry['action']\n"
            "        if candidate != base:\n"
            "            self.activation_steps.append(step)\n"
            "        return candidate\n"
            "    def diagnostics(self):\n"
            "        return {'mode': self.mode, 'start_step': self.start_step,\n"
            "                'active': self.active, 'handoff_step': self.handoff_step,\n"
            "                'activation_count': len(self.activation_steps),\n"
            "                'activation_steps': list(self.activation_steps)}\n",
            encoding="utf-8",
        )
        return path

    def test_build_is_deterministic_and_truncates_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source_arm(root)
            baseline = self._baseline(root)
            runtime = self._runtime(root)
            outputs = []
            for index in range(2):
                output = root / f"prefix-{index}.py"
                receipt = root / f"receipt-{index}.json"
                result = prefix_route.build_prefix(
                    source_arm=source,
                    runtime=runtime,
                    baseline_entry=baseline,
                    cutoff=27,
                    output=output,
                    receipt=receipt,
                )
                outputs.append(output.read_bytes())
                self.assertEqual(result["first_omitted_step"], 28)
                self.assertEqual(result["retained_steps"], 28)
                self.assertEqual(result["removed_steps"], 3)
            self.assertEqual(outputs[0], outputs[1])
            tree = ast.parse(outputs[0].decode())
            packed = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "_PACKED")
            tape = json.loads(zlib.decompress(base64.b85decode(packed.encode())).decode())
            self.assertEqual(sorted(map(int, tape)), list(range(28)))

    def test_generated_arm_hands_back_on_first_missing_row(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source_arm(root)
            baseline = self._baseline(root)
            runtime = self._runtime(root)
            output = root / "prefix.py"
            prefix_route.build_prefix(
                source_arm=source,
                runtime=runtime,
                baseline_entry=baseline,
                cutoff=27,
                output=output,
                receipt=root / "receipt.json",
            )
            spec = importlib.util.spec_from_file_location("prefix_fixture", output)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            obs = lambda step: {"step": step, "player": 0, "farms": [{"hands": [[0, 0]], "unlocked_quadrants": [0]}]}
            for step in range(29):
                module.agent(obs(step), {"maxMarketOrdersPerTurn": 10})
            self.assertEqual(module.diagnostics()["handoff_step"], 28)
            self.assertFalse(module.diagnostics()["active"])
            self.assertEqual(module._baseline.calls, list(range(29)))

    def test_source_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(prefix_route.PrefixRouteError):
                prefix_route.decode_source_arm(self._source_arm(root), expected_python_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
