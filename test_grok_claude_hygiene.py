#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from grok_claude_hygiene import SCHEMA, evaluate_inspection


class TestGrokClaudeHygiene(unittest.TestCase):
    def fixture(self):
        return {
            "grokVersion": "1.0.5",
            "externalCompat": {"cells": [
                {"vendor": "claude", "surface": "skills", "enabled": False}
            ]},
            "projectInstructions": [
                {"vendor": "claude", "path": "C:/u/.claude/CLAUDE.md", "disabled": True}
            ],
            "skills": [
                {"name": "resume-claude", "source": {"type": "bundled"}, "disabled": True}
            ],
            "plugins": [],
            "hooks": [],
            "mcpServers": [],
        }

    def test_disabled_discovery_passes(self):
        result = evaluate_inspection(self.fixture())
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"], "PASS")

    def test_enabled_claude_plugin_blocks(self):
        fixture = self.fixture()
        fixture["plugins"].append({
            "name": "frontend-design",
            "path": "C:/u/.claude/plugins/frontend-design",
            "enabled": True,
        })
        result = evaluate_inspection(fixture)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["claude_plugins_enabled"], 1)

    def test_enabled_compat_and_skill_block(self):
        fixture = self.fixture()
        fixture["externalCompat"]["cells"][0]["enabled"] = True
        fixture["skills"].append({
            "name": "foreign",
            "vendor": "claude",
            "source": {"path": "C:/u/.claude/skills/foreign/SKILL.md"},
        })
        result = evaluate_inspection(fixture)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["violations"]), 2)


if __name__ == "__main__":
    unittest.main()
