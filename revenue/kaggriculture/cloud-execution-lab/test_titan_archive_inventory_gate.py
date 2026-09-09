#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from titan_archive_inventory_gate import GateError, inspect_archive


class ArchiveInventoryGateTests(unittest.TestCase):
    @staticmethod
    def write_tar(path: Path, members: list[dict]) -> None:
        with tarfile.open(path, "w:gz") as archive:
            for spec in members:
                info = tarfile.TarInfo(spec["name"])
                info.mtime = 0
                kind = spec.get("kind", "file")
                if kind == "file":
                    data = spec.get("data", b"")
                    if isinstance(data, str):
                        data = data.encode()
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
                elif kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = spec["linkname"]
                    archive.addfile(info)
                else:
                    raise AssertionError(kind)

    def fixture(
        self,
        root: Path,
        *,
        members: list[dict] | None = None,
        runtime_files: int | None = None,
        entrypoint: str = "main.py::agent",
        raw_archive: bytes | None = None,
    ) -> tuple[Path, Path, dict]:
        archive = root / "exports/titan-current.tar.gz"
        receipt_path = root / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
        archive.parent.mkdir(parents=True)
        receipt_path.parent.mkdir(parents=True)
        members = members or [
            {"name": "main.py", "data": "def agent():\n    pass\n"},
            {"name": "SOURCE.json", "data": "{}\n"},
            {"name": "runtime.py", "data": "class Agent: pass\n"},
        ]
        if raw_archive is None:
            self.write_tar(archive, members)
        else:
            archive.write_bytes(raw_archive)
        data = archive.read_bytes()
        count = sum(row.get("kind", "file") == "file" for row in members)
        receipt = {
            "path": "exports/titan-current.tar.gz",
            "entrypoint": entrypoint,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "runtime_files": count if runtime_files is None else runtime_files,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        return archive, receipt_path, receipt

    @staticmethod
    def codes(report: dict) -> set[str]:
        return {row["code"] for row in report["blockers"]}

    def test_clean_archive_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder))
            report = inspect_archive(folder)
        self.assertEqual("PASS", report["verdict"])
        self.assertEqual(3, report["actual"]["regular_files"])
        self.assertEqual("main.py", report["actual"]["entrypoint_member"])

    def test_member_count_mismatch_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), runtime_files=2)
            report = inspect_archive(folder)
        self.assertIn("ARCHIVE_MEMBER_COUNT_MISMATCH", self.codes(report))

    def test_link_member_is_blocked(self):
        members = [
            {"name": "main.py", "data": ""},
            {"name": "alias.py", "kind": "symlink", "linkname": "main.py"},
        ]
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), members=members)
            report = inspect_archive(folder)
        self.assertIn("UNSAFE_ARCHIVE_MEMBER_TYPE", self.codes(report))

    def test_parent_traversal_is_blocked(self):
        members = [{"name": "main.py", "data": ""}, {"name": "../escape.py", "data": ""}]
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), members=members)
            report = inspect_archive(folder)
        self.assertIn("UNSAFE_ARCHIVE_PATH", self.codes(report))

    def test_backslash_path_is_blocked(self):
        members = [{"name": "main.py", "data": ""}, {"name": "pkg\\escape.py", "data": ""}]
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), members=members)
            report = inspect_archive(folder)
        self.assertIn("UNSAFE_ARCHIVE_PATH", self.codes(report))

    def test_normalized_duplicate_is_blocked(self):
        members = [{"name": "main.py", "data": "a"}, {"name": "./main.py", "data": "b"}]
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), members=members)
            report = inspect_archive(folder)
        self.assertIn("DUPLICATE_ARCHIVE_PATH", self.codes(report))

    def test_missing_entrypoint_is_blocked(self):
        members = [{"name": "worker.py", "data": ""}]
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), members=members)
            report = inspect_archive(folder)
        self.assertIn("ENTRYPOINT_MEMBER_MISSING", self.codes(report))

    def test_byte_mutation_breaks_hash_and_size(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive, _, _ = self.fixture(root)
            archive.write_bytes(archive.read_bytes() + b"mutation")
            report = inspect_archive(folder)
        self.assertIn("ARCHIVE_HASH_MISMATCH", self.codes(report))
        self.assertIn("ARCHIVE_SIZE_MISMATCH", self.codes(report))

    def test_unreadable_payload_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder), raw_archive=b"not a tar archive")
            report = inspect_archive(folder)
        self.assertIn("ARCHIVE_UNREADABLE", self.codes(report))

    def test_duplicate_json_key_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, receipt_path, receipt = self.fixture(root)
            receipt_path.write_text(
                '{"path":"exports/titan-current.tar.gz",'
                '"entrypoint":"main.py::agent",'
                f'"sha256":"{receipt["sha256"]}",'
                f'"bytes":{receipt["bytes"]},"runtime_files":3,"runtime_files":4}}'
            )
            with self.assertRaisesRegex(GateError, "duplicate JSON key"):
                inspect_archive(folder)


if __name__ == "__main__":
    unittest.main()
