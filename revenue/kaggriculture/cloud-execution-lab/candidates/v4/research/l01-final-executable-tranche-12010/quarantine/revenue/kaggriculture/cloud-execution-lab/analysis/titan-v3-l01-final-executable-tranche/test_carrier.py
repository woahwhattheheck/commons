# SPDX-License-Identifier: Apache-2.0
"""Fail-closed contracts for the L01 final-executable-step repair carrier."""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


predecessor = load_module("l01_final_predecessor", "predecessor_l01_mechanics.py")
candidate = load_module("l01_final_candidate", "candidate_l01_mechanics.py")
PIN = json.loads((ROOT / "PIN.json").read_text(encoding="utf-8"))
REPLAY = json.loads((ROOT / "REPLAY-107213024-BOUNDARY.json").read_text(encoding="utf-8"))


def flags(**on):
    result = {key: False for key in candidate.FLAG_KEYS}
    result.update(on)
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SourceCustodyTests(unittest.TestCase):
    def test_exact_standalone_hashes(self):
        for filename, expected in PIN["standalone"].items():
            self.assertEqual(sha256(ROOT / filename), expected, filename)

    def test_carrier_manifest(self):
        manifest = json.loads((ROOT / "CARRIER-MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "titan.v3.l01-final-executable-carrier-manifest.v1")
        for filename, expected in manifest["files"].items():
            self.assertEqual(sha256(ROOT / filename), expected, filename)

    def test_predecessor_is_exact_handoff_l01_source(self):
        path = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/l01_mechanics.py"
        self.assertEqual(PIN["preimages"][path], sha256(ROOT / "predecessor_l01_mechanics.py"))

    def test_patch_has_exact_owned_surface(self):
        text = (ROOT / "one-tree-l01-final-executable.patch").read_text(encoding="utf-8")
        pairs = re.findall(r"^--- a/(.+)\n\+\+\+ b/(.+)$", text, flags=re.MULTILINE)
        expected = [
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/l01_mechanics.py",
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/apply_v3.py",
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/checks/test_v3_l01.py",
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/README.md",
            "revenue/kaggriculture/cloud-execution-lab/candidates/v3/V3-MANIFEST.json",
        ]
        self.assertEqual([left for left, _right in pairs], expected)
        self.assertEqual([right for _left, right in pairs], expected)
        self.assertNotIn("/dev/null", text)
        self.assertIn("step > final_step", text)
        self.assertIn("episode_steps=episode_steps", text)

    def test_non_lifecycle_functions_are_byte_identical(self):
        names = (
            "flags_from_features", "_units", "_set_unit", "_has_buy_land",
            "patch_routes", "install", "shed_snapshot", "plant_counts", "animal_buys",
        )
        for name in names:
            self.assertEqual(
                inspect.getsource(getattr(predecessor, name)),
                inspect.getsource(getattr(candidate, name)),
                name,
            )

    def test_policy_constants_are_unchanged(self):
        names = (
            "LAND_STEPS", "LAND_FALLBACK_STEPS", "KEEP_WHEAT_PLANTS", "DAY0_BASKET",
            "TRANCHE_WHEAT", "TRANCHE_CARROT", "TRANCHE_DAY_FROM", "MAX_ORDERS",
            "MAIN", "NOOP", "FLAG_KEYS", "FEATURE_KEYS", "PRODUCTS",
        )
        for name in names:
            self.assertEqual(getattr(predecessor, name), getattr(candidate, name), name)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.shed = {"WHEAT": 80, "CARROT": 40, "EGG": 2, "MILK": 5}

    def test_predecessor_killed_at_default_final_executable_input(self):
        old_activations = Counter()
        new_activations = Counter()
        old = predecessor.apply_tranche(
            self.action, {"step": 718, "day": 29}, flags(TRANCHE=True),
            old_activations, shed=self.shed,
        )
        new = candidate.apply_tranche(
            self.action, {"step": 718, "day": 29}, flags(TRANCHE=True),
            new_activations, shed=self.shed, episode_steps=720,
        )
        self.assertIs(old, self.action)
        self.assertEqual(old_activations, Counter())
        self.assertIsNot(new, self.action)
        self.assertEqual(
            new["market"],
            [
                ["SELL", "WHEAT", 57],
                ["SELL", "CARROT", 32],
                ["SELL", "EGG", 2],
                ["SELL", "MILK", 5],
            ],
        )
        self.assertEqual(new_activations, Counter({"TRANCHE": 4}))

    def test_post_action_state_is_quarantined(self):
        for module in (predecessor, candidate):
            activations = Counter()
            kwargs = {"episode_steps": 720} if module is candidate else {}
            out = module.apply_tranche(
                self.action, {"step": 719, "day": 29}, flags(TRANCHE=True),
                activations, shed=self.shed, **kwargs,
            )
            self.assertIs(out, self.action)
            self.assertEqual(activations, Counter())

    def test_last_executable_step_is_derived_from_episode_length(self):
        self.assertEqual(candidate.final_executable_step(), 718)
        self.assertEqual(candidate.final_executable_step(720), 718)
        self.assertEqual(candidate.final_executable_step("12"), 10)
        self.assertEqual(candidate.final_executable_step(2), 0)

    def test_configurable_episode_boundary(self):
        live = candidate.apply_tranche(
            self.action, {"step": 10, "day": 29}, flags(TRANCHE=True), Counter(),
            shed={"WHEAT": 80}, episode_steps=12,
        )
        self.assertEqual(live["market"], [["SELL", "WHEAT", 57]])
        dead = candidate.apply_tranche(
            self.action, {"step": 11, "day": 29}, flags(TRANCHE=True), Counter(),
            shed={"WHEAT": 80}, episode_steps=12,
        )
        self.assertIs(dead, self.action)

    def test_explicit_malformed_episode_lengths_fail_closed(self):
        for value in (None, True, False, "", "bad", 1, 0, -1, object()):
            with self.subTest(value=repr(value)):
                activations = Counter()
                out = candidate.apply_tranche(
                    self.action, {"step": 10, "day": 29}, flags(TRANCHE=True),
                    activations, shed={"WHEAT": 80}, episode_steps=value,
                )
                self.assertIs(out, self.action)
                self.assertEqual(activations, Counter())

    def test_flag_off_is_object_identity(self):
        activations = Counter()
        out = candidate.apply_tranche(
            self.action, {"step": 718, "day": 29}, flags(), activations,
            shed=self.shed, episode_steps=720,
        )
        self.assertIs(out, self.action)
        self.assertEqual(activations, Counter())

    def test_early_day_is_object_identity(self):
        activations = Counter()
        out = candidate.apply_tranche(
            self.action, {"step": 670, "day": 27}, flags(TRANCHE=True), activations,
            shed=self.shed, episode_steps=720,
        )
        self.assertIs(out, self.action)
        self.assertEqual(activations, Counter())

    def test_preboundary_semantics_match_predecessor(self):
        actions = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 3]]},
            {"farmer": ["PASS"], "hands": [], "market": [["BUY_LAND"]] * 9},
        ]
        sheds = [
            {}, {"WHEAT": 80}, {"WHEAT": 80, "CARROT": 40, "MILK": 5},
        ]
        for step in (672, 696, 717):
            for action in actions:
                for shed in sheds:
                    with self.subTest(step=step, action=action, shed=shed):
                        old_activations = Counter()
                        new_activations = Counter()
                        old = predecessor.apply_tranche(
                            copy.deepcopy(action), {"step": step, "day": step // 24},
                            flags(TRANCHE=True), old_activations, shed=copy.deepcopy(shed),
                        )
                        new = candidate.apply_tranche(
                            copy.deepcopy(action), {"step": step, "day": step // 24},
                            flags(TRANCHE=True), new_activations, shed=copy.deepcopy(shed),
                            episode_steps=720,
                        )
                        self.assertEqual(new, old)
                        self.assertEqual(new_activations, old_activations)

    def test_inputs_are_not_mutated(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 3]]}
        obs = {"step": 718, "day": 29, "private": {"shed": {"WHEAT": 80}}}
        shed = {"WHEAT": 80, "CARROT": 40}
        before = copy.deepcopy((action, obs, shed))
        candidate.apply_tranche(
            action, obs, flags(TRANCHE=True), Counter(), shed=shed, episode_steps=720,
        )
        self.assertEqual((action, obs, shed), before)

    def test_queue_cap_is_preserved(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_LAND"] for _ in range(9)]}
        activations = Counter()
        out = candidate.apply_tranche(
            action, {"step": 718, "day": 29}, flags(TRANCHE=True), activations,
            shed=self.shed, episode_steps=720,
        )
        self.assertEqual(len(out["market"]), candidate.MAX_ORDERS)
        self.assertEqual(out["market"][-1], ["SELL", "WHEAT", 57])
        self.assertEqual(activations, Counter({"TRANCHE": 1}))

    def test_full_queue_can_enlarge_existing_order_without_repacking(self):
        market = [["SELL", "WHEAT", 3]] + [["BUY_LAND"] for _ in range(9)]
        action = {"farmer": ["PASS"], "hands": [], "market": market}
        out = candidate.apply_tranche(
            action, {"step": 718, "day": 29}, flags(TRANCHE=True), Counter(),
            shed={"WHEAT": 80, "CARROT": 40}, episode_steps=720,
        )
        self.assertEqual(len(out["market"]), 10)
        self.assertEqual(out["market"][0], ["SELL", "WHEAT", 57])
        self.assertFalse(any(order[:2] == ["SELL", "CARROT"] for order in out["market"] if order))

    def test_no_inventory_no_change_preserves_identity(self):
        activations = Counter()
        out = candidate.apply_tranche(
            self.action, {"step": 718, "day": 29}, flags(TRANCHE=True), activations,
            shed={}, episode_steps=720,
        )
        self.assertIs(out, self.action)
        self.assertEqual(activations, Counter())


class ReplayReceiptTests(unittest.TestCase):
    def test_receipt_is_bound_to_exact_public_replay(self):
        self.assertEqual(REPLAY["episode_id"], 107213024)
        self.assertEqual(REPLAY["source_slack_file_id"], "F0C10AT69PU")
        self.assertEqual(REPLAY["source_gzip_sha256"], PIN["replay"]["sha256"])
        self.assertEqual(REPLAY["source_gzip_bytes"], PIN["replay"]["bytes"])
        self.assertEqual(REPLAY["state_count"], 720)
        self.assertEqual(REPLAY["action_count"], 719)
        self.assertEqual(REPLAY["team_names"][0], "Otter Vibe")

    def test_receipt_proves_step_718_produces_state_719(self):
        self.assertEqual(REPLAY["input_state_index"], 718)
        self.assertEqual(REPLAY["input_observation_step"], 718)
        self.assertEqual(REPLAY["input_day"], 29)
        self.assertEqual(REPLAY["input_hour"], 22)
        self.assertEqual(REPLAY["output_state_index"], 719)
        self.assertEqual(REPLAY["output_observation_step"], 719)
        self.assertEqual(REPLAY["status_before"], "ACTIVE")
        self.assertEqual(REPLAY["status_after"], "DONE")
        self.assertEqual(REPLAY["cash_before"], 117176)
        self.assertEqual(REPLAY["cash_after"], 122100)
        self.assertEqual(REPLAY["cash_delta"], 4924)

    def test_final_action_sells_exact_same_turn_drop_inventory(self):
        unit_actions = [REPLAY["final_action"]["farmer"], *REPLAY["final_action"]["hands"]]
        inventories = REPLAY["actor_inventories_before"]
        dropped = Counter()
        for index, action in enumerate(unit_actions):
            if action and action[0] == "DROP":
                dropped.update(inventories[index])
        sales = Counter()
        for order in REPLAY["final_action"]["market"]:
            if order and order[0] == "SELL":
                sales[order[1]] += int(order[2])
        self.assertEqual(dict(sorted(dropped.items())), REPLAY["dropped_inventory"])
        self.assertEqual(dict(sorted(sales.items())), REPLAY["market_sales"])
        self.assertEqual(sales, dropped)

    def test_repaired_tranche_is_live_on_replay_boundary_stock(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        activations = Counter()
        out = candidate.apply_tranche(
            action,
            {
                "step": REPLAY["input_observation_step"],
                "day": REPLAY["input_day"],
                "hour": REPLAY["input_hour"],
            },
            flags(TRANCHE=True),
            activations,
            shed=REPLAY["dropped_inventory"],
            episode_steps=REPLAY["state_count"],
        )
        self.assertEqual(
            out["market"],
            [
                ["SELL", "WHEAT", 31],
                ["SELL", "CARROT", 32],
                ["SELL", "EGG", 1],
                ["SELL", "WOOL", 4],
            ],
        )
        self.assertEqual(activations, Counter({"TRANCHE": 4}))
        self.assertEqual(action["market"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
