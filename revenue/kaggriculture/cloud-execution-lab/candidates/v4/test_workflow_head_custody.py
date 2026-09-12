#!/usr/bin/env python3
"""Fail closed if a TITAN V4 pull-request workflow tests a synthetic merge ref."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

EXPECTED_REF = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
PR_TRIGGER = re.compile(r"(?m)^  pull_request:\s*$")
CHECKOUT = re.compile(r"actions/checkout@")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def checkout_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        if not CHECKOUT.search(line):
            continue
        indent = len(line) - len(line.lstrip())
        block = [line]
        for later in lines[index + 1 :]:
            stripped = later.lstrip()
            later_indent = len(later) - len(stripped)
            if stripped.startswith("- ") and later_indent <= indent:
                break
            block.append(later)
        blocks.append("\n".join(block))
    return blocks


class V4WorkflowHeadCustody(unittest.TestCase):
    def test_every_candidate_executing_pr_workflow_checks_out_literal_head(self) -> None:
        workflows = repo_root() / ".github" / "workflows"
        candidates = sorted(workflows.glob("titan-v4-*.yml"))
        self.assertTrue(candidates, "no TITAN V4 workflows found")

        checked: list[str] = []
        failures: list[str] = []
        for path in candidates:
            text = path.read_text(encoding="utf-8")
            if PR_TRIGGER.search(text) is None:
                continue
            checked.append(path.name)
            blocks = checkout_blocks(text)
            if not blocks:
                failures.append(f"{path.name}: pull_request workflow has no checkout step")
                continue
            for ordinal, block in enumerate(blocks, start=1):
                if EXPECTED_REF not in block:
                    failures.append(
                        f"{path.name}: checkout #{ordinal} does not bind literal PR head"
                    )
            if "git rev-parse HEAD" not in text:
                failures.append(f"{path.name}: no post-checkout HEAD identity proof")
            if "github.event.pull_request.head.sha || github.sha" not in text:
                failures.append(f"{path.name}: no event-derived literal-head identity")

        self.assertTrue(checked, "no ordinary TITAN V4 pull_request workflows found")
        self.assertFalse(failures, "\n" + "\n".join(failures))

    def test_pull_request_target_trust_root_is_not_reclassified(self) -> None:
        trust_root = (
            repo_root() / ".github" / "workflows" / "titan-v4-trust-root.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", trust_root)
        self.assertIsNone(PR_TRIGGER.search(trust_root))


if __name__ == "__main__":
    unittest.main()
