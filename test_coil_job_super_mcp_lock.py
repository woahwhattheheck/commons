#!/usr/bin/env python3
"""Hermetic: tools.json job.to and super_mcp url/door/law stay locked."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilJobSuperMcpLockTest(unittest.TestCase):
    def test_job_to_tools(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(job.get("to"), "TOOLS")
        self.assertTrue(str(job.get("door", "")).endswith("job.html"))

    def test_super_mcp_shape(self) -> None:
        sm = json.loads(TOOLS.read_text(encoding="utf-8"))["super_mcp"]
        url = sm.get("url") or ""
        self.assertTrue(url.startswith("https://"), url)
        self.assertTrue(url.endswith("/mcp"), url)
        self.assertIn("spark-mcp", url)
        door = sm.get("door") or ""
        law = sm.get("law") or ""
        insights = sm.get("insights") or ""
        self.assertTrue((ROOT / door).is_file(), door)
        self.assertTrue((ROOT / law).is_file(), law)
        self.assertTrue((ROOT / insights).is_file(), insights)
        note = (sm.get("note") or "").lower()
        self.assertIn("do not remint", note)


if __name__ == "__main__":
    unittest.main()
