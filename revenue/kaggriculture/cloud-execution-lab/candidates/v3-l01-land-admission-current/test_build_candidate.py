# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from build_candidate import (
    ENTRYPOINT_NEEDLE,
    ENTRYPOINT_REPLACEMENT,
    build,
    patch_entrypoint,
)


class BuildCandidateTests(unittest.TestCase):
    def test_build_is_archive_bound_and_wraps_every_reconstruction(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lab = root / "lab"
            export = lab / "exports"
            runtime = lab / "runtime/integrated-selected"
            export.mkdir(parents=True)
            runtime.mkdir(parents=True)

            # Model the current deadline-aware shape: _new_instance has one
            # construction boundary but agent can call it from two branches.
            source_main = (
                "_INSTANCE = None\n\n"
                "def _new_instance(root, feature_data):\n"
                "    def FinalPressureAgent(*args, **kwargs):\n"
                "        return object()\n"
                "    features = feature_data\n"
                "    admission = None\n"
                + ENTRYPOINT_NEEDLE
                + "\n"
                "def agent(step):\n"
                "    global _INSTANCE\n"
                "    replace = _INSTANCE is None or step == 0\n"
                "    if step < 0 and replace:\n"
                "        _INSTANCE = _new_instance(None, {})\n"
                "    try:\n"
                "        if replace:\n"
                "            _INSTANCE = _new_instance(None, {})\n"
                "    except TimeoutError:\n"
                "        _INSTANCE = None\n"
                "    return _INSTANCE\n"
            )
            package = root / "package"
            package.mkdir()
            (package / "main.py").write_text(source_main, encoding="utf-8")
            (package / "TITAN-CONFIG.json").write_text("{}\n", encoding="utf-8")
            archive = export / "titan-current.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                handle.add(package / "main.py", arcname="main.py")
                handle.add(
                    package / "TITAN-CONFIG.json",
                    arcname="TITAN-CONFIG.json",
                )

            source_manifest = runtime / "CURRENT-SOURCE.json"
            source_manifest.write_text('{"schema":"test"}\n', encoding="utf-8")
            manifest = {
                "path": "exports/titan-current.tar.gz",
                "entrypoint": "main.py::agent",
                "config": "TITAN-CONFIG.json",
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "bytes": archive.stat().st_size,
                "runtime_files": 2,
                "source_manifest": (
                    "runtime/integrated-selected/CURRENT-SOURCE.json"
                ),
                "source_manifest_sha256": hashlib.sha256(
                    source_manifest.read_bytes()
                ).hexdigest(),
            }
            (runtime / "CURRENT-ARCHIVE.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )
            mechanism = root / "land_admission.py"
            mechanism.write_text(
                "def wrap(value):\n    return value\n",
                encoding="utf-8",
            )

            receipt = build(lab, root / "out", mechanism)
            baseline = (root / "out/baseline/main.py").read_text(encoding="utf-8")
            candidate = (root / "out/land/main.py").read_text(encoding="utf-8")
            self.assertEqual(baseline, source_main)
            self.assertEqual(candidate.count(ENTRYPOINT_REPLACEMENT), 1)
            self.assertNotIn(ENTRYPOINT_NEEDLE, candidate)
            self.assertEqual(
                candidate.count(
                    "from land_admission import wrap as _wrap_land_admission"
                ),
                1,
            )
            self.assertEqual(candidate.count("_INSTANCE = _new_instance"), 2)
            self.assertEqual(receipt["hook_surface"], "_new_instance.return")
            self.assertEqual(receipt["baseline_runtime_files"], 2)
            self.assertEqual(receipt["candidate_runtime_files"], 3)
            self.assertNotEqual(
                receipt["baseline_tree_sha256"],
                receipt["candidate_tree_sha256"],
            )

    def test_patch_rejects_constructor_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "main.py"
            source = "def _new_instance():\n    return object()\n"
            path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "constructor hook site"):
                patch_entrypoint(path)
            self.assertEqual(path.read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
