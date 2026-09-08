# SPDX-License-Identifier: Apache-2.0
"""Exact runtime/package boundaries for the opt-in ECON admission callback."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import tarfile
import unittest

import build_integrated
import main


ROOT = Path(__file__).resolve().parent


class FundedPaybackRuntimeTests(unittest.TestCase):
    def config(self):
        return json.loads((ROOT/'TITAN-CONFIG.json').read_text())

    def test_canonical_config_keeps_investment_opt_in(self):
        config = self.config()
        self.assertIs(config['fourth_quadrant'], False)
        instance = main._new_instance(ROOT, config)
        self.assertIsNone(instance._quadrant_admission)

    def test_enabled_runtime_supplies_econ_callback_and_terminal_mechanics(self):
        config = self.config()
        config['fourth_quadrant'] = True
        config['redundant_hire'] = False
        instance = main._new_instance(ROOT, config)
        self.assertEqual(type(instance._quadrant_admission).__name__,
                         'RuntimeFundedPaybackAdmission')
        instance._initialize()
        self.assertIs(instance.quadrant.admit, instance._quadrant_admission)
        self.assertTrue(callable(instance.quadrant.m._parse_order))
        self.assertTrue(callable(instance.quadrant.m._refresh_prices))
        self.assertEqual(instance.quadrant.m._parse_order(
            ['BUY_SEED', 'CARROT', 3]),
            {'type': 'BUY_SEED', 'item': 'CARROT', 'remaining': 3})

    def test_adapter_preserves_slots_and_explicit_physical_rejoin(self):
        config = self.config()
        config.update(fourth_quadrant=True, redundant_hire=False)
        admission = main._new_instance(ROOT, config)._quadrant_admission
        base = [{'farmer': ['PASS'], 'hands': [], 'market': []}
                for _ in range(8)]
        base[2]['market'] = [['SELL', 'WHEAT', 0], ['HIRE']]
        variant = {'patches': {3: {'farmer': ['PASS'], 'hands': [],
                                   'market': [['BUY_SEED', 'CARROT', 0], ['BUY_LAND']]}},
                   'bundle': {'rejoin_step': 7}}
        candidate, rejoin = admission._candidate(base, variant, 2)
        self.assertEqual(candidate[2]['market'], [['PASS'], ['HIRE']])
        self.assertEqual(candidate[3]['market'], [['PASS'], ['BUY_LAND']])
        self.assertEqual(rejoin, 7)
        self.assertEqual(base[2]['market'], [['SELL', 'WHEAT', 0], ['HIRE']])

    def test_rendered_archive_contains_exact_attributed_callback(self):
        data, manifest_bytes, receipt = build_integrated.render()
        manifest = json.loads(manifest_bytes)
        source = (ROOT/'../cloud-economic-stress/funded_payback/funded_payback.py').read_bytes()
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            packaged = archive.extractfile('funded_payback.py').read()
            self.assertEqual(archive.extractfile('funded_payback_runtime.py').read(),
                             (ROOT/'funded_payback_runtime.py').read_bytes())
            config = json.load(archive.extractfile('TITAN-CONFIG.json'))
        self.assertEqual(packaged, source)
        self.assertEqual(manifest['runtime']['funded_payback.py']['source_path'],
                         '../cloud-economic-stress/funded_payback/funded_payback.py')
        self.assertIs(config['fourth_quadrant'], False)
        self.assertEqual(receipt['runtime_files'], len(manifest['runtime']))


if __name__ == '__main__':
    unittest.main()
