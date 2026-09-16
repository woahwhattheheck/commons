"""grok-spark-continue-from-memory-board-20260916-01 — Spark continue_from_observation.

Root cause: stage_spark_mcp_bundle.RUNTIME_FILES listed host/observatory.py
but omitted memory_board.py. continue_from lazy-imported it and 500ed
ModuleNotFoundError on commons-spark-mcp.vercel.app.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from host import observatory

ROOT = Path(__file__).resolve().parent
CLAIM = "grok-spark-continue-from-memory-board-20260916-01"
STAGER = ROOT / "stage_spark_mcp_bundle.py"
OBS = ROOT / "host" / "observatory.py"
ADAPTER = ROOT / "api" / "mcp.py"
HUB = ROOT / "hub_pages.py"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokSparkContinueFromMemoryBoard2026091601(unittest.TestCase):
    def test_stager_lists_memory_board_and_hub_pages(self):
        text = STAGER.read_text(encoding="utf-8")
        self.assertIn('"memory_board.py"', text)
        self.assertIn('"hub_pages.py"', text)
        self.assertIn('"host/observatory.py"', text)
        import stage_spark_mcp_bundle as stager
        self.assertIn("memory_board.py", stager.RUNTIME_FILES)
        self.assertIn("hub_pages.py", stager.RUNTIME_FILES)

    def test_observatory_swallows_missing_memory_board(self):
        src = OBS.read_text(encoding="utf-8")
        self.assertIn("except ModuleNotFoundError", src)
        self.assertIn("MEMORY_BOARD_UNAVAILABLE", src)
        self.assertNotIn("buy.stripe.com", src)

    def test_continue_from_survives_missing_memory_board(self):
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "memory_board" or name.startswith("memory_board."):
                raise ModuleNotFoundError("memory_board")
            return real_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("builtins.__import__", fake_import):
                row = observatory.continue_from(tmp, {"session_id": "spark-probe"})
        self.assertFalse(row["authority"])
        self.assertFalse(row["replay_finished_prompt"])
        self.assertEqual(row["session_memory"]["state"], "NO_OPT_IN")
        self.assertEqual(row["session_memory"]["reason"], "MEMORY_BOARD_UNAVAILABLE")
        self.assertEqual(row["resume_context"], [])

    def test_continue_from_still_binds_when_memory_board_present(self):
        row = observatory.continue_from(str(ROOT), {})
        self.assertFalse(row["authority"])
        self.assertIn("session_memory", row)
        self.assertNotEqual(row["session_memory"].get("reason"), "MEMORY_BOARD_UNAVAILABLE")

    def test_keep_adapter_and_hub_pages_unread(self):
        self.assertTrue(git_blob("api/mcp.py").startswith("393da756"))
        self.assertEqual(ADAPTER.stat().st_size, 21973)
        self.assertTrue(git_blob("hub_pages.py").startswith("7bc61c8b"))
        self.assertTrue(HUB.is_file())
        self.assertNotIn("buy.stripe.com", OBS.read_text(encoding="utf-8"))
        self.assertNotIn("buy.stripe.com", STAGER.read_text(encoding="utf-8"))

    def test_product_pages_untouched(self):
        for name in ("diagnostic.html", "commercial.html", "agent-rescue.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
