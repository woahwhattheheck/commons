"""Exact canonical-reader composition tests for the offline context inspector."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from integrations.command_center import slack_context_inspector as inspector

BASE = Path(__file__).resolve().parent
MODULE = "integrations.command_center.slack_context_inspector"


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")


def inspect(scenario="complete", edit=None):
    value = inspector.example_capture(scenario)
    if edit:
        edit(value)
    return inspector.inspect_capture(encoded(value))


class CanonicalReaderComposition(unittest.TestCase):
    def test_complete_two_pages_exposes_earlier_claim(self):
        report = inspect()
        self.assertTrue(report["capture_inspection_complete"])
        self.assertEqual([inspector.ROOT, inspector.EARLIER, inspector.CHILD],
                         [row["ts"] for row in report["observed_messages"]])
        self.assertIn("already took", report["observed_messages"][1]["text"])
        self.assertEqual(2, report["coverage"]["pages_read"])
        self.assertFalse(report["claim_authority"])
        self.assertFalse(report["provider_write_authority"])
        self.assertEqual([], report["actions_performed"])
        self.assertEqual("NOT_CHECKED", report["live_freshness"])

    def test_nine_distinct_scenario_outcomes(self):
        expected = {"complete": (True, None), "page_limit": (False, "page_limit"),
                    "missing_page": (False, "read_failed"), "wrong_child": (False, "read_failed"),
                    "unknown_root": (False, "root_metadata_missing"),
                    "conflicting_root": (False, "root_metadata_conflict"),
                    "count_mismatch": (False, "reply_evidence_mismatch"),
                    "changed_message": (False, "thread_evidence_changed"),
                    "unused_page": (False, None)}
        for scenario, (complete, reason) in expected.items():
            with self.subTest(scenario=scenario):
                report = inspect(scenario)
                self.assertEqual(complete, report["capture_inspection_complete"])
                self.assertEqual(reason, report["coverage"]["reason"])
                self.assertFalse(report["claim_authority"])

    def test_page_cap_retains_prior_messages_and_cursor(self):
        report = inspect("page_limit")
        self.assertEqual(2, len(report["observed_messages"]))
        self.assertEqual(1, report["reads_unused"])
        self.assertEqual("fixture-page-2", report["continuation_request"]["payload"]["cursor"])
        self.assertNotIn("cursor", report["refresh_request"]["payload"])

    def test_missing_response_retains_requested_cursor(self):
        report = inspect("missing_page")
        self.assertEqual(1, report["reads_consumed"])
        self.assertEqual(2, len(report["requested_reads"]))
        self.assertEqual("capture_response_missing", report["capture_diagnostics"][0]["code"])
        self.assertEqual(report["requested_reads"][-1], report["continuation_request"])

    def test_wrong_child_empty_view_is_never_complete(self):
        report = inspect("wrong_child")
        self.assertEqual(0, report["reads_consumed"])
        self.assertEqual([], report["observed_messages"])
        self.assertEqual(inspector.CHILD, report["selected_message"]["ts"])
        self.assertEqual(inspector.ROOT, report["requested_reads"][0]["payload"]["ts"])
        self.assertEqual("capture_request_mismatch", report["capture_diagnostics"][0]["code"])

    def test_unresolved_metadata_makes_zero_callback_attempts(self):
        for scenario in ("unknown_root", "conflicting_root"):
            with self.subTest(scenario=scenario):
                report = inspect(scenario)
                self.assertEqual([], report["requested_reads"])
                self.assertIsNone(report["refresh_request"])
                self.assertIsNone(report["continuation_request"])

    def test_root_count_zero_is_coverage_not_vacancy(self):
        value = inspector.example_capture()
        root = {"ts": inspector.ROOT, "reply_count": 0, "text": "FICTION: completed order"}
        value["selected_message"] = root
        value["reads"] = [{**value["reads"][0], "response": {"ok": True, "messages": [root]}}]
        report = inspector.inspect_capture(encoded(value))
        self.assertTrue(report["capture_inspection_complete"])
        self.assertFalse(report["claim_authority"])
        self.assertNotIn("claimant", report)

    def test_unused_capture_evidence_is_not_hidden_by_reader_success(self):
        report = inspect("unused_page")
        self.assertTrue(report["coverage"]["complete"])
        self.assertFalse(report["capture_inspection_complete"])
        self.assertEqual(1, report["reads_unused"])

    def test_exact_request_binding_including_bool_integer_distinction(self):
        variations = ({"ts": inspector.CHILD}, {"channel": "COTHER"}, {"limit": True},
                      {"limit": 2.0}, {"cursor": "unexpected"}, {"limit": 1})
        for delta in variations:
            with self.subTest(delta=delta):
                value = inspector.example_capture()
                value["reads"][0]["payload"].update(delta)
                report = inspector.inspect_capture(encoded(value))
                self.assertFalse(report["capture_inspection_complete"])
                self.assertEqual(0, report["reads_consumed"])

    def test_cursor_mismatch_does_not_consume_wrong_page(self):
        value = inspector.example_capture()
        value["reads"][1]["payload"]["cursor"] = "wrong-cursor"
        report = inspector.inspect_capture(encoded(value))
        self.assertEqual(1, report["reads_consumed"])
        self.assertEqual(2, len(report["observed_messages"]))
        self.assertFalse(report["capture_inspection_complete"])

    def test_provider_error_is_sanitized_and_partial_evidence_remains(self):
        value = inspector.example_capture()
        value["reads"][1]["response"] = {"ok": False, "error": "PRIVATE ERROR VALUE"}
        report = inspector.inspect_capture(encoded(value))
        self.assertEqual(2, len(report["observed_messages"]))
        self.assertNotIn("PRIVATE ERROR VALUE", json.dumps(report))
        self.assertFalse(report["capture_inspection_complete"])

    def test_known_provider_error_remains_specific(self):
        value = inspector.example_capture()
        value["reads"][0]["response"] = {"ok": False, "error": "not_in_channel"}
        report = inspector.inspect_capture(encoded(value))
        self.assertEqual("not_in_channel", report["coverage"]["error"]["code"])
        self.assertFalse(report["capture_inspection_complete"])

    def test_malformed_page_is_not_counted_as_observed(self):
        for messages in ({}, [None], [{"ts": False}], [{"ts": inspector.ROOT, "reply_count": -1}]):
            with self.subTest(messages=messages):
                value = inspector.example_capture()
                value["reads"][1]["response"]["messages"] = messages
                report = inspector.inspect_capture(encoded(value))
                self.assertFalse(report["capture_inspection_complete"])
                self.assertEqual(1, report["coverage"]["pages_read"])
                self.assertEqual(2, len(report["observed_messages"]))

    def test_identity_mutation_matrix_never_completes(self):
        variants = ("COTHER", inspector.CHILD, "1700000300.000001", "", True, 0, None)
        for row_index in range(2):
            for key in ("channel", "ts", "limit", "cursor"):
                for value in variants:
                    with self.subTest(row=row_index, key=key, value=value):
                        capture = inspector.example_capture()
                        capture["reads"][row_index]["payload"][key] = value
                        report = inspector.inspect_capture(encoded(capture))
                        self.assertFalse(report["capture_inspection_complete"])

    def test_read_budget_remains_bounded(self):
        for cap in range(1, 11):
            capture = inspector.example_capture()
            capture["max_pages"] = cap
            report = inspector.inspect_capture(encoded(capture))
            self.assertLessEqual(len(report["requested_reads"]), cap)
            self.assertEqual(cap >= 2, report["capture_inspection_complete"])

    def test_source_bytes_and_selected_record_are_preserved(self):
        value = inspector.example_capture()
        original = copy.deepcopy(value)
        raw = b" \r\n" + encoded(value) + b"\r\n"
        report = inspector.inspect_capture(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), report["capture_sha256"])
        self.assertEqual(original, value)
        self.assertEqual(value["selected_message"], report["selected_message"])

    def test_private_classification_and_declared_time_not_promoted(self):
        value = inspector.example_capture()
        value["classification"] = "PRIVATE_CAPTURE"
        value["captured_at"] = "2099-01-01T00:00:00Z"
        report = inspector.inspect_capture(encoded(value))
        self.assertEqual("PRIVATE_CAPTURE", report["classification"])
        self.assertEqual(value["captured_at"], report["capture_declared_at"])
        self.assertEqual("NOT_CHECKED", report["live_freshness"])

    def test_text_render_escapes_control_sequences_and_keeps_long_text(self):
        value = inspector.example_capture()
        text = "\x1b[2J\x00\n" + "Ω|长" * 1000
        value["reads"][0]["response"]["messages"][1]["text"] = text
        report = inspector.inspect_capture(encoded(value))
        rendered = inspector.render_text(report)
        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\x00", rendered)
        self.assertIn(json.dumps(text), rendered)
        self.assertEqual(text, report["observed_messages"][1]["text"])


class InputContract(unittest.TestCase):
    def assert_invalid(self, raw):
        with self.assertRaises(inspector.CaptureError):
            inspector.inspect_capture(raw)

    def test_duplicate_keys_rejected_at_every_depth(self):
        for raw in (b'{"schema":1,"schema":2}', b'{"reads":[{"payload":{"limit":2,"limit":3}}]}'):
            self.assert_invalid(raw)

    def test_nonfinite_literals_and_overflow_rejected(self):
        for value in (b"NaN", b"Infinity", b"-Infinity", b"1e9999"):
            self.assert_invalid(b'{"x":' + value + b'}')

    def test_utf8_and_unicode_scalar_failures(self):
        for raw in (b'\xff', br'"\ud800"', br'"\udfff"', b'\xef\xbb\xbf{}'):
            self.assert_invalid(raw)

    def test_depth_and_size_limits(self):
        self.assert_invalid(b'[' * 80 + b'0' + b']' * 80)
        with patch.object(inspector, "MAX_BYTES", 5):
            self.assert_invalid(b'123456')

    def test_exact_top_level_schema(self):
        self.assert_invalid(b'[]')
        for field in inspector.example_capture():
            value = inspector.example_capture()
            del value[field]
            with self.subTest(field=field):
                self.assert_invalid(encoded(value))
        value = inspector.example_capture()
        value["claim_authority"] = True
        self.assert_invalid(encoded(value))

    def test_classification_limits_and_time_shapes(self):
        changes = [("classification", "PUBLIC_VERIFIED"), ("captured_at", "2026-02-30T00:00:00Z"),
                   ("captured_at", "now"), ("captured_at", None), ("channel_id", "bad"),
                   ("selected_message", []), ("selected_message", {"ts": False})]
        changes += [(field, value) for field in ("page_size", "max_pages")
                    for value in (True, False, 0, -1, 1.0, "2", None, 101)]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                capture = inspector.example_capture()
                capture[field] = value
                self.assert_invalid(encoded(capture))

    def test_response_envelope_and_read_count(self):
        values = ({}, None, [None], [{"method": "chat.postMessage", "payload": {}, "response": {}}],
                  [{"method": "conversations.replies", "payload": {}, "response": []}])
        for reads in values:
            value = inspector.example_capture()
            value["reads"] = reads
            with self.subTest(reads=reads):
                self.assert_invalid(encoded(value))
        value = inspector.example_capture()
        value["reads"] *= 6
        self.assert_invalid(encoded(value))


class CommandAndPublication(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.capture = self.path / "capture.json"
        self.capture.write_bytes(encoded(inspector.example_capture()))

    def run_cli(self, *args):
        command = [sys.executable]
        if sys.flags.optimize:
            command.append("-" + "O" * sys.flags.optimize)
        return subprocess.run([*command, "-B", "-m", MODULE, *map(str, args)], cwd=BASE,
                              capture_output=True, timeout=20)

    def test_real_cli_complete_json_and_text(self):
        result = self.run_cli("inspect", self.capture, "--format", "json")
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["capture_inspection_complete"])
        result = self.run_cli("inspect", self.capture)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(b"Rowan already took", result.stdout)

    def test_real_cli_all_scenarios(self):
        for scenario in inspector.SCENARIOS:
            with self.subTest(scenario=scenario):
                path = self.path / (scenario + ".json")
                made = self.run_cli("example", "--scenario", scenario, "--output", path)
                self.assertEqual(0, made.returncode, made.stderr)
                result = self.run_cli("inspect", path, "--format", "json")
                self.assertEqual(0 if scenario == "complete" else 1, result.returncode, result.stderr)
                self.assertEqual(inspector.REPORT_SCHEMA, json.loads(result.stdout)["schema"])

    def test_invalid_input_does_not_publish_or_replace_report(self):
        self.capture.write_bytes(b'{"x":1,"x":2}')
        for existing in (False, True):
            target = self.path / str(existing)
            if existing:
                target.write_bytes(b"prior report")
            result = self.run_cli("inspect", self.capture, "--output", target)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b"", result.stdout)
            if existing:
                self.assertEqual(b"prior report", target.read_bytes())
            else:
                self.assertFalse(target.exists())

    def test_cli_missing_file_diagnostic_omits_private_path(self):
        result = self.run_cli("inspect", self.path / "PRIVATE_NAME.json")
        self.assertEqual(2, result.returncode)
        self.assertNotIn(b"PRIVATE_NAME", result.stderr)
        self.assertEqual("capture_io_error", json.loads(result.stderr)["error"])

    def test_successful_create_only_output(self):
        target = self.path / "report.json"
        result = self.run_cli("inspect", self.capture, "--format", "json", "--output", target)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b"", result.stdout)
        self.assertTrue(json.loads(target.read_bytes())["capture_inspection_complete"])
        self.assertEqual([], list(self.path.glob(".slack-context-*")))

    def test_prior_output_is_preserved(self):
        target = self.path / "report.json"
        target.write_bytes(b"prior report")
        result = self.run_cli("inspect", self.capture, "--output", target)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"prior report", target.read_bytes())
        self.assertEqual([], list(self.path.glob(".slack-context-*")))

    def test_input_aliases_are_preserved(self):
        for kind in ("direct", "hardlink", "symlink"):
            with self.subTest(kind=kind):
                target = self.capture if kind == "direct" else self.path / kind
                if kind == "hardlink":
                    os.link(self.capture, target)
                elif kind == "symlink":
                    target.symlink_to(self.capture)
                before = self.capture.read_bytes()
                result = self.run_cli("inspect", self.capture, "--output", target)
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertEqual(before, self.capture.read_bytes())
                self.assertEqual(before, target.read_bytes())

    def test_dangling_symlink_and_directory_are_preserved(self):
        target = self.path / "link"
        target.symlink_to(self.path / "absent")
        for path in (target, self.path):
            result = self.run_cli("inspect", self.capture, "--output", path)
            self.assertEqual(2, result.returncode)
        self.assertTrue(target.is_symlink())
        self.assertFalse((self.path / "absent").exists())

    def test_failed_stage_sync_or_link_has_no_new_report(self):
        for action in ("fsync", "link"):
            with self.subTest(action=action):
                target = self.path / action
                with patch.object(inspector.os, action, side_effect=OSError("injected failure")):
                    with self.assertRaises(OSError):
                        inspector._publish_new(target, b"complete bytes")
                self.assertFalse(target.exists())
                self.assertEqual([], list(self.path.glob(".slack-context-*")))

    def test_example_refuses_existing_name(self):
        before = self.capture.read_bytes()
        result = self.run_cli("example", "--output", self.capture)
        self.assertEqual(2, result.returncode)
        self.assertEqual(before, self.capture.read_bytes())

    def test_two_writers_publish_exactly_one_complete_file(self):
        target = self.path / "competing.json"
        python = [sys.executable] + (["-" + "O" * sys.flags.optimize] if sys.flags.optimize else [])
        processes = [subprocess.Popen([*python, "-B", "-m", MODULE, "example", "--scenario", scenario,
                      "--output", str(target)], cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for scenario in ("complete", "unknown_root")]
        outcomes = [process.communicate(timeout=20) for process in processes]
        self.assertEqual([0, 2], sorted(process.returncode for process in processes), outcomes)
        loaded = inspector.decode_capture(target.read_bytes())
        self.assertIn(len(loaded["reads"]), (0, 2))
        self.assertEqual([], list(self.path.glob(".slack-context-*")))

    def test_no_created_directory_on_missing_output_parent(self):
        target = self.path / "missing" / "report.json"
        result = self.run_cli("inspect", self.capture, "--output", target)
        self.assertEqual(2, result.returncode)
        self.assertFalse(target.parent.exists())


if __name__ == "__main__":
    unittest.main()
