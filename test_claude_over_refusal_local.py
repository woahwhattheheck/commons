#!/usr/bin/env python3
"""Local Claude/Cursor split: fix Claude in Claude files; Cursor does not import them."""

from __future__ import annotations

import os
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
PROMPT = os.path.join(ROOT, "ground", "CLAUDE_OVER_REFUSAL_LOCAL.md")
RULE = os.path.join(ROOT, ".cursor", "rules", "no-claude-import.mdc")
IGNORE = os.path.join(ROOT, ".cursorignore")
CITED = (
    "p/spur-over-refusal-prompt-context-20260820-01.md",
    "p/spur-the-diagnostic-is-exact-20260820-01.md",
    "ground/GROK_CLAUDE_HYGIENE.md",
    "lda/CLAUDE.md",
)


def load(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TestClaudeOverRefusalLocal(unittest.TestCase):
    def test_prompt_splits_the_harnesses(self):
        text = load(PROMPT)
        self.assertIn("TWO LANES. DO NOT CROSS THEM.", text)
        self.assertIn("LANE A — Claude Code only", text)
        self.assertIn("LANE B — Cursor only", text)
        self.assertIn("Include third-party Plugins, Skills, and other configs", text)
        self.assertIn("Grant G14", text)
        self.assertIn("Do not disable Claude Code enabledPlugins", text)
        self.assertIn("Do not copy ~/.claude into .cursor/", text)
        self.assertIn("Do not weaken phone §3", text)
        self.assertIn("Never git worktree add", text)

    def test_cursor_rule_forbids_claude_import(self):
        text = load(RULE)
        self.assertIn("alwaysApply: true", text)
        self.assertIn("~/.claude/**", text)
        self.assertIn("resume-claude", text)
        self.assertIn("Do not copy it into `.cursor/rules`", text)
        self.assertNotIn("import ~/.claude/CLAUDE.md into Cursor", text.lower())

    def test_cursorignore_lists_claude_paths(self):
        text = load(IGNORE)
        self.assertIn(".claude/", text)
        self.assertIn("**/.claude/", text)
        self.assertNotIn("**/CLAUDE.md", text)

    def test_cited_records_are_not_reminted(self):
        for rel in CITED:
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(path), rel)
        claude = load(os.path.join(ROOT, "lda", "CLAUDE.md"))
        self.assertIn("## 3. HARD CONSTRAINTS / safety", claude)
        self.assertIn("Never exfiltrate the owner's data to an external AI", claude)
        self.assertIn("## 17. Commons over-refusal", claude)


if __name__ == "__main__":
    unittest.main()
