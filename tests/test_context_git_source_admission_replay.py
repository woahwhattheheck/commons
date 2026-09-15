import subprocess
import tempfile
import unittest
from pathlib import Path

from host.context_packet import compile_packet
from host.git_source_capsules import verify_packet_git_source


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        text=True,
    ).stdout.strip()


class GitSourceAdmissionReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "replay@example.invalid")
        git(self.repo, "config", "user.name", "Replay Tests")
        (self.repo / "alpha.txt").write_text("alpha committed\nline two\n", encoding="utf-8")
        git(self.repo, "add", "alpha.txt")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "branch", "-M", "main")
        self.commit = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_packet_budget_omission_reverifies_valid(self):
        raw = ("budget-line-" * 300).encode()
        (self.repo / "budget.txt").write_bytes(raw)
        git(self.repo, "add", "budget.txt")
        git(self.repo, "commit", "-q", "-m", "budget")
        commit = git(self.repo, "rev-parse", "HEAD")
        packet = compile_packet(
            operation="capsule-op",
            objective="bounded",
            pulse={"head": commit},
            recent=[],
            ledger={"surfaces": []},
            git_repository=self.repo,
            source_commit=commit,
            source_paths=["budget.txt"],
            max_source_file_bytes=5000,
            max_chars=2600,
            max_events=0,
            max_resources=0,
            max_claims=0,
            max_coordination=0,
        )
        row = packet["git_source"]["capsules"][0]
        self.assertFalse(row["text_included"])
        self.assertEqual(row["omission_reason"], "PACKET_BUDGET")
        self.assertEqual(verify_packet_git_source(packet, self.repo), (True, "ok"))

    def test_replay_matches_priority_and_later_sections(self):
        packet = compile_packet(
            operation="capsule-op",
            objective="replay full deterministic admission boundary",
            pulse={"seq": 7, "head": self.commit, "ts": "2026-09-13T13:00:00Z"},
            recent=[
                {"id": "event-1", "ts": "2026-09-13T12:59:00Z", "body": "capsule-op recent evidence"},
                {"id": "event-2", "ts": "2026-09-13T12:58:00Z", "body": "capsule-op second evidence"},
            ],
            ledger={"surfaces": [
                {"name": "capsule-op-ledger", "kind": "git", "stage": "ready", "condition": "exact source"},
            ]},
            claims=[
                {"key": "capsule-op", "holder": "ZZH-P8Q6", "state": "HELD", "heartbeat_at": "2026-09-13T13:00:00Z", "note": "capsule-op source custody"},
            ],
            coordination={"items": [
                {"operation": "capsule-op", "id": "coord-1", "state": "OPEN", "next_action": "review exact source"},
            ]},
            requested_main_head=self.commit,
            git_repository=self.repo,
            source_commit=self.commit,
            source_paths=["alpha.txt"],
            max_chars=8000,
            max_events=2,
            max_resources=1,
            max_claims=1,
            max_coordination=1,
        )
        self.assertEqual(len(packet["claims"]), 1)
        self.assertEqual(len(packet["coordination"]), 1)
        self.assertEqual(len(packet["recent"]), 2)
        self.assertEqual(len(packet["resources"]), 1)
        self.assertTrue(packet["git_source"]["capsules"][0]["text_included"])
        self.assertEqual(verify_packet_git_source(packet, self.repo), (True, "ok"))


if __name__ == "__main__":
    unittest.main()
