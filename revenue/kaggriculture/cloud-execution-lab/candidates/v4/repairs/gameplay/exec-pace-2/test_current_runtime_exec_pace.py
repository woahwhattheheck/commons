# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("execpace_runtime", HERE / "current_runtime_exec_pace.py")
runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
spec2 = importlib.util.spec_from_file_location("execpace_composer", HERE / "compose_current_runtime.py")
composer = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(composer)


def observation(step, player=0, base=100, rising_good=None):
    prices = {good: base for good in runtime.GOODS}
    if rising_good is not None:
        prices[rising_good] = base + step
    return {"step": step, "player": player, "market": {"prices": prices}}


class TrendTests(unittest.TestCase):
    def test_warmup_and_rising(self):
        state = runtime.PriceTrendState()
        for step in range(24):
            state.note_prices(observation(step, rising_good="MILK"))
            self.assertFalse(state.rising("MILK"))
        state.note_prices(observation(24, rising_good="MILK"))
        self.assertTrue(state.rising("MILK"))
        self.assertEqual(state.slope("MILK"), 1.0)

    def test_identical_duplicate_idempotent(self):
        state = runtime.PriceTrendState()
        for step in range(25):
            obs = observation(step, rising_good="WOOL")
            state.note_prices(obs)
            if step == 12:
                state.note_prices(obs)
        self.assertTrue(state.rising("WOOL"))

    def test_gap_and_player_change_restart(self):
        state = runtime.PriceTrendState()
        for step in range(25): state.note_prices(observation(step, rising_good="EGG"))
        self.assertTrue(state.rising("EGG"))
        state.note_prices(observation(26, rising_good="EGG"))
        self.assertFalse(state.rising("EGG"))
        for step in range(27, 51): state.note_prices(observation(step, rising_good="EGG"))
        self.assertTrue(state.rising("EGG"))
        state.note_prices(observation(51, player=1, rising_good="EGG"))
        self.assertFalse(state.rising("EGG"))

    def test_missing_one_quote_clears_only_that_good(self):
        state = runtime.PriceTrendState()
        for step in range(24): state.note_prices(observation(step, rising_good="MILK"))
        broken = observation(24, rising_good="MILK")
        broken["market"]["prices"]["MILK"] = None
        state.note_prices(broken)
        self.assertIsNone(state.slope("MILK"))
        self.assertEqual(state.slope("WOOL"), 0.0)


class GateTests(unittest.TestCase):
    def warm(self, good="MILK"):
        state = runtime.PriceTrendState()
        for step in range(25): state.note_prices(observation(step, rising_good=good))
        return state

    def test_detects_now_advance(self):
        adv = runtime.cumulative_advance(((24, 1), (28, 4)), ((24, 3), (28, 2)))
        self.assertEqual(adv["step"], 24)
        self.assertEqual(adv["delta"], 2)

    def test_detects_mid_window_advance(self):
        adv = runtime.cumulative_advance(((24, 1), (28, 2), (32, 2)),
                                         ((24, 1), (26, 2), (32, 2)))
        self.assertEqual(adv["step"], 26)

    def test_delay_is_not_advance(self):
        self.assertIsNone(runtime.cumulative_advance(((24, 3), (28, 2)),
                                                     ((24, 1), (28, 4))))

    def test_rising_blocks_only_advance(self):
        state = self.warm()
        reference = ((24, 1), (28, 4))
        candidate = ((24, 3), (28, 2))
        kept, report = runtime.gate_plan(state, "MILK", reference, candidate)
        self.assertTrue(report["blocked"])
        self.assertEqual(kept, reference)
        delayed = ((24, 0), (28, 5))
        kept, report = runtime.gate_plan(state, "MILK", reference, delayed)
        self.assertFalse(report["blocked"])
        self.assertEqual(kept, delayed)

    def test_flat_does_not_block(self):
        state = runtime.PriceTrendState()
        for step in range(25): state.note_prices(observation(step))
        candidate = ((24, 3), (28, 2))
        kept, report = runtime.gate_plan(state, "MILK", ((24, 1), (28, 4)), candidate)
        self.assertFalse(report["blocked"])
        self.assertIs(kept, candidate)

    def test_quantity_mismatch_fails_open(self):
        state = self.warm()
        candidate = ((24, 3),)
        kept, report = runtime.gate_plan(state, "MILK", ((24, 1), (28, 4)), candidate)
        self.assertFalse(report["blocked"])
        self.assertEqual(report["reason"], "no-temporal-advance")
        self.assertIs(kept, candidate)


class ComposerTests(unittest.TestCase):
    TITAN = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\nclass Features:\n"
        "    early_capital: bool = False\n"
        "class X:\n"
        "    def f(self,f):\n"
        "        if True:\n"
        "            self.consumer = FrozenSelected()\n"
    )
    FROZEN = (
        "class FrozenSelected:\n"
        "    def transform(self,obs,config,base):\n"
        "        self.observe(obs)\n"
        "        farm,private=post_units(obs,base,config)\n"
        "        for item in items:\n"
        "            plan,info=optimize_lot(item=item,quantity=quantity,inventory=0,params=None,shops=[],config=config,now=0,dates=[],reference=reference,rival_quantity=0,minimum_now=0,capacity_ok=None,last=0)\n"
        "            info['baseline_horizon_end']=horizon['baseline_end'];info['horizon_end']=item_end\n"
        "            self.diagnostics['evaluations'].append(info)\n"
        "            eligible,rank=seller_choice_rank(info)\n"
    )

    def test_composer_is_default_off_and_source_bound(self):
        titan, frozen = composer.compose_sources(self.TITAN, self.FROZEN)
        self.assertIn("exec_pace: bool = False", titan)
        self.assertIn("if f.exec_pace", titan)
        self.assertIn("exec_pace_state", frozen)
        self.assertIn("forced_feasibility", frozen)
        config = composer.compose_config('{"consumer":"frozen"}\n')
        self.assertFalse(json.loads(config)["exec_pace"])

    def test_composer_rejects_drift_and_double_apply(self):
        with self.assertRaises(ValueError): composer.compose_sources(self.TITAN.replace("early_capital", "x"), self.FROZEN)
        titan, frozen = composer.compose_sources(self.TITAN, self.FROZEN)
        with self.assertRaises(ValueError): composer.compose_sources(titan, frozen)
        with self.assertRaises(ValueError): composer.compose_config('{"exec_pace": false}')

    def test_current_repository_sources_are_composable_when_present(self):
        # In the repository this is a mandatory live-source anchor test.  The
        # standalone development copy under /mnt/data has no production tree.
        package_here = Path(__file__).resolve().parent
        root = package_here.parents[4] if len(package_here.parents) > 4 else None
        if root is None or not (root / "titan_runtime.py").is_file():
            self.skipTest("repository production sources are not present in this standalone copy")
        titan_source = (root / "titan_runtime.py").read_text()
        frozen_source = (root / "frozen_selected.py").read_text()
        config_source = (root / "TITAN-CONFIG.json").read_text()
        titan, frozen = composer.compose_sources(titan_source, frozen_source)
        config = composer.compose_config(config_source)
        compile(titan, "titan_runtime.py", "exec")
        compile(frozen, "frozen_selected.py", "exec")
        parsed = json.loads(config)
        self.assertIn("exec_pace", parsed)
        self.assertIs(parsed["exec_pace"], False)
        self.assertEqual(titan.count("exec_pace: bool = False"), 1)
        self.assertEqual(frozen.count("exec_pace_gate"), 2)


if __name__ == "__main__":
    unittest.main()
