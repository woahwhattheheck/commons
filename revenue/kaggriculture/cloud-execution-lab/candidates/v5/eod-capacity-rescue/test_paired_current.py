# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('eod_paired_current', HERE / 'paired_current.py')
MOD = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = MOD; SPEC.loader.exec_module(MOD)


class PairedCurrent(unittest.TestCase):
    def baseline(self, value=False):
        return {
            'main.py': b'def agent(o,c): return {}\n',
            'frozen_selected.py': b'# frozen\n',
            'eod_capacity_rescue.py': b'# helper\n',
            'TITAN-CONFIG.json': (json.dumps({'consumer':'frozen','eod_capacity_rescue':value}, indent=2)+'\n').encode(),
        }

    def test_treatment_changes_config_only(self):
        base = self.baseline(False)
        treatment, identity = MOD.treatment_members(base)
        changed = [name for name in sorted(base) if base[name] != treatment[name]]
        self.assertEqual(changed, ['TITAN-CONFIG.json'])
        self.assertIs(json.loads(base['TITAN-CONFIG.json'])['eod_capacity_rescue'], False)
        self.assertIs(json.loads(treatment['TITAN-CONFIG.json'])['eod_capacity_rescue'], True)
        self.assertEqual(set(identity['members']), set(base))
        self.assertEqual(len(identity['sha256']), 64)

    def test_baseline_bytes_are_not_mutated(self):
        base = self.baseline(False)
        before = dict(base)
        MOD.treatment_members(base)
        self.assertEqual(base, before)

    def test_missing_helper_fails_closed(self):
        base = self.baseline(False); base.pop('eod_capacity_rescue.py')
        with self.assertRaises(ValueError): MOD.treatment_members(base)

    def test_true_baseline_fails_closed(self):
        with self.assertRaises(ValueError): MOD.treatment_members(self.baseline(True))

    def test_non_bool_feature_fails_closed(self):
        base = self.baseline(False)
        base['TITAN-CONFIG.json'] = b'{"eod_capacity_rescue": 0}\n'
        with self.assertRaises(ValueError): MOD.treatment_members(base)


if __name__ == '__main__':
    unittest.main()
