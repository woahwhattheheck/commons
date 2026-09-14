import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from host.context_packet import DIGEST_KEY, canonical, compile_packet, verify_packet
from host.git_source_capsules import collect_git_source, verify_git_source, verify_packet_git_source


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


if __name__ == "__main__":
    unittest.main()
