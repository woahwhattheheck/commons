# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import unittest

import build_candidate


class BuildContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload, cls.receipt = build_candidate.render()

    def test_render_is_deterministic(self):
        payload, receipt = build_candidate.render()
        self.assertEqual(payload, self.payload)
        self.assertEqual(receipt, self.receipt)

    def test_archive_verifies_and_declares_nonmutation(self):
        build_candidate.verify_archive(self.payload, self.receipt)
        self.assertFalse(self.receipt["canonical_release_mutated"])

    def test_manifest_binds_overlay_and_scheduler(self):
        with tarfile.open(fileobj=io.BytesIO(self.payload), mode="r:gz") as archive:
            manifest = json.load(archive.extractfile("SOURCE.json"))
        self.assertIn("multi_lot_portfolio.py", manifest["runtime"])
        self.assertIn("+multi-lot-patch-v1", manifest["runtime"]["scheduler.py"]["source_path"])

    def test_archive_scheduler_and_main_import_in_isolated_process(self):
        with tempfile.TemporaryDirectory(prefix="titan-multi-lot-") as directory:
            root = Path(directory)
            with tarfile.open(fileobj=io.BytesIO(self.payload), mode="r:gz") as archive:
                members = archive.getmembers()
                for member in members:
                    path = PurePosixPath(member.name)
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertTrue(member.isfile())
                archive.extractall(root, members=members)
            code = r'''
import importlib.util
from pathlib import Path
import sys
root = Path.cwd()
sys.path.insert(0, str(root))
for name, filename in (
    ("titan_multi_lot_archive_scheduler", "scheduler.py"),
    ("titan_multi_lot_archive_main", "main.py"),
):
    spec = importlib.util.spec_from_file_location(name, root / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    assert callable(module.agent)
'''
            result = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"isolated archive import failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
