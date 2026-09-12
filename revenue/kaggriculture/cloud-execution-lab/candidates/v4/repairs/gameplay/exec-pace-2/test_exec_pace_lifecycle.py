# SPDX-License-Identifier: Apache-2.0
"""Focused EXEC-PACE-2 lifecycle/activation regressions for the current composer."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import textwrap
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("execpace_composer", HERE / "compose_current_runtime.py")
composer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composer)


class FakeFrozenSelected:
    pass


class FakeTrendState:
    created = 0

    def __init__(self):
        type(self).created += 1
        self.serial = type(self).created


class FakePace:
    PriceTrendState = FakeTrendState
    apply_candidate = staticmethod(lambda *args: args)


def consumer_probe():
    fragment = textwrap.dedent(composer.CONSUMER_INSERT)
    namespace = {"HERE": Path("/tmp")}
    exec(compile(
        "def run(self, f, FrozenSelected, load):\n" + textwrap.indent(fragment, "    "),
        "exec_pace_consumer_fragment.py", "exec"), namespace)
    return namespace["run"]


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        FakeTrendState.created = 0
        self.run = consumer_probe()
        self.loads = []

    def load(self, name, path):
        self.loads.append((name, str(path)))
        return FakePace

    def test_only_literal_true_activates(self):
        poisons = (False, "false", "true", 0, 1, 0.0, 1.0, None, [], [True], {}, {"enabled": True})
        for value in poisons:
            with self.subTest(value=repr(value)):
                holder = SimpleNamespace()
                self.run(holder, SimpleNamespace(exec_pace=value), FakeFrozenSelected, self.load)
                self.assertFalse(hasattr(holder.consumer, "exec_pace_state"))
                self.assertFalse(hasattr(holder.consumer, "exec_pace_apply"))
                self.assertFalse(hasattr(holder, "_exec_pace_state"))
        self.assertEqual(self.loads, [])
        self.assertEqual(FakeTrendState.created, 0)

    def test_literal_true_attaches_gate(self):
        holder = SimpleNamespace()
        self.run(holder, SimpleNamespace(exec_pace=True), FakeFrozenSelected, self.load)
        self.assertIs(holder.consumer.exec_pace_apply, FakePace.apply_candidate)
        self.assertIs(holder.consumer.exec_pace_state, holder._exec_pace_state)
        self.assertEqual(FakeTrendState.created, 1)
        self.assertEqual(len(self.loads), 1)

    def test_state_survives_consumer_reconstruction(self):
        holder = SimpleNamespace()
        enabled = SimpleNamespace(exec_pace=True)
        self.run(holder, enabled, FakeFrozenSelected, self.load)
        first_consumer = holder.consumer
        first_state = first_consumer.exec_pace_state
        first_state.marker = "warm-history"
        self.run(holder, enabled, FakeFrozenSelected, self.load)
        self.assertIsNot(holder.consumer, first_consumer)
        self.assertIs(holder.consumer.exec_pace_state, first_state)
        self.assertEqual(holder.consumer.exec_pace_state.marker, "warm-history")
        self.assertEqual(FakeTrendState.created, 1)
        self.assertEqual(len(self.loads), 2)

    def test_disabled_reconstruction_does_not_attach_stale_state(self):
        holder = SimpleNamespace()
        self.run(holder, SimpleNamespace(exec_pace=True), FakeFrozenSelected, self.load)
        retained = holder._exec_pace_state
        self.run(holder, SimpleNamespace(exec_pace=False), FakeFrozenSelected, self.load)
        self.assertFalse(hasattr(holder.consumer, "exec_pace_state"))
        self.assertIs(holder._exec_pace_state, retained)
        self.run(holder, SimpleNamespace(exec_pace=True), FakeFrozenSelected, self.load)
        self.assertIs(holder.consumer.exec_pace_state, retained)
        self.assertEqual(FakeTrendState.created, 1)

    def test_source_contract_is_literal_true_and_agent_owned(self):
        self.assertIn("if f.exec_pace is True:", composer.CONSUMER_INSERT)
        self.assertIn("getattr(self, '_exec_pace_state', None)", composer.CONSUMER_INSERT)
        self.assertIn("self._exec_pace_state = exec_pace_state", composer.CONSUMER_INSERT)
        self.assertNotIn("if f.exec_pace:\n", composer.CONSUMER_INSERT)


class ComposerShapeTests(unittest.TestCase):
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
        "            info['baseline_horizon_end']=horizon['baseline_end'];info['horizon_end']=item_end\n"
        "            self.diagnostics['evaluations'].append(info)\n"
        "            eligible,rank=seller_choice_rank(info)\n"
    )

    def test_composer_remains_default_off_and_compilable(self):
        titan, frozen = composer.compose_sources(self.TITAN, self.FROZEN)
        self.assertEqual(titan.count("exec_pace: bool = False"), 1)
        self.assertEqual(titan.count("if f.exec_pace is True:"), 1)
        self.assertIn("_exec_pace_state", titan)
        self.assertIn("exec_pace_apply(exec_pace_state,item,reference,plan,info)", frozen)
        self.assertIn('"exec_pace": false', composer.compose_config('{}'))

    def test_double_apply_still_fails_closed(self):
        titan, frozen = composer.compose_sources(self.TITAN, self.FROZEN)
        with self.assertRaises(ValueError):
            composer.compose_sources(titan, frozen)


if __name__ == "__main__":
    unittest.main(verbosity=2)
