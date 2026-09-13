#!/usr/bin/env python3
"""Fail-closed member-shape contracts for MCP discovery pagination."""
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


class DictSubclass(dict):
    pass


class StrSubclass(str):
    pass


class DiscoveryItemValidationTests(unittest.TestCase):
    def _assert_bad_member(self, bad_member, *, page_number: int) -> None:
        responses = []
        if page_number == 2:
            responses.append(
                (
                    {
                        "tools": [{"name": "first", "description": "valid extra field"}],
                        "nextCursor": "next-page",
                    },
                    _transport(1),
                )
            )
        responses.append(
            (
                {"tools": [{"name": "valid"}, bad_member]},
                _transport(page_number),
            )
        )
        row, result = mcp_conformance._discovery_row(
            FakeClient(responses),
            "tools/list",
            max_pages=10,
        )

        self.assertIsNone(result)
        self.assertEqual(row["state"], "FAILED")
        self.assertFalse(row["complete"])
        self.assertEqual(row["page_count"], page_number)
        self.assertEqual(row["error"]["code"], "INVALID_DISCOVERY_ITEM")
        self.assertEqual(row["error"]["page"], page_number)
        self.assertEqual(row["error"]["item_index"], 1)

    def test_scalar_missing_nonstring_and_empty_name_fail_on_first_and_later_page(self):
        bad_members = (
            "ATTACKER-RAW-SCALAR-MUST-NOT-LEAK",
            {},
            {"name": 7},
            {"name": ""},
        )
        for page_number in (1, 2):
            for bad_member in bad_members:
                with self.subTest(page_number=page_number, bad_member=bad_member):
                    self._assert_bad_member(bad_member, page_number=page_number)

    def test_error_receipt_does_not_publish_raw_malformed_member(self):
        secret = "ATTACKER-SECRET-DISCOVERY-MEMBER"
        client = FakeClient(
            [
                (
                    {"tools": [{"name": "good"}, secret]},
                    _transport(1),
                )
            ]
        )
        row, result = mcp_conformance._discovery_row(client, "tools/list")

        self.assertIsNone(result)
        self.assertEqual(row["error"]["code"], "INVALID_DISCOVERY_ITEM")
        self.assertNotIn(secret, json.dumps(row, sort_keys=True))

    def test_exact_builtin_object_and_string_types_are_required(self):
        bad_members = (
            DictSubclass(name="subclass-object"),
            {"name": StrSubclass("subclass-name")},
        )
        for bad_member in bad_members:
            with self.subTest(bad_member=bad_member):
                self._assert_bad_member(bad_member, page_number=1)

    def test_valid_extra_fields_are_preserved_for_all_discovery_collections(self):
        cases = (
            ("tools/list", "tools", {"description": "ok", "inputSchema": {"type": "object"}}),
            ("resources/list", "resources", {"uri": "file:///safe", "mimeType": "text/plain"}),
            ("prompts/list", "prompts", {"description": "ok", "arguments": []}),
        )
        for method, key, extra in cases:
            with self.subTest(method=method):
                item = {"name": "valid-name", **extra}
                row, result = mcp_conformance._discovery_row(
                    FakeClient([({key: [item]}, _transport(1))]),
                    method,
                )
                self.assertEqual(row["state"], "SUPPORTED")
                self.assertTrue(row["complete"])
                self.assertEqual(result, {key: [item]})

    def test_run_conformance_malformed_late_tool_member_never_authorizes_parity(self):
        secret = "ATTACKER-LATE-MEMBER-MUST-NOT-LEAK"
        scripted = FakeClient(
            [
                (
                    {
                        "protocolVersion": mcp_conformance.PROTOCOL_VERSION,
                        "serverInfo": {"name": "hostile-paged", "version": "1"},
                        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    },
                    _transport(1),
                ),
                (
                    {"tools": [{"name": "early"}], "nextCursor": "tool-page-2"},
                    _transport(2),
                ),
                (
                    {"tools": [{"name": "required-late"}, secret]},
                    _transport(3),
                ),
                ({"resources": [{"name": "resource-1"}]}, _transport(4)),
                ({"prompts": [{"name": "prompt-1"}]}, _transport(5)),
            ]
        )

        with mock.patch.object(mcp_conformance, "MCPClient", return_value=scripted):
            report = mcp_conformance.run_conformance(
                "https://example.com/mcp?secret=never",
                required_tools=("required-late",),
                max_discovery_pages=10,
            )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["discovery"]["tools/list"]["state"], "FAILED")
        self.assertFalse(report["discovery"]["tools/list"]["complete"])
        self.assertEqual(
            report["discovery"]["tools/list"]["error"]["code"],
            "INVALID_DISCOVERY_ITEM",
        )
        self.assertEqual(report["tool_names"], [])
        self.assertEqual(report["tool_parity"]["present"], [])
        self.assertEqual(report["tool_parity"]["missing"], [])
        self.assertFalse(report["tool_parity"]["complete"])
        self.assertFalse(report["tool_parity"]["authoritative"])
        self.assertEqual(report["resource_names"], ["resource-1"])
        self.assertEqual(report["prompt_names"], ["prompt-1"])
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("tool-page-2", rendered)
        self.assertNotIn("never", rendered)


if __name__ == "__main__":
    unittest.main()
