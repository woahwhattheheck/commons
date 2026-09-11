"""Focused checks for explicit-package custody in the V3.1 baseline runner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_v31_source_baseline as baseline  # noqa: E402


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


class PackageTreeCustodyTests(unittest.TestCase):
    def _fixture(self, root: Path, submission: bool = True) -> tuple[Path, Path]:
        package = root / "package"
        package.mkdir()
        source_config = {
            "r04_sale_window": False,
            "r04_sale_fertilizer": True,
            "r04_cattle_early": True,
        }
        package_config = dict(source_config)
        package_config["r04_sale_window"] = submission
        source_blob = (json.dumps(source_config, indent=2) + "\n").encode()
        package_blob = (json.dumps(package_config, indent=2) + "\n").encode()
        (package / "TITAN-CONFIG.json").write_bytes(package_blob)
        (package / "main.py").write_bytes(b"print('fixture')\n")
        recorded = {
            "TITAN-CONFIG.json": _sha(source_blob),
            "main.py": _sha((package / "main.py").read_bytes()),
        }
        manifest = root / "FILES.json"
        manifest.write_text(json.dumps(recorded), encoding="utf-8")
        return package, manifest

    def test_submission_toggle_is_the_only_allowed_hash_difference(self):
        with tempfile.TemporaryDirectory() as temp:
            package, manifest = self._fixture(Path(temp), submission=True)
            with mock.patch.object(baseline, "FILES_MANIFEST", manifest):
                baseline._verify_package_tree(package)

    def test_source_mode_tree_also_verifies(self):
        with tempfile.TemporaryDirectory() as temp:
            package, manifest = self._fixture(Path(temp), submission=False)
            with mock.patch.object(baseline, "FILES_MANIFEST", manifest):
                baseline._verify_package_tree(package)

    def test_extra_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            package, manifest = self._fixture(Path(temp))
            (package / "extra.py").write_text("x = 1\n", encoding="utf-8")
            with mock.patch.object(baseline, "FILES_MANIFEST", manifest):
                with self.assertRaisesRegex(SystemExit, "file-set mismatch"):
                    baseline._verify_package_tree(package)

    def test_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            package, manifest = self._fixture(Path(temp))
            (package / "main.py").unlink()
            with mock.patch.object(baseline, "FILES_MANIFEST", manifest):
                with self.assertRaisesRegex(SystemExit, "file-set mismatch"):
                    baseline._verify_package_tree(package)

    def test_non_config_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            package, manifest = self._fixture(Path(temp))
            (package / "main.py").write_text("print('tampered')\n", encoding="utf-8")
            with mock.patch.object(baseline, "FILES_MANIFEST", manifest):
                with self.assertRaisesRegex(SystemExit, "hash mismatch: main.py"):
                    baseline._verify_package_tree(package)

    def test_other_config_drift_is_not_hidden_by_submission_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            package, manifest = self._fixture(Path(temp))
            data = json.loads((package / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
            data["r04_cattle_early"] = False
            (package / "TITAN-CONFIG.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with mock.patch.object(baseline, "FILES_MANIFEST", manifest):
                with self.assertRaisesRegex(SystemExit, "hash mismatch: TITAN-CONFIG.json"):
                    baseline._verify_package_tree(package)

    def test_integrity_failure_happens_before_copy(self):
        package = Path("not-used")
        with (
            mock.patch.object(baseline, "_verify_package_tree", side_effect=SystemExit("bad package")),
            mock.patch.object(baseline, "_copy_tree") as copy_tree,
        ):
            with self.assertRaisesRegex(SystemExit, "bad package"):
                baseline.run(package)
        copy_tree.assert_not_called()


if __name__ == "__main__":
    unittest.main()
