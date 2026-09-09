# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import unittest

from support import fixture, install_archive, restore, sha, tar_bytes


class RejectionTests(unittest.TestCase):
    def test_archive_hash_drift(self):
        fx = fixture(self)
        path = fx.root / fx.pin.source_archive
        path.write_bytes(path.read_bytes() + b"x")
        with self.assertRaisesRegex(restore.SnapshotError, "byte count drift"):
            restore.materialize(fx.root, pin=fx.pin, run_smoke=False)

    def test_artifact_metadata_drift(self):
        fx = fixture(self)
        path = fx.root / "exports" / "ARTIFACTS.json"
        data = json.loads(path.read_text())
        data["selected_source"]["files"] += 1
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(restore.SnapshotError, "ARTIFACTS"):
            restore.materialize(fx.root, pin=fx.pin, run_smoke=False)

    def test_member_manifest_drift(self):
        fx = fixture(self)
        path = fx.root / "exports" / "FILES.json"
        data = json.loads(path.read_text())
        data["scheduler.py"]["sha256"] = "0" * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(restore.SnapshotError, "FILES.json"):
            restore.materialize(fx.root, pin=fx.pin, run_smoke=False)

    def test_freeze_identity_drift(self):
        fx = fixture(self)
        bad = dict(fx.pin.frozen_hashes)
        bad["scheduler.py"] = "f" * 64
        pin = restore.Pin(**{**fx.pin.__dict__, "frozen_hashes": bad})
        with self.assertRaisesRegex(restore.SnapshotError, "freeze identity"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_missing_local_import(self):
        fx = fixture(self, scheduler=b"import missing_runtime_dependency\ndef agent(*args): return {}\n")
        with self.assertRaisesRegex(restore.SnapshotError, "undeclared Python import"):
            restore.materialize(fx.root, pin=fx.pin, run_smoke=False)

    def test_candidate_must_be_thin_alias(self):
        fx = fixture(self, candidate=b"from scheduler import agent\nagent = lambda *args: {}\n")
        with self.assertRaisesRegex(restore.SnapshotError, "must expose only"):
            restore.materialize(fx.root, pin=fx.pin, run_smoke=False)

    def test_path_traversal(self):
        fx = fixture(self)
        members = dict(fx.members)
        members["../escape.py"] = members.pop("NOTICE")
        archive = tar_bytes(members)
        pin = install_archive(fx, archive)
        with self.assertRaisesRegex(restore.SnapshotError, "unsafe archive member"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_symlink(self):
        fx = fixture(self)
        archive = tar_bytes(fx.members, link="NOTICE")
        pin = install_archive(fx, archive)
        with self.assertRaisesRegex(restore.SnapshotError, "not a regular file"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_duplicate_member(self):
        fx = fixture(self)
        archive = tar_bytes(fx.members, duplicate="NOTICE")
        pin = install_archive(fx, archive)
        with self.assertRaisesRegex(restore.SnapshotError, "duplicate archive member"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_member_metadata_drift(self):
        fx = fixture(self)
        archive = tar_bytes(fx.members, metadata_drift="NOTICE")
        pin = install_archive(fx, archive)
        with self.assertRaisesRegex(restore.SnapshotError, "metadata drift"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_excessive_member_count(self):
        fx = fixture(self)
        members = dict(fx.members)
        for index in range(restore.MAX_MEMBER_COUNT):
            members[f"extra-{index}.txt"] = b"x"
        archive = tar_bytes(members)
        pin = install_archive(fx, archive, member_count=len(members))
        with self.assertRaisesRegex(restore.SnapshotError, "too many members"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)


if __name__ == "__main__":
    unittest.main()
