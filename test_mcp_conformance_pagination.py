#!/usr/bin/env python3
"""Focused pagination contracts for the Commons MCP conformance product."""
from __future__ import annotations

import json
import unittest
from unittest import mock

from host import mcp_conformance


def _transport(n: int) -> dict:
    return {
        "http_status": 200,
        "content_type": "application/json",
        "request_sha256": f"{n:064x}",
        "response_sha256": f"{n + 100:064x}",
        "response_bytes": n,
    }


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def call(self, method, params=None):
        self.calls.append((method, params))
        if not self.responses:
            raise AssertionError("unexpected call")
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def notify(self, method, params=None):
        self.calls.append((method, params))
        return _transport(99)


class DiscoveryPaginationTests(unittest.TestCase):
    def test_complete_pagination_aggregates_all_pages_and_binds_each_transport(self):
        client = FakeClient([
            ({"tools": [{"name": "first"}], "nextCursor": "cursor-a"}, _transport(1)),
            ({"tools": [{"name": "required-late"}], "nextCursor": "cursor-b"}, _transport(2)),
            ({"tools": [{"name": "last"}]}, _transport(3)),
        ])

        row, result = mcp_conformance._discovery_row(
            client,
            "tools/list",
            max_pages=10,
        )

        self.assertEqual(row["state"], "SUPPORTED")
        self.assertTrue(row["complete"])
        self.assertEqual(row["page_count"], 3)
        self.assertEqual(row["item_count"], 3)
        self.assertEqual([p["response_bytes"] for p in row["pages"]], [1, 2, 3])
        self.assertEqual(row["content_type"], "application/json")
        self.assertEqual(
            client.calls,
            [
                ("tools/list", {}),
                ("tools/list", {"cursor": "cursor-a"}),
                ("tools/list", {"cursor": "cursor-b"}),
            ],
        )
        self.assertEqual(
            [item["name"] for item in result["tools"]],
            ["first", "required-late", "last"],
        )
        self.assertNotIn("cursor-a", json.dumps(row))
        self.assertNotIn("cursor-b", json.dumps(row))

    def test_cursor_loop_fails_closed_and_hashes_cursor_instead_of_recording_it(self):
        secret_cursor = "opaque-do-not-publish"
        client = FakeClient([
            ({"tools": [], "nextCursor": secret_cursor}, _transport(1)),
            ({"tools": [], "nextCursor": secret_cursor}, _transport(2)),
        ])

        row, result = mcp_conformance._discovery_row(client, "tools/list", max_pages=10)

        self.assertIsNone(result)
        self.assertEqual(row["state"], "FAILED")
        self.assertFalse(row["complete"])
        self.assertEqual(row["error"]["code"], "DISCOVERY_CURSOR_LOOP")
        self.assertRegex(row["error"]["cursor_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(secret_cursor, json.dumps(row))

    def test_invalid_cursor_shape_fails_closed(self):
        for bad in ("", 0, False, [], {}):
            with self.subTest(bad=bad):
                client = FakeClient([
                    ({"tools": [], "nextCursor": bad}, _transport(1)),
                ])
                row, result = mcp_conformance._discovery_row(client, "tools/list")
                self.assertIsNone(result)
                self.assertEqual(row["state"], "FAILED")
                self.assertEqual(row["error"]["code"], "INVALID_DISCOVERY_CURSOR")

    def test_page_limit_fails_instead_of_publishing_partial_parity(self):
        client = FakeClient([
            ({"tools": [{"name": "one"}], "nextCursor": "a"}, _transport(1)),
            ({"tools": [{"name": "two"}], "nextCursor": "b"}, _transport(2)),
        ])

        row, result = mcp_conformance._discovery_row(
            client,
            "tools/list",
            max_pages=2,
        )

        self.assertIsNone(result)
        self.assertEqual(row["state"], "FAILED")
        self.assertEqual(row["page_count"], 2)
        self.assertEqual(row["error"]["code"], "DISCOVERY_PAGE_LIMIT")

    def test_malformed_collection_page_fails_closed(self):
        for result in (None, [], {}, {"tools": {}}, {"tools": "nope"}):
            with self.subTest(result=result):
                client = FakeClient([(result, _transport(1))])
                row, value = mcp_conformance._discovery_row(client, "tools/list")
                self.assertIsNone(value)
                self.assertEqual(row["state"], "FAILED")
                self.assertEqual(row["error"]["code"], "INVALID_DISCOVERY_PAGE")

    def test_method_not_found_is_unsupported_only_before_any_successful_page(self):
        missing = mcp_conformance.ConformanceError(
            "RPC_ERROR",
            "tools/list returned JSON-RPC error",
            rpc_code=-32601,
            rpc_message="not implemented",
        )
        row, value = mcp_conformance._discovery_row(
            FakeClient([missing]),
            "tools/list",
        )
        self.assertIsNone(value)
        self.assertEqual(row["state"], "UNSUPPORTED")
        self.assertEqual(row["page_count"], 0)

        client = FakeClient([
            ({"tools": [], "nextCursor": "a"}, _transport(1)),
            missing,
        ])
        row, value = mcp_conformance._discovery_row(client, "tools/list")
        self.assertIsNone(value)
        self.assertEqual(row["state"], "FAILED")
        self.assertEqual(row["page_count"], 1)

    def test_run_conformance_parity_uses_tool_from_later_page(self):
        scripted = FakeClient([
            (
                {
                    "protocolVersion": mcp_conformance.PROTOCOL_VERSION,
                    "serverInfo": {"name": "paged", "version": "1"},
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                },
                _transport(1),
            ),
            ({"tools": [{"name": "early"}], "nextCursor": "tool-2"}, _transport(2)),
            ({"tools": [{"name": "required-late"}]}, _transport(3)),
            ({"resources": [{"name": "resource-1"}]}, _transport(4)),
            ({"prompts": [{"name": "prompt-1"}]}, _transport(5)),
        ])

        with mock.patch.object(mcp_conformance, "MCPClient", return_value=scripted):
            report = mcp_conformance.run_conformance(
                "https://example.com/mcp?secret=never",
                required_tools=("required-late",),
                max_discovery_pages=10,
            )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["tool_names"], ["early", "required-late"])
        self.assertEqual(report["tool_parity"]["missing"], [])
        self.assertTrue(report["tool_parity"]["complete"])
        self.assertTrue(report["tool_parity"]["authoritative"])
        self.assertEqual(report["discovery"]["tools/list"]["page_count"], 2)
        self.assertEqual(report["resource_names"], ["resource-1"])
        self.assertEqual(report["prompt_names"], ["prompt-1"])
        self.assertNotIn("tool-2", json.dumps(report))
        self.assertNotIn("never", json.dumps(report))
        self.assertRegex(report["receipt_sha256"], r"^[0-9a-f]{64}$")

    def test_invalid_limit_returns_deterministic_failure_receipt(self):
        with mock.patch.object(mcp_conformance, "MCPClient") as client:
            report = mcp_conformance.run_conformance(
                "https://example.com/mcp",
                max_discovery_pages=0,
            )
        client.assert_not_called()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["errors"][0]["code"], "INVALID_DISCOVERY_LIMIT")
        self.assertRegex(report["receipt_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
