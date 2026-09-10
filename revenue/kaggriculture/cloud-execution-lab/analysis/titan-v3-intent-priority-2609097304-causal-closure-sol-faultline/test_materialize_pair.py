#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("faultline_materialize_pair", HERE / "materialize_pair.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


FROZEN = b'''PRODUCTS=("EGG","MILK")\n\nclass FrozenSelected:\n    def transform(self, shed):\n        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS if shed.get(p,0)>0}\n        return targets\n'''
MAIN = b'''def agent(observation, configuration=None):\n    return {"farmer":["PASS"],"hands":[],"market":[]}\n'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_manifest(runtime: dict[str, bytes]) -> bytes:
    payload = {
        "entrypoint": "main.py::agent",
        "runtime": {
            name: {"bytes": len(data), "sha256": sha(data)}
            for name, data in sorted(runtime.items())
        },
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def archive_bytes(members: dict[str, bytes], *, symlink: tuple[str, str] | None = None) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        names = set(members)
        if symlink:
            names.add(symlink[0])
        for name in sorted(names):
            if symlink and name == symlink[0]:
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = symlink[1]
                info.size = 0
                archive.addfile(info)
                continue
            data = members[name]
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


class PairMaterializationContracts(unittest.TestCase):
    def make_closure(self, directory: Path) -> tuple[Path, Path, dict[str, bytes], bytes]:
        runtime = {"frozen_selected.py": FROZEN, "main.py": MAIN}
        source = source_manifest(runtime)
        members = {**runtime, "SOURCE.json": source}
        archive = archive_bytes(members)
        archive_path = directory / "titan-current.tar.gz"
        source_path = directory / "CURRENT-SOURCE.json"
        archive_path.write_bytes(archive)
        source_path.write_bytes(source)
        return archive_path, source_path, members, archive

    def patches(self, members: dict[str, bytes], archive: bytes):
        return mock.patch.multiple(
            m,
            ARCHIVE_SHA256=sha(archive),
            ARCHIVE_BYTES=len(archive),
            SOURCE_SHA256=sha(members["SOURCE.json"]),
            FROZEN_SELECTED_GIT_BLOB=m.git_blob_sha1(FROZEN),
            RUNTIME_FILES=2,
        )

    def test_materializes_exact_control_and_live_seam_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive_path, source_path, members, archive = self.make_closure(root)
            output = root / "pair"
            with self.patches(members, archive):
                receipt = m.materialize(archive_path, source_path, output, "deadbeef")
            self.assertEqual((output / "control" / "frozen_selected.py").read_bytes(), FROZEN)
            candidate = (output / "candidate" / "frozen_selected.py").read_bytes()
            self.assertNotEqual(candidate, FROZEN)
            self.assertNotIn(m.OLD, candidate)
            self.assertIn(m.NEW, candidate)
            compile(candidate.decode(), "frozen_selected.py", "exec")
            self.assertEqual(receipt["only_runtime_delta"], ["frozen_selected.py"])
            self.assertEqual(receipt["git_head"], "deadbeef")
            self.assertEqual(
                json.loads((output / "PAIR-RECEIPT.json").read_text()), receipt
            )
            self.assertEqual(
                set(path.name for path in (output / "control").iterdir()),
                {"SOURCE.json", "frozen_selected.py", "main.py", "control_entry.py"},
            )

    def test_source_and_archive_must_bind_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive_path, source_path, members, archive = self.make_closure(root)
            source_path.write_bytes(members["SOURCE.json"] + b" ")
            with self.patches(members, archive), self.assertRaisesRegex(
                m.MaterializationError, "CURRENT-SOURCE.json identity drift"
            ):
                m.read_archive(archive_path, source_path)

    def test_archive_link_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = {"frozen_selected.py": FROZEN, "main.py": MAIN}
            source = source_manifest(runtime)
            members = {**runtime, "SOURCE.json": source}
            archive = archive_bytes(members, symlink=("zz-link", "../main.py"))
            archive_path = root / "bad.tar.gz"
            source_path = root / "CURRENT-SOURCE.json"
            archive_path.write_bytes(archive)
            source_path.write_bytes(source)
            with self.patches(members, archive), self.assertRaisesRegex(
                m.MaterializationError, "not a regular file"
            ):
                m.read_archive(archive_path, source_path)

    def test_strict_json_rejects_duplicates_and_nonfinite_values(self):
        with self.assertRaisesRegex(m.MaterializationError, "duplicate key"):
            m.strict_json(b'{"runtime":{},"runtime":{}}', "manifest")
        with self.assertRaisesRegex(m.MaterializationError, "non-finite"):
            m.strict_json(b'{"x":NaN}', "manifest")

    def test_seam_patch_fails_closed_on_source_drift(self):
        with mock.patch.object(m, "FROZEN_SELECTED_GIT_BLOB", m.git_blob_sha1(FROZEN)):
            with self.assertRaisesRegex(m.MaterializationError, "pinned frozen_selected"):
                m.patch_frozen_selected(FROZEN + b"# drift\n")


if __name__ == "__main__":
    unittest.main()
