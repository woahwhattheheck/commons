import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "check_native_freshness_skip_worktree_test",
    HERE / "check_native_freshness.py",
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout.strip()


class SkipWorktreeDeletionGateTest(unittest.TestCase):
    def test_skip_worktree_absence_cannot_hide_expected_commit_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init", "-q")
            _git(repo, "config", "user.email", "native-freshness@example.invalid")
            _git(repo, "config", "user.name", "native-freshness-test")

            vanished = repo / "vanish.py"
            vanished.write_text("VALUE = 1\n", encoding="utf-8")
            _git(repo, "add", "vanish.py")
            _git(repo, "commit", "-qm", "base")
            head = _git(repo, "rev-parse", "HEAD")

            # This is the primitive sparse-checkout uses for omitted tracked files.
            # The file is physically absent but ordinary `git diff <HEAD>` deletion
            # scans intentionally ignore it, so live rglob() enumeration can shrink.
            _git(repo, "update-index", "--skip-worktree", "vanish.py")
            vanished.unlink()

            deleted = _git(
                repo,
                "diff",
                "--no-ext-diff",
                "--no-renames",
                "--name-only",
                "--diff-filter=D",
                head,
                "--",
            )
            self.assertEqual("", deleted)
            self.assertTrue(_git(repo, "ls-files", "-t", "--", "vanish.py").startswith("S "))

            with self.assertRaises(MOD.InvalidEvidence):
                MOD._assert_no_tracked_deletions(repo, head)


if __name__ == "__main__":
    unittest.main()
