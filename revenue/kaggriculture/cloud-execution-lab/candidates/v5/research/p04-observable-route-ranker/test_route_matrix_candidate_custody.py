#!/usr/bin/env python3
import gzip
import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import route_matrix_candidate_custody as custody


def manifest(files, archive):
    return {
        "candidate_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": {name: hashlib.sha256(body).hexdigest() for name, body in files.items()},
    }


def noncanonical_archive(name, body):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))
    packed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=packed, mtime=0) as zipped:
        zipped.write(raw.getvalue())
    return packed.getvalue()


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
        archive.write_bytes(custody._build_delivery_module().archive_bytes(files))
        return payload, archive, files, manifest(files, archive)

    def test_capture_binds_canonical_archive_manifest_and_exact_tree(self):
        with tempfile.TemporaryDirectory() as td:
            payload, archive, files, m = self.fixture(Path(td))
            captured, authority = custody.capture_candidate(payload, archive, m)
            self.assertEqual(captured, files)
            self.assertEqual(authority["candidate_archive_sha256"], m["candidate_archive_sha256"])
            self.assertTrue(authority["archive_root_byte_identity"])

    def test_archive_a_root_b_split_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            payload, archive, files_b, _ = self.fixture(Path(td))
            files_a = dict(files_b)
            files_a["r04_full_router.py"] = b"ROUTE_STEP=144\nFORCED_PLAN=3\n"
            archive.write_bytes(custody._build_delivery_module().archive_bytes(files_a))
            split_manifest = manifest(files_b, archive)
            with self.assertRaisesRegex(ValueError, "archive member SHA map"):
                custody.capture_candidate(payload, archive, split_manifest)

    def test_noncanonical_archive_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            payload, archive, files, _ = self.fixture(Path(td))
            archive.write_bytes(noncanonical_archive("../main.py", files["main.py"]))
            bad = manifest(files, archive)
            with self.assertRaisesRegex(ValueError, "Noncanonical archive member"):
                custody.capture_candidate(payload, archive, bad)

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
                self.assertEqual(
                    authority["generated_adapter_sha256"],
                    hashlib.sha256(adapter.read_bytes()).hexdigest(),
                )
                custody.verify_snapshot(private_root, captured)
                (private_root / "main.py").write_bytes(b"mutated\n")
                with self.assertRaisesRegex(ValueError, "changed during game"):
                    custody.verify_snapshot(private_root, captured)
                held.cleanup()
            finally:
                custody.OFFICIAL_FILE_LOADER_SHA256 = old

    def test_shared_publication_primitive_is_loadable_and_effective(self):
        publish = custody.shared_publication()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            row, receipt = root / "row.jsonl", root / "receipt.json"
            publish(((row, b"row\n"), (receipt, b"receipt\n")))
            self.assertEqual(row.read_bytes(), b"row\n")
            self.assertEqual(receipt.read_bytes(), b"receipt\n")
            with self.assertRaises(FileExistsError):
                publish(((row, b"new\n"), (receipt, b"new\n")))


if __name__ == "__main__":
    unittest.main()
