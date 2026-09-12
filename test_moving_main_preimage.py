from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from host.moving_main_preimage import MISSING, ProofError, analyze, main


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc.stdout.strip()


class RepoFixture:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "owned.txt").write_text("base\n", encoding="utf-8")
        (self.repo / "unrelated.txt").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "branch", "main")
        git(self.repo, "checkout", "-qb", "candidate")
        (self.repo / "owned.txt").write_text("candidate\n", encoding="utf-8")
        git(self.repo, "commit", "-qam", "candidate")
        self.head = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "main")
        (self.repo / "unrelated.txt").write_text("main drift\n", encoding="utf-8")
        git(self.repo, "commit", "-qam", "main drift")
        self.current_main = git(self.repo, "rev-parse", "HEAD")

    def close(self) -> None:
        self.tmp.cleanup()


class MovingMainPreimageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = RepoFixture()

    def tearDown(self) -> None:
        self.fx.close()

    def analyze(self, *owned: str):
        return analyze(
            self.fx.repo,
            self.fx.base,
            self.fx.head,
            self.fx.current_main,
            owned,
        )

    def test_path_disjoint_main_advance_is_safe_preflight(self) -> None:
        receipt = self.analyze("owned.txt")
        self.assertTrue(receipt["candidate_descends_base"])
        self.assertEqual(receipt["candidate_delta"]["base_to_head_paths"], ["owned.txt"])
        self.assertEqual(receipt["candidate_delta"]["unowned_paths"], [])
        self.assertEqual(receipt["moving_main"]["owned_preimage_collisions"], [])
        self.assertEqual(receipt["moving_main"]["behind_by"], 1)
        self.assertEqual(receipt["moving_main"]["ahead_by"], 1)
        self.assertEqual(
            receipt["moving_main"]["current_main_to_head_paths"],
            ["owned.txt", "unrelated.txt"],
        )
        self.assertTrue(receipt["verdict"]["pre_refresh_safe"])
        self.assertFalse(receipt["verdict"]["post_refresh_exact"])

    def test_owned_preimage_drift_fails_closed(self) -> None:
        git(self.fx.repo, "checkout", "-q", "main")
        (self.fx.repo / "owned.txt").write_text("main collision\n", encoding="utf-8")
        git(self.fx.repo, "commit", "-qam", "owned collision")
        current_main = git(self.fx.repo, "rev-parse", "HEAD")
        receipt = analyze(
            self.fx.repo,
            self.fx.base,
            self.fx.head,
            current_main,
            ["owned.txt"],
        )
        self.assertEqual(receipt["moving_main"]["owned_preimage_collisions"], ["owned.txt"])
        self.assertFalse(receipt["verdict"]["pre_refresh_safe"])
        self.assertFalse(receipt["verdict"]["post_refresh_exact"])

    def test_unowned_candidate_delta_fails_preflight(self) -> None:
        git(self.fx.repo, "checkout", "-q", "candidate")
        (self.fx.repo / "leak.txt").write_text("leak\n", encoding="utf-8")
        git(self.fx.repo, "add", "leak.txt")
        git(self.fx.repo, "commit", "-qm", "leak")
        head = git(self.fx.repo, "rev-parse", "HEAD")
        receipt = analyze(
            self.fx.repo,
            self.fx.base,
            head,
            self.fx.current_main,
            ["owned.txt"],
        )
        self.assertEqual(receipt["candidate_delta"]["unowned_paths"], ["leak.txt"])
        self.assertFalse(receipt["verdict"]["pre_refresh_safe"])

    def test_missing_path_is_a_real_preimage_value(self) -> None:
        git(self.fx.repo, "checkout", "-q", "candidate")
        (self.fx.repo / "new.txt").write_text("candidate new\n", encoding="utf-8")
        git(self.fx.repo, "add", "new.txt")
        git(self.fx.repo, "commit", "-qm", "candidate adds new")
        head = git(self.fx.repo, "rev-parse", "HEAD")
        receipt = analyze(
            self.fx.repo,
            self.fx.base,
            head,
            self.fx.current_main,
            ["owned.txt", "new.txt"],
        )
        new_row = next(row for row in receipt["owned_paths"] if row["path"] == "new.txt")
        self.assertEqual(new_row["base_blob"], MISSING)
        self.assertEqual(new_row["current_main_blob"], MISSING)
        self.assertTrue(new_row["preimage_equal"])
        self.assertTrue(receipt["verdict"]["pre_refresh_safe"])

    def test_missing_to_present_on_main_is_collision(self) -> None:
        git(self.fx.repo, "checkout", "-q", "candidate")
        (self.fx.repo / "new.txt").write_text("candidate new\n", encoding="utf-8")
        git(self.fx.repo, "add", "new.txt")
        git(self.fx.repo, "commit", "-qm", "candidate adds new")
        head = git(self.fx.repo, "rev-parse", "HEAD")
        git(self.fx.repo, "checkout", "-q", "main")
        (self.fx.repo / "new.txt").write_text("main new\n", encoding="utf-8")
        git(self.fx.repo, "add", "new.txt")
        git(self.fx.repo, "commit", "-qm", "main adds new")
        current_main = git(self.fx.repo, "rev-parse", "HEAD")
        receipt = analyze(
            self.fx.repo,
            self.fx.base,
            head,
            current_main,
            ["owned.txt", "new.txt"],
        )
        self.assertIn("new.txt", receipt["moving_main"]["owned_preimage_collisions"])
        self.assertFalse(receipt["verdict"]["pre_refresh_safe"])

    def test_non_force_composition_becomes_exact_post_refresh(self) -> None:
        git(self.fx.repo, "checkout", "-q", "candidate")
        git(self.fx.repo, "merge", "--no-ff", "-qm", "refresh from main", self.fx.current_main)
        composed = git(self.fx.repo, "rev-parse", "HEAD")
        receipt = analyze(
            self.fx.repo,
            self.fx.base,
            composed,
            self.fx.current_main,
            ["owned.txt"],
        )
        self.assertEqual(receipt["moving_main"]["behind_by"], 0)
        self.assertEqual(receipt["moving_main"]["current_main_to_head_paths"], ["owned.txt"])
        self.assertEqual(receipt["moving_main"]["current_main_to_head_unowned_paths"], [])
        self.assertTrue(receipt["verdict"]["post_refresh_exact"])

    def test_bad_revision_and_bad_owned_path_fail(self) -> None:
        with self.assertRaises(ProofError):
            analyze(self.fx.repo, "does-not-exist", self.fx.head, self.fx.current_main, ["owned.txt"])
        with self.assertRaises(ProofError):
            analyze(self.fx.repo, self.fx.base, self.fx.head, self.fx.current_main, ["../owned.txt"])

    def test_cli_returns_nonzero_for_collision_and_emits_json(self) -> None:
        git(self.fx.repo, "checkout", "-q", "main")
        (self.fx.repo / "owned.txt").write_text("main collision\n", encoding="utf-8")
        git(self.fx.repo, "commit", "-qam", "owned collision")
        current_main = git(self.fx.repo, "rev-parse", "HEAD")

        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(
                [
                    "--repo", str(self.fx.repo),
                    "--base", self.fx.base,
                    "--head", self.fx.head,
                    "--current-main", current_main,
                    "--owned-path", "owned.txt",
                ]
            )
        self.assertEqual(code, 2)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["verdict"]["pre_refresh_safe"])


if __name__ == "__main__":
    unittest.main()
