# SPDX-License-Identifier: Apache-2.0
"""Private experiment metadata must not become Titan runtime features."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
if ROOT.name == 'checks':
    ROOT = ROOT.parent


def load_entrypoint():
    name = '_titan_config_metadata_boundary_test'
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, ROOT/'main.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigMetadataBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.main = load_entrypoint()

    def test_private_experiment_metadata_is_behavior_identity(self):
        plain = self.main._new_instance(ROOT, {
            'consumer': 'frozen',
            'budget_seconds': 0.8,
        })
        tagged = self.main._new_instance(ROOT, {
            'consumer': 'frozen',
            'budget_seconds': 0.8,
            '_ablation': {'market_pressure': False},
            '_run_id': 'ledger-wave1-matched',
            '_budget_seconds': 0.01,
        })
        self.assertEqual(tagged.features, plain.features)
        self.assertEqual(tagged.features.budget_seconds, 0.8)
        self.assertFalse(tagged.town_procurement_enabled)

    def test_private_metadata_does_not_interfere_with_town_procurement(self):
        tagged = self.main._new_instance(ROOT, {
            'consumer': 'frozen',
            'town_procurement': True,
            '_ablation': 'control',
        })
        self.assertTrue(tagged.town_procurement_enabled)
        self.assertEqual(tagged.features.consumer, 'frozen')

    def test_public_unknown_feature_still_fails_closed(self):
        with self.assertRaises(TypeError):
            self.main._new_instance(ROOT, {
                'consumer': 'frozen',
                'market_presure': True,
            })


if __name__ == '__main__':
    unittest.main()
