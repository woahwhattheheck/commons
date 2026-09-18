import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from branch_truth_delta import collect_dirty_worktree, collect_remote_branches, collect_repositories


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


class BranchTruthDeltaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.tempdir.name)
        git(cls.repo, "init", "-b", "main")
        git(cls.repo, "config", "user.name", "Ledger Test")
        git(cls.repo, "config", "user.email", "ledger@example.invalid")
        (cls.repo / "base.txt").write_text("base\n", encoding="utf-8")
        git(cls.repo, "add", "base.txt")
        git(cls.repo, "commit", "-m", "base")
        cls.base = git(cls.repo, "rev-parse", "HEAD")
        git(cls.repo, "update-ref", "refs/remotes/origin/landed", cls.base)

        git(cls.repo, "switch", "-c", "feature")
        (cls.repo / "feature.txt").write_text("same patch\n", encoding="utf-8")
        git(cls.repo, "add", "feature.txt")
        git(cls.repo, "commit", "-m", "feature one")
        feature = git(cls.repo, "rev-parse", "HEAD")
        git(cls.repo, "update-ref", "refs/remotes/origin/feature", feature)
        git(cls.repo, "commit", "--allow-empty", "-m", "history-only duplicate")
        feature_copy = git(cls.repo, "rev-parse", "HEAD")
        git(cls.repo, "update-ref", "refs/remotes/origin/feature-copy", feature_copy)

        git(cls.repo, "switch", "main")
        git(cls.repo, "switch", "-c", "equivalent")
        (cls.repo / "feature.txt").write_text("same patch\n", encoding="utf-8")
        git(cls.repo, "add", "feature.txt")
        git(cls.repo, "commit", "-m", "same content, different commit")
        equivalent = git(cls.repo, "rev-parse", "HEAD")
        git(cls.repo, "update-ref", "refs/remotes/origin/equivalent", equivalent)

        git(cls.repo, "switch", "main")
        (cls.repo / "main.txt").write_text("main advanced\n", encoding="utf-8")
        git(cls.repo, "add", "main.txt")
        git(cls.repo, "commit", "-m", "advance main")
        git(cls.repo, "update-ref", "refs/remotes/origin/main", git(cls.repo, "rev-parse", "HEAD"))
        cls.first = collect_remote_branches(
            cls.repo,
            pr_map={"feature": {"number": 7, "owner": "peer", "state": "OPEN"}},
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_inventory_freezes_base_and_clusters_equivalent_content(self) -> None:
        ledger = self.first
        rows = {row["branch"]: row for row in ledger["branches"]}
        self.assertEqual(ledger["summary"]["remote_branch_count"], 4)
        self.assertTrue(rows["landed"]["is_ancestor"])
        self.assertEqual(rows["landed"]["unique_delta_state"], "ANCESTRAL")
        self.assertEqual(rows["feature"]["ahead"], 1)
        self.assertEqual(rows["feature"]["behind"], 1)
        self.assertEqual(rows["feature"]["active_pr"]["number"], 7)
        self.assertEqual(rows["feature"]["comparison_completeness"], "COMPLETE")
        self.assertEqual(rows["feature"]["fingerprint"]["completeness"], "COMPLETE")
        self.assertEqual(rows["feature"]["tree_sha"], rows["feature-copy"]["tree_sha"])
        self.assertEqual(rows["feature"]["tree_sha"], rows["equivalent"]["tree_sha"])
        self.assertEqual(rows["feature"]["patch_set_digest"], rows["equivalent"]["patch_set_digest"])
        self.assertEqual(rows["feature"]["changed_path_blob_map"]["feature.txt"]["status"], "A")
        self.assertEqual(len(rows["feature"]["unique_commit_ids"]), 1)
        self.assertEqual(len(ledger["clusters"]["exact_tree_cluster"]), 1)
        self.assertEqual(len(ledger["clusters"]["patch_set_cluster"]), 1)

    def test_dirty_worktree_keeps_index_and_worktree_provenance_separate(self) -> None:
        (self.repo / "base.txt").write_text("working\n", encoding="utf-8")
        (self.repo / "new.txt").write_text("untracked\n", encoding="utf-8")
        record = collect_dirty_worktree(self.repo)
        rows = {row["path"]: row for row in record["entries"]}
        self.assertEqual(record["kind"], "dirty-local-provenance")
        self.assertEqual(rows["base.txt"]["worktree_status"], "M")
        self.assertIsNotNone(rows["base.txt"]["index_blob"])
        self.assertIsNotNone(rows["base.txt"]["worktree_blob"])
        self.assertEqual(rows["new.txt"]["index_status"], "?")
        self.assertIsNone(rows["new.txt"]["index_blob"])
        self.assertIsNotNone(rows["new.txt"]["worktree_blob"])

    def test_output_is_json_serializable(self) -> None:
        payload = self.first
        self.assertEqual(json.loads(json.dumps(payload))["schema"], "commons.branch-truth-delta.v1")

    def test_complete_observation_is_resumable_and_mutable_pr_evidence_refreshes(self) -> None:
        second = collect_remote_branches(
            self.repo,
            resume=self.first,
            pr_map={"feature": {"number": 9, "check_head_sha": "a" * 40, "check_conclusions": ["SUCCESS"]}},
        )
        rows = {row["branch"]: row for row in second["branches"]}
        self.assertEqual(second["summary"]["resumed_complete_observation_count"], 4)
        self.assertTrue(rows["feature"]["resumed_from_complete_observation"])
        self.assertEqual(rows["feature"]["active_pr"]["number"], 9)
        self.assertEqual(rows["feature"]["check_head_sha"], "a" * 40)

    def test_resumed_observation_refreshes_mutable_collision_state(self) -> None:
        conflicted = collect_remote_branches(
            self.repo,
            pr_map={"feature": {"number": 7, "collision_state": "CONFLICT"}},
        )
        conflicted_rows = {row["branch"]: row for row in conflicted["branches"]}
        self.assertEqual(conflicted_rows["feature"]["unique_delta_state"], "CONFLICT")

        resolved = collect_remote_branches(
            self.repo,
            resume=conflicted,
            pr_map={"feature": {"number": 7, "collision_state": "CLEAR"}},
        )
        resolved_rows = {row["branch"]: row for row in resolved["branches"]}
        self.assertTrue(resolved_rows["feature"]["resumed_from_complete_observation"])
        self.assertEqual(resolved_rows["feature"]["unique_delta_state"], "UNIQUE")

        newly_conflicted = collect_remote_branches(
            self.repo,
            resume=self.first,
            pr_map={"feature": {"number": 7, "collision_state": "CONFLICT"}},
        )
        newly_conflicted_rows = {row["branch"]: row for row in newly_conflicted["branches"]}
        self.assertTrue(newly_conflicted_rows["feature"]["resumed_from_complete_observation"])
        self.assertEqual(newly_conflicted_rows["feature"]["unique_delta_state"], "CONFLICT")

    def test_multi_repo_envelope(self) -> None:
        payload = collect_repositories(
            [self.repo, self.repo],
            resume={"schema": "commons.branch-truth-delta.v1", "repositories": [self.first]},
        )
        self.assertEqual(payload["summary"]["repository_count"], 2)
        self.assertEqual(len(payload["repositories"]), 2)


if __name__ == "__main__":
    unittest.main()
