#!/usr/bin/env python3
"""Isolated KEEP battery for titanmcp 1.4.5 setup-schema remainder.

Stays green without reminting pad runtime. Does not unique-pack this seat's
Sep 4 HTTP/schema files. Does not take AUTH-STATE or Harborline freeze.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

import commons_mcp as cm


ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "titanmcp_setup_schema.py"
_spec = importlib.util.spec_from_file_location("titanmcp_setup_schema", HOST)
schema = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(schema)
HTML = ROOT / "titanmcp.html"
WORKFLOW = ROOT / ".github" / "workflows" / "webmcp-pad-production.yml"
ADAPTER = ROOT / "api" / "mcp.py"
COMMONS = ROOT / "commons_mcp.py"


class TitanmcpGptUseSetupSchemaTests(unittest.TestCase):
    def test_recorded_request_setup_missing_need_is_bad_argument(self) -> None:
        row = schema.classify_setup_packet(
            "request_setup_missing_need", schema.PACKET_REQUEST_SETUP_MISSING_NEED
        )
        self.assertTrue(row["ok"])
        self.assertEqual(row["pin"], "BAD_ARGUMENT.need")

    def test_recorded_request_setup_empty_need_is_need_required(self) -> None:
        row = schema.classify_setup_packet(
            "request_setup_empty_need", schema.PACKET_REQUEST_SETUP_EMPTY_NEED
        )
        self.assertTrue(row["ok"])
        self.assertEqual(row["pin"], "NEED_REQUIRED")

    def test_submit_task_empty_title_now_requires_task_not_title(self) -> None:
        row = schema.classify_setup_packet(
            "submit_task_empty_title", schema.PACKET_SUBMIT_TASK_EMPTY_TITLE
        )
        self.assertTrue(row["ok"])
        self.assertEqual(row["structured"]["argument"], "task")
        self.assertNotEqual(row["structured"].get("error"), "TASK_REQUIRED")

    def test_set_role_missing_role_now_requires_agent_name(self) -> None:
        row = schema.classify_setup_packet(
            "set_role_missing_role", schema.PACKET_SET_ROLE_MISSING_ROLE
        )
        self.assertTrue(row["ok"])
        self.assertEqual(row["structured"]["argument"], "agent_name")
        self.assertNotEqual(row["structured"].get("error"), "BAD_ROLE")

    def test_unknown_tool_is_jsonrpc_minus_32602_not_iserror(self) -> None:
        row = schema.classify_setup_packet("unknown_tool", schema.PACKET_UNKNOWN_TOOL)
        self.assertTrue(row["ok"])
        self.assertEqual(row["error"]["code"], -32602)
        self.assertNotIn("isError", schema.PACKET_UNKNOWN_TOOL)

    def test_http_transport_error_codes_keep(self) -> None:
        malformed = schema.classify_setup_packet("malformed", schema.PACKET_MALFORMED)
        unknown = schema.classify_setup_packet("unknown_method", schema.PACKET_UNKNOWN_METHOD)
        missing = schema.classify_setup_packet("missing_name", schema.PACKET_MISSING_NAME)
        self.assertTrue(malformed["ok"])
        self.assertTrue(unknown["ok"])
        self.assertTrue(missing["ok"])
        self.assertEqual(malformed["error"]["code"], -32700)
        self.assertEqual(unknown["error"]["code"], -32601)

    def test_twenty_four_tools_include_setup_pair(self) -> None:
        self.assertEqual(len(schema.TOOL_NAMES), 24)
        self.assertIn("request_setup", schema.TOOL_NAMES)
        self.assertIn("get_setup_status", schema.TOOL_NAMES)
        self.assertIn("submit_task", schema.TOOL_NAMES)
        self.assertIn("set_role", schema.TOOL_NAMES)

    def test_first_party_still_three_including_peer_worker(self) -> None:
        self.assertEqual(len(schema.FIRST_PARTY_IDS), 3)
        self.assertIn("peer-worker", schema.FIRST_PARTY_IDS)

    def test_html_keep_facts_unread_no_remint(self) -> None:
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("titanmcp 1.4.5", text)
        self.assertIn("24 tools", text)
        self.assertIn("get_setup_status", text)
        self.assertIn("request_setup", text)
        self.assertIn("webmcp-pad.vercel.app", text)
        self.assertIn("commons-spark-mcp.vercel.app/mcp", text)
        self.assertIn("Commons <code>/mcp</code> KEEP", text)

    def test_workflow_still_names_titanmcp_not_commons_spark(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("woahwhattheheck/webmcp-pad", text)
        self.assertIn("titanmcp|webmcp-pad", text)
        self.assertIn("refusing to deploy webmcp-pad into commons-spark-mcp", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("self-extracting-blob-directories-present", text)

    def test_commons_mcp_identity_stays_commons_1_4_0(self) -> None:
        self.assertEqual(cm.SERVER_NAME, "commons")
        self.assertEqual(cm.SERVER_VERSION, "1.4.0")
        adapter = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("commons-spark-mcp", adapter)
        self.assertNotIn("titanmcp", adapter)

    def test_does_not_remint_listed_keep_paths(self) -> None:
        for rel in schema.DO_NOT_REMINT:
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)

    def test_bake_deploy_go_refused_sent_zero(self) -> None:
        for flag in ("--bake", "--deploy", "--go"):
            proc = subprocess.run(
                [sys.executable, str(HOST), flag],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertEqual(payload["verdict"], "REFUSED")


if __name__ == "__main__":
    unittest.main()
