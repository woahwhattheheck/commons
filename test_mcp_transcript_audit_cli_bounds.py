from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_mcp_transcript_audit import capture
from tools.mcp_transcript_audit.audit import MAX_CAPTURE_BYTES
from tools.mcp_transcript_audit.cli import MAX_RECEIPT_BYTES


class CliInputBoundaryTests(unittest.TestCase):
    @staticmethod
    def _runtime() -> tuple[str, dict[str, str]]:
        repo = str(Path(__file__).resolve().parent)
        env = dict(os.environ)
        env["PYTHONPATH"] = repo + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return repo, env

    def test_cli_rejects_oversized_capture_before_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            capture_path = root / "oversized.jsonl"
            with capture_path.open("wb") as handle:
                handle.truncate(MAX_CAPTURE_BYTES + 1)
            repo, env = self._runtime()
            proc = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "audit", str(capture_path)],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("capture exceeds", proc.stderr)
            self.assertEqual(proc.stdout, "")

    def test_cli_rejects_oversized_receipt_before_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            capture_path = root / "session.jsonl"
            receipt_path = root / "oversized-receipt.json"
            capture_path.write_bytes(capture())
            with receipt_path.open("wb") as handle:
                handle.truncate(MAX_RECEIPT_BYTES + 1)
            repo, env = self._runtime()
            proc = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "verify", str(capture_path), str(receipt_path)],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("receipt exceeds", proc.stderr)
            self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
