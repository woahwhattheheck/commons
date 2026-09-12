#!/usr/bin/env python3
"""CLI and workflow-invocation contracts for the open-door guard.

Hosted run 34373167955 / job 102539209480 exited 2 because a one-use review
carrier invoked `python3 open_door_guard.py` with no --diff / --diff-file
source. The scanner requires exactly one of those options.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUARD = ROOT / "open_door_guard.py"
WORKFLOWS = ROOT / ".github" / "workflows"
REVIEW_PATHS = (
    "land/business-pack-template-20260902.md",
    "land/sku-business-packs-20260902.md",
    "p/goat-business-packs-ready-20260902-01.md",
    "packs/README.md",
    "packs/_template/README.md",
    "packs/_template/assets.md",
    "packs/_template/checkout.md",
    "packs/_template/instructions.md",
    "packs/_template/keep-vs-sell.md",
    "packs/_template/offer.md",
    "packs/_template/week1.md",
    "revenue/outcome_commerce/business_packs_catalog.json",
    "test_business_packs.py",
)
INVOKE_RE = re.compile(
    r"(?:^|[|;&])\s*(?:python3?)\s+open_door_guard\.py(?P<args>[^\n]*)",
    re.MULTILINE,
)
USAGE = "choose exactly one of --diff BASE HEAD or --diff-file PATH"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def missing_diff_source_invocations(text: str) -> list[str]:
    missing = []
    for match in INVOKE_RE.finditer(text):
        args = match.group("args")
        if "--diff" not in args:
            missing.append(match.group(0).strip())
    return missing


class OpenDoorGuardCliTests(unittest.TestCase):
    def test_bare_invocation_is_usage_error(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GUARD)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(USAGE, result.stderr)

    def test_failing_review_carrier_snippet_is_detected(self) -> None:
        snippet = """
        run: |
          python3 -m unittest -q test_business_packs
          python3 open_door_guard.py
          git diff --check
        """
        self.assertEqual(
            missing_diff_source_invocations(snippet),
            ["python3 open_door_guard.py"],
        )

    def test_correct_invocations_are_accepted(self) -> None:
        ok = """
          python3 open_door_guard.py --diff HEAD^ HEAD
          python open_door_guard.py --diff-file -
          python3 open_door_guard.py --diff "$base" HEAD
        """
        self.assertEqual(missing_diff_source_invocations(ok), [])

    def test_live_workflows_pass_a_diff_source(self) -> None:
        offenders = []
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            for item in missing_diff_source_invocations(text):
                offenders.append(f"{path.name}: {item}")
        self.assertEqual(offenders, [])

    def test_goat_business_pack_review_paths_pass_the_guard(self) -> None:
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--no-ext-diff",
                "--text",
                "--unified=0",
                EMPTY_TREE,
                "HEAD",
                "--",
                *REVIEW_PATHS,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertTrue(diff.stdout)
        guard = subprocess.run(
            [sys.executable, str(GUARD), "--diff-file", "-"],
            cwd=ROOT,
            input=diff.stdout,
            capture_output=True,
            text=True,
        )
        self.assertEqual(guard.returncode, 0, guard.stderr)
        self.assertIn("OPEN DOOR GUARD: PASS", guard.stdout)


if __name__ == "__main__":
    unittest.main()
