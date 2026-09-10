#!/usr/bin/env python3
"""Close experience-compiler wiki DRIFT after run 34403364403.

Delayed experience-compiler check on already-merged PR #11127
(head 8ca184705e6b9d6e45f0648ac1f9ec9b3301c7b0) failed because
host/experience_compiler.py did not emit the living KEEP live-cash
and titanmcp cites already on experience/wiki markdown. Emit those
cites from the compiler so compile/check keep the bass/latch shelf.
Do not remint leftover receipts. Wiki markdown bytes stay. Hands
off #8802.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import host.experience_compiler as compiler

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "experience/wiki/index.md"
PATTERN = ROOT / "experience/wiki/patterns/publish-discovery-before-interaction.md"
RECEIPT = ROOT / "p/grokbuild-experience-compiler-wiki-drift-34403364403-01.md"
DEDUPE = (
    "woahwhattheheck/commons:experience-compiler:"
    "8ca184705e6b9d6e45f0648ac1f9ec9b3301c7b0:"
    "python3 host/experience_compiler.py check"
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildExperienceCompilerWikiDrift34403364403(unittest.TestCase):
    def test_compiler_emits_live_cash_keep_on_wiki_markdown(self) -> None:
        outputs = compiler.compile_outputs(compiler.load_records())
        index = outputs[compiler.WIKI_DIR / "index.md"]
        pattern = outputs[
            compiler.PATTERN_DIR / "publish-discovery-before-interaction.md"
        ]
        self.assertEqual(INDEX.read_text(encoding="utf-8"), index)
        self.assertEqual(PATTERN.read_text(encoding="utf-8"), pattern)
        self.assertIn("[$29 Autopsy checkout](../../agent-rescue.html)", index)
        self.assertIn("Cite Latch Pad KEEP", index)
        self.assertIn("[$29 Autopsy checkout](../../../agent-rescue.html)", pattern)
        self.assertIn("Cite Latch Pad KEEP", pattern)

    def test_check_and_existing_compiler_contracts_pass(self) -> None:
        check = subprocess.run(
            ["python3", "host/experience_compiler.py", "check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)
        self.assertIn("CURRENT 1 records 5 outputs", check.stdout)
        unit = subprocess.run(
            ["python3", "-m", "unittest", "-v", "test_experience_compiler.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(unit.returncode, 0, msg=unit.stdout + unit.stderr)

    def test_compile_is_byte_identical_to_live_wiki_markdown(self) -> None:
        before_index = INDEX.read_text(encoding="utf-8")
        before_pattern = PATTERN.read_text(encoding="utf-8")
        rc = subprocess.run(
            ["python3", "host/experience_compiler.py", "compile"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(rc.returncode, 0, msg=rc.stdout + rc.stderr)
        self.assertEqual(before_index, INDEX.read_text(encoding="utf-8"))
        self.assertEqual(before_pattern, PATTERN.read_text(encoding="utf-8"))
        self.assertTrue(git_blob("experience/wiki/index.md").startswith("72983a5f"))
        self.assertTrue(
            git_blob(
                "experience/wiki/patterns/publish-discovery-before-interaction.md"
            ).startswith("23bf2ca8")
        )

    def test_receipt_and_open_door(self) -> None:
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("34403364403", receipt)
        self.assertIn(DEDUPE, receipt)
        builder = (ROOT / "host/experience_compiler.py").read_text(encoding="utf-8")
        for text in (builder, receipt, INDEX.read_text(encoding="utf-8")):
            self.assertNotIn('type="password"', text)
            self.assertNotIn("Authorization", text)
            self.assertNotIn("buy.stripe.com", text)
        guard = subprocess.run(
            ["python3", "open_door_guard.py", "--diff-file", "-"],
            cwd=ROOT,
            text=True,
            input=subprocess.check_output(
                ["git", "diff", "--", "host/experience_compiler.py"],
                cwd=ROOT,
                text=True,
            ),
            capture_output=True,
            check=False,
        )
        self.assertEqual(guard.returncode, 0, msg=guard.stdout + guard.stderr)


if __name__ == "__main__":
    unittest.main()
