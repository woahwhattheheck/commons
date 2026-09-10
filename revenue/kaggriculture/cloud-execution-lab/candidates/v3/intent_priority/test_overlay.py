# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("intent_priority_overlay", HERE / "build_overlay.py")
assert SPEC and SPEC.loader
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


class OverlayContracts(unittest.TestCase):
    def test_build_is_source_inert_and_entrypoint_imports(self):
        before = {
            name: (LAB / name).read_bytes()
            for name in ("main.py", "scheduler.py")
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "overlay"
            receipt_path = root / "receipt.json"
            receipt = b.build(LAB, output, receipt_path)
            self.assertEqual(
                sorted(path.name for path in output.iterdir()),
                ["entrypoint.py", "scheduler.py"],
            )
            self.assertEqual(
                receipt["execution_surface"]["entrypoint"],
                "entrypoint.py::agent",
            )
            self.assertEqual(json.loads(receipt_path.read_text()), receipt)
            probe = (
                "import runpy,sys; "
                "ns=runpy.run_path(sys.argv[1]); "
                "assert callable(ns['agent']); "
                "import scheduler; "
                "assert scheduler.__file__ == sys.argv[2]"
            )
            completed = subprocess.run(
                [sys.executable, "-B", "-I", "-c", probe,
                 str(output / "entrypoint.py"), str(output / "scheduler.py")],
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
        for name, data in before.items():
            self.assertEqual((LAB / name).read_bytes(), data)

    def test_output_inside_source_fails_closed(self):
        with self.assertRaisesRegex(b.OverlayError, "outside canonical"):
            b.build(LAB, LAB / "generated-intent-priority", LAB / "receipt.json")

    def test_nonempty_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "overlay"
            output.mkdir()
            (output / "foreign").write_text("occupied")
            with self.assertRaisesRegex(b.OverlayError, "absent or empty"):
                b.build(LAB, output, Path(directory) / "receipt.json")


if __name__ == "__main__":
    unittest.main()
