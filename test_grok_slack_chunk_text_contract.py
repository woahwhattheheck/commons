#!/usr/bin/env python3
"""Regression contract for nonpositive Grok Slack chunk limits."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BRIDGE_PATH = ROOT / "integrations" / "grok_slack" / "bridge.py"


class GrokSlackChunkTextContractTests(unittest.TestCase):
    def test_nonpositive_limits_fail_fast_in_bounded_processes(self) -> None:
        program = """
import importlib.util
import sys

path = sys.argv[1]
limit = int(sys.argv[2])
spec = importlib.util.spec_from_file_location("grok_slack_chunk_contract", path)
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)
try:
    bridge.chunk_text("abcdef", limit)
except ValueError as exc:
    if str(exc) == "chunk limit must be positive":
        raise SystemExit(0)
    raise
raise SystemExit("nonpositive chunk limit was accepted")
"""
        for limit in (0, -1, -3800):
            with self.subTest(limit=limit):
                completed = subprocess.run(
                    [sys.executable, "-c", program, str(BRIDGE_PATH), str(limit)],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
