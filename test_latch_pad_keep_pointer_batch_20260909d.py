#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['agent-control.html', 'agent-ops.html', 'agent-rescue.html', 'agent-runaway-cost.html', 'agent-triage.html', 'ai-agent-stop-button.html', 'agentic-production-failure.html', 'arbitrage.html', 'attested-inference.html', 'attested-runs.html', 'head.html', 'todo.html', 'boards.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909dTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
