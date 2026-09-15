import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from host.git_source_capsules import GitSourceError, collect_git_source


def run(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout


def loose_path(repo: Path, oid: str) -> Path:
    return repo / ".git" / "objects" / oid[:2] / oid[2:]


def forge_loose(path: Path, kind: str, payload: bytes) -> None:
    raw = f"{kind} {len(payload)}\0".encode("ascii") + payload
    path.write_bytes(zlib.compress(raw))


class GitSourceObjectIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(self.repo, "init", "-q")
        run(self.repo, "config", "user.email", "object-integrity@example.invalid")
        run(self.repo, "config", "user.name", "Object Integrity Tests")
        (self.repo / "alpha.txt").write_text("ORIGINAL BLOB\n", encoding="utf-8")
        run(self.repo, "add", "alpha.txt")
        run(self.repo, "commit", "-q", "-m", "base")
        run(self.repo, "branch", "-M", "main")
        self.commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
        self.tree = run(self.repo, "rev-parse", "HEAD^{tree}").decode().strip()
        self.blob = run(self.repo, "rev-parse", "HEAD:alpha.txt").decode().strip()

    def tearDown(self):
        self.tmp.cleanup()

    def _forge_then_assert_rejected(self, oid: str, kind: str, payload: bytes) -> None:
        path = loose_path(self.repo, oid)
        if not path.is_file():
            self.skipTest(f"fresh Git object {oid} was not loose")
        original = path.read_bytes()
        try:
            forge_loose(path, kind, payload)
            # Ordinary Git trusts the loose-object pathname enough to expose the
            # forged object; the capsule reader must independently re-hash it.
            self.assertEqual(run(self.repo, "cat-file", kind, oid), payload)
            with self.assertRaises(GitSourceError):
                collect_git_source(self.repo, self.commit, ["alpha.txt"])
        finally:
            path.write_bytes(original)

    def test_corrupt_commit_payload_under_real_oid_is_rejected(self):
        payload = run(self.repo, "cat-file", "commit", self.commit)
        self._forge_then_assert_rejected(
            self.commit,
            "commit",
            payload + b"\nforged trailer\n",
        )

    def test_corrupt_tree_payload_under_real_oid_is_rejected(self):
        payload = run(self.repo, "cat-file", "tree", self.tree)
        self.assertGreater(len(payload), 0)
        forged = bytes([payload[0] ^ 1]) + payload[1:]
        self._forge_then_assert_rejected(self.tree, "tree", forged)

    def test_corrupt_blob_payload_under_real_oid_is_rejected(self):
        self._forge_then_assert_rejected(
            self.blob,
            "blob",
            b"FORGED BLOB WITH WRONG OBJECT HASH\n",
        )


if __name__ == "__main__":
    unittest.main()
