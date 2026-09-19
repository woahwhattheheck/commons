"""Original app -> actual loopback HTTP -> recording adapter conformance.

The adapter is a declared spy, not the parent assessment compiler. Existing
compiler/browser acceptance remains a separate suite. No external HTTP is used.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from http.client import HTTPConnection

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get("UIOWA_INTAKE_SOURCE", str(HERE))).resolve()
SPEC = importlib.util.spec_from_file_location("_uiowa_intake_transport_server", SOURCE / "server.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the actual workbench server")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def synthetic_report() -> dict:
    return {
        "schema": "SYNTHETIC_TRANSPORT_FIXTURE_NOT_COMPILER_OUTPUT",
        "synthetic_demo": True,
        "mode": "UNTRUSTED_INSPECTION",
        "receipt_sha256": "a" * 64,
        "aggregate_state": "HOLD_TRUSTED_AUTHORITY_REQUIRED",
        "trust": {"current_evidence_review_authority": False,
                  "authority_root_supplied_out_of_band": False},
        "commercial_terms": {"status": "PROPOSED_NOT_ACCEPTED"},
        "assessment_matrix": [
            {"group": group, "dimension": dimension, "status": "HOLD_MISSING_EVIDENCE"}
            for group in ("ESS", "RIS", "IAM")
            for dimension in ("software_development", "security", "deployment", "ai_readiness")
        ],
    }


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, dict]] = []
        self.reject = False

    def inspect(self, candidate, authority):
        self.calls.append((candidate, authority))
        if self.reject:
            raise server.WorkbenchError("synthetic compiler rejection")
        return synthetic_report()


class IntakeTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if cls.node is None:
            raise RuntimeError("Node.js with fetch and Blob is required; intake tests were not run")
        cls.adapter = RecordingAdapter()
        cls.httpd = server.create_server(port=0, adapter=cls.adapter, static_root=SOURCE)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.adapter.calls.clear()
        self.adapter.reject = False

    def app(self, candidate='{}', authority='{}', **options):
        def encode(value):
            raw = value.encode("utf-8") if isinstance(value, str) else value
            return base64.b64encode(raw).decode("ascii")
        config = {"origin": self.origin, "candidate": encode(candidate), "authority": encode(authority), **options}
        proc = subprocess.run(
            [self.node, str(HERE / "intake_transport_harness.js"), str(SOURCE / "app.js")],
            input=json.dumps(config), capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def accepted(self, result):
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertEqual(result["error"], "")
        self.assertEqual(result["state"]["receipt"], "a" * 64)
        self.assertEqual(result["state"]["cells"], 12)
        self.assertEqual(result["state"]["notes"], [])
        self.assertFalse(result["disabled"]["inspectBtn"])
        self.assertFalse(result["disabled"]["exportBtn"])

    def rejected(self, result, message, *, posts=1):
        self.assertEqual(self.adapter.calls, [], "rejected data reached the compiler adapter")
        self.assertIn(message, result["error"])
        self.assertEqual(len(result["requests"]), posts)
        self.assertIsNone(result["state"]["receipt"])
        self.assertEqual(result["state"]["notes"], [])
        self.assertFalse(result["disabled"]["inspectBtn"])
        for button in ("exportBtn", "markdownBtn", "importDraftBtn"):
            self.assertTrue(result["disabled"][button], button)

    def post(self, body):
        conn = HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        try:
            conn.request("POST", "/api/inspect", body=body, headers={
                "Origin": self.origin, "Content-Type": "application/json",
            })
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_preserves_original_candidate_text_and_integer(self):
        candidate = ' \n{ "n": 9007199254740993, "note": "café 🚀", "scientific": 1.2500e+2 }\t'
        result = self.app(candidate)
        self.accepted(result)
        self.assertEqual(result["requests"][0]["body"], '{"candidate":' + candidate + ',"authority":{}}')
        self.assertEqual(self.adapter.calls[0][0]["n"], 9007199254740993)
        self.assertEqual(self.adapter.calls[0][0]["note"], "café 🚀")
        self.assertEqual(result["requests"][0]["credentials"], "same-origin")
        self.assertEqual(result["requests"][0]["cache"], "no-store")

    def test_preserves_original_authority_text(self):
        authority = '\r\n{ "n" : 9007199254740993, "label":"fictional" }\r\n'
        result = self.app('{}', authority)
        self.accepted(result)
        self.assertEqual(result["requests"][0]["body"], '{"candidate":{},"authority":' + authority + '}')
        self.assertEqual(self.adapter.calls[0][1]["n"], 9007199254740993)

    def test_preserves_decimal_lexeme_without_claiming_decimal_arithmetic(self):
        token = '0.123456789012345678901234567890123456789'
        result = self.app('{"ratio":' + token + '}')
        self.accepted(result)
        self.assertIn(token, result["requests"][0]["body"])
        self.assertEqual(self.adapter.calls[0][0]["ratio"], float(token))
        self.assertIsInstance(self.adapter.calls[0][0]["ratio"], float)

    def test_duplicate_candidate_members_reach_strict_decoder(self):
        result = self.app('{"count":1,"count":2}')
        self.rejected(result, 'duplicate JSON key')
        self.assertIn('"count":1,"count":2', result["requests"][0]["body"])

    def test_duplicate_authority_members_reach_strict_decoder(self):
        self.rejected(self.app('{}', '{"revision":1,"revision":2}'), 'duplicate JSON key')

    def test_escaped_equivalent_member_names_are_duplicates(self):
        self.rejected(self.app(r'{"a":1,"\u0061":2}'), 'duplicate JSON key')

    def test_nested_duplicate_members_are_not_laundered(self):
        self.rejected(self.app('{"items":[{"state":"old","state":"new"}]}'), 'duplicate JSON key')

    def test_repeated_names_in_different_objects_are_valid(self):
        self.accepted(self.app('{"a":{"x":1},"b":{"x":2}}'))
        self.assertEqual(self.adapter.calls[0][0], {"a": {"x": 1}, "b": {"x": 2}})

    def test_integer_larger_than_binary64_range_stays_an_integer(self):
        digits = '9' * 350
        self.accepted(self.app('{"n":' + digits + '}'))
        self.assertEqual(self.adapter.calls[0][0]["n"], int(digits))

    def test_finite_overflow_is_rejected_not_changed_to_null(self):
        for token in ('1e400', '-1e400'):
            with self.subTest(token=token):
                self.adapter.calls.clear()
                self.rejected(self.app('{"n":' + token + '}'), 'overflows')

    def test_nonzero_underflow_is_rejected_not_changed_to_zero(self):
        for token in ('1e-400', '-1e-400', '0.000000001e-999999'):
            with self.subTest(token=token):
                self.adapter.calls.clear()
                self.rejected(self.app('{"n":' + token + '}'), 'underflows')

    def test_real_zero_and_smallest_nonzero_float_are_not_rejected(self):
        result = self.app('{"zero":0,"negative_zero":-0.0,"tiny":5e-324,"huge_exponent_zero":0e999999}')
        self.accepted(result)
        self.assertEqual(self.adapter.calls[0][0]["zero"], 0)
        self.assertGreater(self.adapter.calls[0][0]["tiny"], 0)
        self.assertEqual(self.adapter.calls[0][0]["huge_exponent_zero"], 0)

    def test_non_json_numeric_constants_rejected_in_browser(self):
        for token in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(token=token):
                self.rejected(self.app('{"n":' + token + '}'), 'not valid JSON', posts=0)

    def test_invalid_utf8_candidate_is_not_replacement_decoded(self):
        self.rejected(self.app(b'{"note":"\xff"}'), 'UTF-8', posts=0)

    def test_invalid_utf8_authority_is_not_replacement_decoded(self):
        self.rejected(self.app('{}', b'{"note":"\xc3("}'), 'UTF-8', posts=0)

    def test_real_unicode_replacement_character_remains_valid(self):
        self.accepted(self.app('{"note":"�"}'))
        self.assertEqual(self.adapter.calls[0][0]["note"], '�')

    def test_lone_surrogate_values_rejected_at_http_boundary(self):
        for text in (r'{"note":"\ud800"}', r'{"a":["\udfff"]}'):
            with self.subTest(text=text):
                self.adapter.calls.clear()
                self.rejected(self.app(text), 'Unicode scalar')

    def test_lone_surrogate_keys_rejected_with_encodable_diagnostic(self):
        self.rejected(self.app(r'{"\ud800":1}'), 'Unicode scalar')

    def test_duplicate_surrogate_keys_have_encodable_diagnostic(self):
        self.rejected(self.app(r'{"\ud800":1,"\ud800":2}'), 'duplicate JSON key')

    def test_valid_surrogate_pair_escape_is_preserved(self):
        result = self.app(r'{"note":"\ud83d\ude80"}')
        self.accepted(result)
        self.assertEqual(self.adapter.calls[0][0]["note"], '🚀')
        self.assertIn(r'\ud83d\ude80', result["requests"][0]["body"])

    def test_complete_object_required_no_envelope_breakout(self):
        for text in ('', 'null', '[]', 'true', '42', '{}{}', '{} , "authority": {}', '{"x":1,}'):
            with self.subTest(text=text):
                result = self.app(text)
                self.assertEqual(result["requests"], [])
                self.assertEqual(self.adapter.calls, [])
                self.assertTrue(result["error"])
                self.assertIsNone(result["state"]["receipt"])

    def test_bom_is_not_silently_removed(self):
        self.rejected(self.app(b'\xef\xbb\xbf{}'), 'not valid JSON', posts=0)

    def test_size_metadata_limit_remains(self):
        self.rejected(self.app('{}', candidate_options={"declared_size": 1024 * 1024 + 1}), '1 MiB', posts=0)

    def test_actual_read_limit_cannot_be_bypassed_by_small_metadata(self):
        self.rejected(self.app('{}' + ' ' * (1024 * 1024), candidate_options={"declared_size": 2}), '1 MiB', posts=0)

    def test_combined_wire_limit_accounts_for_original_text_and_envelope(self):
        text = '{}' + ' ' * (1024 * 1024 - 2)
        self.rejected(self.app(text, text), 'Combined evidence', posts=0)

    def test_exact_combined_limit_succeeds(self):
        envelope = len('{"candidate":,"authority":}')
        candidate = '{}' + ' ' * (1024 * 1024 - 2)
        authority = '{}' + ' ' * (1024 * 1024 - envelope - 2)
        result = self.app(candidate, authority)
        self.accepted(result)
        self.assertEqual(len(result["requests"][0]["body"].encode()), 2 * 1024 * 1024)

    def test_missing_file_remains_controlled(self):
        self.rejected(self.app(omit_candidate=True), 'file is required', posts=0)

    def test_file_read_error_remains_controlled(self):
        self.rejected(self.app(candidate_options={"read_error": True}), 'read', posts=0)

    def test_quoted_structure_in_strings_cannot_change_envelope(self):
        value = {"note": '\"},\"authority\":{\"replaced\":true},\"candidate\":{\"', "line": "\r\n\t"}
        self.accepted(self.app(json.dumps(value)))
        self.assertEqual(self.adapter.calls[0], (value, {}))

    def test_direct_http_rejects_nonfinite_and_underflow_values(self):
        for token in ('NaN', 'Infinity', '-Infinity', '1e999', '-1e-999'):
            with self.subTest(token=token):
                self.adapter.calls.clear()
                status, payload = self.post(('{"candidate":{"n":' + token + '},"authority":{}}').encode())
                self.assertEqual(status, 400)
                self.assertIn('error', payload)
                self.assertEqual(self.adapter.calls, [])

    def test_direct_http_rejects_invalid_utf8(self):
        status, payload = self.post(b'{"candidate":{"n":"\xff"},"authority":{}}')
        self.assertEqual(status, 400)
        self.assertIn('UTF-8', payload['error'])
        self.assertEqual(self.adapter.calls, [])

    def test_decoder_resource_exception_has_controlled_json_error(self):
        # Decoder recursion behavior differs across supported Python builds. Inject
        # the exception explicitly; do not claim a guessed nesting limit was hit.
        original_loads = server.json.loads
        with patch.object(server.json, "loads", side_effect=RecursionError("synthetic decoder limit")):
            conn = HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
            try:
                conn.request("POST", "/api/inspect", body=b'{"candidate":{},"authority":{}}',
                             headers={"Origin": self.origin, "Content-Type": "application/json"})
                response = conn.getresponse()
                status, raw = response.status, response.read()
            finally:
                conn.close()
        payload = original_loads(raw)
        self.assertEqual(status, 400)
        self.assertIn('parsing limits', payload['error'])
        self.assertEqual(self.adapter.calls, [])

    def test_deep_scalar_validation_is_iterative(self):
        body = b'{"candidate":{"n":' + b'[' * 1500 + b'"\\ud800"' + b']' * 1500 + b'},"authority":{}}'
        status, payload = self.post(body)
        self.assertEqual(status, 400)
        # Builds whose decoder stops earlier may report their parsing boundary;
        # either case must be a controlled diagnostic before adapter invocation.
        self.assertTrue('Unicode scalar' in payload['error'] or 'parsing limits' in payload['error'])
        self.assertEqual(self.adapter.calls, [])

    def test_python_integer_limit_has_controlled_error(self):
        if sys.get_int_max_str_digits() == 0:
            # Exercise a representable integer instead of inventing an enabled limit.
            self.accepted(self.app('{"n":' + '9' * 4500 + '}'))
        else:
            digits = '9' * (sys.get_int_max_str_digits() + 1)
            self.rejected(self.app('{"n":' + digits + '}'), 'parsing limits')

    def test_compiler_rejection_does_not_restore_previous_review(self):
        self.adapter.reject = True
        result = self.app()
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertIn('synthetic compiler rejection', result['error'])
        self.assertIsNone(result['state']['receipt'])
        self.assertEqual(result['state']['notes'], [])
        self.assertTrue(result['disabled']['exportBtn'])

    def test_reset_during_file_read_prevents_post(self):
        result = self.app(race='reset_file')
        self.assertEqual(result['requests'], [])
        self.assertEqual(self.adapter.calls, [])
        self.assertIsNone(result['state']['receipt'])
        self.assertFalse(result['disabled']['inspectBtn'])

    def test_reset_during_response_prevents_reinstallation(self):
        result = self.app(race='reset_response')
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertIsNone(result['state']['receipt'])
        self.assertEqual(result['error'], '')
        self.assertTrue(result['disabled']['exportBtn'])

    def test_newer_demo_during_response_is_not_overwritten(self):
        result = self.app(race='demo_response')
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertEqual(result['state']['receipt'], 'd' * 64)
        self.assertTrue(result['state']['synthetic'])
        self.assertEqual(result['error'], '')

    def test_transport_failure_leaves_no_old_export(self):
        result = self.app(network_error=True)
        self.rejected(result, 'synthetic transport unavailable')


if __name__ == '__main__':
    unittest.main()
