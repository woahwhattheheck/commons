import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

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
        self.live = self.root / "revenue/kaggriculture/cloud-execution-lab"
        self.live.mkdir(parents=True)
        for name, data in CORE.items():
            (self.live / name).write_bytes(data)
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "base", cwd=self.root)
        self.commit = run("git", "rev-parse", "HEAD", cwd=self.root)

    def tearDown(self):
        self.td.cleanup()

    def archive(self, members=None, *, duplicate=None, symlink=None):
        members = dict(CORE if members is None else members)
        path = self.root / "candidate.tar.gz"
        with tarfile.open(path, "w:gz") as tf:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
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
        return path, sha256(path.read_bytes())

    def verify(self, archive, digest, commit=None):
        return fresh.verify_freshness(
            repo_root=self.root,
            live_dir="revenue/kaggriculture/cloud-execution-lab",
            archive=archive,
            expected_archive_sha256=digest,
            expected_commit=commit or self.commit,
        )

    def test_current_exact_core(self):
        archive, digest = self.archive()
        report = self.verify(archive, digest)
        self.assertEqual("CURRENT", report["verdict"])
        self.assertEqual([], report["stale_paths"])
        self.assertTrue(all(row["same"] for row in report["files"]))

    def test_stale_runtime_only(self):
        old = dict(CORE)
        old["titan_runtime.py"] = b"RUNTIME = 0\n"
        archive, digest = self.archive(old)
        report = self.verify(archive, digest)
        self.assertEqual("STALE", report["verdict"])
        self.assertEqual(["titan_runtime.py"], report["stale_paths"])
        row = next(r for r in report["files"] if r["path"] == "titan_runtime.py")
        self.assertNotEqual(row["live"]["git_blob"], row["package"]["git_blob"])

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

    def test_dirty_live_file_invalid(self):
        archive, digest = self.archive()
        (self.live / "scheduler.py").write_bytes(b"DIRTY\n")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("not byte-identical to HEAD", report["problems"][0])

    def test_missing_core_member_invalid(self):
        members = dict(CORE)
        members.pop("scheduler.py")
        archive, digest = self.archive(members)
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("missing core member", report["problems"][0])

    def test_duplicate_core_member_invalid(self):
        archive, digest = self.archive(duplicate="main.py")
        report = self.verify(archive, digest)
        self.assertEqual("INVALID", report["verdict"])
        self.assertIn("duplicate archive core member", report["problems"][0])

    def test_symlink_core_member_invalid(self):
        members = dict(CORE)
        members.pop("scheduler.py")
        archive, digest = self.archive(members, symlink="scheduler.py")
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
