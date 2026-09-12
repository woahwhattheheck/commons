import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("fresh", HERE / "check_native_freshness.py")
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)

CORE = {
    "main.py": b"def agent(obs, cfg):\n    return {}\n",
    "titan_runtime.py": b"RUNTIME = 1\n",
    "scheduler.py": b"SCHEDULER = 1\n",
    "frozen_selected.py": b"FROZEN = 1\n",
    "TITAN-CONFIG.json": b'{"consumer":"frozen"}\n',
}
EXTRA = {"spatial_tempo.py": b"SPATIAL = 1\n"}
ALL = {**CORE, **EXTRA}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        run("git", "init", "-q", cwd=self.root)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.root)
        run("git", "config", "user.name", "test", cwd=self.root)
        self.live = self.root / fresh.CANONICAL_LIVE_DIR
        self.live.mkdir(parents=True)
        for name, data in ALL.items():
            path = self.live / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "base", cwd=self.root)
        self.commit = run("git", "rev-parse", "HEAD", cwd=self.root)

    def tearDown(self):
        self.td.cleanup()

    def source(self, members, *, source_paths=None):
        source_paths = source_paths or {}
        return {
            "runtime": {
                name: {
                    "bytes": len(data),
                    "sha256": sha256(data),
                    "source_path": source_paths.get(name, name),
                }
                for name, data in members.items()
            }
        }

    def archive(
        self,
        members=None,
        *,
        source=None,
        duplicate=None,
        symlink=None,
        extra_member=None,
        source_raw=None,
    ):
        members = dict(ALL if members is None else members)
        if source_raw is None:
            source = self.source(members) if source is None else source
            source_raw = json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
        path = self.root / "candidate.tar.gz"
        with tarfile.open(path, "w:gz") as tf:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            info = tarfile.TarInfo(fresh.SOURCE_MEMBER)
            info.size = len(source_raw)
            tf.addfile(info, io.BytesIO(source_raw))
            if duplicate:
                data = members[duplicate]
                info = tarfile.TarInfo(duplicate)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            if symlink:
                info = tarfile.TarInfo(symlink)
                info.type = tarfile.SYMTYPE
                info.linkname = "main.py"
                tf.addfile(info)
            if extra_member:
                data = b"EXTRA\n"
                info = tarfile.TarInfo(extra_member)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
        return path, sha256(path.read_bytes())

    def verify(self, archive, digest, commit=None, live_dir=None):
        return fresh.verify_freshness(
            repo_root=self.root,
            live_dir=fresh.CANONICAL_LIVE_DIR if live_dir is None else live_dir,
            archive=archive,
            expected_archive_sha256=digest,
            expected_commit=commit or self.commit,
        )

    def test_current_exact_source_closure(self):
        archive, digest = self.archive()
        report = self.verify(archive, digest)
        self.assertEqual("CURRENT", report["verdict"])
        self.assertEqual([], report["stale_paths"])
        self.assertEqual(len(ALL), report["runtime_members"])
        self.assertTrue(all(row["same"] for row in report["files"]))

    def test_stale_runtime_only(self):
        old = dict(ALL)
        old["titan_runtime.py"] = b"RUNTIME = 0\n"
        archive, digest = self.archive(old)
        report = self.verify(archive, digest)
        self.assertEqual("STALE", report["verdict"])
        self.assertEqual(["titan_runtime.py"], report["stale_paths"])

    def test_stale_imported_dependency_with_core_identical(self):
        old = dict(ALL)
        old["spatial_tempo.py"] = b"SPATIAL = 0\n"
        archive, digest = self.archive(old)
        report = self.verify(archive, digest)
        self.assertEqual("STALE", report["verdict"])
        self.assertEqual(["spatial_tempo.py"], report["stale_paths"])
        self.assertTrue(all(row["same"] for row in report["files"] if row["path"] in CORE))

    def test_noncanonical_live_dir_decoy_invalid(self):
        decoy = self.root / "tracked-decoy"
        decoy.mkdir()
        for name, data in ALL.items():
            path = decoy / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "decoy", cwd=self.root)
        self.commit = run("git", "rev-parse", "HEAD", cwd=self.root)
        # Make canonical bytes newer while decoy still matches the package.
        (self.live / "titan_runtime.py").write_bytes(b"RUNTIME = 2\n")
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "canonical-newer", cwd=self.root)
        self.commit = run("git", "rev-parse", "HEAD", cwd=self.root)
        archive, digest = self.archive()
        report = self.verify(archive, digest, live_dir="tracked-decoy")
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("must be canonical", report["problems"][0])

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

    def test_midrun_checkout_advance_cannot_rebind_expected_commit(self):
        moved = dict(ALL)
        moved["spatial_tempo.py"] = b"SPATIAL = 2\n"
        (self.live / "spatial_tempo.py").write_bytes(moved["spatial_tempo.py"])
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "moved helper", cwd=self.root)
        moved_commit = run("git", "rev-parse", "HEAD", cwd=self.root)
        archive, digest = self.archive(moved)
        run("git", "reset", "--hard", self.commit, cwd=self.root)

        original = fresh._read_archive

        def read_then_advance(*args, **kwargs):
            result = original(*args, **kwargs)
            run("git", "reset", "--hard", moved_commit, cwd=self.root)
            return result

        with mock.patch.object(fresh, "_read_archive", side_effect=read_then_advance):
            report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("expected commit", report["problems"][0])

    def test_midrun_ref_advance_with_identical_closure_invalid(self):
        archive, digest = self.archive()
        marker = self.root / "UNRELATED.txt"
        marker.write_text("new commit, same declared source closure\n", encoding="utf-8")
        run("git", "add", "UNRELATED.txt", cwd=self.root)
        run("git", "commit", "-qm", "unrelated commit", cwd=self.root)
        moved_commit = run("git", "rev-parse", "HEAD", cwd=self.root)
        run("git", "reset", "--hard", self.commit, cwd=self.root)
        branch = run("git", "symbolic-ref", "--short", "HEAD", cwd=self.root)

        original = fresh._read_archive

        def read_then_move_ref(*args, **kwargs):
            result = original(*args, **kwargs)
            run("git", "update-ref", f"refs/heads/{branch}", moved_commit, cwd=self.root)
            return result

        with mock.patch.object(fresh, "_read_archive", side_effect=read_then_move_ref):
            report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("HEAD changed during verification", report["problems"][0])

    def test_dirty_live_file_invalid(self):
        archive, digest = self.archive()
        (self.live / "scheduler.py").write_bytes(b"DIRTY\n")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("not byte-identical to expected commit", report["problems"][0])

    def test_missing_declared_member_invalid(self):
        members = dict(ALL)
        source = self.source(members)
        missing = dict(members)
        missing.pop("scheduler.py")
        archive, digest = self.archive(missing, source=source)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("missing SOURCE runtime member", report["problems"][0])

    def test_extra_undeclared_member_invalid(self):
        archive, digest = self.archive(extra_member="surprise.py")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("member-set mismatch", report["problems"][0])

    def test_duplicate_member_invalid(self):
        archive, digest = self.archive(duplicate="main.py")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("duplicate archive member", report["problems"][0])

    def test_symlink_archive_member_invalid(self):
        members = dict(ALL)
        source = self.source(members)
        members.pop("scheduler.py")
        archive, digest = self.archive(members, source=source, symlink="scheduler.py")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("not a regular file", report["problems"][0])

    def test_live_symlink_invalid(self):
        archive, digest = self.archive()
        target = self.live / "scheduler.real"
        target.write_bytes((self.live / "scheduler.py").read_bytes())
        (self.live / "scheduler.py").unlink()
        (self.live / "scheduler.py").symlink_to(target.name)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("symlink live path forbidden", report["problems"][0])

    def test_source_path_escape_invalid(self):
        source = self.source(ALL, source_paths={"spatial_tempo.py": "../../../../escape.py"})
        archive, digest = self.archive(source=source)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("escapes repository", report["problems"][0])

    def test_core_source_path_substitution_invalid(self):
        source = self.source(ALL, source_paths={"main.py": "scheduler.py"})
        archive, digest = self.archive(source=source)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("canonical core source_path mismatch", report["problems"][0])

    def test_nonfinite_source_json_invalid(self):
        source = json.dumps(self.source(ALL), sort_keys=True)
        source = source[:-1] + ',"poison":NaN}'
        archive, digest = self.archive(source_raw=source.encode())
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("non-finite constant", report["problems"][0])

    def test_duplicate_source_json_key_invalid(self):
        source = json.dumps(self.source(ALL), sort_keys=True)
        poisoned = '{"runtime":{},' + source[1:]
        archive, digest = self.archive(source_raw=poisoned.encode())
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("duplicate key", report["problems"][0])

    def test_archive_member_count_bound_invalid(self):
        path = self.root / "candidate.tar.gz"
        source = json.dumps(self.source(ALL), sort_keys=True).encode()
        with tarfile.open(path, "w:gz") as tf:
            for index in range(fresh.MAX_TAR_MEMBERS):
                info = tarfile.TarInfo(f"junk/{index}")
                info.size = 0
                tf.addfile(info, io.BytesIO(b""))
            info = tarfile.TarInfo(fresh.SOURCE_MEMBER)
            info.size = len(source)
            tf.addfile(info, io.BytesIO(source))
        report = self.verify(path, sha256(path.read_bytes()))
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("member count", report["problems"][0])

    def test_type_poisoned_digest_and_commit_invalid(self):
        archive, digest = self.archive()
        r1 = self.verify(archive, "ABC")
        self.assertEqual("INVALID", r1["verdict"])
        r2 = fresh.verify_freshness(
            repo_root=self.root,
            archive=archive,
            expected_archive_sha256=digest,
            expected_commit="not-a-sha",
        )
        self.assertEqual("INVALID", r2["verdict"])


if __name__ == "__main__":
    unittest.main()
