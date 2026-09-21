"""Real-engine report/CLI regressions using fictional captures only."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.mcp_transcript_audit import (
    audit_transcript, canonical_json_bytes, encode_capture_event, verify_receipt,
)
from tools.mcp_transcript_audit.report import render_markdown

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "tools/mcp_transcript_audit/example_session.jsonl"


def events():
    return [
        (row["direction"], json.loads(base64.b64decode(row["payload_base64"])))
        for row in (json.loads(line) for line in EXAMPLE.read_bytes().splitlines())
    ]


def capture(rows):
    return b"\n".join(encode_capture_event(direction, message) for direction, message in rows) + b"\n"


class AuditReportTests(unittest.TestCase):
    def setUp(self):
        self.source = EXAMPLE.read_bytes()
        self.result = audit_transcript(self.source)

    def test_example_is_actual_pass_with_full_identity(self):
        text = render_markdown(self.result)
        self.assertEqual(self.result["status"], "PASS")
        self.assertIn("**Capture audit: PASS.**", text)
        for field in ("source_sha256", "receipt_sha256"):
            self.assertIn(self.result[field], text)
        self.assertIn("| Capture bytes | 921 |", text)
        self.assertIn("| Requests | 2 |", text)
        self.assertIn("| Responses | 2 |", text)
        self.assertIn("| Notifications | 1 |", text)

    def test_source_bytes_and_result_are_unchanged(self):
        original = canonical_json_bytes(self.result)
        render_markdown(self.result)
        self.assertEqual(canonical_json_bytes(self.result), original)
        self.assertEqual(self.source, EXAMPLE.read_bytes())

    def test_output_is_deterministic_and_has_no_final_newline(self):
        first = render_markdown(self.result)
        self.assertEqual(first, render_markdown(audit_transcript(self.source)))
        self.assertFalse(first.endswith("\n"))

    def test_empty_capture_holds_without_inventing_lifecycle(self):
        text = render_markdown(audit_transcript(b""))
        self.assertIn("**Capture audit: HOLD.**", text)
        self.assertIn("EMPTY\\_CAPTURE", text)
        self.assertIn("| Initialize request | not recorded |", text)
        self.assertIn("No event evidence rows were recorded.", text)

    def test_missing_notification_diagnostic_is_retained(self):
        rows = events()
        del rows[2]
        result = audit_transcript(capture(rows))
        text = render_markdown(result)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("INITIALIZED\\_NOTIFICATION\\_MISSING", text)
        self.assertIn("| Initialized notification | not recorded |", text)

    def test_lifecycle_and_index_use_physical_line_numbers(self):
        source = b"\n" + self.source.replace(b"\n", b"\n\n")
        text = render_markdown(audit_transcript(source))
        self.assertIn("| Initialize request | 2 |", text)
        self.assertIn("| Initialize response | 4 |", text)
        self.assertIn("| Initialized notification | 6 |", text)
        self.assertIn("| 10 | server\\_to\\_client | response | tools/list |", text)

    def test_unparsed_tail_is_indexed_but_never_called_successful(self):
        source = b"not-json\n" + self.source
        result = audit_transcript(source)
        text = render_markdown(result)
        self.assertEqual(result["event_count"], 6)
        self.assertIn("| Classified messages | 0 |", text)
        self.assertEqual(text.count("| not classified |"), 6)
        self.assertIn("| 1 | INVALID\\_CAPTURE\\_EVENT |", text)
        self.assertIn("Missing classifications are not successful checks.", text)

    def test_all_recorded_rows_are_present_without_hidden_truncation(self):
        rows = events()
        rows += [("server_to_client", {"jsonrpc": "2.0", "method": "notifications/message",
                  "params": {"level": "info", "data": "FICTIONAL-NOT-COPIED"}})] * 205
        result = audit_transcript(capture(rows))
        text = render_markdown(result)
        self.assertEqual(result["event_count"], 210)
        self.assertIn("| 210 | server\\_to\\_client | notification | notifications/message |", text)
        self.assertEqual(text.count("| notification |"), 206)
        self.assertNotIn("FICTIONAL-NOT-COPIED", text)

    def test_raw_ids_params_results_and_error_data_not_copied(self):
        rows = events()
        rows[3][1]["id"] = "FICTIONAL-RAW-SECRET-ID"
        rows[3][1]["params"] = {"record": "FICTIONAL-SECRET-PARAM"}
        rows[4][1]["id"] = "FICTIONAL-RAW-SECRET-ID"
        rows[4][1].pop("result")
        rows[4][1]["error"] = {"code": -32000, "message": "FICTIONAL-SECRET-MESSAGE",
                              "data": "FICTIONAL-SECRET-DATA"}
        result = audit_transcript(capture(rows))
        self.assertEqual(result["status"], "PASS")
        text = render_markdown(result)
        self.assertNotIn("FICTIONAL-", text)
        rows[4][1].pop("error")
        rows[4][1]["result"] = {"record": "FICTIONAL-SECRET-RESULT"}
        self.assertNotIn("FICTIONAL-", render_markdown(audit_transcript(capture(rows))))

    def test_arbitrary_extra_fields_are_not_dumped(self):
        self.result["private_note"] = "DO-NOT-DUMP-THIS"
        self.result["evidence"][0]["payload"] = "DO-NOT-DUMP-THIS"
        self.assertNotIn("DO-NOT-DUMP-THIS", render_markdown(self.result))

    def test_method_metadata_cannot_break_markdown_table_or_add_raw_html(self):
        rows = events()
        method = 'odd|[link](https://invalid.example/)`*_<img src="x">&entity;'
        rows[3][1]["method"] = method
        text = render_markdown(audit_transcript(capture(rows)))
        self.assertIn("odd\\|\\[link\\]\\(https://invalid\\.example/\\)", text)
        self.assertNotIn('<img src="x">', text)
        self.assertIn("&lt;img src=&quot;x&quot;&gt;&amp;entity;", text)
        self.assertNotIn("[link](https://invalid.example/)", text)

    def test_newline_terminal_and_bidi_controls_are_visible(self):
        rows = events()
        rows[3][1]["method"] = "demo\r\n\t\x1b[31m\u202e\u200b\u2028"
        text = render_markdown(audit_transcript(capture(rows)))
        for char in ("\r", "\t", "\x1b", "\u202e", "\u200b", "\u2028"):
            self.assertNotIn(char, text)
        for digits in ("000d", "000a", "0009", "001b", "202e", "200b", "2028"):
            self.assertIn("u" + digits, text)
        self.assertEqual(sum(line.startswith("| demo") for line in text.splitlines()), 1)

    def test_unicode_names_remain_readable(self):
        rows = events()
        rows[3][1]["method"] = "outil/évidence/日本語"
        self.assertIn("outil/évidence/日本語", render_markdown(audit_transcript(capture(rows))))

    def test_methods_are_sorted_even_when_input_dictionary_is_reordered(self):
        self.result["method_counts"] = dict(reversed(list(self.result["method_counts"].items())))
        text = render_markdown(self.result).split("## Method counts", 1)[1].split("## Event index", 1)[0]
        self.assertLess(text.index("| initialize |"), text.index("| notifications/initialized |"))
        self.assertLess(text.index("| notifications/initialized |"), text.index("| tools/list |"))

    def test_explicit_scope_and_privacy_limits_are_present(self):
        text = render_markdown(self.result)
        self.assertIn("not endpoint identity", text)
        self.assertIn("not a verification input", text)
        self.assertIn("not an anonymization guarantee", text)
        self.assertIn("executes no captured tool", text)

    def test_unknown_schema_and_nonobject_are_rejected(self):
        for value in ({"schema": "future/v9"}, [], None, "{}"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_markdown(value)

    def test_unknown_audit_status_is_rejected(self):
        self.result["status"] = "DEPLOYED"
        with self.assertRaisesRegex(ValueError, "unsupported audit status"):
            render_markdown(self.result)


class VerificationReportTests(unittest.TestCase):
    def test_match_carries_all_three_identities(self):
        source = EXAMPLE.read_bytes()
        saved = canonical_json_bytes(audit_transcript(source)) + b"\n"
        result = verify_receipt(source, saved)
        text = render_markdown(result)
        self.assertIn("**Receipt verification: MATCH.**", text)
        for field in ("source_sha256", "receipt_file_sha256", "verification_sha256"):
            self.assertIn(result[field], text)
        self.assertIn("No receipt-mismatch diagnostics", text)

    def test_valid_hold_receipt_is_match_not_capture_pass(self):
        source = b""
        receipt = audit_transcript(source)
        self.assertEqual(receipt["status"], "HOLD")
        result = verify_receipt(source, canonical_json_bytes(receipt))
        self.assertTrue(result["valid"])
        text = render_markdown(result)
        self.assertIn("**Receipt verification: MATCH.**", text)
        self.assertNotIn("**Capture audit: PASS.**", text)
        self.assertIn("A matching receipt can describe a HOLD capture.", text)

    def test_modified_false_pass_is_mismatch_without_copying_supplied_fields(self):
        source = b""
        saved = audit_transcript(source)
        saved["status"] = "PASS"
        saved["extra"] = "FICTIONAL-UNTRUSTED-PAYLOAD"
        result = verify_receipt(source, canonical_json_bytes(saved))
        text = render_markdown(result)
        self.assertFalse(result["valid"])
        self.assertIn("**Receipt verification: MISMATCH.**", text)
        self.assertIn("RECEIPT\\_RECOMPUTE\\_MISMATCH", text)
        self.assertIn("RECEIPT\\_SELF\\_HASH\\_MISMATCH", text)
        self.assertNotIn("FICTIONAL-UNTRUSTED-PAYLOAD", text)

    def test_resealed_false_pass_still_fails_exact_recomputation(self):
        source = b""
        saved = audit_transcript(source)
        saved["status"] = "PASS"
        saved.pop("receipt_sha256")
        saved["receipt_sha256"] = hashlib.sha256(canonical_json_bytes(saved)).hexdigest()
        result = verify_receipt(source, canonical_json_bytes(saved))
        self.assertFalse(result["valid"])
        self.assertEqual(result["reasons"], ["RECEIPT_RECOMPUTE_MISMATCH"])
        self.assertIn("**Receipt verification: MISMATCH.**", render_markdown(result))

    def test_invalid_saved_json_reports_literal_reason_without_payload(self):
        result = verify_receipt(EXAMPLE.read_bytes(), b"FICTIONAL-INVALID-RECEIPT")
        text = render_markdown(result)
        self.assertIn("INVALID\\_RECEIPT\\_JSON", text)
        self.assertNotIn("FICTIONAL-INVALID-RECEIPT", text)

    def test_cross_capture_receipt_does_not_match(self):
        source = EXAMPLE.read_bytes()
        result = verify_receipt(source + b"\n", canonical_json_bytes(audit_transcript(source)))
        self.assertFalse(result["valid"])
        self.assertIn("MISMATCH", render_markdown(result))

    def test_integer_alias_does_not_render_as_boolean_verdict(self):
        result = verify_receipt(b"", canonical_json_bytes(audit_transcript(b"")))
        for value in (1, 0, "true", None):
            result["valid"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_markdown(result)

    def test_verification_result_remains_unchanged(self):
        result = verify_receipt(b"", canonical_json_bytes(audit_transcript(b"")))
        before = copy.deepcopy(result)
        render_markdown(result)
        self.assertEqual(before, result)


class ReportCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = EXAMPLE.read_bytes()
        self.path = self.root / "capture.jsonl"
        self.path.write_bytes(self.source)
        self.saved = self.root / "receipt.json"
        self.saved.write_bytes(canonical_json_bytes(audit_transcript(self.source)) + b"\n")

    def run_cli(self, *args):
        command = [sys.executable]
        if sys.flags.optimize:
            command.append("-O")
        command += ["-m", "tools.mcp_transcript_audit.cli", *map(str, args)]
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=20, check=False)

    def test_default_and_explicit_json_are_byte_identical(self):
        expected = self.saved.read_bytes()
        for extra in ((), ("--format", "json")):
            result = self.run_cli("audit", self.path, *extra)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)

    def test_markdown_stdout_matches_library_and_preserves_capture(self):
        result = self.run_cli("audit", self.path, "--format", "markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, render_markdown(audit_transcript(self.source)).encode() + b"\n")
        self.assertEqual(self.path.read_bytes(), self.source)
        self.assertFalse(result.stdout.endswith(b"\n\n"))

    def test_output_file_matches_stdout_and_does_not_also_print(self):
        output = self.root / "report.md"
        result = self.run_cli("audit", self.path, "--format", "markdown", "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(output.read_bytes(), self.run_cli("audit", self.path, "--format", "markdown").stdout)

    def test_hold_audit_keeps_exit_three_in_both_formats(self):
        self.path.write_bytes(b"")
        for fmt in ("json", "markdown"):
            result = self.run_cli("audit", self.path, "--format", fmt)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn(b"HOLD", result.stdout)

    def test_verification_json_default_remains_exact(self):
        result = self.run_cli("verify", self.path, self.saved)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, canonical_json_bytes(verify_receipt(self.source, self.saved.read_bytes())) + b"\n")

    def test_verification_match_markdown_keeps_exit_zero(self):
        result = self.run_cli("verify", self.path, self.saved, "--format", "markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"**Receipt verification: MATCH.**", result.stdout)

    def test_matching_hold_receipt_keeps_exit_zero(self):
        self.path.write_bytes(b"")
        self.saved.write_bytes(canonical_json_bytes(audit_transcript(b"")))
        result = self.run_cli("verify", self.path, self.saved, "--format", "markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"A matching receipt can describe a HOLD capture.", result.stdout)

    def test_mismatched_receipt_keeps_exit_three(self):
        self.path.write_bytes(self.source + b"\n")
        result = self.run_cli("verify", self.path, self.saved, "--format", "markdown")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn(b"MISMATCH", result.stdout)

    def test_saved_markdown_is_not_accepted_as_receipt(self):
        self.saved.write_bytes(self.run_cli("audit", self.path, "--format", "markdown").stdout)
        result = self.run_cli("verify", self.path, self.saved, "--format", "markdown")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn(b"INVALID\\_RECEIPT\\_JSON", result.stdout)

    def test_existing_report_is_not_overwritten(self):
        output = self.root / "report.md"
        output.write_bytes(b"PRESERVE-EXISTING")
        result = self.run_cli("audit", self.path, "--format", "markdown", "-o", output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_bytes(), b"PRESERVE-EXISTING")
        self.assertEqual(result.stdout, b"")

    def test_output_equal_to_capture_is_not_overwritten(self):
        result = self.run_cli("audit", self.path, "--format", "markdown", "-o", self.path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_bytes(), self.source)

    def test_verification_cannot_overwrite_saved_receipt(self):
        before = self.saved.read_bytes()
        result = self.run_cli("verify", self.path, self.saved, "--format", "markdown", "-o", self.saved)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.saved.read_bytes(), before)

    def test_missing_input_keeps_exit_two_without_output(self):
        output = self.root / "absent.md"
        result = self.run_cli("audit", self.root / "missing.jsonl", "--format", "markdown", "-o", output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())
        self.assertNotIn(b"Traceback", result.stderr)

    def test_invalid_format_keeps_argparse_exit_two_without_output(self):
        output = self.root / "report.md"
        result = self.run_cli("audit", self.path, "--format", "yaml", "-o", output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_help_exposes_both_formats_on_both_commands(self):
        for command in ("audit", "verify"):
            result = self.run_cli(command, "--help")
            self.assertEqual(result.returncode, 0)
            self.assertIn(b"--format {json,markdown}", result.stdout)


if __name__ == "__main__":
    unittest.main()
