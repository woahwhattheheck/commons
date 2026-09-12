# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

import harvest_probe as probe
import run_native_harvest as runner


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def make_tar(entries: list[tuple[str, bytes]]) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        for name, raw in entries:
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(raw))
    return out.getvalue()


class HarvestImmutableCustodyTests(unittest.TestCase):
    def runtime_files(self):
        return {
            "main.py": b"MARKER = 'captured-main'\n",
            "scheduler.py": b"MARKER = 'captured-scheduler'\n",
            "checks/reference/evaluator/loader.py": b"MARKER = 'captured-loader'\n",
            "checks/reference/engine/kaggriculture.py": b"MARKER = 'captured-engine'\n",
            "checks/reference/engine/kaggriculture.json": b"{}\n",
            "checks/reference/engine/utils.py": b"MARKER = 'captured-utils'\n",
        }

    def materialized_fixture(self, base: Path):
        files = self.runtime_files()
        root = base / "runtime"
        root.mkdir()
        for name, raw in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        archive_raw = make_tar(list(files.items()))
        archive = base / "native.tar.gz"
        archive.write_bytes(archive_raw)
        pins = {
            "kaggriculture.py": sha(files["checks/reference/engine/kaggriculture.py"]),
            "kaggriculture.json": sha(files["checks/reference/engine/kaggriculture.json"]),
            "utils.py": sha(files["checks/reference/engine/utils.py"]),
        }
        patches = patch.multiple(
            runner,
            ARCHIVE_SHA=sha(archive_raw),
            ENGINE_PINS=pins,
            LOADER_SHA=sha(files["checks/reference/evaluator/loader.py"]),
        )
        return root, archive, files, patches

    def test_donor_path_swap_after_read_executes_authenticated_buffer(self):
        original = b"MARKER = 'authenticated'\n"
        attacker = "raise RuntimeError('attacker donor executed')\n"
        old_read = Path.read_bytes
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "donor.py"
            path.write_bytes(original)

            def read_then_swap(target):
                raw = old_read(target)
                if target == path:
                    target.write_text(attacker, encoding="utf-8")
                return raw

            with patch.object(Path, "read_bytes", new=read_then_swap):
                module, captured = probe._load_captured("_custody_donor", path, blob(original))
            self.assertEqual(captured, original)
            self.assertEqual(module.MARKER, "authenticated")
            self.assertIn("attacker donor", path.read_text(encoding="utf-8"))

    def test_donor_git_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "donor.py"
            path.write_bytes(b"VALUE = 1\n")
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                probe._load_captured("_custody_bad_donor", path, "0" * 40)

    def test_live_root_poison_after_capture_cannot_change_frozen_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root, archive, files, patches = self.materialized_fixture(Path(d))
            with patches:
                members, captured = runner.capture_runtime(root, archive)
            self.assertEqual(set(members), set(files))
            (root / "main.py").write_text("raise RuntimeError('attacker main')\n")
            (root / "scheduler.py").write_text("raise RuntimeError('attacker scheduler')\n")
            frozen = Path(d) / "frozen"
            runner.materialize_runtime(frozen, captured)
            self.assertEqual((frozen / "main.py").read_bytes(), files["main.py"])
            self.assertEqual((frozen / "scheduler.py").read_bytes(), files["scheduler.py"])

    def test_duplicate_archive_member_fails_closed(self):
        files = self.runtime_files()
        entries = list(files.items()) + [("main.py", files["main.py"])]
        raw = make_tar(entries)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "runtime"
            root.mkdir()
            archive = Path(d) / "native.tar.gz"
            archive.write_bytes(raw)
            with patch.object(runner, "ARCHIVE_SHA", sha(raw)):
                with self.assertRaisesRegex(RuntimeError, "duplicate archive member"):
                    runner.capture_runtime(root, archive)

    def test_unsafe_archive_member_fails_closed(self):
        raw = make_tar([("../escape.py", b"x")])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "runtime"
            root.mkdir()
            archive = Path(d) / "native.tar.gz"
            archive.write_bytes(raw)
            with patch.object(runner, "ARCHIVE_SHA", sha(raw)):
                with self.assertRaisesRegex(RuntimeError, "unsafe archive member"):
                    runner.capture_runtime(root, archive)

    def test_symlinked_live_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root, archive, files, patches = self.materialized_fixture(Path(d))
            outside = Path(d) / "outside.py"
            outside.write_bytes(files["main.py"])
            (root / "main.py").unlink()
            (root / "main.py").symlink_to(outside)
            with patches:
                with self.assertRaisesRegex(RuntimeError, "symlink native member"):
                    runner.capture_runtime(root, archive)

    def test_preloaded_runtime_module_outside_system_fails_closed(self):
        attacker = types.ModuleType("scheduler")
        attacker.__file__ = "/tmp/harvest-custody-attacker/scheduler.py"
        previous = sys.modules.get("scheduler")
        sys.modules["scheduler"] = attacker
        try:
            with self.assertRaisesRegex(RuntimeError, "preloaded runtime module escapes frozen custody"):
                runner._reject_preloaded_runtime_modules({"scheduler.py": b"captured\n"})
        finally:
            if previous is None:
                sys.modules.pop("scheduler", None)
            else:
                sys.modules["scheduler"] = previous


if __name__ == "__main__":
    unittest.main()
