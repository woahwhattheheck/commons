# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zlib

from certified_prefix import (
    CertifiedPrefixError,
    build_certified_prefix,
    decode_prefix_arm,
)
from certified_route_runtime import prestate_certificate

HERE = Path(__file__).resolve().parent


def cfg():
    return {
        "boardSize": 10,
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
        "marketParams": None,
    }


def farm(money=100):
    return {
        "money": money,
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "tiles": [],
        "farmer": {"location": [0, 0], "inventory": []},
    }


def obs(step, player=0):
    return {
        "step": step,
        "day": step // 24,
        "player": player,
        "farms": [farm(100 + step), farm(50)],
        "private": {"shed": {"WHEAT": step}, "seeds": {}},
        "market": {"inventory": {"WHEAT": 10000 - step}, "shops": []},
    }


def action(step):
    return {
        "farmer": ["MOVE", "EAST"] if step >= 24 else ["PASS"],
        "hands": [],
        "market": [["SELL", "WHEAT", 1]] if step >= 24 else [],
    }


def replay_bytes(cutoff=24, mutate_step=None):
    frames = []
    for step in range(cutoff + 2):
        row = {"observation": obs(step if step <= cutoff else cutoff + 1)}
        if step > 0:
            emitted = action(step - 1)
            if mutate_step == step - 1:
                emitted = copy.deepcopy(emitted)
                emitted["farmer"] = ["MOVE", "WEST"]
            row["action"] = emitted
        frames.append([row, {"observation": obs(step if step <= cutoff else cutoff + 1, player=1)}])
    replay = {
        "info": {"TeamNames": ["Pensukesan", "Arlene"]},
        "configuration": cfg(),
        "steps": frames,
        "rewards": [1234, 1000],
    }
    return json.dumps(replay, sort_keys=True, separators=(",", ":")).encode()


def prefix_arm(replay_sha, cutoff=24):
    tape = {
        str(step): {
            "action": action(step),
            "signature": {"hands": 0, "quadrants": 1},
        }
        for step in range(cutoff + 1)
    }
    raw = json.dumps(tape, sort_keys=True, separators=(",", ":")).encode()
    packed = base64.b85encode(zlib.compress(raw, 9)).decode("ascii")
    return f'''# generated fixture
ARM_ID = 'pensukesan-e1-s0--post24_full--prefix{cutoff}'
PARENT_ARM_ID = 'pensukesan-e1-s0--post24_full'
PREFIX_CUTOFF = {cutoff}
SOURCE_EPISODE = '1'
SOURCE_TEAM = 'Pensukesan'
SOURCE_SEAT = 0
SOURCE_REWARD = 1234.0
SOURCE_SHA256 = {replay_sha!r}
PARENT_TAPE_SHA256 = {'0' * 64!r}
TAPE_SHA256 = {hashlib.sha256(raw).hexdigest()!r}
_PACKED = {packed!r}
'''


def literal(path, name):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise KeyError(name)


class CertifiedPrefixTests(unittest.TestCase):
    def build_fixture(self, root: Path, mutate_step=None):
        replay = replay_bytes(mutate_step=mutate_step)
        replay_path = root / "episode_1.json"
        replay_path.write_bytes(replay)
        replay_sha = hashlib.sha256(replay).hexdigest()
        arm_path = root / "prefix.py"
        arm_path.write_text(prefix_arm(replay_sha))
        baseline = root / "baseline.py"
        baseline.write_text(
            "def agent(obs, configuration=None):\n"
            "    return {'farmer':['PASS'],'hands':[],'market':[]}\n"
        )
        return replay_path, replay_sha, arm_path, baseline

    def build(self, root: Path, mutate_step=None):
        replay_path, replay_sha, arm_path, baseline = self.build_fixture(root, mutate_step)
        output, receipt = root / "certified.py", root / "receipt.json"
        arm_sha = hashlib.sha256(arm_path.read_bytes()).hexdigest()
        result = build_certified_prefix(
            source_arm=arm_path,
            source_replay=replay_path,
            runtime=HERE / "certified_route_runtime.py",
            baseline_entry=baseline,
            output=output,
            receipt=receipt,
            expected_source_arm_sha256=arm_sha,
            expected_replay_sha256=replay_sha,
            expected_episode="1",
            expected_cutoff=24,
        )
        return result, output, receipt, replay_path, arm_path, baseline

    def test_builder_embeds_aligned_exact_certificate_and_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result, output, receipt, *_ = self.build(root)
            self.assertEqual(result["certificate_summary"]["rows"], 25)
            self.assertEqual(result["certificate_summary"]["owned_rows"], 1)
            packed = literal(output, "_PACKED")
            tape = json.loads(zlib.decompress(base64.b85decode(packed.encode())))
            expected = prestate_certificate(obs(24), cfg(), action(24), seat=0, mode="full")
            self.assertEqual(tape["24"]["certificate"], expected)
            self.assertEqual(tape["24"]["source_frame"], 24)
            self.assertEqual(json.loads(receipt.read_text())["output_python_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_generated_arm_executes_route_only_on_matching_source_prestate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, output, _, *_ = self.build(root)
            spec = importlib.util.spec_from_file_location("generated_certified_arm", output)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            self.assertEqual(module.agent(obs(24), cfg()), action(24))
            drift = obs(24)
            drift["farms"][0]["money"] += 1
            # Start a new game before the mismatched step.
            module.agent(obs(0), cfg())
            self.assertEqual(
                module.agent(drift, cfg()),
                {"farmer": ["PASS"], "hands": [], "market": []},
            )
            self.assertEqual(module.diagnostics()["handoff_step"], 24)

    def test_action_alignment_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            replay_path, replay_sha, arm_path, baseline = self.build_fixture(root, mutate_step=24)
            with self.assertRaisesRegex(CertifiedPrefixError, "action mismatch"):
                build_certified_prefix(
                    source_arm=arm_path,
                    source_replay=replay_path,
                    runtime=HERE / "certified_route_runtime.py",
                    baseline_entry=baseline,
                    output=root / "out.py",
                    receipt=root / "receipt.json",
                    expected_source_arm_sha256=hashlib.sha256(arm_path.read_bytes()).hexdigest(),
                    expected_replay_sha256=replay_sha,
                    expected_episode="1",
                    expected_cutoff=24,
                )

    def test_wrong_replay_or_arm_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            replay_path, replay_sha, arm_path, baseline = self.build_fixture(root)
            common = dict(
                source_arm=arm_path,
                source_replay=replay_path,
                runtime=HERE / "certified_route_runtime.py",
                baseline_entry=baseline,
                output=root / "out.py",
                receipt=root / "receipt.json",
                expected_episode="1",
                expected_cutoff=24,
            )
            with self.assertRaisesRegex(CertifiedPrefixError, "source arm SHA-256"):
                build_certified_prefix(
                    **common,
                    expected_source_arm_sha256="f" * 64,
                    expected_replay_sha256=replay_sha,
                )
            with self.assertRaisesRegex(CertifiedPrefixError, "replay digest drift"):
                build_certified_prefix(
                    **common,
                    expected_source_arm_sha256=hashlib.sha256(arm_path.read_bytes()).hexdigest(),
                    expected_replay_sha256="e" * 64,
                )

    def test_output_alias_and_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            replay_path, replay_sha, arm_path, baseline = self.build_fixture(root)
            kwargs = dict(
                source_arm=arm_path,
                source_replay=replay_path,
                runtime=HERE / "certified_route_runtime.py",
                baseline_entry=baseline,
                expected_source_arm_sha256=hashlib.sha256(arm_path.read_bytes()).hexdigest(),
                expected_replay_sha256=replay_sha,
                expected_episode="1",
                expected_cutoff=24,
            )
            with self.assertRaisesRegex(CertifiedPrefixError, "path alias"):
                build_certified_prefix(**kwargs, output=arm_path, receipt=root / "receipt.json")
            existing = root / "existing.py"
            existing.write_text("do not replace")
            with self.assertRaisesRegex(CertifiedPrefixError, "must be absent"):
                build_certified_prefix(**kwargs, output=existing, receipt=root / "receipt2.json")

    def test_build_is_byte_deterministic_for_identical_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, output, receipt, replay_path, arm_path, baseline = self.build(root)
            first_output, first_receipt = output.read_bytes(), receipt.read_bytes()
            output.unlink()
            receipt.unlink()
            second = build_certified_prefix(
                source_arm=arm_path,
                source_replay=replay_path,
                runtime=HERE / "certified_route_runtime.py",
                baseline_entry=baseline,
                output=output,
                receipt=receipt,
                expected_source_arm_sha256=hashlib.sha256(arm_path.read_bytes()).hexdigest(),
                expected_replay_sha256=hashlib.sha256(replay_path.read_bytes()).hexdigest(),
                expected_episode="1",
                expected_cutoff=24,
            )
            self.assertEqual(first_output, output.read_bytes())
            self.assertEqual(first_receipt, receipt.read_bytes())
            self.assertEqual(first, second)

    def test_duplicate_source_arm_literal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            replay = replay_bytes()
            replay_sha = hashlib.sha256(replay).hexdigest()
            arm = prefix_arm(replay_sha) + "\nARM_ID = 'second-definition'\n"
            path = root / "duplicate.py"
            path.write_text(arm)
            with self.assertRaisesRegex(CertifiedPrefixError, "duplicate source-arm literal"):
                decode_prefix_arm(path)

    def test_noncontiguous_source_tape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            replay = replay_bytes()
            replay_sha = hashlib.sha256(replay).hexdigest()
            arm = prefix_arm(replay_sha)
            packed = ast.literal_eval(next(
                node.value for node in ast.parse(arm).body
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "_PACKED"
            ))
            tape = json.loads(zlib.decompress(base64.b85decode(packed.encode())))
            del tape["12"]
            raw = json.dumps(tape, sort_keys=True, separators=(",", ":")).encode()
            broken = arm.replace(
                repr(packed), repr(base64.b85encode(zlib.compress(raw, 9)).decode("ascii"))
            ).replace(
                repr(hashlib.sha256(zlib.decompress(base64.b85decode(packed.encode()))).hexdigest()),
                repr(hashlib.sha256(raw).hexdigest()),
            )
            path = root / "broken.py"
            path.write_text(broken)
            with self.assertRaisesRegex(CertifiedPrefixError, "contiguous"):
                decode_prefix_arm(path)


if __name__ == "__main__":
    unittest.main()
