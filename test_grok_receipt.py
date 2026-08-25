#!/usr/bin/env python3
"""Synthetic tests for the Grok Build receipt boundary."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

import grok_receipt as gr


def envelope_bytes(text=None, thought="scratch"):
    packet = {"packet_id": "synthetic-packet", "value": 7}
    body = text
    if body is None:
        body = "answer\n```json\n%s\n```\n" % json.dumps(packet)
    return json.dumps(
        {
            "text": body,
            "thought": thought,
            "stopReason": "end_turn",
            "sessionId": "synthetic-session",
            "requestId": "synthetic-request",
            "usage": {"total_tokens": 42},
            "num_turns": 2,
            "total_cost_usd": 0.01,
            "modelUsage": {
                "grok-4.6-build": {
                    "inputTokens": 30,
                    "outputTokens": 12,
                    "modelCalls": 2,
                }
            },
        }
    ).encode("utf-8")


class TestGrokReceipt(unittest.TestCase):
    def test_valid_envelope_normalizes_one_text_packet(self):
        raw = envelope_bytes(
            thought="```json\n{\"packet_id\":\"scratch\",\"value\":0}\n```"
        )
        got, code = gr.evaluate_receipt(raw, source="C:/private/receipt.json")
        self.assertEqual(code, gr.EXIT_OK)
        self.assertEqual(got["status"], "OK")
        self.assertEqual(got["packet_id"], "synthetic-packet")
        self.assertEqual(got["packet"]["value"], 7)
        self.assertEqual(got["source"]["name"], "receipt.json")
        self.assertEqual(got["sessionId"], "synthetic-session")
        self.assertEqual(got["model"], "grok-4.6-build")
        self.assertEqual(got["usage"]["total_tokens"], 42)
        self.assertEqual(got["fence_count"], 1)
        self.assertNotIn("thought", got)
        self.assertNotIn("text", got)
        self.assertEqual(got["excluded_fields"], ["text", "thought"])

    def test_source_sha_is_exact_raw_bytes(self):
        raw = envelope_bytes()
        got, code = gr.evaluate_receipt(raw)
        self.assertEqual(code, gr.EXIT_OK)
        self.assertEqual(got["source_sha256"], gr.sha256_hex(raw))
        self.assertEqual(got["source"]["bytes"], len(raw))

    def test_outer_not_json_is_invalid_envelope(self):
        got, code = gr.evaluate_receipt(b"not-json")
        self.assertEqual(code, gr.EXIT_INVALID_ENVELOPE)
        self.assertEqual(got["status"], "INVALID_ENVELOPE")

    def test_outer_wrong_type_is_invalid_envelope(self):
        got, code = gr.evaluate_receipt(b"[]")
        self.assertEqual(code, gr.EXIT_INVALID_ENVELOPE)
        self.assertEqual(got["status"], "INVALID_ENVELOPE")

    def test_outer_required_fields_are_checked(self):
        raw = json.dumps({"text": "```json\n{}\n```"}).encode("utf-8")
        got, code = gr.evaluate_receipt(raw)
        self.assertEqual(code, gr.EXIT_INVALID_ENVELOPE)
        self.assertIn("sessionId", got["error"])
        self.assertIn("usage", got["error"])
        self.assertIn("modelUsage", got["error"])

    def test_zero_json_fences_is_not_zero_receipts(self):
        got, code = gr.evaluate_receipt(envelope_bytes(text="prose only"))
        self.assertEqual(code, gr.EXIT_ZERO_FENCES)
        self.assertEqual(got["status"], "ZERO_FENCES")

    def test_multiple_complete_json_fences_are_rejected(self):
        text = (
            "```json\n{\"packet_id\":\"scratch\"}\n```\n"
            "```json\n{\"packet_id\":\"final\"}\n```\n"
        )
        got, code = gr.evaluate_receipt(envelope_bytes(text=text))
        self.assertEqual(code, gr.EXIT_MULTIPLE_FENCES)
        self.assertEqual(got["status"], "MULTIPLE_FENCES")

    def test_measured_grok_appended_opener_form_is_accepted(self):
        text = (
            "Returning the single JSON object.```json\n"
            "{\"packet_id\":\"synthetic-packet\"}\n```\n"
        )
        got, code = gr.evaluate_receipt(envelope_bytes(text=text))
        self.assertEqual(code, gr.EXIT_OK)
        self.assertEqual(got["packet_id"], "synthetic-packet")

    def test_complete_fence_plus_unclosed_opener_is_multiple(self):
        text = (
            "```json\n{\"packet_id\":\"first\"}\n```\n"
            "```json\n{\"packet_id\":\"scratch\"}"
        )
        _, code = gr.evaluate_receipt(envelope_bytes(text=text))
        self.assertEqual(code, gr.EXIT_MULTIPLE_FENCES)

    def test_one_unclosed_fence_is_invalid_inner_json(self):
        _, code = gr.evaluate_receipt(
            envelope_bytes(text="```json\n{\"packet_id\":\"x\"}")
        )
        self.assertEqual(code, gr.EXIT_INVALID_INNER_JSON)

    def test_invalid_inner_json_has_distinct_exit(self):
        _, code = gr.evaluate_receipt(envelope_bytes(text="```json\n{\n```"))
        self.assertEqual(code, gr.EXIT_INVALID_INNER_JSON)

    def test_inner_array_has_wrong_type_exit(self):
        _, code = gr.evaluate_receipt(envelope_bytes(text="```json\n[]\n```"))
        self.assertEqual(code, gr.EXIT_WRONG_TYPE)

    def test_missing_packet_id_has_distinct_exit(self):
        _, code = gr.evaluate_receipt(envelope_bytes(text="```json\n{}\n```"))
        self.assertEqual(code, gr.EXIT_MISSING_PACKET_ID)

    def test_non_json_fence_does_not_count_as_authoritative(self):
        text = (
            "```text\nnot authoritative\n```\n"
            "```json\n{\"packet_id\":\"synthetic-packet\"}\n```\n"
        )
        got, code = gr.evaluate_receipt(envelope_bytes(text=text))
        self.assertEqual(code, gr.EXIT_OK)
        self.assertEqual(got["packet_id"], "synthetic-packet")

    def test_fence_markers_inside_json_strings_do_not_end_or_multiply(self):
        packet = {
            "packet_id": "synthetic-packet",
            "example": "literal markers: ```json and ``` stay packet data",
        }
        text = "```json\n%s\n```\n" % json.dumps(packet, indent=2)
        got, code = gr.evaluate_receipt(envelope_bytes(text=text))
        self.assertEqual(code, gr.EXIT_OK)
        self.assertEqual(got["packet"], packet)

    def test_unclosed_fence_in_outer_thought_is_ignored(self):
        raw = envelope_bytes(thought="scratch ```json never closes")
        got, code = gr.evaluate_receipt(raw)
        self.assertEqual(code, gr.EXIT_OK)
        self.assertEqual(got["packet_id"], "synthetic-packet")

    def test_stdin_and_stdout(self):
        raw = envelope_bytes()
        out = io.BytesIO()
        code = gr.main(["--check", "-"], stdin=io.BytesIO(raw), stdout=out)
        self.assertEqual(code, gr.EXIT_OK)
        got = json.loads(out.getvalue())
        self.assertEqual(got["source"]["name"], "-")
        self.assertEqual(got["source_sha256"], gr.sha256_hex(raw))

    def test_output_file_matches_stdout(self):
        raw = envelope_bytes()
        with tempfile.TemporaryDirectory() as td:
            source = os.path.join(td, "receipt.json")
            target = os.path.join(td, "normalized.json")
            with open(source, "wb") as handle:
                handle.write(raw)
            out = io.BytesIO()
            code = gr.main(["--output", target, source], stdout=out)
            self.assertEqual(code, gr.EXIT_OK)
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), out.getvalue())

    def test_missing_input_file_has_distinct_exit(self):
        with tempfile.TemporaryDirectory() as td:
            source = os.path.join(td, "missing.json")
            out = io.BytesIO()
            code = gr.main([source], stdout=out)
        self.assertEqual(code, gr.EXIT_MISSING_FILE)
        self.assertEqual(json.loads(out.getvalue())["status"], "MISSING_FILE")

    def test_write_failure_has_distinct_exit(self):
        raw = envelope_bytes()
        with tempfile.TemporaryDirectory() as td:
            source = os.path.join(td, "receipt.json")
            target = os.path.join(td, "missing-parent", "normalized.json")
            with open(source, "wb") as handle:
                handle.write(raw)
            out = io.BytesIO()
            code = gr.main(["--output", target, source], stdout=out)
        self.assertEqual(code, gr.EXIT_WRITE_FAILURE)
        self.assertEqual(json.loads(out.getvalue())["status"], "WRITE_FAILURE")

    def test_self_test_does_not_require_account_state(self):
        out = io.BytesIO()
        code = gr.main(["--self-test"], stdout=out)
        self.assertEqual(code, gr.EXIT_OK)
        self.assertTrue(json.loads(out.getvalue())["self_test"])


if __name__ == "__main__":
    unittest.main()
