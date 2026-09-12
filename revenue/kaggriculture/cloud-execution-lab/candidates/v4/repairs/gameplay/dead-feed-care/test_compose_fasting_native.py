from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("compose_fasting_native", HERE / "compose_fasting_native.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

W2_RUNTIME = '''from dataclasses import dataclass
from copy import deepcopy
@dataclass
class Features:
    early_capital: bool = False
    r04_dead_feed_care: bool = False
class TitanAgent:
    def act(self, obs):
        cfg = {}
        if True:
            if True:
                selected = self.production.act(obs)
                # W2-BEGIN: optional CARE completes before unit-snapshot capture.
                if self.features.r04_dead_feed_care:
                    # Retain the completed parent if import/rewrite is cancelled.
                    parent_checkpoint = (deepcopy(selected), self.controller.cur)
                    fallback = parent_checkpoint[0]
                    selected_checkpoint = parent_checkpoint
                    self.selected = parent_checkpoint[0]
                    stage = 'dead_feed_care'
                    care = load('_titan_dead_feed_care',
                                HERE/'r04_dead_feed_care.py', cache=True)
                    selected = care.apply_dead_feed_care(
                        selected, obs, cfg, enabled=True)
                # W2-END: existing detached selected checkpoint and consumers.
                self.selected = deepcopy(selected)
                selected_checkpoint = (self.selected, self.controller.cur)
                fallback = selected_checkpoint[0]
                sentinel_unrelated = 7
                return selected
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ComposeFastingNativeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.pkg = self.root / "pkg"
        self.pkg.mkdir()
        (self.pkg / "titan_runtime.py").write_text(W2_RUNTIME)
        (self.pkg / "r04_dead_feed_care.py").write_text(
            "def apply_dead_feed_care(action, observation, configuration, *, enabled=False):\n    return action\n"
        )
        (self.pkg / "TITAN-CONFIG.json").write_text('{"existing":true}\n')
        self.fasting = self.root / "uncared_eod_feed_skip.py"
        self.fasting.write_text(
            "def apply_uncared_eod_feed_skip(action, observation, configuration, *, enabled=False):\n    return action\n"
        )

    def tearDown(self) -> None:
        self.td.cleanup()

    def args(self, output: Path, **kw):
        values = dict(
            package=self.pkg,
            fasting_helper=self.fasting,
            output=output,
            runtime_sha256=sha(self.pkg / "titan_runtime.py"),
            w2_helper_sha256=sha(self.pkg / "r04_dead_feed_care.py"),
            fasting_helper_sha256=sha(self.fasting),
            enable=False,
        )
        values.update(kw)
        return values

    def test_compose_runtime_orders_w2_then_fasting_then_checkpoint(self):
        out = M.compose_runtime(W2_RUNTIME)
        self.assertLess(out.index("care.apply_dead_feed_care"), out.index("fasting.apply_uncared_eod_feed_skip"))
        self.assertLess(out.index("fasting.apply_uncared_eod_feed_skip"), out.index("self.selected = deepcopy(selected)"))
        self.assertEqual(out.count(M.FASTING_MARKER), 1)
        self.assertIn("r04_uncared_eod_feed_skip: bool = False", out)
        self.assertIn("sentinel_unrelated = 7", out)
        compile(out, "runtime", "exec")

    def test_requires_existing_w2(self):
        with self.assertRaises(M.CompositionError):
            M.compose_runtime(W2_RUNTIME.replace(M.W2_MARKER, "# no w2"))

    def test_rejects_drifted_w2_seam(self):
        with self.assertRaises(M.CompositionError):
            M.compose_runtime(W2_RUNTIME.replace("selected, obs, cfg, enabled=True", "selected, obs, cfg, enabled=False"))

    def test_idempotent_exact_integrated_bytes(self):
        once = M.compose_runtime(W2_RUNTIME)
        self.assertEqual(M.compose_runtime(once), once)

    def test_rejects_partial_fasting_marker(self):
        with self.assertRaises(M.CompositionError):
            M.compose_runtime(W2_RUNTIME + "\n# FASTING-BEGIN: W2 retains precedence; FASTING sees W2's final action.\n")

    def test_materialize_disabled_keeps_config_exact_and_input_untouched(self):
        out = self.root / "out"
        runtime_before = (self.pkg / "titan_runtime.py").read_bytes()
        config_before = (self.pkg / "TITAN-CONFIG.json").read_bytes()
        result = M.materialize(**self.args(out))
        self.assertTrue(result["input_config_unchanged_when_disabled"])
        self.assertEqual((out / "TITAN-CONFIG.json").read_bytes(), config_before)
        self.assertEqual((self.pkg / "titan_runtime.py").read_bytes(), runtime_before)
        self.assertFalse((self.pkg / M.FASTING_RUNTIME_HELPER).exists())
        self.assertEqual((out / M.FASTING_RUNTIME_HELPER).read_bytes(), self.fasting.read_bytes())

    def test_materialize_enable_changes_only_scratch_config(self):
        out = self.root / "on"
        M.materialize(**self.args(out, enable=True))
        self.assertNotIn(M.FASTING_FEATURE, json.loads((self.pkg / "TITAN-CONFIG.json").read_text()))
        self.assertIs(json.loads((out / "TITAN-CONFIG.json").read_text())[M.FASTING_FEATURE], True)

    def test_wrong_runtime_hash_fails_before_output(self):
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out, runtime_sha256="0" * 64))
        self.assertFalse(out.exists())

    def test_wrong_w2_hash_fails_before_output(self):
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out, w2_helper_sha256="0" * 64))
        self.assertFalse(out.exists())

    def test_wrong_fasting_hash_fails_before_output(self):
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out, fasting_helper_sha256="0" * 64))
        self.assertFalse(out.exists())

    def test_missing_w2_api_fails_before_output(self):
        (self.pkg / "r04_dead_feed_care.py").write_text("def wrong():\n    pass\n")
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))
        self.assertFalse(out.exists())

    def test_missing_fasting_api_fails_before_output(self):
        self.fasting.write_text("def wrong():\n    pass\n")
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))
        self.assertFalse(out.exists())

    def test_existing_output_rejected(self):
        out = self.root / "out"
        out.mkdir()
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))

    def test_output_inside_package_rejected(self):
        out = self.pkg / "child"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))
        self.assertFalse(out.exists())

    def test_symlinked_parent_into_package_is_rejected_before_write(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.pkg, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        out = alias / "nested" / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))
        self.assertFalse((self.pkg / "nested").exists())

    def test_existing_fasting_helper_in_input_rejected(self):
        (self.pkg / M.FASTING_RUNTIME_HELPER).write_text("# collision\n")
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))
        self.assertFalse(out.exists())

    def test_existing_fasting_config_in_input_rejected(self):
        (self.pkg / "TITAN-CONFIG.json").write_text(json.dumps({M.FASTING_FEATURE: False}))
        out = self.root / "out"
        with self.assertRaises(M.CompositionError):
            M.materialize(**self.args(out))
        self.assertFalse(out.exists())

    def test_order_receipt_is_explicit(self):
        out = self.root / "out"
        result = M.materialize(**self.args(out))
        self.assertEqual(result["composition_order"], ["production", "W2", "FASTING", "selected_checkpoint_consumers"])
        self.assertEqual(result["policy_authority"], "none_consume_existing_w2_and_fasting_only")


if __name__ == "__main__":
    unittest.main()
