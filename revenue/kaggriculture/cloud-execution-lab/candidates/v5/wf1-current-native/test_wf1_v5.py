#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


materialize = load(HERE / 'materialize.py', 'wf1_v5_materialize_tested')


class Wf1V5ConvergenceTest(unittest.TestCase):
    def test_canonical_source_pins_and_evidence(self):
        source = materialize.SOURCE_ROOT / 'candidates/v4/repairs/gameplay/wf1-wheat-fertilize'
        for name, expected in materialize.PINS.items():
            with self.subTest(name=name):
                self.assertEqual(materialize.git_blob_sha((source / name).read_bytes()), expected)
        receipt = json.loads((source / 'WF1-CURRENT-NATIVE-FIELD-RECEIPT.json').read_text())
        self.assertEqual(receipt['validation']['complete_cells'], 8)
        self.assertEqual(receipt['validation']['game_failures'], 0)
        self.assertEqual(receipt['summary']['positive_margin_cells'], 8)
        self.assertEqual(receipt['summary']['negative_margin_cells'], 0)
        self.assertEqual(receipt['summary']['mean_margin_delta'], 143.25)
        self.assertEqual(receipt['summary']['mean_own_delta'], 132.375)

    def test_materialize_preserves_baseline_and_records_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / 'runtime'
            output = root / 'candidate'
            runtime.mkdir()
            main_bytes = b"VALUE = 'baseline'\n"
            config_bytes = b'{"consumer":"frozen"}\n'
            (runtime / 'main.py').write_bytes(main_bytes)
            (runtime / 'TITAN-CONFIG.json').write_bytes(config_bytes)
            expected_main = materialize.git_blob_sha(main_bytes)
            expected_config = materialize.git_blob_sha(config_bytes)
            receipt = materialize.materialize(
                runtime, output,
                expected_main_blob=expected_main,
                expected_config_blob=expected_config,
            )
            self.assertEqual((output / 'main.py').read_bytes(), main_bytes)
            self.assertEqual((output / 'TITAN-CONFIG.json').read_bytes(), config_bytes)
            self.assertTrue((output / 'r04_wheat_fert.py').is_file())
            self.assertTrue((output / 'wf1_current_adapter.py').is_file())
            self.assertTrue((output / 'wf1_v5_entry.py').is_file())
            self.assertEqual(receipt['baseline']['main_git_blob'], expected_main)
            self.assertEqual(receipt['baseline']['config_git_blob'], expected_config)
            self.assertEqual(receipt['component']['ordering'], 'after_parent_main_agent')
            persisted = json.loads((output / 'WF1-V5-MATERIALIZATION.json').read_text())
            self.assertEqual(persisted, receipt)

    def test_baseline_drift_fails_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / 'runtime'
            output = root / 'candidate'
            runtime.mkdir()
            config = b'{}\n'
            (runtime / 'main.py').write_text('x = 1\n')
            (runtime / 'TITAN-CONFIG.json').write_bytes(config)
            with self.assertRaisesRegex(ValueError, 'main.py identity mismatch'):
                materialize.materialize(
                    runtime, output,
                    expected_main_blob='0' * 40,
                    expected_config_blob=materialize.git_blob_sha(config),
                )
            self.assertFalse(output.exists())

    def test_nested_output_fails_before_mutating_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / 'runtime'
            output = runtime / 'candidate'
            runtime.mkdir()
            main_bytes = b"VALUE = 'baseline'\n"
            config_bytes = b'{}\n'
            (runtime / 'main.py').write_bytes(main_bytes)
            (runtime / 'TITAN-CONFIG.json').write_bytes(config_bytes)
            before = sorted(path.relative_to(runtime).as_posix()
                            for path in runtime.rglob('*'))
            with self.assertRaisesRegex(ValueError, 'outside runtime'):
                materialize.materialize(
                    runtime, output,
                    expected_main_blob=materialize.git_blob_sha(main_bytes),
                    expected_config_blob=materialize.git_blob_sha(config_bytes),
                )
            self.assertFalse(output.exists())
            self.assertEqual(
                sorted(path.relative_to(runtime).as_posix()
                       for path in runtime.rglob('*')),
                before,
            )
            self.assertEqual((runtime / 'main.py').read_bytes(), main_bytes)
            self.assertEqual((runtime / 'TITAN-CONFIG.json').read_bytes(), config_bytes)

    def test_entry_calls_parent_before_outer_wf1_transform(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy2(HERE / 'entry.py', root / 'entry.py')
            (root / 'main.py').write_text(
                "def agent(observation, configuration=None):\n"
                "    return {'trace':['parent']}\n",
                encoding='utf-8')
            (root / 'wf1_current_adapter.py').write_text(
                "def apply_wf1_current(observation, action, configuration, enabled=False):\n"
                "    assert enabled is True\n"
                "    return {'trace': action['trace'] + ['wf1']}\n",
                encoding='utf-8')
            entry = load(root / 'entry.py', 'wf1_v5_entry_order_test')
            self.assertEqual(entry.agent({'step': 1}, {}), {'trace': ['parent', 'wf1']})


if __name__ == '__main__':
    unittest.main()
