from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.mcp_transcript_audit import (
    audit_transcript,
    canonical_json_bytes,
    encode_capture_event,
    verify_receipt,
)

CLIENT = "client_to_server"
SERVER = "server_to_client"
VERSION = "2025-11-25"


def initialize(request_id=1, version=VERSION):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "audit-test", "version": "1.0.0"},
        },
    }


def initialize_result(request_id=1, version=VERSION):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "audit-server", "version": "1.0.0"},
        },
    }


def initialized():
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def valid_events():
    return [
        (CLIENT, initialize()),
        (SERVER, initialize_result()),
        (CLIENT, initialized()),
        (CLIENT, {"jsonrpc": "2.0", "id": "tools-1", "method": "tools/list", "params": {}}),
        (SERVER, {"jsonrpc": "2.0", "id": "tools-1", "result": {"tools": []}}),
        (SERVER, {"jsonrpc": "2.0", "id": 77, "method": "ping", "params": {}}),
        (CLIENT, {"jsonrpc": "2.0", "id": 77, "result": {}}),
        (SERVER, {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info", "data": "secret-ish"}}),
    ]


def capture(events=None):
    events = valid_events() if events is None else events
    return b"\n".join(encode_capture_event(d, m) for d, m in events) + b"\n"


def raw_line(direction, payload_bytes):
    return canonical_json_bytes(
        {"direction": direction, "payload_base64": base64.b64encode(payload_bytes).decode("ascii")}
    )


def reason_codes(receipt):
    return {row["code"] for row in receipt["reasons"]}


class AuditHappyPathTests(unittest.TestCase):
    def test_valid_bidirectional_session_passes_and_is_deterministic(self):
        source = capture()
        first = audit_transcript(source)
        second = audit_transcript(source)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["negotiated_protocol_version"], VERSION)
        self.assertEqual(first["counts"], {
            "client_to_server": 4,
            "server_to_client": 4,
            "requests": 3,
            "responses": 3,
            "notifications": 2,
        })
        self.assertEqual(first["lifecycle"], {
            "initialize_request_line": 1,
            "initialize_response_line": 2,
            "initialized_notification_line": 3,
        })
        self.assertFalse(first["authority"]["network_access"])
        self.assertFalse(first["authority"]["tool_execution"])
        self.assertEqual(len(first["receipt_sha256"]), 64)

    def test_receipt_omits_params_results_error_data_and_raw_ids(self):
        events = valid_events()
        events.insert(4, (CLIENT, {
            "jsonrpc": "2.0",
            "id": "PRIVATE-ID-XYZ",
            "method": "tools/call",
            "params": {"name": "danger", "arguments": {"secret": "DO-NOT-COPY"}},
        }))
        events.insert(5, (SERVER, {
            "jsonrpc": "2.0",
            "id": "PRIVATE-ID-XYZ",
            "result": {"content": [{"text": "DO-NOT-COPY-RESULT"}]},
        }))
        receipt = audit_transcript(capture(events))
        self.assertEqual(receipt["status"], "PASS")
        rendered = canonical_json_bytes(receipt).decode("utf-8")
        for forbidden in ("PRIVATE-ID-XYZ", "DO-NOT-COPY", "DO-NOT-COPY-RESULT", "arguments"):
            self.assertNotIn(forbidden, rendered)
        self.assertIn("tools/call", rendered)

    def test_ping_can_interleave_before_initialize_response(self):
        events = [
            (CLIENT, initialize(1)),
            (CLIENT, {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}),
            (SERVER, {"jsonrpc": "2.0", "id": 2, "result": {}}),
            (SERVER, initialize_result(1)),
            (CLIENT, initialized()),
        ]
        self.assertEqual(audit_transcript(capture(events))["status"], "PASS")

    def test_server_logging_notification_can_precede_initialized(self):
        events = [
            (CLIENT, initialize()),
            (SERVER, initialize_result()),
            (SERVER, {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info", "data": "x"}}),
            (CLIENT, initialized()),
        ]
        self.assertEqual(audit_transcript(capture(events))["status"], "PASS")

    def test_preinit_logging_requires_params(self):
        events = [(CLIENT, initialize()), (SERVER, initialize_result()), (SERVER, {"jsonrpc": "2.0", "method": "notifications/message"}), (CLIENT, initialized())]
        self.assertIn("INVALID_LOGGING_NOTIFICATION", reason_codes(audit_transcript(capture(events))))

    def test_preinit_logging_requires_level(self):
        events = [(CLIENT, initialize()), (SERVER, initialize_result()), (SERVER, {"jsonrpc": "2.0", "method": "notifications/message", "params": {"data": "x"}}), (CLIENT, initialized())]
        self.assertIn("INVALID_LOGGING_NOTIFICATION", reason_codes(audit_transcript(capture(events))))

    def test_preinit_logging_rejects_unknown_level(self):
        events = [(CLIENT, initialize()), (SERVER, initialize_result()), (SERVER, {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "verbose", "data": "x"}}), (CLIENT, initialized())]
        self.assertIn("INVALID_LOGGING_NOTIFICATION", reason_codes(audit_transcript(capture(events))))

    def test_preinit_logging_requires_data_key(self):
        events = [(CLIENT, initialize()), (SERVER, initialize_result()), (SERVER, {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}}), (CLIENT, initialized())]
        self.assertIn("INVALID_LOGGING_NOTIFICATION", reason_codes(audit_transcript(capture(events))))


class LifecycleHostileTests(unittest.TestCase):
    def assert_holds(self, events, code):
        receipt = audit_transcript(capture(events))
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn(code, reason_codes(receipt))

    def test_initialize_must_be_first(self):
        self.assert_holds(
            [(CLIENT, {"jsonrpc": "2.0", "id": 9, "method": "ping", "params": {}})] + valid_events(),
            "INITIALIZE_NOT_FIRST_INTERACTION",
        )

    def test_required_version_must_be_requested(self):
        events = valid_events()
        events[0] = (CLIENT, initialize(version="2025-06-18"))
        self.assert_holds(events, "REQUIRED_PROTOCOL_VERSION_NOT_REQUESTED")

    def test_required_version_must_be_negotiated(self):
        events = valid_events()
        events[1] = (SERVER, initialize_result(version="2025-06-18"))
        self.assert_holds(events, "REQUIRED_PROTOCOL_VERSION_NOT_NEGOTIATED")
        self.assertIn("PROTOCOL_VERSION_MISMATCH", reason_codes(audit_transcript(capture(events))))

    def test_initialize_request_requires_capabilities_and_client_info(self):
        bad = initialize()
        del bad["params"]["clientInfo"]
        events = valid_events()
        events[0] = (CLIENT, bad)
        self.assert_holds(events, "INVALID_INITIALIZE_REQUEST")

    def test_initialize_client_info_requires_name_and_version_strings(self):
        bad = initialize()
        bad["params"]["clientInfo"] = {"name": "client"}
        events = valid_events()
        events[0] = (CLIENT, bad)
        self.assert_holds(events, "INVALID_INITIALIZE_REQUEST")

    def test_initialize_response_must_be_success_with_required_fields(self):
        events = valid_events()
        events[1] = (SERVER, {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "no"}})
        self.assert_holds(events, "INVALID_INITIALIZE_RESPONSE")

    def test_initialize_server_info_requires_name_and_version_strings(self):
        bad = initialize_result()
        bad["result"]["serverInfo"] = {"name": "server"}
        events = valid_events()
        events[1] = (SERVER, bad)
        self.assert_holds(events, "INVALID_INITIALIZE_RESPONSE")

    def test_initialized_cannot_precede_initialize_response(self):
        events = [(CLIENT, initialize()), (CLIENT, initialized()), (SERVER, initialize_result())]
        self.assert_holds(events, "INITIALIZED_BEFORE_INITIALIZE_RESPONSE")

    def test_initialized_must_come_from_client(self):
        events = [(CLIENT, initialize()), (SERVER, initialize_result()), (SERVER, initialized())]
        self.assert_holds(events, "INITIALIZED_NOTIFICATION_WRONG_DIRECTION")

    def test_initialized_must_not_repeat(self):
        events = valid_events()
        events.insert(3, (CLIENT, initialized()))
        self.assert_holds(events, "INITIALIZED_NOTIFICATION_DUPLICATE")

    def test_normal_request_before_initialized_holds(self):
        events = [
            (CLIENT, initialize()),
            (SERVER, initialize_result()),
            (CLIENT, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            (SERVER, {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}),
            (CLIENT, initialized()),
        ]
        self.assert_holds(events, "REQUEST_BEFORE_INITIALIZED")

    def test_initialized_missing_holds(self):
        self.assert_holds(valid_events()[:2], "INITIALIZED_NOTIFICATION_MISSING")


class CorrelationHostileTests(unittest.TestCase):
    def assert_holds(self, events, code):
        receipt = audit_transcript(capture(events))
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn(code, reason_codes(receipt))

    def test_orphan_response(self):
        events = valid_events()
        events.append((SERVER, {"jsonrpc": "2.0", "id": 999, "result": {}}))
        self.assert_holds(events, "ORPHAN_RESPONSE")

    def test_duplicate_response(self):
        events = valid_events()
        events.append((SERVER, {"jsonrpc": "2.0", "id": "tools-1", "result": {"tools": []}}))
        self.assert_holds(events, "DUPLICATE_RESPONSE")

    def test_request_id_reuse_same_direction(self):
        events = valid_events()
        events.extend([
            (CLIENT, {"jsonrpc": "2.0", "id": "tools-1", "method": "resources/list", "params": {}}),
            (SERVER, {"jsonrpc": "2.0", "id": "tools-1", "result": {"resources": []}}),
        ])
        self.assert_holds(events, "REQUEST_ID_REUSED")

    def test_same_id_is_legal_in_opposite_request_directions(self):
        events = valid_events()
        events.extend([
            (CLIENT, {"jsonrpc": "2.0", "id": 77, "method": "resources/list", "params": {}}),
            (SERVER, {"jsonrpc": "2.0", "id": 77, "result": {"resources": []}}),
        ])
        # server already used 77 for its ping; opposite namespaces must not collide.
        self.assertEqual(audit_transcript(capture(events))["status"], "PASS")

    def test_unresolved_request_holds(self):
        events = valid_events()[:-1]
        events.append((CLIENT, {"jsonrpc": "2.0", "id": 909, "method": "resources/list", "params": {}}))
        self.assert_holds(events, "UNRESOLVED_REQUESTS")

    def test_bool_id_rejected(self):
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": True, "method": "tools/list", "params": {}})
        receipt = audit_transcript(capture(events))
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(receipt))

    def test_fractional_numeric_id_roundtrip_passes(self):
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": 1.5, "method": "tools/list", "params": {}})
        events[4] = (SERVER, {"jsonrpc": "2.0", "id": 1.5, "result": {"tools": []}})
        self.assertEqual(audit_transcript(capture(events))["status"], "PASS")

    def test_fractional_numeric_id_mismatch_holds(self):
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": 1.5, "method": "tools/list", "params": {}})
        events[4] = (SERVER, {"jsonrpc": "2.0", "id": 1.5000000000000002, "result": {"tools": []}})
        receipt = audit_transcript(capture(events))
        self.assertIn("ORPHAN_RESPONSE", reason_codes(receipt))
        self.assertIn("UNRESOLVED_REQUESTS", reason_codes(receipt))

    def test_equivalent_numeric_id_spellings_correlate(self):
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        events[4] = (SERVER, {"jsonrpc": "2.0", "id": 2.0, "result": {"tools": []}})
        self.assertEqual(audit_transcript(capture(events))["status"], "PASS")

    def test_result_and_error_together_rejected(self):
        events = valid_events()
        events[4] = (SERVER, {"jsonrpc": "2.0", "id": "tools-1", "result": {}, "error": {"code": -1, "message": "x"}})
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(audit_transcript(capture(events))))

    def test_array_params_rejected_by_mcp_schema(self):
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": "tools-1", "method": "tools/list", "params": []})
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(audit_transcript(capture(events))))

    def test_non_object_result_rejected_by_mcp_schema(self):
        events = valid_events()
        events[4] = (SERVER, {"jsonrpc": "2.0", "id": "tools-1", "result": []})
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(audit_transcript(capture(events))))


class StrictInputHostileTests(unittest.TestCase):
    def test_duplicate_capture_key_rejected(self):
        payload = canonical_json_bytes(initialize())
        b64 = base64.b64encode(payload).decode("ascii")
        line = ('{"direction":"client_to_server","direction":"server_to_client","payload_base64":"%s"}' % b64).encode()
        receipt = audit_transcript(line + b"\n")
        self.assertIn("DUPLICATE_JSON_KEY", reason_codes(receipt))

    def test_duplicate_payload_key_rejected(self):
        payload = b'{"jsonrpc":"2.0","id":1,"id":2,"method":"initialize","params":{}}'
        receipt = audit_transcript(raw_line(CLIENT, payload) + b"\n")
        self.assertIn("DUPLICATE_JSON_KEY", reason_codes(receipt))

    def test_nonfinite_payload_rejected(self):
        payload = b'{"jsonrpc":"2.0","id":NaN,"method":"initialize","params":{}}'
        receipt = audit_transcript(raw_line(CLIENT, payload) + b"\n")
        self.assertIn("NONFINITE_JSON", reason_codes(receipt))

    def test_invalid_utf8_payload_rejected(self):
        receipt = audit_transcript(raw_line(CLIENT, b"\xff\xfe") + b"\n")
        self.assertIn("INVALID_UTF8", reason_codes(receipt))

    def test_unknown_rpc_top_level_key_rejected(self):
        bad = initialize()
        bad["surprise"] = True
        receipt = audit_transcript(capture([(CLIENT, bad)]))
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(receipt))

    def test_invalid_base64_rejected(self):
        line = canonical_json_bytes({"direction": CLIENT, "payload_base64": "%%%"})
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(audit_transcript(line + b"\n")))

    def test_noncanonical_base64_rejected(self):
        payload = canonical_json_bytes(initialize())
        canonical = base64.b64encode(payload).decode("ascii")
        line = canonical_json_bytes({"direction": CLIENT, "payload_base64": canonical + "="})
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(audit_transcript(line + b"\n")))

    def test_deep_payload_nesting_holds_without_recursion_escape(self):
        from tools.mcp_transcript_audit.audit import MAX_JSON_NESTING
        nested = 0
        for _ in range(MAX_JSON_NESTING + 5):
            nested = {"x": nested}
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": "deep", "method": "tools/list", "params": {"nested": nested}})
        receipt = audit_transcript(capture(events))
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("JSON_NESTING_TOO_DEEP", reason_codes(receipt))

    def test_empty_capture_holds(self):
        self.assertIn("EMPTY_CAPTURE", reason_codes(audit_transcript(b"\n\n")))

    def test_oversized_capture_holds_without_event_scan(self):
        from tools.mcp_transcript_audit.audit import MAX_CAPTURE_BYTES
        source = b"x" * (MAX_CAPTURE_BYTES + 1)
        receipt = audit_transcript(source)
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("CAPTURE_TOO_LARGE", reason_codes(receipt))
        self.assertEqual(receipt["event_count"], 0)
        self.assertEqual(receipt["evidence"], [])

    def test_event_count_limit_stops_scan_at_first_overflow(self):
        from tools.mcp_transcript_audit.audit import MAX_EVENTS
        event = encode_capture_event(CLIENT, {"jsonrpc": "2.0", "method": "ping"})
        source = (event + b"\n") * (MAX_EVENTS + 1)
        receipt = audit_transcript(source)
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("TOO_MANY_EVENTS", reason_codes(receipt))
        self.assertEqual(receipt["event_count"], MAX_EVENTS + 1)

    def test_single_line_size_limit_holds_before_payload_decode(self):
        from tools.mcp_transcript_audit.audit import MAX_LINE_BYTES
        source = b"x" * (MAX_LINE_BYTES + 1)
        receipt = audit_transcript(source)
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("EVENT_TOO_LARGE", reason_codes(receipt))
        self.assertEqual(receipt["evidence"], [])

    def test_source_byte_change_changes_source_and_receipt_hash(self):
        one = capture()
        two = one + b"\n"
        r1 = audit_transcript(one)
        r2 = audit_transcript(two)
        self.assertNotEqual(r1["source_sha256"], r2["source_sha256"])
        self.assertNotEqual(r1["receipt_sha256"], r2["receipt_sha256"])
        # Semantic events can remain equal while exact capture provenance changes.
        self.assertEqual(r1["event_count"], r2["event_count"])


class VerificationTests(unittest.TestCase):
    def test_exact_receipt_reverifies(self):
        source = capture()
        receipt = audit_transcript(source)
        verification = verify_receipt(source, canonical_json_bytes(receipt))
        self.assertTrue(verification["valid"])
        self.assertEqual(verification["reasons"], [])
        self.assertEqual(len(verification["verification_sha256"]), 64)

    def test_receipt_tamper_fails_even_if_json_valid(self):
        source = capture()
        receipt = audit_transcript(source)
        receipt["counts"]["requests"] += 1
        verification = verify_receipt(source, canonical_json_bytes(receipt))
        self.assertFalse(verification["valid"])
        self.assertIn("RECEIPT_SELF_HASH_MISMATCH", verification["reasons"])
        self.assertIn("RECEIPT_RECOMPUTE_MISMATCH", verification["reasons"])

    def test_resigned_semantic_tamper_still_fails_recompute(self):
        source = capture()
        receipt = audit_transcript(source)
        receipt["counts"]["requests"] += 1
        receipt.pop("receipt_sha256")
        from hashlib import sha256
        receipt["receipt_sha256"] = sha256(canonical_json_bytes(receipt)).hexdigest()
        verification = verify_receipt(source, canonical_json_bytes(receipt))
        self.assertFalse(verification["valid"])
        self.assertNotIn("RECEIPT_SELF_HASH_MISMATCH", verification["reasons"])
        self.assertIn("RECEIPT_RECOMPUTE_MISMATCH", verification["reasons"])

    def test_changed_source_fails_recompute(self):
        source = capture()
        receipt_bytes = canonical_json_bytes(audit_transcript(source))
        changed = capture(valid_events()[:-1])
        verification = verify_receipt(changed, receipt_bytes)
        self.assertFalse(verification["valid"])
        self.assertIn("RECEIPT_RECOMPUTE_MISMATCH", verification["reasons"])

    def test_duplicate_key_in_receipt_rejected(self):
        source = capture()
        verification = verify_receipt(source, b'{"schema":"x","schema":"y"}')
        self.assertFalse(verification["valid"])
        self.assertIn("INVALID_RECEIPT_JSON", verification["reasons"])

    def test_deep_receipt_nesting_fails_closed(self):
        from tools.mcp_transcript_audit.audit import MAX_JSON_NESTING
        deep = b'{"x":' * (MAX_JSON_NESTING + 5) + b'0' + b'}' * (MAX_JSON_NESTING + 5)
        verification = verify_receipt(capture(), deep)
        self.assertFalse(verification["valid"])
        self.assertIn("INVALID_RECEIPT_JSON", verification["reasons"])

    def test_protocol_version_override_is_rejected_by_library(self):
        with self.assertRaises(ValueError):
            audit_transcript(capture(), required_protocol_version="2025-06-18")
        receipt = canonical_json_bytes(audit_transcript(capture()))
        with self.assertRaises(ValueError):
            verify_receipt(capture(), receipt, required_protocol_version="2025-06-18")


class CliTests(unittest.TestCase):
    def test_cli_audit_verify_and_create_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            capture_path = root / "session.jsonl"
            receipt_path = root / "receipt.json"
            verify_path = root / "verification.json"
            capture_path.write_bytes(capture())
            env = dict(os.environ)
            repo = str(Path(__file__).resolve().parent)
            env["PYTHONPATH"] = repo + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            first = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "audit", str(capture_path), "-o", str(receipt_path)],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            verify = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "verify", str(capture_path), str(receipt_path), "-o", str(verify_path)],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertTrue(json.loads(verify_path.read_text())["valid"])
            second = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "audit", str(capture_path), "-o", str(receipt_path)],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(second.returncode, 2)
            self.assertIn("File exists", second.stderr)

    def test_cli_cannot_downgrade_required_protocol_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            capture_path = root / "old.jsonl"
            old_events = valid_events()
            old_events[0] = (CLIENT, initialize(version="2025-06-18"))
            old_events[1] = (SERVER, initialize_result(version="2025-06-18"))
            capture_path.write_bytes(capture(old_events))
            repo = str(Path(__file__).resolve().parent)
            env = dict(os.environ)
            env["PYTHONPATH"] = repo + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            fixed = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "audit", str(capture_path)],
                cwd=repo, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(fixed.returncode, 3, fixed.stderr)
            self.assertEqual(json.loads(fixed.stdout)["status"], "HOLD")
            bypass = subprocess.run(
                [sys.executable, "-m", "tools.mcp_transcript_audit.cli", "audit", str(capture_path), "--protocol-version", "2025-06-18"],
                cwd=repo, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(bypass.returncode, 2)
            self.assertIn("unrecognized arguments", bypass.stderr)


if __name__ == "__main__":
    unittest.main()
