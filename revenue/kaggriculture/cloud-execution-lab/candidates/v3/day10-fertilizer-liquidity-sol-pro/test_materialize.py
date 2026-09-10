# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

import materialize as subject


class MaterializeTests(unittest.TestCase):
    def make_archive(self, root: Path, members):
        path = root / "canonical.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name, payload, kind in members:
                info = tarfile.TarInfo(name)
                if kind == "file":
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
                elif kind == "dir":
                    info.type = tarfile.DIRTYPE
                    archive.addfile(info)
                elif kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = payload.decode()
                    archive.addfile(info)
        return path

    def overlays(self, root: Path):
        source = root / "overlays"
        source.mkdir()
        for name in subject.OVERLAY_FILES:
            (source / name).write_text(f"# {name}\n", encoding="utf-8")
        return source

    def call(self, root: Path, archive: Path):
        with mock.patch.object(subject, "EXPECTED_ARCHIVE_BYTES", archive.stat().st_size), mock.patch.object(
            subject, "EXPECTED_ARCHIVE_SHA256", subject.sha256_file(archive)
        ):
            return subject.materialize(
                archive,
                self.overlays(root),
                root / "control",
                root / "candidate",
                root / "receipt.json",
            )

    def test_exact_archive_produces_byte_identical_control_and_additive_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = self.make_archive(
                root,
                [
                    ("main.py", b"def agent(o,c=None): return {}\n", "file"),
                    ("SOURCE.json", b"{}\n", "file"),
                    ("nested/", b"", "dir"),
                    ("nested/runtime.py", b"x=1\n", "file"),
                ],
            )
            receipt = self.call(root, archive)
            self.assertEqual((root / "control/main.py").read_bytes(), (root / "candidate/main.py").read_bytes())
            self.assertFalse((root / "control/candidate.py").exists())
            self.assertTrue((root / "candidate/candidate.py").exists())
            self.assertEqual(receipt["candidate"]["canonical_regular_files"], 3)
            loaded = json.loads((root / "receipt.json").read_text())
            self.assertEqual(loaded["canonical_archive"]["sha256"], subject.sha256_file(archive))

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = self.make_archive(
                root,
                [("main.py", b"x", "file"), ("SOURCE.json", b"{}", "file"), ("../escape", b"x", "file")],
            )
            with self.assertRaisesRegex(subject.MaterializationError, "unsafe_or_duplicate_member"):
                self.call(root, archive)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = self.make_archive(
                root,
                [("main.py", b"x", "file"), ("SOURCE.json", b"{}", "file"), ("link", b"main.py", "symlink")],
            )
            with self.assertRaisesRegex(subject.MaterializationError, "nonregular_archive_member"):
                self.call(root, archive)

    def test_duplicate_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "canonical.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                for payload in (b"one", b"two"):
                    info = tarfile.TarInfo("main.py")
                    info.size = len(payload)
                    tar.addfile(info, io.BytesIO(payload))
                info = tarfile.TarInfo("SOURCE.json")
                info.size = 2
                tar.addfile(info, io.BytesIO(b"{}"))
            with self.assertRaisesRegex(subject.MaterializationError, "unsafe_or_duplicate_member"):
                self.call(root, archive)

    def test_overlay_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = self.make_archive(
                root,
                [("main.py", b"x", "file"), ("SOURCE.json", b"{}", "file"), ("candidate.py", b"old", "file")],
            )
            with self.assertRaisesRegex(subject.MaterializationError, "overlay_collides_with_archive"):
                self.call(root, archive)

    def test_archive_hash_drift_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = self.make_archive(root, [("main.py", b"x", "file"), ("SOURCE.json", b"{}", "file")])
            with mock.patch.object(subject, "EXPECTED_ARCHIVE_BYTES", archive.stat().st_size), mock.patch.object(
                subject, "EXPECTED_ARCHIVE_SHA256", "0" * 64
            ):
                with self.assertRaisesRegex(subject.MaterializationError, "canonical_archive_sha256_drift"):
                    subject.materialize(
                        archive,
                        self.overlays(root),
                        root / "control",
                        root / "candidate",
                        root / "receipt.json",
                    )
            self.assertFalse((root / "control").exists())

    def test_existing_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = self.make_archive(root, [("main.py", b"x", "file"), ("SOURCE.json", b"{}", "file")])
            (root / "control").mkdir()
            with mock.patch.object(subject, "EXPECTED_ARCHIVE_BYTES", archive.stat().st_size), mock.patch.object(
                subject, "EXPECTED_ARCHIVE_SHA256", subject.sha256_file(archive)
            ):
                with self.assertRaisesRegex(subject.MaterializationError, "destination_already_exists"):
                    subject.materialize(
                        archive,
                        self.overlays(root),
                        root / "control",
                        root / "candidate",
                        root / "receipt.json",
                    )


if __name__ == "__main__":
    unittest.main()
