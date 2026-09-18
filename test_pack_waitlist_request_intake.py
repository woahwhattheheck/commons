#!/usr/bin/env python3
"""Real-file and loopback HTTP coverage for waitlist request intake."""
from __future__ import annotations

import http.client
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from host import pack_waitlist as waitlist


ADDRESS = "fixture@example.invalid"
SIGNUP = {"email": ADDRESS, "tier": "desk", "state": "IN", "consent": True}
POST_ROUTES = ("/waitlist", "/waitlist/", "/", "/waitlist/opt-out", "/opt-out")
BAD_EMAILS = (None, False, 17, 1.5, [], [ADDRESS], {"address": ADDRESS})
BAD_BODIES = (b'{"email":', b'{"email":"fixture@example.invalid",}', b'\xff')


class WaitlistRequestIntakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "records.jsonl"

    def post(self, route: str, body: bytes, content_type: str = "application/json") -> dict:
        return waitlist.handle_http(
            "POST", route, body=body, content_type=content_type, jsonl_path=self.path
        )

    def assert_private_invalid(self, result: dict, total: int = 0) -> None:
        self.assertEqual(result["status"], 400)
        self.assertEqual(result["body"]["verdict"], "WAITLIST_INVALID")
        self.assertEqual(result["body"]["counts"]["total"], total)
        self.assertIs(result["body"]["addresses_public"], False)
        self.assertEqual(result["body"]["sends"], 0)
        self.assertNotIn("@", json.dumps(result))

    def test_string_email_normalization_is_unchanged(self) -> None:
        self.assertEqual(waitlist.normalize_email("  FIXTURE@EXAMPLE.INVALID \n"), ADDRESS)
        self.assertEqual(waitlist.normalize_email(""), "")

    def test_non_string_email_is_not_coerced(self) -> None:
        for value in BAD_EMAILS + (ADDRESS.encode(), (ADDRESS,)):
            with self.subTest(value=value):
                self.assertEqual(waitlist.normalize_email(value), "")

    def test_signup_and_opt_out_reject_non_string_email(self) -> None:
        for kind in ("signup", "opt_out"):
            for value in BAD_EMAILS:
                with self.subTest(kind=kind, value=value):
                    result = waitlist.validate_signup(dict(SIGNUP, email=value, kind=kind))
                    self.assertEqual(result["verdict"], "WAITLIST_INVALID")
                    self.assertIn("email", result["missing"])

    def test_invalid_append_does_not_create_storage(self) -> None:
        result = waitlist.append_signup(self.path, dict(SIGNUP, email=[ADDRESS]))
        self.assertEqual(result["verdict"], "WAITLIST_INVALID")
        self.assertEqual(result["counts"]["total"], 0)
        self.assertFalse(self.path.exists())

    def test_non_string_records_do_not_inflate_counts(self) -> None:
        rows = [dict(SIGNUP, email=value) for value in BAD_EMAILS] + [SIGNUP]
        self.path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        before = self.path.read_bytes()
        counts = waitlist.public_counts(self.path)
        self.assertEqual(counts["total"], 1)
        self.assertEqual(counts["tiers"]["desk"], 1)
        self.assertNotIn("@", json.dumps(counts))
        self.assertEqual(self.path.read_bytes(), before)

    def test_malformed_body_is_400_for_every_post_route(self) -> None:
        for route in POST_ROUTES:
            for body in BAD_BODIES:
                with self.subTest(route=route, body=body):
                    result = self.post(route, body)
                    self.assert_private_invalid(result)
                    if "opt-out" in route:
                        self.assertIs(result["body"]["pixel_allowed"], False)
                    self.assertFalse(self.path.exists())

    def test_invalid_requests_preserve_existing_bytes_and_counts(self) -> None:
        waitlist.append_signup(self.path, SIGNUP)
        before = self.path.read_bytes()
        for route in POST_ROUTES:
            for body in BAD_BODIES + (json.dumps(dict(SIGNUP, email=[ADDRESS])).encode(),):
                with self.subTest(route=route, body=body):
                    self.assert_private_invalid(self.post(route, body), total=1)
                    self.assertEqual(self.path.read_bytes(), before)

    def test_non_object_json_is_invalid_without_writes(self) -> None:
        for value in ([], [SIGNUP], None, False, 17, ADDRESS):
            for route in ("/waitlist", "/opt-out"):
                with self.subTest(value=value, route=route):
                    self.assert_private_invalid(self.post(route, json.dumps(value).encode()))
                    self.assertFalse(self.path.exists())

    def test_form_signup_and_opt_out_keep_existing_contract(self) -> None:
        content_type = "application/x-www-form-urlencoded; charset=utf-8"
        form = urlencode(dict(SIGNUP, email=" FIXTURE@EXAMPLE.INVALID ", consent="on"))
        result = self.post("/waitlist?source=test", form.encode(), content_type)
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["body"]["counts"]["total"], 1)
        self.assertNotIn("@", json.dumps(result))
        out = self.post("/opt-out", urlencode({"email": ADDRESS}).encode(), content_type)
        self.assertEqual(out["status"], 200)
        self.assertEqual(out["body"]["verdict"], "OPT_OUT_OK")
        self.assertIs(out["body"]["pixel_allowed"], False)
        self.assertEqual(out["body"]["counts"]["total"], 0)
        rows = waitlist.read_jsonl(self.path)
        self.assertEqual([row["kind"] for row in rows], ["signup", "opt_out"])
        self.assertEqual([row["email"] for row in rows], [ADDRESS, ADDRESS])

    def test_latest_record_and_consent_behavior_is_unchanged(self) -> None:
        waitlist.append_signup(self.path, SIGNUP)
        moved = waitlist.append_signup(self.path, dict(SIGNUP, tier="plant"))
        self.assertEqual(moved["counts"]["total"], 1)
        self.assertEqual(moved["counts"]["tiers"]["desk"], 0)
        self.assertEqual(moved["counts"]["tiers"]["plant"], 1)
        before = self.path.read_bytes()
        denied = waitlist.append_signup(self.path, dict(SIGNUP, consent=False))
        self.assertEqual(denied["verdict"], "WAITLIST_INVALID")
        self.assertEqual(self.path.read_bytes(), before)
        out = waitlist.append_signup(self.path, {"email": ADDRESS, "kind": "opt_out"})
        self.assertEqual(out["counts"]["total"], 0)
        self.assertFalse(out["pixel_allowed"])
        self.assertEqual(out["sends"], 0)

    def test_parse_body_remains_strict_for_direct_callers(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            waitlist.parse_body(b"{", "application/json")
        with self.assertRaises(UnicodeDecodeError):
            waitlist.parse_body(b"\xff", "application/json")

    def test_unknown_routes_are_not_reclassified_as_bad_json(self) -> None:
        self.assertEqual(self.post("/unknown", b"{")["status"], 404)
        result = waitlist.handle_http("PUT", "/waitlist", body=b"{", jsonl_path=self.path)
        self.assertEqual(result["status"], 404)
        self.assertFalse(self.path.exists())

    def test_storage_decode_error_is_not_a_request_validation_error(self) -> None:
        self.path.write_bytes(b"not-json\n")
        with self.assertRaises(json.JSONDecodeError):
            self.post("/waitlist", b"{}")
        self.assertEqual(self.path.read_bytes(), b"not-json\n")

    def test_cli_append_counts_and_opt_out(self) -> None:
        script = Path(waitlist.__file__)
        common = [sys.executable, str(script), "append", "--jsonl", str(self.path), "--email", ADDRESS]
        first = subprocess.run(
            common + ["--tier", "desk", "--state", "IN", "--consent"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(json.loads(first.stdout)["counts"]["total"], 1)
        second = subprocess.run(
            common + ["--opt-out"], check=True, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(json.loads(second.stdout)["counts"]["total"], 0)

    def test_real_http_bad_then_good_requests_keep_service_available(self) -> None:
        class Handler(waitlist.WaitlistHandler):
            jsonl_path = self.path

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            cases = (
                ("/waitlist", b"{", 400, 0),
                ("/waitlist", json.dumps(SIGNUP).encode(), 200, 1),
                ("/opt-out", b"\xff", 400, 1),
                ("/waitlist", json.dumps(dict(SIGNUP, email=[ADDRESS])).encode(), 400, 1),
                ("/opt-out", json.dumps({"email": ADDRESS}).encode(), 200, 0),
            )
            for route, body, expected_status, total in cases:
                with self.subTest(route=route, body=body):
                    conn = http.client.HTTPConnection(*server.server_address, timeout=5)
                    try:
                        conn.request("POST", route, body=body, headers={"Content-Type": "application/json"})
                        response = conn.getresponse()
                        raw = response.read()
                        self.assertEqual(response.status, expected_status)
                        self.assertEqual(int(response.getheader("Content-Length")), len(raw))
                        self.assertEqual(response.getheader("Cache-Control"), "no-store")
                        parsed = json.loads(raw)
                        self.assertEqual(parsed["counts"]["total"], total)
                        self.assertNotIn("@", raw.decode())
                    finally:
                        conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
