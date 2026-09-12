# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LAB = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(HERE))

from compose_v5_carebank import (
    CONFIG_BLOB,
    HELPER_BLOB,
    HELPER_RELATIVE,
    RUNTIME_BLOB,
    git_blob_id,
    materialize,
    patch_config,
    patch_runtime,
)


def _features_class(source: str):
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == "Features")
    lines = source.splitlines(keepends=True)
    start = min((decorator.lineno for decorator in node.decorator_list), default=node.lineno)
    text = "".join(lines[start - 1 : node.end_lineno])
    namespace = {"__name__": __name__, "dataclass": dataclass, "math": math}
    exec(text, namespace)
    return namespace["Features"]


class V5CarebankComposerTests(unittest.TestCase):
    def test_source_pins_match_current_v5_and_existing_w2_authority(self):
        expected = {
            LAB / "titan_runtime.py": RUNTIME_BLOB,
            LAB / "TITAN-CONFIG.json": CONFIG_BLOB,
            LAB / HELPER_RELATIVE: HELPER_BLOB,
        }
        for path, blob in expected.items():
            with self.subTest(path=str(path)):
                self.assertEqual(git_blob_id(path.read_bytes()), blob)

    def test_runtime_hook_preserves_parent_fallback_then_replaces_checkpoint(self):
        out = patch_runtime((LAB / "titan_runtime.py").read_text(encoding="utf-8"))
        self.assertEqual(out.count("r04_dead_feed_care: bool = False"), 1)
        self.assertEqual(out.count("'r04_dead_feed_care',"), 1)
        producer = out.index("selected = self.production.act(obs)")
        parent = out.index("parent_checkpoint = (deepcopy(selected), self.controller.cur)", producer)
        fallback = out.index("fallback = parent_checkpoint[0]", parent)
        interim_checkpoint = out.index("selected_checkpoint = parent_checkpoint", fallback)
        repeated_feed = out.index("selected = care.apply_dead_feed_care(", interim_checkpoint)
        carebank = out.index("selected = care.apply_carebank_feed_swap(", repeated_feed)
        final_selected = out.index("self.selected = deepcopy(selected)", carebank)
        final_checkpoint = out.index("selected_checkpoint = (self.selected, self.controller.cur)", final_selected)
        transform = out.index("output = self.transform_selected(obs, cfg, selected)", final_checkpoint)
        self.assertLess(producer, parent)
        self.assertLess(parent, fallback)
        self.assertLess(fallback, interim_checkpoint)
        self.assertLess(interim_checkpoint, repeated_feed)
        self.assertLess(repeated_feed, carebank)
        self.assertLess(carebank, final_selected)
        self.assertLess(final_selected, final_checkpoint)
        self.assertLess(final_checkpoint, transform)
        ast.parse(out)

    def test_feature_is_exact_bool_and_only_nonterminal_frozen_can_enable(self):
        Features = _features_class(patch_runtime((LAB / "titan_runtime.py").read_text(encoding="utf-8")))
        self.assertIs(Features().r04_dead_feed_care, False)
        self.assertIs(Features(r04_dead_feed_care=True).r04_dead_feed_care, True)
        for bad in (0, 1, "false", [], None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    Features(r04_dead_feed_care=bad)
        for kwargs in (
            {"consumer": "parent", "r04_dead_feed_care": True},
            {"consumer": "ordered", "r04_dead_feed_care": True},
            {"consumer": "frozen", "terminal_route": True, "r04_dead_feed_care": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    Features(**kwargs)

    def test_config_is_default_off_and_enable_is_scratch_explicit(self):
        text = (LAB / "TITAN-CONFIG.json").read_text(encoding="utf-8")
        self.assertIs(json.loads(patch_config(text, enabled=False))["r04_dead_feed_care"], False)
        self.assertIs(json.loads(patch_config(text, enabled=True))["r04_dead_feed_care"], True)
        with self.assertRaises(TypeError):
            patch_config(text, enabled=1)
        with self.assertRaises(ValueError):
            patch_config(patch_config(text, enabled=False), enabled=False)

    def test_materialize_authenticates_sources_and_never_changes_input(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "package"
            package.mkdir()
            for relative in ("titan_runtime.py", "TITAN-CONFIG.json"):
                shutil.copyfile(LAB / relative, package / relative)
            before_runtime = (package / "titan_runtime.py").read_bytes()
            before_config = (package / "TITAN-CONFIG.json").read_bytes()

            control = root / "control"
            receipt = materialize(LAB, package, control, enabled=False)
            self.assertEqual(receipt["schema"], "titan-v5-carebank-current-native/v1")
            self.assertIs(receipt["enabled_in_scratch_only"], False)
            self.assertIs(receipt["production_default_changed"], False)
            self.assertEqual(receipt["consumer_contract"], "frozen_nonterminal_only")
            self.assertEqual(receipt["deadline_fallback"], "completed_parent_selected_action")
            self.assertEqual(
                receipt["selected_pipeline"],
                ["apply_dead_feed_care", "apply_carebank_feed_swap"],
            )
            self.assertIs(json.loads((control / "TITAN-CONFIG.json").read_text())["r04_dead_feed_care"], False)
            self.assertEqual(git_blob_id((control / "r04_dead_feed_care.py").read_bytes()), HELPER_BLOB)
            self.assertIn("apply_carebank_feed_swap", (control / "titan_runtime.py").read_text())

            treatment = root / "treatment"
            enabled = materialize(LAB, package, treatment, enabled=True)
            self.assertIs(enabled["enabled_in_scratch_only"], True)
            self.assertIs(json.loads((treatment / "TITAN-CONFIG.json").read_text())["r04_dead_feed_care"], True)
            self.assertEqual((package / "titan_runtime.py").read_bytes(), before_runtime)
            self.assertEqual((package / "TITAN-CONFIG.json").read_bytes(), before_config)

    def test_source_drift_fails_before_output_is_published(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "package"
            package.mkdir()
            shutil.copyfile(LAB / "titan_runtime.py", package / "titan_runtime.py")
            shutil.copyfile(LAB / "TITAN-CONFIG.json", package / "TITAN-CONFIG.json")
            (package / "titan_runtime.py").write_text(
                (package / "titan_runtime.py").read_text() + "\n# drift\n",
                encoding="utf-8",
            )
            output = root / "output"
            with self.assertRaises(ValueError):
                materialize(LAB, package, output, enabled=True)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
