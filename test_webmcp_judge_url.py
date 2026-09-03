#!/usr/bin/env python3
"""Pin WebMCP judge-URL leftover. Do not remint adapter or contest canary."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/webmcp_judge_url.py"
RECEIPT = ROOT / "p/cursor-webmcp-judge-url-20260903-01.md"
ADAPTER = ROOT / "api/mcp.py"

KEEP = {
    "api/mcp.py": "9ae34f64",
    "webmcp.html": "b18ec98e",
    "p/wire-webmcp-challenge-20260903-01.md": "0e815c6d",
    "p/cursor-webmcp-contest-20260903-01.md": "98fb6b6f",
    "test_webmcp_door.py": "21b6993f",
    "test_cursor_webmcp_contest.py": "dd92af29",
    "vercel.json": "86c5b13a",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestWebmcpJudgeUrl(unittest.TestCase):
    def test_keep_adapter_pad_and_contest_canary(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertGreaterEqual(ADAPTER.stat().st_size, 20000)
        self.assertLessEqual(ADAPTER.stat().st_size, 23000)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertNotIn("CLAUDE.md", KEEP)

    def test_json_judge_url_finder_failed_keeps_mcp(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 1, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-webmcp-judge-url-20260903-01")
        self.assertEqual(packet["judge_url"], "https://commons-spark-mcp.vercel.app/webmcp")
        self.assertEqual(packet["verdict"], "FINDER-FAILED")
        self.assertIn("judge_url_not_200", packet["errors"])
        self.assertIn("judge_url_not_html", packet["errors"])
        self.assertEqual(packet["mcp_initialize"]["status"], 200)
        self.assertEqual(packet["mcp_initialize"]["name"], "commons")
        self.assertEqual(packet["mcp_initialize"]["version"], "1.4.0")
        self.assertEqual(packet["adapter_blob"], "9ae34f64")
        self.assertEqual(packet["pad_blob"], "b18ec98e")
        self.assertEqual(packet["contest_receipt"], "98fb6b6f")
        self.assertEqual(packet["vercel_team_token"], "FINDER-FAILED")
        self.assertFalse(packet["second_mcp"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["sent"], 0)
        self.assertEqual(packet["type_devpost"], "unread")
        self.assertNotIn("buy.stripe.com", proc.stdout)

    def test_send_go_deploy_refused(self) -> None:
        for flag in ("--send", "--go", "--deploy", "--live"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["second_mcp"])

    def test_independently_leftover_door_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_webmcp_door.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 4 tests", leftover.stderr)

    def test_receipt_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-webmcp-judge-url-20260903-01", text)
        self.assertIn("1788464053.553519", text)
        self.assertIn("1788464261.550789", text)
        self.assertIn("9ae34f64", text)
        self.assertIn("98fb6b6f", text)
        self.assertIn("61a505eef", text)
        self.assertIn("Did **not** remint", text)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
