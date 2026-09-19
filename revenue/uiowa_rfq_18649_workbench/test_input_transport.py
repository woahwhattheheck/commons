"""App-source -> request bytes -> actual loopback HTTP parser regressions.

The recording adapter observes exactly what the unchanged server would supply to
its compiler. A separate test exercises the real compiler when the parent exists.
Node executes the actual app.js click handler with a controlled DOM, not a browser.
"""
from __future__ import annotations

import base64
import http.client
import importlib.util
import json
import shutil
import subprocess
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("workbench_transport_server", HERE / "server.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("workbench server loader unavailable")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def browser_body(candidate: bytes, authority: bytes = b"{}") -> dict:
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required to execute the actual workbench import path")
    payload = {"candidate_b64": base64.b64encode(candidate).decode("ascii"),
               "authority_b64": base64.b64encode(authority).decode("ascii")}
    result = subprocess.run(
        [node, str(HERE / "test_input_transport.js"), "--bridge"],
        input=json.dumps(payload), text=True, capture_output=True, timeout=20,
        check=True,
    )
    value = json.loads(result.stdout)
    value["body"] = (base64.b64decode(value["body_b64"], validate=True)
                     if value["body_b64"] is not None else None)
    return value


class RecordingAdapter:
    def __init__(self):
        self.calls = []

    def inspect(self, candidate, authority):
        self.calls.append((candidate, authority))
        return {"schema": "transport-test-recording-adapter", "mode": "UNTRUSTED_INSPECTION",
                "trust": {"current_evidence_review_authority": False},
                "candidate": candidate, "authority": authority}


class TransportHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = RecordingAdapter()
        cls.httpd = server.create_server(port=0, adapter=cls.adapter, static_root=HERE)
        cls.host, cls.port = cls.httpd.server_address[:2]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.adapter.calls.clear()

    def post(self, body: bytes, **extra_headers):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request("POST", "/api/inspect", body=body, headers={
                "Content-Type": "application/json", "Host": f"127.0.0.1:{self.port}",
                "Origin": f"http://127.0.0.1:{self.port}", **extra_headers,
            })
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            conn.close()

    def test_original_two_documents_reach_the_server(self):
        candidate = ' \r\n{"note":"caf\u00e9 \u6771\u4eac \U0001f642", "value":null}\t'.encode("utf-8")
        authority = b'\r\n{"sources": [], "label":"\\u0061"}\n'
        emitted = browser_body(candidate, authority)
        self.assertEqual(emitted["body"], b'{"candidate":' + candidate + b',"authority":' + authority + b'}')
        status, headers, _ = self.post(emitted["body"])
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.adapter.calls, [(json.loads(candidate), json.loads(authority))])

    def assert_duplicate_rejected(self, candidate, authority=b"{}"):
        emitted = browser_body(candidate, authority)
        self.assertEqual(emitted["requests"], 1)
        status, _, payload = self.post(emitted["body"])
        self.assertEqual(status, 400)
        self.assertIn("duplicate JSON key", payload["error"])
        self.assertEqual(self.adapter.calls, [])

    def test_candidate_duplicate_never_calls_the_compiler(self):
        self.assert_duplicate_rejected(b'{"count":1,"count":2}')

    def test_nested_duplicate_never_calls_the_compiler(self):
        self.assert_duplicate_rejected(b'{"rows":[{"count":1,"count":2}]}')

    def test_escaped_duplicate_never_calls_the_compiler(self):
        self.assert_duplicate_rejected(b'{"name":1,"n\\u0061me":2}')

    def test_authority_duplicate_never_calls_the_compiler(self):
        self.assert_duplicate_rejected(b'{}', b'{"sources":[],"sources":[1]}')

    def test_integer_outside_javascript_safe_range_arrives_exactly(self):
        candidate = b'{"count":9007199254740993,"negative":-9007199254740993}'
        emitted = browser_body(candidate)
        status, _, payload = self.post(emitted["body"])
        self.assertEqual(status, 200)
        self.assertEqual(self.adapter.calls[0][0]["count"], 9007199254740993)
        self.assertEqual(self.adapter.calls[0][0]["negative"], -9007199254740993)
        self.assertEqual(payload["report"]["candidate"]["count"], 9007199254740993)

    def test_lexical_number_forms_survive_to_parser_boundary(self):
        candidate = b'{"zero":-0,"decimal":1.2300,"exponent":1e+30}'
        emitted = browser_body(candidate)
        self.assertIn(candidate, emitted["body"])
        self.assertEqual(self.post(emitted["body"])[0], 200)
        self.assertEqual(self.adapter.calls[0][0], json.loads(candidate))

    def test_invalid_utf8_stops_before_http(self):
        emitted = browser_body(b'{"note":"\xc3("}')
        self.assertIsNone(emitted["body"])
        self.assertEqual(emitted["requests"], 0)
        self.assertIn("valid UTF-8", emitted["error"])
        self.assertEqual(self.adapter.calls, [])

    def test_bom_is_not_silently_removed(self):
        emitted = browser_body(b'\xef\xbb\xbf{}')
        self.assertIsNone(emitted["body"])
        self.assertIn("valid JSON", emitted["error"])

    def test_literal_replacement_character_remains_valid_data(self):
        candidate = '{"note":"\ufffd"}'.encode("utf-8")
        emitted = browser_body(candidate)
        self.assertEqual(self.post(emitted["body"])[0], 200)
        self.assertEqual(self.adapter.calls[0][0]["note"], "\ufffd")

    def test_combined_byte_limit_stops_before_http(self):
        candidate = b'{"x":"' + b'x' * (1024*1024-8) + b'"}'
        emitted = browser_body(candidate, candidate)
        self.assertIsNone(emitted["body"])
        self.assertIn("2 MiB", emitted["error"])
        self.assertEqual(self.adapter.calls, [])

    def test_exactly_full_body_is_accepted_by_unchanged_server(self):
        overhead = len(b'{"candidate":,"authority":}')
        candidate = b'{"x":"' + b'x' * (1024*1024-8) + b'"}'
        authority = b'{"x":"' + b'x' * (1024*1024-overhead-8) + b'"}'
        emitted = browser_body(candidate, authority)
        self.assertEqual(len(emitted["body"]), server.MAX_BODY_BYTES)
        self.assertEqual(self.post(emitted["body"])[0], 200)
        self.assertEqual(len(self.adapter.calls), 1)

    def test_same_origin_boundary_is_unchanged(self):
        emitted = browser_body(b'{}')
        self.assertEqual(self.post(emitted["body"], Origin="http://example.invalid")[0], 403)
        self.assertEqual(self.adapter.calls, [])

    def test_no_new_trusted_root_input_is_permitted(self):
        emitted = browser_body(b'{}')
        modified = emitted["body"][:-1] + b',"trusted_authority_sha256":"fake"}'
        self.assertEqual(self.post(modified)[0], 400)
        self.assertEqual(self.adapter.calls, [])


class RealCompilerTransportTests(unittest.TestCase):
    def test_existing_parent_receipt_matches_direct_inspection(self):
        parent = HERE.parent / "uiowa_rfq_18649_workshare"
        if not parent.is_dir():
            self.skipTest("parent compiler absent in isolated transport checkout; no compiler-pass claim")
        candidate = (parent / "fixtures" / "synthetic_packet.json").read_bytes()
        authority = (parent / "fixtures" / "synthetic_authority.json").read_bytes()
        adapter = server.CompilerAdapter()
        expected = adapter.inspect(server.loads_strict_json(candidate), server.loads_strict_json(authority))
        emitted = browser_body(candidate, authority)
        self.assertIsNotNone(emitted["body"], emitted["error"])
        httpd = server.create_server(port=0, adapter=adapter, static_root=HERE)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        conn = http.client.HTTPConnection(*httpd.server_address, timeout=10)
        try:
            host = f"127.0.0.1:{httpd.server_address[1]}"
            conn.request("POST", "/api/inspect", body=emitted["body"], headers={
                "Host": host, "Origin": f"http://{host}", "Content-Type": "application/json"})
            response = conn.getresponse()
            payload = json.loads(response.read())
            self.assertEqual(response.status, 200, payload)
            self.assertEqual(payload["report"], expected)
            self.assertEqual(payload["report"]["mode"], "UNTRUSTED_INSPECTION")
            self.assertFalse(payload["report"]["trust"]["current_evidence_review_authority"])
        finally:
            conn.close()
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
