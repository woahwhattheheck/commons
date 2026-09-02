#!/usr/bin/env python3
"""Google AI Mode hall pass skill encodes Bryce's blocked-fetch teach-back."""
from __future__ import annotations

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / ".agents" / "skills" / "google-ai-mode-hall-pass" / "SKILL.md"
TOKEN = ROOT / "ground" / "tokens" / "google-ai-mode-hall-pass.md"
MANIFEST = ROOT / "skills.json"
MANUAL = ROOT / "skills" / "MANUAL.md"
RECEIPT = ROOT / "p" / "cursor-google-ai-mode-hall-pass-20260902-01.md"
SID = "google-ai-mode-hall-pass"

KEEP = (
    "codex-google-research-routing-notice-20260902-01",
    "codex-google-research-grok-automation-resource-delta-20260902-01",
    "codex-google-research-resource-delta-landed-20260902-01",
)


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unclosed YAML frontmatter")
    data: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        if line.startswith("  ") and key == "description":
            data[key] = (data.get(key, "") + " " + line.strip()).strip()
            continue
        if line.startswith("  ") and key == "metadata":
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", "|"):
            data[key] = ""
            continue
        data[key] = val.strip("\"'")
    return data


class GoogleAiModeHallPassTests(unittest.TestCase):
    def test_skill_and_token_exist(self):
        self.assertTrue(SKILL.is_file(), SKILL)
        self.assertTrue(TOKEN.is_file(), TOKEN)
        self.assertTrue(RECEIPT.is_file(), RECEIPT)

    def test_frontmatter_matches_directory(self):
        meta = _frontmatter(SKILL.read_text(encoding="utf-8"))
        self.assertEqual(meta.get("name"), SID)
        desc = meta.get("description") or ""
        self.assertGreaterEqual(len(desc), 1)
        self.assertLessEqual(len(desc), 1024)
        self.assertIn("hall pass", desc.lower())
        self.assertIn("no login", desc.lower())
        self.assertIn(meta.get("token"), ("ground/tokens/google-ai-mode-hall-pass.md",))

    def test_owner_four_steps_and_intended_feature(self):
        body = SKILL.read_text(encoding="utf-8")
        token = TOKEN.read_text(encoding="utf-8")
        joined = body + "\n" + token
        self.assertIn("www.google.com", joined)
        self.assertRegex(joined, r"no login", re.I)
        self.assertIn("AI Mode", joined)
        self.assertIn("Google tool calls", joined)
        self.assertIn("partner infra", joined)
        self.assertIn("Intended feature, not a hack", joined)
        self.assertIn("1788388806.376349", joined)
        self.assertIn("clan/grokbot", body)

    def test_does_not_remint_discovery_mesh(self):
        body = SKILL.read_text(encoding="utf-8")
        token = TOKEN.read_text(encoding="utf-8")
        receipt = RECEIPT.read_text(encoding="utf-8")
        for keep in KEEP:
            self.assertIn(keep, body)
            self.assertIn(keep, token)
            self.assertIn(keep, receipt)
        self.assertIn("Do not remint", body)
        self.assertIn("google-ai-mode-browser-mesh", token)

    def test_open_door_and_no_private_claim(self):
        body = SKILL.read_text(encoding="utf-8")
        self.assertIn("Do not add Commons login", body)
        self.assertIn("UNSEATED", body)
        self.assertIn("paywalled", body)
        self.assertNotRegex(body, r"(?i)require (login|auth|oauth)")

    def test_registered_in_manifest_and_manual(self):
        rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["skills"]
        ids = [row["id"] for row in rows]
        self.assertIn(SID, ids)
        row = next(r for r in rows if r["id"] == SID)
        self.assertEqual(row.get("token"), "ground/tokens/google-ai-mode-hall-pass.md")
        self.assertIn("hall pass", (row.get("job") or "").lower())
        manual = MANUAL.read_text(encoding="utf-8")
        self.assertIn(SID, manual)
        self.assertIn("google-ai-mode-hall-pass/SKILL.md", manual)

    def test_skills_check_passes(self):
        result = subprocess.run(
            ["python3", str(ROOT / "skills" / "check.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("PASS"), result.stdout)

    def test_receipt_cites_wire_claim_not_remint(self):
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: cursor-google-ai-mode-hall-pass-20260902-01", text)
        self.assertIn("clan: grokbot", text)
        self.assertIn("1788388806.376349", text)
        self.assertIn("not a remint", text.lower())
        self.assertIn("google-ai-mode-hall-pass", text)


if __name__ == "__main__":
    unittest.main()
