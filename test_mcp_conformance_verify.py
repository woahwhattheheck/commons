#!/usr/bin/env python3
"""Adversarial contracts for the offline MCP Conformance receipt verifier."""
from __future__ import annotations

import copy
import json
import unittest

from host import mcp_conformance_verify as verifier


def _sha(ch: str) -> str:
    return ch * 64


def _transport(seed: str, response_bytes: int = 10) -> dict:
    return {
        "http_status": 200,
        "content_type": "application/json",
        "request_sha256": _sha(seed),
        "response_sha256": _sha(chr(ord(seed) + 1)),
        "response_bytes": response_bytes,
    }


def _page(number: int, item_count: int, seed: str) -> dict:
    return {"page": number, "item_count": item_count, **_transport(seed, response_bytes=number * 10)}


def _supported(pages: list[dict]) -> dict:
    first = pages[0]
    return {
        "state": "SUPPORTED",
        "complete": True,
        "page_count": len(pages),
        "item_count": sum(row["item_count"] for row in pages),
        "pages": pages,
        **{field: first[field] for field in verifier.TRANSPORT_FIELDS},
    }


def _signed_current_receipt() -> dict:
    required = ["late", "present"]
    receipt = {
        "schema": verifier.RECEIPT_SCHEMA,
        "measured_at": "2026-09-13T07:00:00Z",
        "endpoint": "https://example.com/mcp",
        "input_sha256": _sha("1"),
        "protocol_requested": "2025-06-18",
        "protocol_negotiated": "2025-06-18",
        "server_info": {"name": "fixture", "version": "1"},
        "required_tools": required,
        "transport": {"initialize": _transport("2", 20), "initialized": _transport("4", 0)},
        "discovery": {
            "tools/list": _supported([_page(1, 1, "6"), _page(2, 2, "8")]),
            "resources/list": _supported([_page(1, 1, "a")]),
            "prompts/list": _supported([_page(1, 0, "c")]),
        },
        "discovery_limits": {"max_pages_per_method": 500},
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        "tool_call": None,
        "errors": [],
        "tool_names": ["early", "late", "present"],
        "tool_parity": {"present": required, "missing": [], "complete": True, "authoritative": True},
        "resource_names": ["r1"],
        "prompt_names": [],
        "status": "PASS",
    }
    receipt["receipt_sha256"] = verifier.sha256_text(verifier.canonical_json(receipt))
    return receipt


def _resign(receipt: dict) -> dict:
    receipt = copy.deepcopy(receipt)
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = verifier.sha256_text(verifier.canonical_json(receipt))
    return receipt


def _legacy_receipt() -> dict:
    receipt = {
        "schema": verifier.RECEIPT_SCHEMA,
        "measured_at": "2026-09-12T07:00:00Z",
        "endpoint": "https://legacy.example/mcp",
        "input_sha256": _sha("1"),
        "protocol_requested": "2025-06-18",
        "required_tools": ["wanted"],
        "transport": {"initialize": _transport("2"), "initialized": _transport("4", 0)},
        "discovery": {
            "tools/list": {"state": "SUPPORTED", **_transport("6")},
            "resources/list": {"state": "SUPPORTED", **_transport("8")},
            "prompts/list": {"state": "UNSUPPORTED", "error": {"code": "RPC_ERROR", "message": "prompts/list returned JSON-RPC error", "rpc_code": -32601}},
        },
        "capabilities": {},
        "tool_call": None,
        "errors": [],
        "tool_names": ["wanted"],
        "tool_parity": {"present": ["wanted"], "missing": [], "complete": True},
        "resource_names": [],
        "prompt_names": [],
        "status": "PARTIAL",
    }
    receipt["receipt_sha256"] = verifier.sha256_text(verifier.canonical_json(receipt))
    return receipt


class MCPConformanceVerifierTests(unittest.TestCase):
    def test_valid_paginated_receipt_produces_self_hashed_verification(self):
        receipt = _signed_current_receipt()
        report = verifier.verify_receipt(receipt)
        self.assertTrue(report["valid"])
        self.assertEqual(report["profile"], "paginated-v1")
        self.assertEqual(report["subject_receipt_sha256"], receipt["receipt_sha256"])
        verification_hash = report.pop("verification_sha256")
        self.assertEqual(verification_hash, verifier.sha256_text(verifier.canonical_json(report)))

    def test_unsigned_tamper_is_detected_by_receipt_hash(self):
        receipt = _signed_current_receipt()
        receipt["tool_names"].append("tampered")
        report = verifier.verify_receipt(receipt)
        self.assertFalse(report["valid"])
        self.assertFalse(report["checks"]["integrity"])
        self.assertIn("RECEIPT_HASH_MISMATCH", {row["code"] for row in report["errors"]})

    def test_resigned_contradictory_parity_is_rejected_semantically(self):
        receipt = _signed_current_receipt()
        receipt["tool_parity"]["missing"] = ["late"]
        receipt["tool_parity"]["complete"] = False
        report = verifier.verify_receipt(_resign(receipt))
        self.assertFalse(report["valid"])
        self.assertTrue(report["checks"]["integrity"])
        self.assertFalse(report["checks"]["semantics"])
        self.assertIn("PARITY_SET_MISMATCH", {row["code"] for row in report["errors"]})

    def test_resigned_private_endpoint_label_is_rejected(self):
        for endpoint, code in (
            ("https://user:password@example.com/mcp", "ENDPOINT_USERINFO_PRESENT"),
            ("https://example.com/mcp?token=secret", "ENDPOINT_QUERY_PRESENT"),
            ("https://example.com/mcp#secret", "ENDPOINT_FRAGMENT_PRESENT"),
        ):
            with self.subTest(endpoint=endpoint):
                receipt = _signed_current_receipt()
                receipt["endpoint"] = endpoint
                report = verifier.verify_receipt(_resign(receipt))
                self.assertFalse(report["valid"])
                self.assertFalse(report["checks"]["privacy"])
                self.assertIn(code, {row["code"] for row in report["errors"]})

    def test_resigned_page_ledger_contradictions_fail_closed(self):
        mutations = []
        r = _signed_current_receipt(); r["discovery"]["tools/list"]["page_count"] = 1; mutations.append((r, "PAGE_COUNT_MISMATCH"))
        r = _signed_current_receipt(); r["discovery"]["tools/list"]["pages"][1]["page"] = 7; mutations.append((r, "NONSEQUENTIAL_PAGE"))
        r = _signed_current_receipt(); r["discovery"]["tools/list"]["item_count"] = 99; mutations.append((r, "ITEM_COUNT_MISMATCH"))
        r = _signed_current_receipt(); r["discovery"]["tools/list"]["response_sha256"] = _sha("f"); mutations.append((r, "FIRST_PAGE_PROJECTION_MISMATCH"))
        r = _signed_current_receipt(); r["discovery"]["tools/list"]["pages"][0]["nextCursor"] = "raw-secret"; mutations.append((r, "RAW_CURSOR_PRESENT"))
        for receipt, expected in mutations:
            with self.subTest(expected=expected):
                report = verifier.verify_receipt(_resign(receipt))
                self.assertFalse(report["valid"])
                self.assertIn(expected, {row["code"] for row in report["errors"]})

    def test_failed_discovery_requires_fail_status_and_non_authoritative_parity(self):
        receipt = _signed_current_receipt()
        receipt["discovery"]["tools/list"] = {
            "state": "FAILED", "complete": False, "page_count": 0, "pages": [],
            "error": {"code": "TRANSPORT_ERROR", "message": "MCP endpoint could not be reached"},
        }
        receipt["tool_names"] = []
        receipt["tool_parity"] = {"present": [], "missing": [], "complete": False, "authoritative": False}
        receipt["status"] = "FAIL"
        report = verifier.verify_receipt(_resign(receipt))
        self.assertTrue(report["valid"], report["errors"])
        receipt["status"] = "PASS"
        report = verifier.verify_receipt(_resign(receipt))
        self.assertFalse(report["valid"])
        self.assertIn("STATUS_MISMATCH", {row["code"] for row in report["errors"]})

    def test_included_tool_result_must_match_result_hash_and_size_even_if_receipt_is_resigned(self):
        receipt = _signed_current_receipt()
        result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
        packed = verifier.canonical_json(result)
        receipt["tool_call"] = {
            "name": "echo", "request_sha256": _sha("d"), "state": "RETURNED",
            "transport": _transport("1", 50), "result_sha256": verifier.sha256_text(packed),
            "result_bytes": len(packed.encode("utf-8")), "result": result,
        }
        receipt = _resign(receipt)
        self.assertTrue(verifier.verify_receipt(receipt)["valid"])
        receipt["tool_call"]["result"]["isError"] = True
        report = verifier.verify_receipt(_resign(receipt))
        self.assertFalse(report["valid"])
        codes = {row["code"] for row in report["errors"]}
        self.assertIn("TOOL_RESULT_HASH_MISMATCH", codes)
        self.assertIn("TOOL_RESULT_SIZE_MISMATCH", codes)

    def test_legacy_single_page_v1_remains_verifiable(self):
        report = verifier.verify_receipt(_legacy_receipt())
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["profile"], "legacy-single-page-v1")

    def test_strict_bytes_reject_duplicate_keys_and_nonfinite_numbers_without_echoing_content(self):
        for raw in (b'{"schema":"x","schema":"y"}', b'{"schema":"x","value":NaN}', b'\xffnot-utf8'):
            with self.subTest(raw=raw[:10]):
                report = verifier.verify_bytes(raw)
                self.assertFalse(report["valid"])
                self.assertEqual(report["profile"], "invalid-json")
                self.assertRegex(report["subject_file_sha256"], r"^[0-9a-f]{64}$")
                self.assertNotIn("not-utf8", json.dumps(report))
                self.assertNotIn("schema\":\"x", json.dumps(report))

    def test_invalid_digest_shape_is_rejected_even_when_other_semantics_match(self):
        receipt = _signed_current_receipt()
        receipt["input_sha256"] = "ABC"
        report = verifier.verify_receipt(_resign(receipt))
        self.assertFalse(report["valid"])
        self.assertIn("INVALID_SHA256", {row["code"] for row in report["errors"]})


if __name__ == "__main__":
    unittest.main()
