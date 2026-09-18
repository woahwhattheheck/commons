#!/usr/bin/env python3
"""Focused contract tests for the bounded peer self-probe."""

from __future__ import annotations

import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest import mock

from host import peer_probe


ROOT = Path(__file__).resolve().parent


def fixture() -> dict:
    return {
        "schema": peer_probe.INPUT_SCHEMA,
        "harness": {"family": "Codex", "surface": "test"},
        "observed_at": "2026-09-01T08:00:00Z",
        "roads": [
            {
                "id": "pass-command",
                "kind": "command",
                "argv": [sys.executable, "-c", "print('READY')"],
                "timeout_seconds": 2,
            },
            {
                "id": "fail-command",
                "kind": "command",
                "argv": [sys.executable, "-c", "raise SystemExit(7)"],
                "timeout_seconds": 2,
            },
        ],
        "claimed_cants": [
            {
                "id": "no-direct-slack",
                "condition": "UNAVAILABLE",
                "evidence_ref": "measurement:local",
                "tooling_need": "Slack relay adapter",
            }
        ],
    }


class PeerProbeTests(unittest.TestCase):
    def test_fixed_fixture_is_byte_identical_and_keeps_catalog_order(self) -> None:
        request = fixture()
        first = peer_probe.canonical(peer_probe.compile_report(request))
        second = peer_probe.canonical(peer_probe.compile_report(request))
        self.assertEqual(first, second)
        report = json.loads(first)
        peer_probe.validate_report(report)
        self.assertEqual(report["roads_attempted"], ["pass-command", "fail-command"])
        self.assertEqual([row["status"] for row in report["road_results"]], ["PASS", "FAIL"])
        self.assertEqual(report["claimed_cants"], request["claimed_cants"])

    def test_unknown_road_fails_closed_before_any_probe(self) -> None:
        request = fixture()
        request["roads"].append({"id": "mystery", "kind": "telepathy", "timeout_seconds": 1})
        with mock.patch.object(peer_probe, "run_probe") as run:
            with self.assertRaisesRegex(peer_probe.ProbeInputError, "kind unknown"):
                peer_probe.compile_report(request)
        run.assert_not_called()

    def test_command_uses_a_credential_free_environment_and_bounded_capture(self) -> None:
        request = fixture()
        request["roads"] = [{
            "id": "bounded-env",
            "kind": "command",
            "argv": [
                sys.executable,
                "-c",
                "import os,sys; sys.stdout.write(os.getenv('PROBE_PRIVATE_VALUE','missing') + 'x' * 1000)",
            ],
            "timeout_seconds": 2,
            "max_capture_bytes": 32,
        }]
        with mock.patch.dict(os.environ, {"PROBE_PRIVATE_VALUE": "must-not-reach-child"}):
            result = peer_probe.compile_report(request)["road_results"][0]
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["evidence"]["stdout"]["truncated"])
        self.assertEqual(result["evidence"]["stdout"]["bytes"], 32)
        expected = ("missing" + "x" * 25).encode("ascii")
        self.assertEqual(result["evidence"]["stdout"]["sha256"], peer_probe.hashlib.sha256(expected).hexdigest())

    def test_http_probe_is_explicit_bounded_and_does_not_follow_redirects(self) -> None:
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/unexpected")
                    self.end_headers()
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"unexpected")

            def log_message(self, _format, *args):
                return

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = fixture()
            request["roads"] = [{
                "id": "redirect",
                "kind": "http",
                "url": f"http://127.0.0.1:{server.server_port}/redirect",
                "method": "GET",
                "expected_status": [200],
                "timeout_seconds": 2,
                "max_capture_bytes": 32,
            }]
            result = peer_probe.compile_report(request)["road_results"][0]
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["evidence"]["status_code"], 302)
            self.assertEqual(result["evidence"]["body"]["sha256"], peer_probe.EMPTY_SHA256)
        finally:
            server.shutdown()
            server.server_close()

    def test_command_timeout_is_an_explicit_measured_error(self) -> None:
        request = fixture()
        request["roads"] = [{
            "id": "slow-command",
            "kind": "command",
            "argv": [sys.executable, "-c", "import time; time.sleep(1)"],
            "timeout_seconds": 0.05,
        }]
        result = peer_probe.compile_report(request)["road_results"][0]
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["evidence"]["error"], "TIMEOUT")

    def test_url_credentials_are_rejected_before_network(self) -> None:
        request = fixture()
        request["roads"] = [{
            "id": "bad-url", "kind": "http", "url": "https://user:" + "private-value@127.0.0.1/",
            "timeout_seconds": 1,
        }]
        with mock.patch.object(peer_probe.urllib.request.OpenerDirector, "open") as opened:
            with self.assertRaisesRegex(peer_probe.ProbeInputError, "must not contain credentials"):
                peer_probe.compile_report(request)
        opened.assert_not_called()

    def test_cli_unknown_road_writes_no_report(self) -> None:
        request = fixture()
        request["roads"] = [{"id": "bad", "kind": "unknown", "timeout_seconds": 1}]
        stdin = io.StringIO(json.dumps(request))
        stdout = io.BytesIO()

        class Stdout:
            buffer = stdout

        with mock.patch.object(peer_probe.sys, "stdin", stdin), mock.patch.object(peer_probe.sys, "stdout", Stdout()):
            self.assertEqual(peer_probe.main([]), 2)
        self.assertEqual(stdout.getvalue(), b"")

    def test_self_test_cli_reports_pass(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host" / "peer_probe.py"), "--self-test"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
