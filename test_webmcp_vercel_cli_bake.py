#!/usr/bin/env python3
"""Pin WebMCP Vercel CLI bake leftover. Do not remint adapter or Actions workflow."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/webmcp_vercel_cli_bake.py"
RECEIPT = ROOT / "p/cursor-webmcp-vercel-cli-20260903-01.md"
ADAPTER = ROOT / "api/mcp.py"

KEEP = {
    "api/mcp.py": "9ae34f64",
    "webmcp.html": "f2757068",
    "vercel.json": "86c5b13a",
    "stage_spark_mcp_bundle.py": "8b2045c9",
    ".github/workflows/spark-mcp-production.yml": "dc9fa8ae",
    "p/wire-webmcp-challenge-20260903-01.md": "0e815c6d",
    "p/cursor-webmcp-contest-20260903-01.md": "98fb6b6f",
    "p/cursor-webmcp-judge-url-20260903-01.md": "eb52debf",
    "test_webmcp_door.py": "21b6993f",
    "test_cursor_webmcp_contest.py": "a0664d2d",
    "host/webmcp_judge_url.py": "a677b1a5",
    "host/webmcp_live.py": "52253820",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    for key in ("VERCEL_TEAM_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID", "VERCEL_TOKEN"):
        env.pop(key, None)
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class TestWebmcpVercelCliBake(unittest.TestCase):
    def test_keep_adapter_pad_stager_workflow_and_leftovers(self) -> None:
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

    def test_json_token_finder_failed_wires_outside_actions_plan(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 1, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-webmcp-vercel-cli-20260903-01")
        self.assertEqual(packet["verdict"], "FINDER-FAILED")
        self.assertIn("token_absent", packet["errors"])
        self.assertIn("org_id_absent", packet["errors"])
        self.assertIn("project_id_absent", packet["errors"])
        self.assertFalse(packet["bake_ready"])
        self.assertEqual(packet["mcp_initialize"]["status"], 200)
        self.assertEqual(packet["mcp_initialize"]["name"], "commons")
        self.assertEqual(packet["mcp_initialize"]["version"], "1.4.0")
        self.assertEqual(packet["judge"]["status"], 200)
        self.assertIn("text/html", str(packet["judge"]["content_type"]).lower())
        self.assertTrue(packet["judge"]["html"])
        self.assertEqual(packet["adapter_blob"], "9ae34f64")
        self.assertEqual(packet["pad_blob"], "f2757068")
        self.assertEqual(packet["stager_blob"], "8b2045c9")
        self.assertEqual(packet["contest_receipt"], "98fb6b6f")
        self.assertEqual(packet["judge_receipt"], "eb52debf")
        self.assertEqual(packet["live_canary"], "52253820")
        self.assertEqual(packet["billing_lock_class"], "unread")
        self.assertEqual(packet["credentials"]["VERCEL_TEAM_TOKEN"], "FINDER-FAILED")
        plan = packet["bake_plan"]
        self.assertEqual(plan["cli"], "vercel@56.1.0")
        self.assertEqual(plan["stager"], "stage_spark_mcp_bundle.py")
        self.assertEqual(plan["deploy_argv"], ["vercel", "deploy", "--prod", "--yes"])
        self.assertTrue(plan["outside_actions"])
        self.assertFalse(plan["remint_adapter"])
        self.assertIn("/webmcp", packet["webmcp_rewrites"])
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
            self.assertFalse(payload["reminted_adapter"])

    def test_bake_without_token_finder_failed(self) -> None:
        proc = run_helper("--bake")
        self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["sent"], 0)
        self.assertEqual(packet["refused"], "--bake")
        self.assertEqual(packet["verdict"], "FINDER-FAILED")
        self.assertIn("token_absent", packet["errors"])
        self.assertFalse(packet["bake_ready"])
        self.assertNotIn("buy.stripe.com", proc.stdout)

    def test_receipt_and_independently_leftover_door(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-webmcp-vercel-cli-20260903-01", text)
        self.assertIn("1788476745.654259", text)
        self.assertIn("1788476434.139399", text)
        self.assertIn("stage_spark_mcp_bundle.py", text)
        self.assertIn("vercel deploy --prod", text)
        self.assertIn("9ae34f64", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("billing-lock", text)
        self.assertIn("LIVE_WEBMCP_HTML", text)
        self.assertNotIn("buy.stripe.com", text)
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_webmcp_door.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 4 tests", leftover.stderr)


if __name__ == "__main__":
    unittest.main()
