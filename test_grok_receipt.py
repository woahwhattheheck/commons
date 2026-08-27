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


MEASURED_EXPECTED_EXITS = {
    "H-001-ARCHITECT.json": gr.RECEIPT_EXIT_OK,
    "H-001-SKEPTIC.json": gr.RECEIPT_EXIT_OK,
    "H-002-CONTAMINATION.json": gr.RECEIPT_EXIT_OK,
    "H-003-INTEGRATION-ARCHITECT.json": gr.RECEIPT_EXIT_OK,
    "H-004-FALSE-ZERO.json": gr.RECEIPT_EXIT_OK,
    "H-005-FRONTIER-ADJACENCY.json": gr.RECEIPT_EXIT_OK,
    "H-006-RESOURCE-ROUTER.json": gr.RECEIPT_EXIT_OK,
    "H-007-RECONCILE.json": gr.RECEIPT_EXIT_OK,
    "H-008-RECEIPT-VALIDATOR.json": gr.RECEIPT_EXIT_REVISION_CONTRADICTION,
    "H-009-DEVICE-ZERO-PATCH.json": gr.RECEIPT_EXIT_OK,
    "H-010-CATALOG-DELTA.json": gr.RECEIPT_EXIT_OK,
}

LEGACY_SUFFIX_PROSE = {
    "H-001-ARCHITECT.json": "Returning the single JSON object.",
    "H-002-CONTAMINATION.json": (
        "Cargo is not on this host, so unit tests were not executed."
    ),
    "H-003-INTEGRATION-ARCHITECT.json": (
        "I will pull those plus the seven consumer files and check for MORROW."
    ),
    "H-005-FRONTIER-ADJACENCY.json": (
        "Next I will compare reversible hardware and mmap model execution."
    ),
    "H-006-RESOURCE-ROUTER.json": (
        "Re-pinning origin/main, then I will emit the single JSON object."
    ),
}


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

    def test_multiple_markers_on_one_line_cannot_smuggle_one_opener(self):
        for opener in (
            "```json```json",
            "prose ```json before an apparent suffix ```json",
        ):
            with self.subTest(opener=opener):
                text = "%s\n{\"packet_id\":\"smuggled\"}\n```\n" % opener
                got, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
                self.assertEqual(code, gr.RECEIPT_EXIT_ZERO_FENCES)
                self.assertEqual(got["status"], "ZERO_FENCES")
                self.assertNotIn("packet", got)

    def test_measured_legacy_suffix_openers_are_accepted(self):
        for name, prose in LEGACY_SUFFIX_PROSE.items():
            with self.subTest(receipt=name):
                packet = {
                    "packet_id": name[:-5],
                    "source_head": "1a41a228",
                }
                text = "%s```json\n%s\n```\n" % (
                    prose,
                    json.dumps(packet),
                )
                thought = (
                    "non-authoritative scratch has an unclosed ```json marker "
                    "and another ```json marker"
                    if name == "H-002-CONTAMINATION.json"
                    else "scratch"
                )
                got, code = gr.evaluate_receipt(
                    completed_envelope_bytes(text=text, thought=thought)
                )
                self.assertEqual(code, gr.RECEIPT_EXIT_OK, (name, got))
                self.assertEqual(got["fence_count"], 1)
                self.assertEqual(got["packet_id"], packet["packet_id"])
                self.assertNotIn("thought", got)

    def test_measured_h008_shape_remains_revision_contradiction(self):
        packet = {
            "packet_id": "H-008-RECEIPT-VALIDATOR",
            "source_head": {"git_head": "1a41a228"},
            "measured_envelope_contract": {
                "inner_3_of_3": {"source_head": "1a41a228"}
            },
        }
        text = "```json\n%s\n```\n" % json.dumps(packet)
        got, code = gr.evaluate_receipt(
            completed_envelope_bytes(
                text=text,
                thought="scratch contains an unclosed ```json opener",
            )
        )
        self.assertEqual(code, gr.RECEIPT_EXIT_REVISION_CONTRADICTION)
        self.assertEqual(got["fence_count"], 1)
        self.assertEqual(
            got["revision_contradictions"][0]["reason"],
            "SCALAR_OBJECT_CONFLICT",
        )

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

    def test_inline_prose_marker_is_not_a_fence_and_non_json_fence_is_ignored(self):
        appended = (
            "Prose contains the literal marker ```json before more prose\n"
            "{\"packet_id\":\"synthetic-packet\"}\n```\n"
        )
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=appended))
        self.assertEqual(code, gr.RECEIPT_EXIT_ZERO_FENCES)
        self.assertEqual(got["status"], "ZERO_FENCES")
        mixed = (
            "Prose contains the literal marker ```json before more prose\n"
            "```json\n{\"packet_id\":\"real\"}\n```\n"
        )
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=mixed))
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["packet_id"], "real")
        text = (
            "```text\nnot authoritative\n```\n"
            "  ```JSON  \n{\"packet_id\":\"synthetic-packet\"}\n  ```\n"
        )
        _, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)

    def test_revision_truth_labels_are_inner_only_and_fail_closed(self):
        conflict = {
            "packet_id": "revision-conflict",
            "source_head": "aaaaaaaa",
            "nested": {"source_head": "bbbbbbbb"},
        }
        text = "```json\n%s\n```\n" % json.dumps(conflict)
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_REVISION_CONTRADICTION)
        self.assertEqual(got["status"], "REVISION_CONTRADICTION")
        self.assertEqual(got["packet"], conflict)
        self.assertEqual(
            got["revision_contradictions"][0]["reason"],
            "INCOMPATIBLE_REVISIONS",
        )
        self.assertNotIn("thought", got)
        self.assertNotIn("text", got)

        shape_conflict = {
            "packet_id": "shape-conflict",
            "source_head": {"git_head": "1a41a228"},
            "nested": {"source_head": "1a41a228"},
        }
        text = "```json\n%s\n```\n" % json.dumps(shape_conflict)
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_REVISION_CONTRADICTION)
        self.assertEqual(
            got["revision_contradictions"][0]["reason"],
            "SCALAR_OBJECT_CONFLICT",
        )

    def test_revision_prefixes_are_compatible_and_generic_hashes_are_ignored(self):
        packet = {
            "packet_id": "revision-prefix",
            "source_head": {"git_head": "1a41a228"},
            "nested": {"git_head": "1a41a228b63b3c8c4e5632fd98f4375205d692e6"},
            "nodes": [{"head_sha": "a" * 40}, {"head_sha": "b" * 40}],
            "next_handoff": {"state": "NOT_LANDED"},
        }
        text = "```json\n%s\n```\n" % json.dumps(packet)
        got, code = gr.evaluate_receipt(
            completed_envelope_bytes(
                text=text,
                thought=(
                    "prose ```json plus source_head cccccccc and an unclosed "
                    "scratch marker"
                ),
            )
        )
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["revision_contradictions"], [])
        self.assertEqual(got["packet"]["next_handoff"]["state"], "NOT_LANDED")

    def test_revision_placeholders_inside_schema_templates_are_not_facts(self):
        packet = {
            "packet_id": "schema-placeholder",
            "source_head": {"git_head": "1a41a228"},
            "final_receipt_schema": {"source_head": "official main SHA"},
            "nested": {
                "schema": {
                    "source_head": ["placeholder with an invalid fact type"]
                }
            },
        }
        text = "```json\n%s\n```\n" % json.dumps(packet)
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["revision_contradictions"], [])

    def test_invalid_revision_type_is_explicit_contradiction(self):
        packet = {"packet_id": "bad-revision-type", "source_rev": ["abc1234"]}
        text = "```json\n%s\n```\n" % json.dumps(packet)
        got, code = gr.evaluate_receipt(completed_envelope_bytes(text=text))
        self.assertEqual(code, gr.RECEIPT_EXIT_REVISION_CONTRADICTION)
        self.assertEqual(
            got["revision_contradictions"][0]["reason"], "INVALID_REVISION_TYPE"
        )

    def test_duplicate_inner_identity_and_nested_keys_fail_closed(self):
        bodies = (
            (
                "source_head",
                '{"packet_id":"dup-key-probe","source_head":"1111111",'
                '"source_head":"2222222"}',
            ),
            (
                "packet_id",
                '{"packet_id":"first","packet_id":"second"}',
            ),
            (
                "git_head",
                '{"packet_id":"nested","facts":{"git_head":"1111111",'
                '"git_head":"2222222"}}',
            ),
        )
        for key, body in bodies:
            with self.subTest(duplicate_key=key):
                raw = completed_envelope_bytes(text="```json\n%s\n```\n" % body)
                got, code = gr.evaluate_receipt(raw)
                self.assertEqual(code, gr.RECEIPT_EXIT_DUPLICATE_KEY)
                self.assertEqual(got["status"], "DUPLICATE_KEY")
                self.assertIn(repr(key), got["error"])
                self.assertEqual(got["source_sha256"], gr.receipt_sha256(raw))
                self.assertEqual(got["source"]["bytes"], len(raw))
                self.assertNotIn("packet", got)

    def test_duplicate_outer_identity_fields_and_nested_usage_fail_closed(self):
        valid_text = "```json\n{\"packet_id\":\"outer\"}\n```\n"
        base_pairs = [
            ("text", valid_text),
            ("sessionId", "session-one"),
            ("usage", {"total_tokens": 1}),
            ("modelUsage", {"model-one": {"modelCalls": 1}}),
        ]
        replacements = {
            "text": "prose only",
            "sessionId": "session-two",
            "usage": {"total_tokens": 2},
            "modelUsage": {"model-two": {"modelCalls": 2}},
        }
        for duplicate_key, replacement in replacements.items():
            with self.subTest(duplicate_outer=duplicate_key):
                pairs = []
                for key, value in base_pairs:
                    pairs.append((key, value))
                    if key == duplicate_key:
                        pairs.append((key, replacement))
                raw = (
                    "{"
                    + ",".join(
                        "%s:%s" % (json.dumps(key), json.dumps(value))
                        for key, value in pairs
                    )
                    + "}"
                ).encode("utf-8")
                got, code = gr.evaluate_receipt(raw)
                self.assertEqual(code, gr.RECEIPT_EXIT_DUPLICATE_KEY)
                self.assertIn("outer envelope", got["error"])
                self.assertIn(repr(duplicate_key), got["error"])
                self.assertEqual(got["source_sha256"], gr.receipt_sha256(raw))

        nested_usage = (
            '{"text":%s,"sessionId":"session","usage":'
            '{"total_tokens":1,"total_tokens":2},'
            '"modelUsage":{"model":{"modelCalls":1}}}'
            % json.dumps(valid_text)
        ).encode("utf-8")
        got, code = gr.evaluate_receipt(nested_usage)
        self.assertEqual(code, gr.RECEIPT_EXIT_DUPLICATE_KEY)
        self.assertIn("'total_tokens'", got["error"])

    def test_repeated_values_and_same_keys_in_distinct_objects_are_safe(self):
        body = (
            '{"packet_id":"safe","rows":['
            '{"packet_id":"row","source_head":"1111111"},'
            '{"packet_id":"row","source_head":"1111111"}],'
            '"values":[1,1,"same","same"]}'
        )
        got, code = gr.evaluate_receipt(
            completed_envelope_bytes(text="```json\n%s\n```\n" % body)
        )
        self.assertEqual(code, gr.RECEIPT_EXIT_OK)
        self.assertEqual(got["packet_id"], "safe")
        self.assertEqual(got["revision_contradictions"], [])

    def test_empty_usage_and_overbudget_sources_are_invalid_without_hash_claims(self):
        envelope = json.loads(completed_envelope_bytes())
        envelope["usage"] = {}
        got, code = gr.evaluate_receipt(json.dumps(envelope).encode("utf-8"))
        self.assertEqual(code, gr.RECEIPT_EXIT_INVALID_ENVELOPE)
        self.assertIn("usage:nonempty-object", got["error"])

        overbudget = b"x" * (gr.RECEIPT_MAX_SOURCE_BYTES + 1)
        got, code = gr.evaluate_receipt(overbudget)
        self.assertEqual(code, gr.RECEIPT_EXIT_INVALID_ENVELOPE)
        self.assertIn("receipt budget", got["error"])
        self.assertNotIn("source_sha256", got)
        out = io.BytesIO()
        code = gr.main(
            ["--check", "-"], stdin=io.BytesIO(overbudget), stdout=out
        )
        self.assertEqual(code, gr.RECEIPT_EXIT_INVALID_ENVELOPE)
        self.assertNotIn("source_sha256", json.loads(out.getvalue()))

    def test_measured_finder_never_reports_failure_as_zero(self):
        with tempfile.TemporaryDirectory() as td:
            calibration = os.path.join(td, "known-present")
            with open(calibration, "w", encoding="utf-8") as handle:
                handle.write("present")
            missing = gr.find_measured_receipts(
                os.path.join(td, "missing"), calibration
            )
            self.assertEqual(missing["state"], "FINDER-FAILED")
            self.assertIsNone(missing["count"])

            receipts = os.path.join(td, "receipts")
            os.mkdir(receipts)
            with open(
                os.path.join(receipts, gr.MEASURED_NAMES[0]),
                "wb",
            ) as handle:
                handle.write(b"synthetic")
            partial = gr.find_measured_receipts(receipts, calibration)
            self.assertEqual(partial["state"], "FINDER-FAILED")
            self.assertEqual(partial["count"], 1)
            for name in gr.MEASURED_NAMES[1:]:
                with open(os.path.join(receipts, name), "wb") as handle:
                    handle.write(b"synthetic")
            found = gr.find_measured_receipts(receipts, calibration)
            self.assertEqual(found["state"], "FOUND")
            self.assertEqual(found["count"], len(gr.MEASURED_NAMES))

    def test_optional_measured_smoke_is_found_or_explicit_finder_failure(self):
        root = os.environ.get(gr.SMOKE_ENV)
        found = gr.find_measured_receipts(root)
        if found["state"] != "FOUND":
            self.assertNotEqual(found["count"], 0)
            return
        self.assertEqual(found["count"], len(gr.MEASURED_NAMES))
        for name in gr.MEASURED_NAMES:
            with open(os.path.join(root, name), "rb") as handle:
                got, code = gr.evaluate_receipt(handle.read(), source=name)
            self.assertEqual(code, got["exit_code"], (name, got))
            self.assertEqual(got["status"], gr.RECEIPT_STATUS_BY_EXIT[code])
            self.assertNotEqual(got["status"], "UNMEASURED")
            self.assertNotIn("thought", got)
            self.assertNotIn("text", got)
        for name, expected_exit in MEASURED_EXPECTED_EXITS.items():
            path = os.path.join(root, name)
            self.assertTrue(os.path.isfile(path), name)
            with open(path, "rb") as handle:
                got, code = gr.evaluate_receipt(handle.read(), source=name)
            self.assertEqual(code, expected_exit, (name, got))
            self.assertEqual(got["exit_code"], expected_exit)
            self.assertEqual(got["status"], gr.RECEIPT_STATUS_BY_EXIT[expected_exit])
            self.assertNotIn("thought", got)
            self.assertNotIn("text", got)

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
            invalid_target = os.path.join(td, "must-not-exist.json")
            invalid_source = os.path.join(td, "invalid.json")
            with open(invalid_source, "wb") as handle:
                handle.write(completed_envelope_bytes(text="prose only"))
            invalid_out = io.BytesIO()
            code = gr.main(
                ["--output", invalid_target, invalid_source], stdout=invalid_out
            )
            self.assertEqual(code, gr.RECEIPT_EXIT_ZERO_FENCES)
            self.assertFalse(os.path.exists(invalid_target))
            duplicate_target = os.path.join(td, "duplicate-must-not-exist.json")
            duplicate_source = os.path.join(td, "duplicate.json")
            duplicate_raw = completed_envelope_bytes(
                text=(
                    "```json\n"
                    '{"packet_id":"first","packet_id":"second"}\n'
                    "```\n"
                )
            )
            with open(duplicate_source, "wb") as handle:
                handle.write(duplicate_raw)
            duplicate_out = io.BytesIO()
            code = gr.main(
                ["--output", duplicate_target, duplicate_source],
                stdout=duplicate_out,
            )
            self.assertEqual(code, gr.RECEIPT_EXIT_DUPLICATE_KEY)
            self.assertFalse(os.path.exists(duplicate_target))
            self.assertEqual(
                json.loads(duplicate_out.getvalue())["source_sha256"],
                gr.receipt_sha256(duplicate_raw),
            )


if __name__ == "__main__":
    unittest.main()
