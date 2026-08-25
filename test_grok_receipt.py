#!/usr/bin/env python3
"""Exact-one-fence leftover. Last-fence is collision."""

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
from grok_receipt import (
    ALREADY_LANDED,
    CALIBRATION,
    CANDIDATE_RECEIPTS,
    H009_PATCHED,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    normalize_envelope,
    raw_sha,
)


class TestGrokReceipt(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
                "h009_present": True,
                "raw_sha": "0" * 40,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_null_sha_is_unmeasured(self):
        verdict = classify(
            measure_from_rows(
                {
                    "card_present": True,
                    "catalog_present": True,
                    "h009_present": True,
                    "calibration_ok": True,
                    "raw_sha": None,
                }
            )
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("raw SHA is null", verdict["note"])

    def test_two_fences_are_finder_failed(self):
        envelope = (
            "scratch thought {\"rank\": 1}\n"
            "```json\n{\"scratch\": true}\n```\n"
            "more thought\n"
            "```json\n{\"ok\": true, \"delta\": [\"rivet\"]}\n```\n"
        )
        got = normalize_envelope(envelope)
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertIsNone(got["authoritative"])
        self.assertEqual(got["fence_count"], 2)
        self.assertIn("FINDER-FAILED", got["error"])
        self.assertIn("collision", got["error"].lower())

    def test_exact_one_fence_is_authoritative(self):
        got = normalize_envelope("```json\n{\"ok\": true, \"delta\": [\"rivet\"]}\n```\n")
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertEqual(got["authoritative"], {"ok": True, "delta": ["rivet"]})
        self.assertEqual(got["fence_count"], 1)
        self.assertIn("scratch/thought", got["excluded"])

    def test_missing_fence_is_finder_failed(self):
        got = normalize_envelope("thought only")
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertIsNone(got["authoritative"])
        self.assertIn("FINDER-FAILED", got["error"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "h009_present": False,
                "misses": ["ground/GROK_RECEIPT.md"],
                "calibration_ok": True,
                "raw_sha": "0" * 40,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_tree_is_exact_one_fence(self):
        catalog_path = os.path.join(ROOT, "ground", "GROK_RECEIPT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["titan_helper"], "BOUNDARY_ONLY")
        self.assertEqual(catalog["architect_rank_1"], "REFUSED")
        self.assertEqual(catalog["posting"], "OPEN")
        ids = [item["id"] for item in catalog["receipts"]]
        for name in CANDIDATE_RECEIPTS:
            self.assertTrue(any(name.lower() in item.lower() for item in ids), name)
        self.assertTrue(all(item["status"] == "CANDIDATE" for item in catalog["receipts"]))
        sha = raw_sha(ROOT)
        self.assertIsNotNone(sha)
        self.assertEqual(len(sha), 40)
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(len(row["calibration_hits"]), len(CALIBRATION))
        self.assertEqual(row["raw_sha"], sha)
        self.assertTrue(row["exact_one_fence"])
        self.assertTrue(row["last_fence_absent"])
        self.assertTrue(row["rivet_heartbeat_row"])
        self.assertTrue(row["gemma_path_current"])
        self.assertTrue(row["dump_impl_present"])
        self.assertTrue(row["census_invalid_ref_null"])
        self.assertTrue(row["churn_missing_dir_null"])
        self.assertTrue(row["titan_helper_boundary"])
        self.assertEqual(len(row["h009_patched"]), len(H009_PATCHED))
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(row)["note"])
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        self.assertEqual(len(row["landed_missing"]), 0)
        self.assertEqual(len(row["landed_present"]), len(ALREADY_LANDED))


def completed_envelope_bytes(text=None, thought="scratch"):
    packet = {"packet_id": "synthetic-packet", "value": 7}
    if text is None:
        text = "answer\n```json\n%s\n```\n" % json.dumps(packet)
    return json.dumps(
        {
            "text": text,
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


class TestCompletedGrokEnvelope(unittest.TestCase):
    def test_valid_envelope_ignores_outer_thought(self):
        raw = completed_envelope_bytes(
            thought="```json\n{\"packet_id\":\"scratch\",\"value\":0}\n```"
        )
        got, code = gr.evaluate_receipt(raw, source="C:/private/receipt.json")
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["packet_id"], "synthetic-packet")
        self.assertEqual(got["packet"]["value"], 7)
        self.assertEqual(got["source"]["name"], "receipt.json")
        self.assertEqual(got["sessionId"], "synthetic-session")
        self.assertEqual(got["model"], "grok-4.6-build")
        self.assertNotIn("thought", got)
        self.assertNotIn("text", got)
        self.assertEqual(got["excluded_fields"], ["text", "thought"])

    def test_source_sha_is_exact_completed_envelope_bytes(self):
        raw = completed_envelope_bytes()
        got, code = gr.evaluate_receipt(raw)
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["source_sha256"], gr.receipt_sha256(raw))
        self.assertEqual(got["source"]["bytes"], len(raw))

    def test_literal_fence_markers_and_thinking_string_stay_packet_data(self):
        packet = {
            "packet_id": "synthetic-packet",
            "example": "literal markers: ```json and ``` stay packet data",
            "note": "thinking: keep this",
        }
        text = "```json\n%s\n```\n" % json.dumps(packet, indent=2)
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["packet"], packet)

    def test_outer_validation_is_explicit(self):
        for raw in (b"not-json", b"[]"):
            got, code = gr.evaluate_receipt(raw)
            self.assertEqual(code, gr.RECEIPT_EXIT_INVALID_ENVELOPE)
            self.assertEqual(got["status"], "INVALID_ENVELOPE")
        raw = json.dumps({"text": "```json\n{}\n```"}).encode("utf-8")
        got, code = gr.evaluate_receipt(raw)
        self.assertEqual(code, gr.RECEIPT_EXIT_INVALID_ENVELOPE)
        self.assertIn("sessionId", got["error"])
        self.assertIn("usage", got["error"])
        self.assertIn("modelUsage", got["error"])

    def test_zero_multiple_and_unclosed_fences_are_distinct(self):
        _, zero = gr.evaluate_receipt(completed_envelope_bytes(text="prose only"))
        self.assertEqual(zero, gr.RECEIPT_EXIT_ZERO_FENCES)
        two = (
            "```json\n{\"packet_id\":\"scratch\"}\n```\n"
            "```json\n{\"packet_id\":\"final\"}\n```\n"
        )
        _, multiple = gr.evaluate_receipt(completed_envelope_bytes(text=two))
        self.assertEqual(multiple, gr.RECEIPT_EXIT_MULTIPLE_FENCES)
        unclosed = "```json\n{\"packet_id\":\"x\"}"
        _, invalid = gr.evaluate_receipt(completed_envelope_bytes(text=unclosed))
        self.assertEqual(invalid, gr.RECEIPT_EXIT_INVALID_INNER_JSON)

    def test_complete_fence_plus_unclosed_second_opener_is_multiple(self):
        text = (
            "```json\n{\"packet_id\":\"first\"}\n```\n"
            "```json\n{\"packet_id\":\"scratch\"}"
        )
        _, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_MULTIPLE_FENCES)

    def test_inner_shape_and_packet_id_are_explicit(self):
        _, invalid = gr.evaluate_receipt(
            completed_envelope_bytes(text="```json\n{\n```")
        )
        self.assertEqual(invalid, gr.RECEIPT_EXIT_INVALID_INNER_JSON)
        _, wrong_type = gr.evaluate_receipt(
            completed_envelope_bytes(text="```json\n[]\n```")
        )
        self.assertEqual(wrong_type, gr.RECEIPT_EXIT_WRONG_TYPE)
        _, no_id = gr.evaluate_receipt(
            completed_envelope_bytes(text="```json\n{}\n```")
        )
        self.assertEqual(no_id, gr.RECEIPT_EXIT_MISSING_PACKET_ID)

    def test_measured_appended_opener_and_non_json_fence(self):
        appended = (
            "Returning the single JSON object.```json\n"
            "{\"packet_id\":\"synthetic-packet\"}\n```\n"
        )
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=appended))
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["packet_id"], "synthetic-packet")
        text = (
            "```text\nnot authoritative\n```\n"
            "```json\n{\"packet_id\":\"synthetic-packet\"}\n```\n"
        )
        _, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)

    def test_cli_stdin_output_and_failures(self):
        raw = completed_envelope_bytes()
        out = io.BytesIO()
        code = gr.main(["--check", "-"], stdin=io.BytesIO(raw), stdout=out)
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(json.loads(out.getvalue())["source"]["name"], "-")
        with tempfile.TemporaryDirectory() as td:
            source = os.path.join(td, "receipt.json")
            target = os.path.join(td, "normalized.json")
            with open(source, "wb") as handle:
                handle.write(raw)
            out = io.BytesIO()
            code = gr.main(["--output", target, source], stdout=out)
            self.assertEqual(code, gr.RECEIPT_EXIT_OK)
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), out.getvalue())
            missing_out = io.BytesIO()
            code = gr.main([os.path.join(td, "missing.json")], stdout=missing_out)
            self.assertEqual(code, gr.RECEIPT_EXIT_MISSING_FILE)
            bad_target = os.path.join(td, "missing-parent", "normalized.json")
            write_out = io.BytesIO()
            code = gr.main(["--output", bad_target, source], stdout=write_out)
            self.assertEqual(code, gr.RECEIPT_EXIT_WRITE_FAILURE)


if __name__ == "__main__":
    unittest.main()
