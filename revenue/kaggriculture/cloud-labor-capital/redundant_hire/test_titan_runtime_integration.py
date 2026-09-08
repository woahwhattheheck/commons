# SPDX-License-Identifier: Apache-2.0
"""Current TitanAgent integration checks for the landed redundant-hire component."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LAB = Path(os.environ.get('TITAN_CURRENT_DIR', HERE.parents[1] / 'cloud-execution-lab')).resolve()
FIXTURE = Path(os.environ.get('TITAN_REDUNDANT_HIRE_INPUT', HERE / 'current-integration-input.json')).resolve()
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))
from titan_runtime import Features, TitanAgent


class CurrentRedundantHireIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(FIXTURE.read_text())

    def inputs(self):
        return copy.deepcopy(self.case['observation']), copy.deepcopy(self.case['configuration'])

    def test_actual_current_actor_changes_only_the_redundant_hire(self):
        obs, cfg = self.inputs(); before = copy.deepcopy((obs, cfg))
        actor = TitanAgent(Features(redundant_hire=True))
        out = actor.act(obs, cfg)
        self.assertEqual(out, self.case['expected_candidate_action'])
        self.assertEqual(actor.selected, self.case['expected_control_action'])
        self.assertEqual(actor.diagnostics['parent_calls'], 1)
        report = actor.diagnostics['redundant_hire']
        self.assertTrue(report['changed'])
        self.assertEqual(report['step'], 121)
        self.assertEqual(report['route_id'], '7015cc00acfa4922')
        self.assertEqual(report['removed_order_indices'], [1])
        self.assertEqual(report['immediate_wage_saving'], 5)
        self.assertEqual((obs, cfg), before)

    def test_default_actor_is_byte_behavior_unchanged(self):
        obs, cfg = self.inputs()
        actor = TitanAgent(Features())
        out = actor.act(obs, cfg)
        self.assertEqual(out, self.case['expected_control_action'])
        self.assertNotIn('redundant_hire', actor.diagnostics)
        self.assertFalse(hasattr(actor, 'redundant_hire_module'))

    def test_landed_component_is_consumed_byte_exact(self):
        canonical = LAB / 'reference/titan-current/redundant_hire.py'
        landed = HERE / 'redundant_hire.py'
        self.assertEqual(canonical.read_bytes(), landed.read_bytes())
        self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(),
                         'a881284d6b59366536ebc5e77f0f7c7f2923599dfb8588fd8b1ed6166bd51483')

    def test_feature_is_limited_to_tested_frozen_nonterminal_mode(self):
        for kwargs in ({'consumer':'ordered'}, {'consumer':'parent'}, {'terminal_route':True}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, 'redundant_hire'):
                Features(redundant_hire=True, **kwargs)

    def test_no_hire_fast_path_preserves_action_and_skips_component(self):
        obs, cfg = self.inputs()
        actor = TitanAgent(Features(redundant_hire=True)); actor._initialize()
        action = copy.deepcopy(self.case['expected_control_action']); action['market'] = []
        original = actor.redundant_hire_module.propose_redundant_hires
        actor.redundant_hire_module.propose_redundant_hires = lambda *a, **k: (_ for _ in ()).throw(AssertionError('called'))
        try:
            self.assertEqual(actor._redundant_hire_selected(obs, cfg, action), action)
        finally:
            actor.redundant_hire_module.propose_redundant_hires = original

    def test_pipeline_order_is_sell_then_hire_then_seed(self):
        obs, cfg = self.inputs()
        actor = TitanAgent(Features(redundant_hire=True)); actor._initialize()
        calls = []
        selected = copy.deepcopy(self.case['expected_control_action'])
        actor.consumer.transform = lambda o, c, s: calls.append('sell') or copy.deepcopy(s)
        actor._redundant_hire_selected = lambda o, c, s: calls.append('hire') or copy.deepcopy(s)
        actor._seed_selected = lambda o, c, s: calls.append('seed') or copy.deepcopy(s)
        self.assertEqual(actor.transform_selected(obs, cfg, selected), selected)
        self.assertEqual(calls, ['sell', 'hire', 'seed'])

    def test_selected_transform_does_not_call_the_parent(self):
        obs, cfg = self.inputs()
        actor = TitanAgent(Features(redundant_hire=True)); actor._initialize()
        selected = copy.deepcopy(self.case['expected_control_action'])
        original = actor.production.act
        actor.production.act = lambda *_: (_ for _ in ()).throw(AssertionError('second parent call'))
        try:
            out = actor.transform_selected(obs, cfg, selected)
        finally:
            actor.production.act = original
        self.assertEqual(out, self.case['expected_candidate_action'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
