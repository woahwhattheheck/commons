#!/usr/bin/env python3
"""Hermetic: tools.json job hook object — machine-readable job door."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonJobHookTest(unittest.TestCase):
    def test_job_hook_object(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.json missing")
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        job = data.get("job")
        self.assertIsInstance(job, dict)
        self.assertEqual(job.get("door"), "./job.html")
        self.assertEqual(job.get("to"), "TOOLS")
        self.assertEqual(job.get("button"), "python host/muhl_tools_once.py --go")
        self.assertIn("issues/new", job.get("issue_new") or "")
        for field in ("from", "to", "id", "tool", "op"):
            self.assertIn(field, job.get("fields") or [])
        # not a Live-cash remint
        self.assertNotIn("Live cash", json.dumps(job))
        self.assertNotIn("$29", json.dumps(job))


if __name__ == "__main__":
    unittest.main()
