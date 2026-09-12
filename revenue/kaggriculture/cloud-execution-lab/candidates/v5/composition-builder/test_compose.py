from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import gzip

import compose


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_tar(path: Path, files: dict[str, bytes]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for name, data in files.items():
                    info = tarfile.TarInfo(name)
                    info.mode = 0o644
                    info.mtime = 1
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))


def read_tar(path: Path) -> dict[str, bytes]:
    out = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            out[member.name] = archive.extractfile(member).read()
    return out


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / "src"
        self.src.mkdir()
        self.base = self.root / "base.tar.gz"
        config = {"consumer": "frozen", "funding": False, "worker": False}
        self.base_files = {
            "TITAN-CONFIG.json": (json.dumps(config, indent=2) + "\n").encode(),
            "seller.py": b"seller-base\n",
            "worker.py": b"worker-base\n",
        }
        write_tar(self.base, self.base_files)
        (self.src / "seller.py").write_bytes(b"seller-a\n")
        (self.src / "worker.py").write_bytes(b"worker-b\n")

    def tearDown(self):
        self.tmp.cleanup()

    def manifest(self, *, components=None):
        if components is None:
            components = {
                "joint": {
                    "files": [{
                        "archive_path": "seller.py",
                        "source_path": "seller.py",
                        "sha256": h(b"seller-a\n"),
                    }],
                    "config": {"funding": True},
                },
                "worker": {
                    "files": [{
                        "archive_path": "worker.py",
                        "source_path": "worker.py",
                        "sha256": h(b"worker-b\n"),
                    }],
                    "config": {"worker": True},
                },
            }
        data = {
            "schema": compose.SCHEMA,
            "baseline": {"sha256": compose.sha256_file(self.base), "member_count": 3},
            "components": components,
        }
        path = self.root / "manifest.json"
        path.write_text(json.dumps(data))
        return path

    def test_builds_control_components_and_pair_with_activation(self):
        out = self.root / "out"
        receipt = compose.build(
            baseline=self.base,
            source_root=self.src,
            manifest_path=self.manifest(),
            output=out,
        )
        self.assertEqual(set(receipt["variants"]), {"control", "joint", "worker", "joint+worker"})
        control = read_tar(out / "control.tar.gz")
        joint = read_tar(out / "joint.tar.gz")
        worker = read_tar(out / "worker.tar.gz")
        pair = read_tar(out / "joint-plus-worker.tar.gz")
        self.assertEqual(control, self.base_files)
        self.assertEqual(joint["seller.py"], b"seller-a\n")
        self.assertEqual(joint["worker.py"], b"worker-base\n")
        self.assertEqual(worker["seller.py"], b"seller-base\n")
        self.assertEqual(worker["worker.py"], b"worker-b\n")
        self.assertEqual(pair["seller.py"], b"seller-a\n")
        self.assertEqual(pair["worker.py"], b"worker-b\n")
        self.assertTrue(json.loads(pair["TITAN-CONFIG.json"])["funding"])
        self.assertTrue(json.loads(pair["TITAN-CONFIG.json"])["worker"])
        self.assertEqual(
            receipt["variants"]["joint+worker"]["changed_members"],
            ["TITAN-CONFIG.json", "seller.py", "worker.py"],
        )

    def test_stale_source_hash_fails_closed(self):
        data = json.loads(self.manifest().read_text())
        data["components"]["joint"]["files"][0]["sha256"] = "0" * 64
        path = self.root / "stale.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(compose.CompositionError, "stale source"):
            compose.build(
                baseline=self.base,
                source_root=self.src,
                manifest_path=path,
                output=self.root / "out",
            )

    def test_incompatible_same_member_fails_closed(self):
        (self.src / "seller-b.py").write_bytes(b"seller-b\n")
        components = {
            "a": {
                "files": [{"archive_path": "seller.py", "source_path": "seller.py", "sha256": h(b"seller-a\n")}],
                "config": {},
            },
            "b": {
                "files": [{"archive_path": "seller.py", "source_path": "seller-b.py", "sha256": h(b"seller-b\n")}],
                "config": {},
            },
        }
        with self.assertRaisesRegex(compose.CompositionError, "conflict on seller.py"):
            compose.build(
                baseline=self.base,
                source_root=self.src,
                manifest_path=self.manifest(components=components),
                output=self.root / "out",
            )

    def test_config_conflict_fails_closed(self):
        components = {
            "a": {
                "files": [{"archive_path": "seller.py", "source_path": "seller.py", "sha256": h(b"seller-a\n")}],
                "config": {"funding": True},
            },
            "b": {
                "files": [{"archive_path": "worker.py", "source_path": "worker.py", "sha256": h(b"worker-b\n")}],
                "config": {"funding": False},
            },
        }
        with self.assertRaisesRegex(compose.CompositionError, "conflict on config"):
            compose.build(
                baseline=self.base,
                source_root=self.src,
                manifest_path=self.manifest(components=components),
                output=self.root / "out",
            )

    def test_path_escape_fails_closed(self):
        data = json.loads(self.manifest().read_text())
        data["components"]["joint"]["files"][0]["source_path"] = "../seller.py"
        path = self.root / "escape.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(compose.CompositionError, "unsafe source_path"):
            compose.build(
                baseline=self.base,
                source_root=self.src,
                manifest_path=path,
                output=self.root / "out",
            )

    def test_source_symlink_escape_fails_closed_even_with_matching_hash(self):
        outside = self.root / "outside-seller.py"
        outside.write_bytes(b"outside-but-hash-matches\n")
        link = self.src / "linked-seller.py"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")

        data = json.loads(self.manifest().read_text())
        entry = data["components"]["joint"]["files"][0]
        entry["source_path"] = "linked-seller.py"
        entry["sha256"] = h(b"outside-but-hash-matches\n")
        path = self.root / "symlink-escape.json"
        path.write_text(json.dumps(data))

        with self.assertRaisesRegex(compose.CompositionError, "source escapes source root"):
            compose.build(
                baseline=self.base,
                source_root=self.src,
                manifest_path=path,
                output=self.root / "out",
            )


if __name__ == "__main__":
    unittest.main()
