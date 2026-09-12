import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("fresh", HERE / "check_native_freshness.py")
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)

LOCAL = {
    "main.py": b"def agent(obs, cfg):\n    return {}\n",
    "titan_runtime.py": b"RUNTIME = 1\n",
    "scheduler.py": b"SCHEDULER = 1\n",
    "frozen_selected.py": b"FROZEN = 1\n",
    "TITAN-CONFIG.json": b'{"consumer":"frozen"}\n',
    "spatial_tempo.py": b"SPATIAL = 1\n",
}
SIBLING = b"SELLER = 1\n"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def publisher_source(mapping):
    return (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent\n"
        "def source_files():\n"
        f"    return {mapping!r}\n"
    ).encode()


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        run("git", "init", "-q", cwd=self.root)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.root)
        run("git", "config", "user.name", "test", cwd=self.root)
        self.live = self.root / "revenue/kaggriculture/cloud-execution-lab"
        self.live.mkdir(parents=True)
        for name, data in LOCAL.items():
            (self.live / name).write_bytes(data)
        self.sibling = self.root / "revenue/kaggriculture/cloud-quickstep"
        self.sibling.mkdir(parents=True)
        (self.sibling / "seller_snapshot.py").write_bytes(SIBLING)
        self.mapping = {name: name for name in LOCAL}
        self.mapping["seller_snapshot.py"] = "../cloud-quickstep/seller_snapshot.py"
        (self.live / "build_integrated.py").write_bytes(publisher_source(self.mapping))
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "base", cwd=self.root)
        self.commit = run("git", "rev-parse", "HEAD", cwd=self.root)

    def tearDown(self):
        self.td.cleanup()

    def members_from_live(self, mapping=None):
        mapping = self.mapping if mapping is None else mapping
        out = {}
        for member, source in mapping.items():
            source_path = (self.live / source).resolve()
            out[member] = source_path.read_bytes()
        return out

    def source_manifest(self, members, mapping=None):
        mapping = self.mapping if mapping is None else mapping
        return {
            "entrypoint": "main.py::agent",
            "config": "TITAN-CONFIG.json",
            "runtime": {
                name: {
                    "source_path": mapping[name],
                    "sha256": sha256(members[name]),
                    "bytes": len(members[name]),
                }
                for name in mapping
            },
        }

    def archive(
        self,
        members=None,
        *,
        mapping=None,
        manifest=None,
        duplicate=None,
        symlink=None,
        extra=None,
    ):
        mapping = self.mapping if mapping is None else mapping
        members = dict(self.members_from_live(mapping) if members is None else members)
        manifest = self.source_manifest(members, mapping) if manifest is None else manifest
        path = self.root / "candidate.tar.gz"
        with tarfile.open(path, "w:gz") as tf:
            all_members = dict(members)
            all_members["SOURCE.json"] = (
                json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            )
            if extra:
                all_members.update(extra)
            for name, data in all_members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            if duplicate:
                data = all_members[duplicate]
                info = tarfile.TarInfo(duplicate)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            if symlink:
                info = tarfile.TarInfo(symlink)
                info.type = tarfile.SYMTYPE
                info.linkname = "main.py"
                tf.addfile(info)
        return path, sha256(path.read_bytes())

    def verify(self, archive, digest, commit=None):
        return fresh.verify_freshness(
            repo_root=self.root,
            live_dir="revenue/kaggriculture/cloud-execution-lab",
            archive=archive,
            expected_archive_sha256=digest,
            expected_commit=commit or self.commit,
        )

    def test_current_exact_full_publisher_closure(self):
        archive, digest = self.archive()
        report = self.verify(archive, digest)
        self.assertEqual("CURRENT", report["verdict"])
        self.assertEqual([], report["stale_paths"])
        self.assertEqual(sorted(self.mapping), report["tracked_members"])
        self.assertTrue(all(row["same"] for row in report["files"]))
        seller = next(r for r in report["files"] if r["path"] == "seller_snapshot.py")
        self.assertEqual(
            "revenue/kaggriculture/cloud-quickstep/seller_snapshot.py",
            seller["repo_path"],
        )

    def test_stale_runtime_only(self):
        old = self.members_from_live()
        old["titan_runtime.py"] = b"RUNTIME = 0\n"
        archive, digest = self.archive(old)
        report = self.verify(archive, digest)
        self.assertEqual("STALE", report["verdict"])
        self.assertEqual(["titan_runtime.py"], report["stale_paths"])

    def test_stale_spatial_tempo_only_is_not_false_current(self):
        old = self.members_from_live()
        old["spatial_tempo.py"] = b"SPATIAL = 0\n"
        archive, digest = self.archive(old)
        report = self.verify(archive, digest)
        self.assertEqual("STALE", report["verdict"])
        self.assertEqual(["spatial_tempo.py"], report["stale_paths"])

    def test_stale_sibling_source_only_is_not_false_current(self):
        old = self.members_from_live()
        old["seller_snapshot.py"] = b"SELLER = 0\n"
        archive, digest = self.archive(old)
        report = self.verify(archive, digest)
        self.assertEqual("STALE", report["verdict"])
        self.assertEqual(["seller_snapshot.py"], report["stale_paths"])

    def test_wrong_authenticated_digest_invalid(self):
        archive, _ = self.archive()
        report = self.verify(archive, "0" * 64)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("archive sha256", report["problems"][0])

    def test_expected_commit_drift_invalid(self):
        archive, digest = self.archive()
        report = self.verify(archive, digest, commit="0" * 40)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("checkout HEAD drift", report["problems"][0])

    def test_midrun_head_move_with_changed_source_cannot_rebind_expected_commit(self):
        moved = self.members_from_live()
        moved["titan_runtime.py"] = b"RUNTIME = 2\n"
        (self.live / "titan_runtime.py").write_bytes(moved["titan_runtime.py"])
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "new runtime", cwd=self.root)
        commit_b = run("git", "rev-parse", "HEAD", cwd=self.root)
        archive, digest = self.archive(moved)
        run("git", "reset", "--hard", self.commit, cwd=self.root)

        original = fresh._read_archive_members

        def read_then_advance(*args, **kwargs):
            result = original(*args, **kwargs)
            run("git", "reset", "--hard", commit_b, cwd=self.root)
            return result

        fresh._read_archive_members = read_then_advance
        try:
            report = self.verify(archive, digest)
        finally:
            fresh._read_archive_members = original
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("expected commit", report["problems"][0])

    def test_midrun_ref_advance_with_same_sources_invalid(self):
        archive, digest = self.archive()
        marker = self.root / "UNRELATED.txt"
        marker.write_text("different commit, same publisher sources\n", encoding="utf-8")
        run("git", "add", "UNRELATED.txt", cwd=self.root)
        run("git", "commit", "-qm", "non-source advance", cwd=self.root)
        commit_b = run("git", "rev-parse", "HEAD", cwd=self.root)
        run("git", "reset", "--hard", self.commit, cwd=self.root)
        branch = run("git", "symbolic-ref", "--short", "HEAD", cwd=self.root)

        original = fresh._read_archive_members

        def read_then_move_ref(*args, **kwargs):
            result = original(*args, **kwargs)
            run("git", "update-ref", f"refs/heads/{branch}", commit_b, cwd=self.root)
            return result

        fresh._read_archive_members = read_then_move_ref
        try:
            report = self.verify(archive, digest)
        finally:
            fresh._read_archive_members = original
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("HEAD changed during verification", report["problems"][0])

    def test_dirty_execution_helper_invalid(self):
        archive, digest = self.archive()
        (self.live / "spatial_tempo.py").write_bytes(b"DIRTY\n")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("expected commit", report["problems"][0])

    def test_dirty_publisher_invalid(self):
        archive, digest = self.archive()
        (self.live / "build_integrated.py").write_text("# dirty\n", encoding="utf-8")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("expected commit", report["problems"][0])

    def test_missing_mapped_member_invalid(self):
        members = self.members_from_live()
        members.pop("spatial_tempo.py")
        manifest = self.source_manifest(self.members_from_live())
        # Hand-build so the archive is missing a member while SOURCE still claims it.
        path = self.root / "candidate.tar.gz"
        with tarfile.open(path, "w:gz") as tf:
            for name, data in {
                **members,
                "SOURCE.json": json.dumps(manifest).encode(),
            }.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
        report = self.verify(path, sha256(path.read_bytes()))
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("missing source member", report["problems"][0])

    def test_duplicate_mapped_member_invalid(self):
        archive, digest = self.archive(duplicate="main.py")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("duplicate archive source member", report["problems"][0])

    def test_symlink_mapped_member_invalid(self):
        members = self.members_from_live()
        members.pop("scheduler.py")
        path = self.root / "candidate.tar.gz"
        manifest = self.source_manifest(self.members_from_live())
        with tarfile.open(path, "w:gz") as tf:
            for name, data in {
                **members,
                "SOURCE.json": json.dumps(manifest).encode(),
            }.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            info = tarfile.TarInfo("scheduler.py")
            info.type = tarfile.SYMTYPE
            info.linkname = "main.py"
            tf.addfile(info)
        report = self.verify(path, sha256(path.read_bytes()))
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("not a regular file", report["problems"][0])

    def test_live_symlink_invalid(self):
        archive, digest = self.archive()
        target = self.live / "spatial.real"
        target.write_bytes((self.live / "spatial_tempo.py").read_bytes())
        (self.live / "spatial_tempo.py").unlink()
        (self.live / "spatial_tempo.py").symlink_to(target.name)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("symlink live path forbidden", report["problems"][0])

    def test_unexpected_archive_member_invalid(self):
        archive, digest = self.archive(extra={"NOT_PUBLISHED.txt": b"x\n"})
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("unexpected archive member", report["problems"][0])

    def test_source_manifest_omission_invalid(self):
        members = self.members_from_live()
        manifest = self.source_manifest(members)
        manifest["runtime"].pop("spatial_tempo.py")
        archive, digest = self.archive(members, manifest=manifest)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("source-set mismatch", report["problems"][0])

    def test_source_manifest_identity_tamper_invalid(self):
        members = self.members_from_live()
        manifest = self.source_manifest(members)
        manifest["runtime"]["spatial_tempo.py"]["sha256"] = "0" * 64
        archive, digest = self.archive(members, manifest=manifest)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("member identity mismatch", report["problems"][0])

    def test_publisher_mapping_expansion_makes_old_package_invalid(self):
        archive, digest = self.archive()
        mapping_b = dict(self.mapping)
        mapping_b["new_helper.py"] = "new_helper.py"
        (self.live / "new_helper.py").write_bytes(b"NEW = 1\n")
        (self.live / "build_integrated.py").write_bytes(publisher_source(mapping_b))
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "publisher expands source closure", cwd=self.root)
        commit_b = run("git", "rev-parse", "HEAD", cwd=self.root)
        report = self.verify(archive, digest, commit=commit_b)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("missing source member", report["problems"][0])

    def test_publisher_source_escape_invalid(self):
        bad = dict(self.mapping)
        bad["escape.py"] = "../../../../outside.py"
        (self.live / "build_integrated.py").write_bytes(publisher_source(bad))
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "unsafe publisher mapping", cwd=self.root)
        commit_b = run("git", "rev-parse", "HEAD", cwd=self.root)
        archive, digest = self.archive()
        report = self.verify(archive, digest, commit=commit_b)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("escapes repository root", report["problems"][0])

    def test_type_poisoned_digest_and_commit_invalid(self):
        archive, digest = self.archive()
        r1 = self.verify(archive, "ABC")
        self.assertEqual("INVALID", r1["verdict"])
        r2 = fresh.verify_freshness(
            repo_root=self.root,
            live_dir="revenue/kaggriculture/cloud-execution-lab",
            archive=archive,
            expected_archive_sha256=digest,
            expected_commit="not-a-sha",
        )
        self.assertEqual("INVALID", r2["verdict"])


if __name__ == "__main__":
    unittest.main()
