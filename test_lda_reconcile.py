from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from host.lda_reconcile import compare, render_markdown


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.check_call(["git", "-C", str(repo), "add", "."])
    subprocess.check_call(
        [
            "git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", message,
        ],
        stdout=subprocess.DEVNULL,
    )
    return git(repo, "rev-parse", "HEAD")


class ReconcileTests(unittest.TestCase):
    def test_tracked_source_comparison_ignores_build_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commons = root / "commons"
            source = root / "source"
            for repo in (commons, source):
                repo.mkdir()
                git(repo, "init")
            commit(
                commons,
                {
                    "lda/app/src/main/Same.kt": "same\n",
                    "lda/app/src/main/Different.kt": "commons\n",
                    "lda/app/src/main/Only.kt": "commons only\n",
                },
                "commons",
            )
            commit(
                source,
                {
                    "app/src/main/Same.kt": "same\n",
                    "app/src/main/Different.kt": "source\n",
                    "app/src/test/ContractTest.kt": "test\n",
                },
                "source",
            )
            generated = source / "app/build/generated.bin"
            generated.parent.mkdir(parents=True)
            generated.write_bytes(b"ignored")
            manifest = compare(commons, "HEAD", "lda", source, "HEAD", "")
            self.assertEqual(
                manifest["summary"],
                {"total": 4, "same": 1, "different": 1, "commons_only": 1, "source_only": 1},
            )
            test_record = next(r for r in manifest["records"] if r["path"].endswith("ContractTest.kt"))
            self.assertEqual(test_record["recommendation"], "candidate-test")
            self.assertNotIn("generated.bin", render_markdown(manifest))


if __name__ == "__main__":
    unittest.main()
