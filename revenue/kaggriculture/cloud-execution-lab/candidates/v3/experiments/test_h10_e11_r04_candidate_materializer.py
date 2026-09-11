#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "h10_materializer", HERE / "materialize_h10_e11_r04_candidate.py"
)
materializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materializer)


class H10CandidateMaterializerTests(unittest.TestCase):
    def _package(self, root: Path, overrides=None):
        root.mkdir(parents=True, exist_ok=True)
        config = dict(materializer.EXPECTED_CONFIG)
        config.update(overrides or {})
        (root / "TITAN-CONFIG.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
        (root / "main.py").write_text(
            "def agent(observation, configuration=None):\n"
            "    return {'farmer':['PASS'],'hands':[],'market':[]}\n",
            encoding="utf-8",
        )
        (root / "scheduler.py").write_text(
            "def absorption(item, step, shops, config):\n"
            "    return 1 if step % int(config.get('townCenterSellInterval', 24)) == 0 else 0\n",
            encoding="utf-8",
        )
        (root / "r04_full_router.py").write_text("_POLICY = None\n", encoding="utf-8")
        (root / "e11_rival_sell.py").write_text(
            "def apply_e11(observation, action, history, cfg, absorption_fn, enabled=False):\n"
            "    return action, {'changed': False, 'enabled': bool(enabled)}\n",
            encoding="utf-8",
        )

    def _archive(self, tree: Path, archive: Path) -> str:
        with tarfile.open(archive, "w:gz") as handle:
            for path in sorted(tree.iterdir()):
                handle.add(path, arcname=path.name, recursive=True)
        return hashlib.sha256(archive.read_bytes()).hexdigest()

    def test_materialized_candidate_binds_scheduler_absorption_and_live_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tree = tmp / "tree"
            self._package(tree)
            archive = tmp / "package.tar.gz"
            digest = self._archive(tree, archive)
            out = tmp / "out"
            receipt = materializer.materialize(archive, out, digest)

            self.assertEqual(receipt["input_archive_sha256"], digest)
            self.assertEqual(receipt["absorption_callable"], "scheduler.absorption")
            self.assertEqual(receipt["entrypoint"], "h10_candidate.py:agent")
            self.assertEqual(receipt["baseline_config"], materializer.EXPECTED_CONFIG)
            self.assertTrue((out / "h10_e11_r04_reachability.py").is_file())
            self.assertTrue((out / "H10-CARRIER-RECEIPT.json").is_file())
            self.assertFalse((tree / "h10_candidate.py").exists())

            code = f"""
import importlib.util
from pathlib import Path
p = Path({str(out / 'h10_candidate.py')!r})
spec = importlib.util.spec_from_file_location('h10_candidate_exact', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.agent)
assert module.ABSORPTION_FN is module.scheduler.absorption
assert module.CUSTODY['absorption_callable'] == 'scheduler.absorption'
assert module.CUSTODY['baseline_config'] == module.EXPECTED_CONFIG
assert module.agent.h10_custody == module.CUSTODY
print('H10_CANDIDATE_IMPORT_OK')
"""
            run = subprocess.run(
                [sys.executable, "-I", "-B", "-c", code],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("H10_CANDIDATE_IMPORT_OK", run.stdout)

    def test_wrong_archive_sha_fails_before_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tree = tmp / "tree"
            self._package(tree)
            archive = tmp / "package.tar.gz"
            self._archive(tree, archive)
            out = tmp / "out"
            with self.assertRaisesRegex(RuntimeError, "SHA256 mismatch"):
                materializer.materialize(archive, out, "0" * 64)
            self.assertFalse(out.exists())

    def test_config_bool_int_confusion_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tree = tmp / "tree"
            self._package(tree, {"r04_row_order": 1})
            archive = tmp / "package.tar.gz"
            digest = self._archive(tree, archive)
            with self.assertRaisesRegex(RuntimeError, "r04_row_order"):
                materializer.materialize(archive, tmp / "out", digest)

    def test_source_mode_package_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tree = tmp / "tree"
            self._package(tree, {"r04_sale_window": False})
            archive = tmp / "package.tar.gz"
            digest = self._archive(tree, archive)
            with self.assertRaisesRegex(RuntimeError, "r04_sale_window"):
                materializer.materialize(archive, tmp / "out", digest)

    def test_unsafe_tar_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                info = tarfile.TarInfo("../escape.py")
                data = b"bad\n"
                info.size = len(data)
                handle.addfile(info, io.BytesIO(data))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(RuntimeError, "unsafe archive member path"):
                materializer.materialize(archive, tmp / "out", digest)


if __name__ == "__main__":
    unittest.main()
