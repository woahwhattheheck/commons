# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import materialize_factorial as materializer


MAIN = "def agent(observation, configuration=None):\n    return {}\n"
OWN = (
    "class MarketPath:\n"
    "    def score(self):\n"
    "        own_cash=carry=other_cash=remaining=0\n"
    + materializer.OWN_OLD.decode("utf-8")
)
PRESSURE = (
    "from collections.abc import Mapping\n"
    "from typing import Callable\n"
    "PriceFunction = Callable\n"
    + materializer.PRESSURE_SIGNATURE_OLD.decode("utf-8")
    + "    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):\n"
      "        raise ValueError\n"
      "    orders=[]; scores=[]; start=0; stop=0\n"
      "    if True:\n"
    + materializer.PRESSURE_RANKING_OLD.decode("utf-8")
    + "    return action\n"
)
RUNTIME = (
    "class Runtime:\n"
    "    def f(self, pressure, selected, obs, cfg, mechanics):\n"
    + materializer.RUNTIME_CALL_OLD.decode("utf-8")
    + "        return result\n"
)


def fixture(root: Path) -> None:
    root.mkdir()
    (root / "main.py").write_text(MAIN, encoding="utf-8")
    (root / materializer.OWN_FILE).write_text(OWN, encoding="utf-8")
    (root / materializer.PRESSURE_FILE).write_text(PRESSURE, encoding="utf-8")
    (root / materializer.RUNTIME_FILE).write_text(RUNTIME, encoding="utf-8")


class ArmPatchTests(unittest.TestCase):
    def _apply(self, arm: str):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "root"
        fixture(root)
        before = {name: (root / name).read_bytes() for name in (
            materializer.OWN_FILE,
            materializer.PRESSURE_FILE,
            materializer.RUNTIME_FILE,
        )}
        receipts = materializer.apply_arm(root, arm)
        after = {name: (root / name).read_bytes() for name in before}
        return temporary, root, before, after, receipts

    def test_control_changes_nothing(self):
        temporary, _, before, after, receipts = self._apply("control")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(before, after)
        self.assertEqual(receipts, [])

    def test_own_only_changes_only_objective(self):
        temporary, _, before, after, receipts = self._apply("own_only")
        self.addCleanup(temporary.cleanup)
        self.assertNotEqual(before[materializer.OWN_FILE], after[materializer.OWN_FILE])
        self.assertEqual(before[materializer.PRESSURE_FILE], after[materializer.PRESSURE_FILE])
        self.assertEqual(before[materializer.RUNTIME_FILE], after[materializer.RUNTIME_FILE])
        self.assertEqual([item["label"] for item in receipts], ["own-value objective"])
        self.assertIn(materializer.OWN_NEW, after[materializer.OWN_FILE])

    def test_strict_only_changes_pressure_and_runtime(self):
        temporary, _, before, after, receipts = self._apply("strict_only")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(before[materializer.OWN_FILE], after[materializer.OWN_FILE])
        self.assertNotEqual(before[materializer.PRESSURE_FILE], after[materializer.PRESSURE_FILE])
        self.assertNotEqual(before[materializer.RUNTIME_FILE], after[materializer.RUNTIME_FILE])
        labels = [item["label"] for item in receipts]
        self.assertEqual(
            labels,
            [
                "strict-dominance signature",
                "strict-dominance validation",
                "strict-dominance ranking",
                "strict-dominance runtime call",
            ],
        )
        self.assertIn(b"strict_dominance=True", after[materializer.RUNTIME_FILE])
        self.assertIn(b"if strict_dominance:", after[materializer.PRESSURE_FILE])

    def test_both_is_exact_union_of_factor_bytes(self):
        own_tmp, _, _, own_after, _ = self._apply("own_only")
        strict_tmp, _, _, strict_after, _ = self._apply("strict_only")
        both_tmp, _, _, both_after, receipts = self._apply("both")
        self.addCleanup(own_tmp.cleanup)
        self.addCleanup(strict_tmp.cleanup)
        self.addCleanup(both_tmp.cleanup)
        self.assertEqual(both_after[materializer.OWN_FILE], own_after[materializer.OWN_FILE])
        self.assertEqual(both_after[materializer.PRESSURE_FILE], strict_after[materializer.PRESSURE_FILE])
        self.assertEqual(both_after[materializer.RUNTIME_FILE], strict_after[materializer.RUNTIME_FILE])
        self.assertEqual(len(receipts), 5)

    def test_reapplying_factor_fails_closed(self):
        temporary, root, _, _, _ = self._apply("both")
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(materializer.MaterializationError, "cardinality"):
            materializer.apply_arm(root, "both")

    def test_unknown_arm_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            fixture(root)
            with self.assertRaisesRegex(materializer.MaterializationError, "unknown arm"):
                materializer.apply_arm(root, "mystery")


class SafeExtractionTests(unittest.TestCase):
    def _archive(self, path: Path, name: str, data: bytes = b"x") -> None:
        with tarfile.open(path, "w:gz") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))

    def test_regular_file_extracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "ok.tar.gz"
            self._archive(archive, "nested/file.txt", b"hello")
            destination = root / "out"
            members = materializer.safe_extract(archive, destination)
            self.assertEqual(members, ["nested/file.txt"])
            self.assertEqual((destination / "nested/file.txt").read_bytes(), b"hello")

    def test_parent_traversal_is_rejected_and_cleaned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "bad.tar.gz"
            self._archive(archive, "../escape.txt")
            destination = root / "out"
            with self.assertRaisesRegex(materializer.MaterializationError, "unsafe"):
                materializer.safe_extract(archive, destination)
            self.assertFalse(destination.exists())
            self.assertFalse((root / "escape.txt").exists())

    def test_symbolic_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "link.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("link")
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                tar.addfile(info)
            destination = root / "out"
            with self.assertRaisesRegex(materializer.MaterializationError, "unsupported"):
                materializer.safe_extract(archive, destination)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
