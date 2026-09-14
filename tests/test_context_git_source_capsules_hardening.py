import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from host.context_packet import DIGEST_KEY, canonical, compile_packet, verify_packet
from host.git_source_capsules import (
    GitSourceError,
    collect_git_source,
    verify_git_source,
    verify_packet_git_source,
)


def run(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout


def reseal(packet: dict) -> None:
    semantic = {key: value for key, value in packet.items() if key != DIGEST_KEY}
    packet[DIGEST_KEY] = hashlib.sha256(canonical(semantic).encode()).hexdigest()


class GitSourceCapsuleHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(self.repo, "init", "-q")
        run(self.repo, "config", "user.email", "hardening@example.invalid")
        run(self.repo, "config", "user.name", "Capsule Hardening Tests")
        (self.repo / "alpha.txt").write_text("alpha committed\nline two\n", encoding="utf-8")
        (self.repo / "one.txt").write_text("x", encoding="utf-8")
        run(self.repo, "add", "alpha.txt", "one.txt")
        run(self.repo, "commit", "-q", "-m", "base")
        run(self.repo, "branch", "-M", "main")
        self.commit = run(self.repo, "rev-parse", "HEAD").decode().strip()

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, *, paths=("alpha.txt",), commit=None, max_file_bytes=16384, max_chars=12000):
        source_commit = commit or self.commit
        return compile_packet(
            operation="capsule-hardening",
            objective="verify exact committed source authority",
            pulse={"seq": 1, "head": source_commit, "ts": "2026-09-13T22:40:00Z"},
            recent=[],
            ledger={"surfaces": []},
            requested_main_head=source_commit,
            git_repository=self.repo,
            source_commit=source_commit,
            source_paths=list(paths),
            max_source_file_bytes=max_file_bytes,
            max_chars=max_chars,
            max_events=0,
            max_resources=0,
            max_claims=0,
            max_coordination=0,
        )

    def test_resealed_unknown_capsule_key_is_rejected(self):
        packet = self.packet()
        bad = copy.deepcopy(packet)
        bad["git_source"]["capsules"][0]["authority"] = "not committed source"
        reseal(bad)
        self.assertTrue(verify_packet(bad)[0])
        self.assertEqual(
            verify_git_source(bad["git_source"], self.repo),
            (False, "git-source-capsule-shape"),
        )
        self.assertEqual(
            verify_packet_git_source(bad, self.repo),
            (False, "git-source-readback"),
        )

    def test_bool_and_float_byte_aliases_are_rejected_before_equality(self):
        packet = self.packet(paths=("one.txt",))
        self.assertEqual(packet["git_source"]["capsules"][0]["bytes"], 1)
        for forged in (True, 1.0):
            with self.subTest(forged=repr(forged)):
                bad = copy.deepcopy(packet)
                bad["git_source"]["capsules"][0]["bytes"] = forged
                reseal(bad)
                self.assertTrue(verify_packet(bad)[0])
                self.assertEqual(
                    verify_git_source(bad["git_source"], self.repo),
                    (False, "git-source-bytes"),
                )
                self.assertEqual(
                    verify_packet_git_source(bad, self.repo),
                    (False, "git-source-readback"),
                )

    def test_boolean_source_omission_counters_are_rejected(self):
        (self.repo / "one.bin").write_bytes(b"\xff")
        run(self.repo, "add", "one.bin")
        run(self.repo, "commit", "-q", "-m", "one-byte-binary")
        commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
        packet = self.packet(paths=("one.bin",), commit=commit)
        self.assertEqual(packet["omitted"]["git_source_text_files"], 1)
        self.assertEqual(packet["omitted"]["git_source_text_bytes"], 1)
        for field in ("git_source_text_files", "git_source_text_bytes"):
            with self.subTest(field=field):
                bad = copy.deepcopy(packet)
                bad["omitted"][field] = True
                reseal(bad)
                self.assertTrue(verify_packet(bad)[0])
                self.assertEqual(
                    verify_packet_git_source(bad, self.repo),
                    (False, "git-source-omitted-shape"),
                )

    def test_git_replace_cannot_rewrite_requested_commit_tree_or_blob(self):
        packet = self.packet(paths=("alpha.txt",))
        self.assertEqual(packet["git_source"]["capsules"][0]["text"], "alpha committed\nline two\n")

        (self.repo / "alpha.txt").write_text("REPLACEMENT\n", encoding="utf-8")
        run(self.repo, "add", "alpha.txt")
        run(self.repo, "commit", "-q", "-m", "replacement")
        replacement = run(self.repo, "rev-parse", "HEAD").decode().strip()
        run(self.repo, "replace", self.commit, replacement)

        # Ordinary Git observes refs/replace; the authoritative reader must not.
        self.assertEqual(run(self.repo, "show", f"{self.commit}:alpha.txt"), b"REPLACEMENT\n")
        reread = collect_git_source(self.repo, self.commit, ["alpha.txt"])
        self.assertEqual(reread["capsules"][0]["text"], "alpha committed\nline two\n")
        self.assertTrue(verify_git_source(packet["git_source"], self.repo)[0])
        self.assertTrue(verify_packet_git_source(packet, self.repo)[0])

    def test_inherited_replace_reenable_attempt_is_overridden(self):
        (self.repo / "alpha.txt").write_text("REPLACEMENT\n", encoding="utf-8")
        run(self.repo, "add", "alpha.txt")
        run(self.repo, "commit", "-q", "-m", "replacement-env")
        replacement = run(self.repo, "rev-parse", "HEAD").decode().strip()
        run(self.repo, "replace", self.commit, replacement)

        prior = os.environ.get("GIT_NO_REPLACE_OBJECTS")
        os.environ["GIT_NO_REPLACE_OBJECTS"] = "0"
        try:
            bundle = collect_git_source(self.repo, self.commit, ["alpha.txt"])
        finally:
            if prior is None:
                os.environ.pop("GIT_NO_REPLACE_OBJECTS", None)
            else:
                os.environ["GIT_NO_REPLACE_OBJECTS"] = prior
        self.assertEqual(bundle["capsules"][0]["text"], "alpha committed\nline two\n")

    def test_inherited_git_dir_cannot_redirect_explicit_repository(self):
        with tempfile.TemporaryDirectory() as other_tmp:
            other = Path(other_tmp)
            run(other, "init", "-q")
            run(other, "config", "user.email", "decoy@example.invalid")
            run(other, "config", "user.name", "Decoy Repo")
            (other / "alpha.txt").write_text("DECOY REPOSITORY\n", encoding="utf-8")
            run(other, "add", "alpha.txt")
            run(other, "commit", "-q", "-m", "decoy")
            run(other, "branch", "-M", "main")
            decoy_commit = run(other, "rev-parse", "HEAD").decode().strip()

            prior = os.environ.get("GIT_DIR")
            os.environ["GIT_DIR"] = str(other / ".git")
            try:
                # Ordinary Git proves that -C does not defeat inherited GIT_DIR.
                self.assertEqual(
                    run(self.repo, "rev-parse", "HEAD").decode().strip(),
                    decoy_commit,
                )
                bundle = collect_git_source(self.repo, self.commit, ["alpha.txt"])
                with self.assertRaises(GitSourceError):
                    collect_git_source(self.repo, decoy_commit, ["alpha.txt"])
            finally:
                if prior is None:
                    os.environ.pop("GIT_DIR", None)
                else:
                    os.environ["GIT_DIR"] = prior

        self.assertEqual(bundle["commit"], self.commit)
        self.assertEqual(bundle["capsules"][0]["text"], "alpha committed\nline two\n")

    def test_inherited_object_directory_cannot_inject_forged_blob(self):
        blob_sha = run(self.repo, "rev-parse", f"{self.commit}:alpha.txt").decode().strip()
        forged = b"FORGED OBJECT STORE\n"
        forged_object = b"blob " + str(len(forged)).encode("ascii") + b"\0" + forged
        # Prove this is not a SHA-1 collision; Git still trusts the loose-object pathname.
        self.assertNotEqual(hashlib.sha1(forged_object).hexdigest(), blob_sha)

        with tempfile.TemporaryDirectory() as object_tmp:
            object_dir = Path(object_tmp)
            forged_path = object_dir / blob_sha[:2] / blob_sha[2:]
            forged_path.parent.mkdir(parents=True)
            forged_path.write_bytes(zlib.compress(forged_object))

            prior_object = os.environ.get("GIT_OBJECT_DIRECTORY")
            prior_alt = os.environ.get("GIT_ALTERNATE_OBJECT_DIRECTORIES")
            os.environ["GIT_OBJECT_DIRECTORY"] = str(object_dir)
            os.environ["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(self.repo / ".git" / "objects")
            try:
                # Ordinary Git accepts attacker bytes under the legitimate OID path.
                self.assertEqual(run(self.repo, "cat-file", "blob", blob_sha), forged)
                bundle = collect_git_source(self.repo, self.commit, ["alpha.txt"])
            finally:
                if prior_object is None:
                    os.environ.pop("GIT_OBJECT_DIRECTORY", None)
                else:
                    os.environ["GIT_OBJECT_DIRECTORY"] = prior_object
                if prior_alt is None:
                    os.environ.pop("GIT_ALTERNATE_OBJECT_DIRECTORIES", None)
                else:
                    os.environ["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = prior_alt

        self.assertEqual(bundle["capsules"][0]["text"], "alpha committed\nline two\n")

    def test_partial_clone_missing_blob_fails_closed_without_lazy_fetch(self):
        payload = "L" * 200_000
        (self.repo / "promised.txt").write_text(payload, encoding="utf-8")
        run(self.repo, "add", "promised.txt")
        run(self.repo, "commit", "-q", "-m", "promised")
        commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
        blob_sha = run(self.repo, "rev-parse", f"{commit}:promised.txt").decode().strip()
        run(self.repo, "config", "uploadpack.allowFilter", "true")

        with tempfile.TemporaryDirectory() as clone_tmp:
            clone = Path(clone_tmp) / "partial"
            proc = subprocess.run(
                [
                    "git",
                    "clone",
                    "-q",
                    "--no-checkout",
                    "--filter=blob:none",
                    self.repo.as_uri(),
                    str(clone),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if proc.returncode != 0:
                self.skipTest("local Git transport does not support partial clone filtering")

            no_lazy = os.environ.copy()
            no_lazy["GIT_NO_LAZY_FETCH"] = "1"
            before = subprocess.run(
                ["git", "-C", str(clone), "cat-file", "-e", blob_sha],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=no_lazy,
                check=False,
            )
            if before.returncode == 0:
                self.skipTest("partial clone server materialized filtered blob")

            with self.assertRaises(GitSourceError):
                collect_git_source(clone, commit, ["promised.txt"])

            after = subprocess.run(
                ["git", "-C", str(clone), "cat-file", "-e", blob_sha],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=no_lazy,
                check=False,
            )
            self.assertNotEqual(after.returncode, 0)


if __name__ == "__main__":
    unittest.main()
