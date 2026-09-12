# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location('overflow_compose', HERE / 'compose_current_runtime.py')
compose = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compose)


class OverflowCurrentRuntimeComposerTests(unittest.TestCase):
    def test_root_helper_is_exact_canonical_bytes(self):
        compose._authenticate_helper(ROOT)
        self.assertEqual(
            (ROOT / 'overflow_safe_drop.py').read_bytes(),
            (ROOT / compose.CANONICAL).read_bytes(),
        )

    def test_runtime_adds_exact_bool_and_nonterminal_frozen_guard(self):
        source = (ROOT / 'titan_runtime.py').read_text()
        rendered = compose.compose_runtime(source)
        self.assertIn('    overflow_safe_drop: bool = False\n', rendered)
        self.assertIn("bool_fields = (*bool_fields, 'exec_pace', 'overflow_safe_drop')", rendered)
        self.assertIn(
            "if self.overflow_safe_drop and (self.consumer != 'frozen' or self.terminal_route):",
            rendered,
        )
        with self.assertRaises(ValueError):
            compose.compose_runtime(rendered)

    def test_main_places_overflow_after_town_and_suppresses_terminal(self):
        source = (ROOT / 'main.py').read_text()
        rendered = compose.compose_main(source)
        town = rendered.index("self._checkpoint_finalizer(obs, returned, 'town_procurement')")
        overflow = rendered.index("if features.overflow_safe_drop and completed:")
        transform = rendered.index("from overflow_safe_drop import transform")
        checkpoint = rendered.index("self._checkpoint_finalizer(obs, returned, 'overflow_safe_drop')")
        self.assertLess(town, overflow)
        self.assertLess(overflow, transform)
        self.assertLess(transform, checkpoint)
        self.assertIn("obs['step'] == episode_steps - 2", rendered)
        self.assertIn("'terminal_or_invalid_episode_suppressed'", rendered)
        terminal_block = rendered[overflow:transform]
        self.assertNotIn("_checkpoint_finalizer(obs, returned, 'overflow_safe_drop')", terminal_block)
        with self.assertRaises(ValueError):
            compose.compose_main(rendered)

    def test_config_default_is_false_and_type_is_literal_bool(self):
        rendered = compose.compose_config((ROOT / 'TITAN-CONFIG.json').read_text())
        payload = json.loads(rendered)
        self.assertIs(payload['overflow_safe_drop'], False)
        with self.assertRaises(ValueError):
            compose.compose_config(rendered)

    def test_build_maps_root_helper_and_existing_canonical_helper_tests(self):
        source = (ROOT / 'build_integrated.py').read_text()
        rendered = compose.compose_build(source)
        self.assertIn("'overflow_safe_drop.py'", rendered)
        self.assertIn(
            "mapping['checks/test_overflow_safe_drop.py']='candidates/v5/research/overflow-safe-drop/test_overflow_safe_drop.py'",
            rendered,
        )
        with self.assertRaises(ValueError):
            compose.compose_build(rendered)

    def test_materialize_emits_only_four_integration_postimages(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'postimage'
            outputs = compose.materialize(ROOT, out)
            self.assertEqual(set(outputs), set(compose.TARGETS))
            self.assertEqual({p.name for p in out.iterdir()}, set(compose.TARGETS))
            self.assertIn('overflow_safe_drop', outputs['main.py'].read_text())
            self.assertIn('overflow_safe_drop', outputs['titan_runtime.py'].read_text())
            self.assertIs(json.loads(outputs['TITAN-CONFIG.json'].read_text())['overflow_safe_drop'], False)
            self.assertIn('overflow_safe_drop.py', outputs['build_integrated.py'].read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
