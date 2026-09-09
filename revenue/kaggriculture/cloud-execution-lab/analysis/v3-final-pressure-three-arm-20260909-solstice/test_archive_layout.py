from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import evidence
import game_runner
import run_final_pressure_panel_v2 as corrected


class ArchiveLayoutTests(unittest.TestCase):
    def _release_tree(self, root: Path) -> tuple[Path, Path, Path]:
        evaluator = root / "reference/evaluator/evaluate.py"
        loader = root / "reference/evaluator/loader.py"
        engine = root / "reference/engine"
        evaluator.parent.mkdir(parents=True)
        engine.mkdir(parents=True)
        evaluator.write_text("# evaluator\n", encoding="utf-8")
        loader.write_text("# loader\n", encoding="utf-8")
        for name in ("kaggriculture.py", "kaggriculture.json", "utils.py"):
            (engine / name).write_text(name + "\n", encoding="utf-8")
        return evaluator, loader, engine

    def test_loader_binds_root_reference_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluator_path, loader, engine_dir = self._release_tree(root)
            fake_evaluator = SimpleNamespace(
                ENGINE_REF=game_runner.ENGINE_REF,
                get_engine=lambda engine, loader_path: (
                    "ENGINE",
                    {"engine": "bound"},
                ),
            )
            with patch.object(
                game_runner,
                "import_file",
                return_value=fake_evaluator,
            ) as imported:
                evaluator, engine, got_engine_dir, got_loader, receipt = (
                    corrected.load_release_evaluator(root)
                )
            imported.assert_called_once_with(
                evaluator_path,
                "titan_final_pressure_evaluator_release_layout",
            )
            self.assertIs(evaluator, fake_evaluator)
            self.assertEqual(engine, "ENGINE")
            self.assertEqual(got_engine_dir, engine_dir)
            self.assertEqual(got_loader, loader)
            self.assertEqual(receipt["archive_layout"], "reference/**")
            self.assertEqual(
                receipt["evaluator_sha256"],
                evidence.snapshot(evaluator_path).sha256,
            )
            self.assertEqual(
                receipt["loader_sha256"], evidence.snapshot(loader).sha256
            )

    def test_development_checks_prefix_does_not_satisfy_release_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrong = root / "checks"
            self._release_tree(wrong)
            with self.assertRaisesRegex(
                evidence.EvidenceError,
                r"Missing evaluator input: reference/evaluator/evaluate\.py",
            ):
                corrected.load_release_evaluator(root)

    def test_engine_ref_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._release_tree(root)
            fake_evaluator = SimpleNamespace(
                ENGINE_REF="wrong",
                get_engine=lambda *_: ("ENGINE", {}),
            )
            with patch.object(
                game_runner,
                "import_file",
                return_value=fake_evaluator,
            ):
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "Engine ref drift"
                ):
                    corrected.load_release_evaluator(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
