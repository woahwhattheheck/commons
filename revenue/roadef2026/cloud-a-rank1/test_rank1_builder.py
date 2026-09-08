#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


def load(path: Path):
    spec = importlib.util.spec_from_file_location("rank1_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuilderTests(unittest.TestCase):
    def test_inserts_once_and_preserves_normal_dispatch(self):
        source = "class X {\npublic:\n    void run() {\n}\n};\n" + self.mod.MAIN_OLD
        changed = self.mod.transform(source)
        self.assertEqual(changed.count(self.mod.MARKER), 1)
        self.assertIn('setting("FLEET_RANK1", 0) != 0', changed)
        self.assertIn("else solver.run();", changed)

    def test_reapplication_rejected(self):
        source = "class X {\npublic:\n    void run() {\n}\n};\n" + self.mod.MAIN_OLD
        with self.assertRaisesRegex(ValueError, "already"):
            self.mod.transform(self.mod.transform(source))

    def test_missing_and_duplicate_anchors_rejected(self):
        with self.assertRaisesRegex(ValueError, "run"):
            self.mod.transform(self.mod.MAIN_OLD)
        source = "\n    void run() {\n\n    void run() {\n" + self.mod.MAIN_OLD
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.mod.transform(source)

    def test_real_source_compiles(self):
        changed = self.mod.transform(self.source.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder) / "main.cpp"
            binary = Path(folder) / "candidate"
            cpp.write_text(changed, encoding="utf-8")
            result = subprocess.run([
                "g++", "-std=c++20", "-O2", "-DNDEBUG", "-Wall", "-Wextra", "-Werror",
                "-I", str(self.vendor), str(cpp), "-o", str(binary)
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            invoked = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(invoked.returncode, 2)
            self.assertIn("Usage:", invoked.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--vendor", type=Path, required=True)
    args, rest = parser.parse_known_args()
    BuilderTests.mod = load(args.builder)
    BuilderTests.source = args.source
    BuilderTests.vendor = args.vendor
    unittest.main(argv=[__file__, *rest])
