# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import unittest

from compose_current_runtime import compose_build, compose_config, compose_main, compose_runtime


class ComposeEODCapacityRescue(unittest.TestCase):
    def test_runtime_adds_default_exact_bool_and_topology_guard(self):
        source = """    exec_pace: bool = False
        bool_fields = (*bool_fields, 'exec_pace')
        if self.exec_pace and (self.consumer != 'frozen' or self.terminal_route):
            raise ValueError('exec_pace is the tested nonterminal frozen SELL composition')
"""
        rendered = compose_runtime(source)
        self.assertIn('eod_capacity_rescue: bool = False', rendered)
        self.assertIn("'exec_pace', 'eod_capacity_rescue'", rendered)
        self.assertIn('if self.eod_capacity_rescue and', rendered)
        with self.assertRaises(ValueError):
            compose_runtime(rendered)

    def test_main_wires_after_town_and_before_return(self):
        source = """            if self.town_procurement_enabled:
                from town_procurement import apply
                returned, report = apply(obs, returned, cfg, completed=completed)
                self.diagnostics['town_procurement'] = report
                self._checkpoint_finalizer(obs, returned, 'town_procurement')
            return returned
"""
        rendered = compose_main(source)
        self.assertLess(rendered.index("'town_procurement'"), rendered.index('features.eod_capacity_rescue'))
        self.assertLess(rendered.index('features.eod_capacity_rescue'), rendered.index('            return returned'))
        self.assertIn("self.diagnostics['eod_capacity_rescue'] = report", rendered)
        with self.assertRaises(ValueError):
            compose_main(rendered)

    def test_config_adds_false_only(self):
        rendered = compose_config(json.dumps({'consumer': 'frozen', 'exec_pace': False}))
        payload = json.loads(rendered)
        self.assertIs(payload['eod_capacity_rescue'], False)
        self.assertIs(payload['exec_pace'], False)
        with self.assertRaises(ValueError):
            compose_config(rendered)

    def test_build_maps_runtime_and_check(self):
        source = """              'exec_pace_runtime.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:
    mapping['checks/test_early_capital.py']='test_early_capital.py'
"""
        rendered = compose_build(source)
        self.assertIn("'eod_capacity_rescue.py'", rendered)
        self.assertIn("checks/test_eod_capacity_rescue.py", rendered)
        with self.assertRaises(ValueError):
            compose_build(rendered)

    def test_all_composers_fail_on_anchor_drift(self):
        for composer in (compose_main, compose_runtime, compose_build):
            with self.subTest(composer=composer.__name__):
                with self.assertRaises(ValueError):
                    composer('anchor moved')


if __name__ == '__main__':
    unittest.main()
