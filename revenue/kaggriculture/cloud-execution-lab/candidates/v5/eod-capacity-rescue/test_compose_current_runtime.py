# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import unittest

from compose_current_runtime import compose_build, compose_config, compose_main, compose_runtime


class ComposeEODCapacityRescue(unittest.TestCase):
    def test_runtime_adds_default_exact_bool_and_post_overflow_guard(self):
        source = """    overflow_safe_drop: bool = False
        bool_fields = (*bool_fields, 'exec_pace', 'overflow_safe_drop')
        if self.overflow_safe_drop and (self.consumer != 'frozen' or self.terminal_route):
            raise ValueError('overflow_safe_drop is the tested nonterminal frozen composition')
"""
        rendered = compose_runtime(source)
        self.assertIn('eod_capacity_rescue: bool = False', rendered)
        self.assertIn("'overflow_safe_drop', 'eod_capacity_rescue'", rendered)
        self.assertLess(rendered.index('if self.overflow_safe_drop and'),
                        rendered.index('if self.eod_capacity_rescue and'))
        self.assertIn("tested post-overflow frozen composition", rendered)
        with self.assertRaises(ValueError):
            compose_runtime(rendered)

    def test_main_wires_after_overflow_and_before_return(self):
        source = """            # Overflow preservation is an optional final-return transform only.
            # Do not run it on an incomplete producer result or on the terminal
            # settlement step, where liquidation semantics own the returned bytes.
            if self.overflow_safe_drop is not None and completed:
                episode_steps = cfg.get('episodeSteps', 720)
                nonterminal = (type(episode_steps) is int and episode_steps >= 2
                               and obs.get('step') != episode_steps - 2)
                if nonterminal:
                    returned, report = self.overflow_safe_drop.transform(returned, obs, cfg)
                    self.diagnostics['overflow_safe_drop'] = report
                    self._checkpoint_finalizer(obs, returned, 'overflow_safe_drop')
            return returned
"""
        rendered = compose_main(source)
        self.assertLess(rendered.index("self.diagnostics['overflow_safe_drop']"),
                        rendered.index('features.eod_capacity_rescue'))
        self.assertLess(rendered.index('features.eod_capacity_rescue'),
                        rendered.index('            return returned'))
        self.assertIn('if features.eod_capacity_rescue and completed:', rendered)
        self.assertIn("self.diagnostics['eod_capacity_rescue'] = report", rendered)
        self.assertIn("_checkpoint_finalizer(obs, returned, 'eod_capacity_rescue')", rendered)
        # The EOD call consumes the current `returned` variable after overflow;
        # there is no second overflow invocation after the EOD stage.
        eod = rendered.index('features.eod_capacity_rescue')
        self.assertNotIn('overflow_safe_drop.transform', rendered[eod:])
        with self.assertRaises(ValueError):
            compose_main(rendered)

    def test_config_adds_false_only_after_canonical_overflow_default(self):
        rendered = compose_config(json.dumps({
            'consumer': 'frozen',
            'exec_pace': False,
            'overflow_safe_drop': False,
        }))
        payload = json.loads(rendered)
        self.assertIs(payload['eod_capacity_rescue'], False)
        self.assertIs(payload['overflow_safe_drop'], False)
        with self.assertRaises(ValueError):
            compose_config(rendered)
        with self.assertRaises(ValueError):
            compose_config(json.dumps({'overflow_safe_drop': True}))

    def test_build_maps_runtime_and_check_after_overflow_sources_exist(self):
        source = """              'exec_pace_runtime.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:
    mapping['overflow_safe_drop.py']='candidates/v5/research/overflow-safe-drop/overflow_safe_drop.py'
    mapping['checks/test_overflow_safe_drop.py']='candidates/v5/research/overflow-safe-drop/test_overflow_safe_drop.py'
"""
        rendered = compose_build(source)
        self.assertIn("'eod_capacity_rescue.py'", rendered)
        self.assertIn("checks/test_eod_capacity_rescue.py", rendered)
        self.assertIn("overflow_safe_drop.py", rendered)
        with self.assertRaises(ValueError):
            compose_build(rendered)

    def test_all_composers_fail_on_anchor_drift(self):
        for composer in (compose_main, compose_runtime, compose_build):
            with self.subTest(composer=composer.__name__):
                with self.assertRaises(ValueError):
                    composer('anchor moved')


if __name__ == '__main__':
    unittest.main()
