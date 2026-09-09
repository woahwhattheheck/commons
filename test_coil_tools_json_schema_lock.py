#!/usr/bin/env python3
"""Hermetic: tools.json catalog schema lock (required keys + job/super_mcp/cash shapes)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"

REQUIRED_TOP = ["share", "button", "job", "tools", "refuse", "super_mcp", "cash"]


class CoilToolsJsonSchemaLockTest(unittest.TestCase):
    def test_required_top_level_keys(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.json missing")
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        for key in REQUIRED_TOP:
            self.assertIn(key, data, f"missing top-level key {key}")

    def test_button_and_share(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        self.assertIsInstance(data["share"], str)
        self.assertTrue(data["share"].strip())
        self.assertEqual(data["button"], "python host/muhl_tools_once.py --go")

    def test_job_shape(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertIsInstance(job, dict)
        self.assertEqual(job.get("door"), "./job.html")
        self.assertEqual(job.get("to"), "TOOLS")
        self.assertEqual(job.get("button"), "python host/muhl_tools_once.py --go")
        self.assertIsInstance(job.get("fields"), list)
        for field in ("from", "to", "id", "tool", "op"):
            self.assertIn(field, job["fields"])

    def test_super_mcp_shape(self) -> None:
        sm = json.loads(TOOLS.read_text(encoding="utf-8"))["super_mcp"]
        self.assertIsInstance(sm, dict)
        self.assertIn("mcp", (sm.get("url") or ""))
        self.assertTrue(sm.get("door"))
        self.assertTrue(sm.get("law"))

    def test_cash_shape(self) -> None:
        cash = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]
        self.assertIsInstance(cash, dict)
        doors = cash.get("doors")
        self.assertIsInstance(doors, list)
        self.assertGreaterEqual(len(doors), 5)
        hrefs = [d.get("href") for d in doors if isinstance(d, dict)]
        self.assertIn("./agent-rescue.html", hrefs)
        blob = TOOLS.read_text(encoding="utf-8")
        self.assertNotIn("buy.stripe.com", blob)

    def test_tools_and_refuse(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        self.assertIsInstance(data["tools"], list)
        self.assertGreater(len(data["tools"]), 0)
        self.assertIsInstance(data["refuse"], list)
        self.assertIn("titan", data["refuse"])


if __name__ == "__main__":
    unittest.main()
