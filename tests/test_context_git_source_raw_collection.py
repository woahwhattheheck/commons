import subprocess
import tempfile
import unittest
from pathlib import Path

from host.git_source_capsules import GIT_SOURCE_KEYS, collect_git_source


class GitSourceRawCollectionTests(unittest.TestCase):
    def test_raw_collection_omits_historical_main_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "raw@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Raw Collection Tests"], check=True)
            (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "alpha.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
            subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], check=True)
            commit = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()

            bundle = collect_git_source(repo, commit, ["alpha.txt"])
            self.assertEqual(set(bundle), GIT_SOURCE_KEYS)
            self.assertNotIn("observed_main_head", bundle)
            self.assertNotIn("source_commit_matches_observed_main", bundle)
            self.assertEqual(bundle["capsules"][0]["text"], "alpha\n")


if __name__ == "__main__":
    unittest.main()
