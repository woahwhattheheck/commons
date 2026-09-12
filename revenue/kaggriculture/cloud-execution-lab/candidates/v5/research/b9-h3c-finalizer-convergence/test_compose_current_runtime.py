# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location(
    "b9_h3c_finalizer_composer", HERE / "compose_current_runtime.py"
)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


class B9H3CFinalizerConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.captured = M.capture_authorities(LAB)

    def test_exact_current_and_semantic_authorities_are_pinned(self):
        self.assertEqual(M.CURRENT_COMMIT, "70c31154193f6f993a117284ba35e10bf5434ca9")
        for name, raw in self.captured.items():
            with self.subTest(name=name):
                self.assertEqual(M.git_blob(raw), M.PINS[name])
        self.assertEqual(
            M.PINS["outer_wrappers_current.py"],
            "c56b65d12a0886ddb2c26bc49a35f76899b48c98",
        )
        self.assertEqual(
            M.PINS["b9_terminal_fertilizer.py"],
            "ed8d6923541e700c3a0ae4b93695bbd56455a3b6",
        )
        self.assertEqual(
            M.PINS["h3c_goose_eod_cap_rescue.py"],
            "2044d6cf1e0c51f95027229863f910aa43ac7008",
        )

    def test_materialization_is_additive_default_off_and_compiles(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "postimage"
            receipt = M.materialize(LAB, output)
            self.assertFalse(receipt["production_activation"])
            self.assertEqual(receipt["integration"]["producer_calls_added"], 0)

            runtime = (output / "titan_runtime.py").read_text()
            build = (output / "build_integrated.py").read_text()
            config = json.loads((output / "TITAN-CONFIG.json").read_text())
            compile(runtime, "<runtime-postimage>", "exec")
            compile(build, "<build-postimage>", "exec")
            self.assertIs(config["terminal_fertilizer"], False)
            self.assertIs(config["goose_rescue"], False)

            self.assertEqual(
                M.git_blob((output / "b9_h3c/outer_wrappers_current.py").read_bytes()),
                M.PINS["outer_wrappers_current.py"],
            )
            self.assertEqual(
                M.git_blob(
                    (output / "b9_h3c/vendor/b9_terminal_fertilizer.py").read_bytes()
                ),
                M.PINS["b9_terminal_fertilizer.py"],
            )
            self.assertEqual(
                M.git_blob(
                    (output / "b9_h3c/vendor/h3c_goose_eod_cap_rescue.py").read_bytes()
                ),
                M.PINS["h3c_goose_eod_cap_rescue.py"],
            )

    def test_single_producer_topology_and_outer_order_are_source_real(self):
        before = self.captured["titan_runtime.py"].decode()
        after = M.compose_runtime(before)

        self.assertEqual(
            after.count("self.production.act("),
            before.count("self.production.act("),
        )

        early = after.index(
            "returned = self._early_capital_selected(obs, cfg or {}, returned)"
        )
        outer = after.index(
            "returned, post = self._b9_h3c_selected(obs, cfg or {}, returned, post)"
        )
        quadrant = after.index("if self.quadrant is not None:", outer)
        history = after.index("self.history.remember(", outer)
        self.assertLess(early, outer)
        self.assertLess(outer, quadrant)
        self.assertLess(outer, history)

        authority = self.captured["outer_wrappers_current.py"].decode()
        self.assertIn(
            '"order": ("terminal_fertilizer", "goose_rescue")',
            authority,
        )

    def test_fallback_is_identity_and_unit_changes_rebind_post_snapshot(self):
        after = M.compose_runtime(self.captured["titan_runtime.py"].decode())
        helper_start = after.index("    def _b9_h3c_selected(")
        helper_end = after.index("    def _seed_selected(", helper_start)
        helper = after[helper_start:helper_end]

        self.assertIn("self.diagnostics.get('status') != 'completed'", helper)
        self.assertIn("'reason': 'deadline_fallback_identity'", helper)
        self.assertIn("prior_state = deepcopy(adapter._b9_state)", helper)
        self.assertIn("farm, private = post_units(obs, result, cfg)", helper)
        self.assertIn("adapter._b9_state = prior_state", helper)
        self.assertIn("checkpoint(obs, result, 'b9_h3c')", helper)

    def test_feature_keys_are_exact_bool_and_nonterminal_frozen_only(self):
        after = M.compose_runtime(self.captured["titan_runtime.py"].decode())
        self.assertIn(
            "bool_fields = (*bool_fields, 'exec_pace', 'terminal_fertilizer', 'goose_rescue')",
            after,
        )
        self.assertIn(
            "if ((self.terminal_fertilizer or self.goose_rescue)",
            after,
        )
        self.assertIn(
            "and (self.consumer != 'frozen' or self.terminal_route))",
            after,
        )

    def test_archive_mapping_carries_exact_canonical_module_and_donors(self):
        after = M.compose_build(self.captured["build_integrated.py"].decode())
        for path in (
            "b9_h3c/outer_wrappers_current.py",
            "b9_h3c/vendor/b9_terminal_fertilizer.py",
            "b9_h3c/vendor/h3c_goose_eod_cap_rescue.py",
        ):
            self.assertIn(f"mapping['{path}']='{path}'", after)

    def test_drift_and_double_application_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "drift"):
            M._require_pin("titan_runtime.py", b"not current runtime")
        rendered = M.compose_runtime(self.captured["titan_runtime.py"].decode())
        with self.assertRaisesRegex(ValueError, "already present"):
            M.compose_runtime(rendered)
        rendered_config = M.compose_config(self.captured["TITAN-CONFIG.json"].decode())
        with self.assertRaisesRegex(ValueError, "already present"):
            M.compose_config(rendered_config)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "postimage"
            output.mkdir()
            sentinel = output / "sentinel"
            sentinel.write_text("keep")
            with self.assertRaises(FileExistsError):
                M.materialize(LAB, output)
            self.assertEqual(sentinel.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
