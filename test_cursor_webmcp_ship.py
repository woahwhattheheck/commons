#!/usr/bin/env python3
"""Independent ship of leftover cursor-webmcp-contest-20260903-01.

Do not remint leftover adapter, leftover pad, or leftover receipt id.
"""
from __future__ import annotations

import json
import subprocess
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEFTOVER = ROOT / "p/cursor-webmcp-contest-20260903-01.md"
CHALLENGE = ROOT / "p/wire-webmcp-challenge-20260903-01.md"
SHIP = ROOT / "p/cursor-webmcp-ship-20260903-01.md"
ADAPTER = ROOT / "api/mcp.py"
DOOR = ROOT / "webmcp.html"
WORKFLOW = ROOT / ".github/workflows/spark-mcp-production.yml"
CANARY = ROOT / "host/webmcp_live.py"

KEEP = {
    "api/mcp.py": "393da756",
    "webmcp.html": "3b4df417",
    "p/wire-webmcp-challenge-20260903-01.md": "0e815c6d",
    "p/cursor-webmcp-contest-20260903-01.md": "98fb6b6f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWebmcpShip(unittest.TestCase):
    def test_keep_leftover_adapter_pad_and_receipt(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertEqual(ADAPTER.stat().st_size, 21973)
        leftover = LEFTOVER.read_text(encoding="utf-8")
        ship = SHIP.read_text(encoding="utf-8")
        self.assertIn("cursor-webmcp-contest-20260903-01", leftover)
        self.assertIn("cursor-webmcp-ship-20260903-01", ship)
        self.assertNotEqual(ship, leftover)
        self.assertNotEqual(ship, CHALLENGE.read_text(encoding="utf-8"))
        self.assertIn("LIVE_WEBMCP_HTML", ship)
        self.assertIn("33797525326", ship)
        self.assertNotIn("buy.stripe.com", ship)

    def test_production_wait_still_requires_live_webmcp_html(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("LIVE_WEBMCP_HTML", text)
        self.assertIn("https://commons-spark-mcp.vercel.app/webmcp", text)
        self.assertIn("document.modelContext", DOOR.read_text(encoding="utf-8"))

    def test_leftover_door_count_stays_four(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_webmcp_door.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, leftover.stdout + leftover.stderr)
        self.assertIn("Ran 4 tests", leftover.stderr)

    def test_canary_names_live_html_or_named_404(self) -> None:
        src = CANARY.read_text(encoding="utf-8")
        self.assertIn("LIVE_WEBMCP_HTML", src)
        self.assertIn("NAMED_VERCEL_NOT_FOUND", src)
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", src)
        proc = subprocess.run(
            ["python3", str(CANARY)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertIn(proc.returncode, {0, 2}, proc.stdout + proc.stderr)
        blob = proc.stdout
        row = json.loads(blob[blob.find("{") : blob.rfind("}") + 1])
        self.assertEqual(row["mcp"]["status"], 200)
        self.assertEqual(row["mcp"]["name"], "commons")
        self.assertEqual(row["mcp"]["version"], "1.4.0")
        self.assertEqual(row["one_public_mcp"], "https://commons-spark-mcp.vercel.app/mcp")
        if proc.returncode == 0:
            self.assertTrue(row["LIVE_WEBMCP_HTML"])
            self.assertEqual(row["verdict"], "LIVE_WEBMCP_HTML")
        else:
            self.assertEqual(row["verdict"], "NAMED_VERCEL_NOT_FOUND")
            self.assertEqual(row["webmcp"]["status"], 404)
            self.assertEqual(row["webmcp"]["x_vercel_error"], "NOT_FOUND")

    def test_live_webmcp_html_or_named_not_found(self) -> None:
        req = urllib.request.Request(
            "https://commons-spark-mcp.vercel.app/webmcp", method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                ctype = resp.headers.get("content-type") or ""
                self.assertEqual(resp.status, 200)
                self.assertIn("text/html", ctype)
                self.assertIn(b"document.modelContext", raw)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)
            self.assertIn("text/plain", exc.headers.get("content-type") or "")
            self.assertEqual(exc.headers.get("x-vercel-error"), "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
