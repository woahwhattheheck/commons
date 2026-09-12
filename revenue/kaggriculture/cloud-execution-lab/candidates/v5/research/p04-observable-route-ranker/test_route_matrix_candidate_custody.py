#!/usr/bin/env python3
import hashlib
import tempfile
import unittest
from pathlib import Path

import route_matrix_candidate_custody as custody


def manifest(files, archive):
    return {
        "candidate_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": {name: hashlib.sha256(body).hexdigest() for name, body in files.items()},
    }


class CandidateCustody(unittest.TestCase):
    def fixture(self, root):
        payload = root / "payload"
        payload.mkdir()
        files = {
            "main.py": b"def agent(observation, configuration): return {}\n",
            "r04_full_router.py": b"ROUTE_STEP=144\nFINAL_PLAN_STEP=648\n",
        }
        for name, body in files.items():
            (payload / name).write_bytes(body)
        archive = root / "candidate.tar.gz"
        archive.write_bytes(b"route archive")
        return payload, archive, files, manifest(files, archive)

    def test_capture_binds_archive_and_exact_tree(self):
        with tempfile.TemporaryDirectory() as td:
            payload, archive, files, m = self.fixture(Path(td))
            captured, authority = custody.capture_candidate(payload, archive, m)
            self.assertEqual(captured, files)
            self.assertEqual(authority["candidate_archive_sha256"], m["candidate_archive_sha256"])

    def test_wrong_plan_tree_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            payload, archive, _, m = self.fixture(Path(td))
            (payload / "r04_full_router.py").write_bytes(b"wrong plan\n")
            with self.assertRaisesRegex(ValueError, "member SHA256 drift"):
                custody.capture_candidate(payload, archive, m)

    def test_extra_and_symlink_members_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            payload, archive, _, m = self.fixture(Path(td))
            (payload / "extra.py").write_text("x=1\n")
            with self.assertRaisesRegex(ValueError, "member set drift"):
                custody.capture_candidate(payload, archive, m)
            (payload / "extra.py").unlink()
            try:
                (payload / "linked.py").symlink_to(payload / "main.py")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "contains symlink"):
                custody.capture_candidate(payload, archive, m)

    def test_private_snapshot_detects_postcapture_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload, archive, _, m = self.fixture(root)
            captured, _ = custody.capture_candidate(payload, archive, m)
            official = root / "official.py"
            official.write_text("def make_agent(path): return lambda obs,cfg: {}\n")
            old = custody.OFFICIAL_FILE_LOADER_SHA256
            custody.OFFICIAL_FILE_LOADER_SHA256 = hashlib.sha256(official.read_bytes()).hexdigest()
            try:
                held, private_root, adapter, authority = custody.private_snapshot(captured, official)
                self.assertEqual(authority["generated_adapter_sha256"], hashlib.sha256(adapter.read_bytes()).hexdigest())
                custody.verify_snapshot(private_root, captured)
                (private_root / "main.py").write_bytes(b"mutated\n")
                with self.assertRaisesRegex(ValueError, "changed during game"):
                    custody.verify_snapshot(private_root, captured)
                held.cleanup()
            finally:
                custody.OFFICIAL_FILE_LOADER_SHA256 = old


if __name__ == "__main__":
    unittest.main()
