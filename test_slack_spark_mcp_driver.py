#!/usr/bin/env python3
"""@spark Slack custom-tool drives Commons Spark MCP. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_service_all_drivers as all_drivers  # noqa: E402
import slack_service_tag as sst  # noqa: E402
import slack_spark_mcp_driver as spark  # noqa: E402


class SlackSparkMcpDriverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = sst.load_catalog()
        self.card = (ROOT / "ground" / "SLACK_SPARK_MCP_DRIVER.md").read_text(
            encoding="utf-8"
        )

    def test_catalog_spark_is_no_auth_custom_tool(self) -> None:
        spec = self.cat["services"]["spark"]
        self.assertEqual(spec["tag"], "spark")
        self.assertIs(spec["needs_owner_signin"], False)
        self.assertEqual(spec["auth"], "none")
        self.assertEqual(spec["mcp_url"], spark.SPARK_MCP_URL)
        self.assertEqual(self.cat["aliases"]["gemini-spark"], "spark")
        self.assertEqual(self.cat["aliases"]["commons-spark"], "spark")
        result = sst.route("@spark discover", connected=["slack"])
        self.assertEqual(result["tags"], ["spark"])
        roads = {job["road"] for job in result["jobs"] if job["tag"] == "spark"}
        self.assertEqual(roads, {"SLACK_CUSTOM_TOOL"})
        kinds = {row["kind"] for row in result["slack_jobs"]}
        self.assertIn("SLACK_CUSTOM_TOOL", kinds)
        self.assertNotIn("OWNER_BLOCKER", kinds)

    def test_gemini_spark_alias_canonicalizes(self) -> None:
        result = sst.route("@gemini-spark search dests", connected=["slack"])
        self.assertEqual(result["tags"], ["spark"])
        self.assertIn("search dests", result["body"])
        self.assertNotIn("@gemini-spark", result["body"])

    def test_dry_run_does_not_call_http(self) -> None:
        calls: list[dict[str, Any]] = []

        def http_request(**kwargs: object) -> tuple[int, dict[str, str], dict[str, Any]]:
            calls.append(kwargs)
            return 200, {}, {}

        out = spark.drive_spark("discover", execute=False, http_request=http_request)
        self.assertTrue(out["ok"])
        self.assertEqual(out["road"], "SLACK_CUSTOM_TOOL")
        self.assertEqual(out["reason"], "ready_dry_run")
        self.assertFalse(out["http_called"])
        self.assertEqual(out["auth"], "none")
        self.assertIs(out["reopen_need"], False)
        self.assertIs(out["notion_owner_action_done"], False)
        self.assertEqual(out["intent"]["tool"], "discover_commons_capabilities")
        self.assertEqual(calls, [])

    def test_execute_initialize_list_and_discover(self) -> None:
        calls: list[dict[str, Any]] = []

        def http_request(**kwargs: object) -> tuple[int, dict[str, str], dict[str, Any]]:
            calls.append(kwargs)
            raw = kwargs.get("body") or b""
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            method = payload.get("method")
            if method == "initialize":
                return (
                    200,
                    {},
                    {
                        "result": {
                            "protocolVersion": "2025-03-26",
                            "serverInfo": {"name": "commons", "version": "1.4.0"},
                        }
                    },
                )
            if method == "tools/list":
                return (
                    200,
                    {},
                    {
                        "result": {
                            "tools": [
                                {"name": "discover_commons_capabilities"},
                                {"name": "search_commons"},
                            ]
                        }
                    },
                )
            if method == "tools/call":
                return (200, {}, {"result": {"content": [{"type": "text", "text": "ok"}]}})
            return 500, {}, {"error": method}

        out = spark.drive_spark("discover", execute=True, http_request=http_request)
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "driven")
        self.assertTrue(out["http_called"])
        self.assertEqual(out["server_name"], "commons")
        self.assertEqual(out["server_version"], "1.4.0")
        self.assertIn("discover_commons_capabilities", out["tools"])
        self.assertEqual(out["called_tool"], "discover_commons_capabilities")
        self.assertEqual(len(calls), 3)
        for row in calls:
            headers = row.get("headers") or {}
            self.assertNotIn("Authorization", headers)
            self.assertEqual(row["url"], spark.SPARK_MCP_URL)
        blob = json.dumps(out)
        self.assertNotIn("xoxb-", blob)
        self.assertNotIn("sk-ant-", blob)
        self.assertIs(out["copy_secrets"], False)

    def test_parse_search_and_list(self) -> None:
        search = spark.parse_intent("search dests")
        self.assertEqual(search["tool"], "search_commons")
        self.assertEqual(search["arguments"]["query"], "dests")
        listed = spark.parse_intent("tools/list")
        self.assertEqual(listed["rpc"], "tools/list")

    def test_all_drivers_delegates_without_stealing_facebook(self) -> None:
        out = all_drivers.drive("spark", "discover", connected=["slack"])
        self.assertEqual(out["tag"], "spark")
        self.assertEqual(out["road"], "SLACK_CUSTOM_TOOL")
        self.assertEqual(out["reason"], "ready_dry_run")
        self.assertEqual(out["mcp_url"], spark.SPARK_MCP_URL)
        self.assertIs(out["reopen_need"], False)
        facebook = all_drivers.drive("facebook", "post the drop", connected=["slack"])
        self.assertEqual(facebook["road"], "OWNER_SIGNIN")
        notion = all_drivers.drive("notion", "list databases", connected=["slack"])
        self.assertEqual(notion["reason"], "peer_harness_remainder")
        self.assertEqual(notion["peer_desk"], "GOAT")
        self.assertIs(notion["reopen_need"], False)

    def test_card_stays_open(self) -> None:
        lowered = self.card.lower()
        self.assertIn("no auth", lowered)
        self.assertIn("@spark", lowered)
        self.assertIn("commons-spark-mcp.vercel.app/mcp", lowered)
        self.assertIn("do not reopen", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("login form", lowered)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "slack_spark_mcp_driver.py"),
                "--body",
                "discover",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["tag"], "spark")
        self.assertEqual(data["reason"], "ready_dry_run")
        self.assertIs(data["commons_admission"], False)
        self.assertIs(data["reopen_need"], False)


if __name__ == "__main__":
    unittest.main()
