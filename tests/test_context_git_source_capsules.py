import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from host.context_packet import DIGEST_KEY, PacketError, canonical, compile_packet, verify_packet
from host.git_source_capsules import GitSourceError, collect_git_source, verify_git_source


def run(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(["git","-C",str(repo),*args], input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout


class GitSourceCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(self.repo, "init", "-q")
        run(self.repo, "config", "user.email", "capsules@example.invalid")
        run(self.repo, "config", "user.name", "Capsule Tests")
        (self.repo/"alpha.txt").write_text("alpha committed\nline two\n", encoding="utf-8")
        (self.repo/"nested").mkdir()
        (self.repo/"nested/beta.py").write_text("print('beta')\n", encoding="utf-8")
        run(self.repo, "add", "alpha.txt", "nested/beta.py")
        run(self.repo, "commit", "-q", "-m", "base")
        run(self.repo, "branch", "-M", "main")
        self.commit = run(self.repo, "rev-parse", "HEAD").decode().strip()

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, *, paths=("alpha.txt","nested/beta.py"), max_chars=12000, max_file_bytes=16384):
        return compile_packet(
            operation="capsule-op",
            objective="handoff exact committed source",
            pulse={"seq":1,"head":self.commit,"ts":"2026-09-13T13:00:00Z"},
            recent=[],
            ledger={"surfaces":[]},
            requested_main_head=self.commit,
            git_repository=self.repo,
            source_commit=self.commit,
            source_paths=list(paths),
            max_source_file_bytes=max_file_bytes,
            max_chars=max_chars,
            max_events=0,
            max_resources=0,
            max_claims=0,
            max_coordination=0,
        )

    def test_exact_committed_bytes_ignore_moving_worktree(self):
        (self.repo/"alpha.txt").write_text("UNCOMMITTED ATTACK\n", encoding="utf-8")
        packet = self.packet(paths=("alpha.txt",))
        row = packet["git_source"]["capsules"][0]
        self.assertTrue(row["text_included"])
        self.assertEqual(row["text"], "alpha committed\nline two\n")
        self.assertEqual(row["content_sha256"], hashlib.sha256(b"alpha committed\nline two\n").hexdigest())
        self.assertTrue(verify_git_source(packet["git_source"], self.repo)[0])

    def test_argument_order_is_deterministic_and_commit_is_semantic(self):
        a = self.packet(paths=("nested/beta.py","alpha.txt"))
        b = self.packet(paths=("alpha.txt","nested/beta.py"))
        self.assertEqual(a, b)
        self.assertEqual(a["git_source"]["requested_paths"], ["alpha.txt","nested/beta.py"])
        self.assertEqual(a[DIGEST_KEY], b[DIGEST_KEY])

    def test_binary_is_metadata_only_with_exact_hash(self):
        raw = b"\x00\xffbinary"
        (self.repo/"binary.bin").write_bytes(raw)
        run(self.repo, "add", "binary.bin"); run(self.repo, "commit", "-q", "-m", "binary")
        commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
        bundle = collect_git_source(self.repo, commit, ["binary.bin"])
        row = bundle["capsules"][0]
        self.assertIsNone(row["text"])
        self.assertIn(row["source_omission_reason"], {"NON_UTF8","NON_TEXT_CONTROL"})
        self.assertEqual(row["content_sha256"], hashlib.sha256(raw).hexdigest())

    def test_oversize_is_metadata_only_not_truncated_authoritative_text(self):
        raw = ("z"*5000).encode()
        (self.repo/"big.txt").write_bytes(raw)
        run(self.repo, "add", "big.txt"); run(self.repo, "commit", "-q", "-m", "big")
        commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
        packet = compile_packet(
            operation="capsule-op", objective="bounded", pulse={"head":commit}, recent=[], ledger={"surfaces":[]},
            git_repository=self.repo, source_commit=commit, source_paths=["big.txt"], max_source_file_bytes=1024,
            max_chars=5000, max_events=0, max_resources=0, max_claims=0, max_coordination=0,
        )
        row=packet["git_source"]["capsules"][0]
        self.assertFalse(row["text_included"]); self.assertEqual(row["omission_reason"],"FILE_TOO_LARGE")
        self.assertNotIn("text",row); self.assertEqual(row["content_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(packet["omitted"]["git_source_text_bytes"], len(raw))

    def test_packet_budget_omits_whole_text_and_keeps_identity(self):
        raw = ("budget-line-" * 300).encode()
        (self.repo/"budget.txt").write_bytes(raw)
        run(self.repo, "add", "budget.txt"); run(self.repo, "commit", "-q", "-m", "budget")
        commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
        packet = compile_packet(
            operation="capsule-op", objective="bounded", pulse={"head":commit}, recent=[], ledger={"surfaces":[]},
            git_repository=self.repo, source_commit=commit, source_paths=["budget.txt"], max_source_file_bytes=5000,
            max_chars=2600, max_events=0, max_resources=0, max_claims=0, max_coordination=0,
        )
        self.assertLessEqual(len(canonical(packet)),2600)
        self.assertEqual(packet["omitted"]["git_source_text_files"],1)
        row = packet["git_source"]["capsules"][0]
        self.assertFalse(row["text_included"])
        self.assertNotIn("text",row); self.assertEqual(row["omission_reason"],"PACKET_BUDGET")
        self.assertEqual(row["content_sha256"], hashlib.sha256(raw).hexdigest())

    def test_symlink_tree_missing_and_traversal_fail_closed(self):
        if hasattr(os, "symlink"):
            os.symlink("alpha.txt", self.repo/"link.txt")
            run(self.repo, "add", "link.txt"); run(self.repo, "commit", "-q", "-m", "link")
            commit = run(self.repo, "rev-parse", "HEAD").decode().strip()
            with self.assertRaises(GitSourceError): collect_git_source(self.repo, commit, ["link.txt"])
        with self.assertRaises(GitSourceError): collect_git_source(self.repo, self.commit, ["nested"])
        with self.assertRaises(GitSourceError): collect_git_source(self.repo, self.commit, ["missing.txt"])
        for bad in ("../alpha.txt","/alpha.txt","nested/../alpha.txt","*.txt",":(glob)*"):
            with self.assertRaises(GitSourceError): collect_git_source(self.repo, self.commit, [bad])

    def test_wrong_ref_and_noncommit_fail_closed(self):
        blob = run(self.repo, "rev-parse", f"{self.commit}:alpha.txt").decode().strip()
        with self.assertRaises(GitSourceError): collect_git_source(self.repo, blob, ["alpha.txt"])
        with self.assertRaises(GitSourceError): collect_git_source(self.repo, "a"*40, ["alpha.txt"])

    def test_main_drift_is_metadata_not_relabel(self):
        first = self.packet(paths=("alpha.txt",))
        (self.repo/"later.txt").write_text("later\n", encoding="utf-8")
        run(self.repo,"add","later.txt"); run(self.repo,"commit","-q","-m","later")
        ok, reason = verify_git_source(first["git_source"], self.repo)
        self.assertTrue(ok, reason)
        self.assertEqual(first["git_source"]["commit"], self.commit)
        self.assertTrue(first["git_source"]["source_commit_matches_observed_main"])
        newer = collect_git_source(self.repo, self.commit, ["alpha.txt"])
        self.assertFalse(newer["source_commit_matches_observed_main"])
        self.assertEqual(newer["commit"], self.commit)

    def test_tamper_and_reseal_still_fail_git_reverification(self):
        packet = self.packet(paths=("alpha.txt",))
        bad = copy.deepcopy(packet)
        bad["git_source"]["capsules"][0]["content_sha256"] = "0"*64
        semantic = {k:v for k,v in bad.items() if k != DIGEST_KEY}
        bad[DIGEST_KEY] = hashlib.sha256(canonical(semantic).encode()).hexdigest()
        self.assertTrue(verify_packet(bad)[0])
        self.assertEqual(verify_git_source(bad["git_source"], self.repo), (False,"git-source-content-sha256"))

    def test_source_argument_triad_is_fail_closed(self):
        with self.assertRaises(PacketError):
            compile_packet(
                operation="x",objective="y",pulse={},recent=[],ledger={"surfaces":[]},
                source_commit=self.commit,source_paths=["alpha.txt"],
            )


if __name__=="__main__":
    unittest.main()
