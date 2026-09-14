import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.agent_false_success_survival import proof as p


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def make_case(cid, family, status, ctype, body, observed):
    return {
        "id": cid,
        "family": family,
        "status": status,
        "content_type": ctype,
        "body_base64": b64(body),
        "observed_client_disposition": observed,
        "client_event_sha256": digest(cid + "-event"),
        "source_sha256": digest(cid + "-source"),
    }


def complete_bundle(*, vulnerable=True):
    valid = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"isError": False, "content": [{"type": "text", "text": "ok=1"}]}}, separators=(",", ":"))
    rpc_error = json.dumps({"jsonrpc": "2.0", "id": 2, "error": {"code": -32000, "message": "nope"}}, separators=(",", ":"))
    tool_error = json.dumps({"jsonrpc": "2.0", "id": 3, "result": {"isError": True, "content": [{"type": "text", "text": "nope"}]}}, separators=(",", ":"))
    wrapped = json.dumps({"jsonrpc": "2.0", "id": 4, "result": {"isError": False, "content": [{"type": "text", "text": "<html><body>Sign in</body></html>"}]}}, separators=(",", ":"))
    bad_observed = "SUCCESS" if vulnerable else "ERROR"
    return {
        "schema": p.CAPTURE_SCHEMA,
        "client": {"name": "client", "version": "1.2.3"},
        "captured_at": "2026-09-14T04:00:00Z",
        "cases": [
            make_case("html", "HTTP_200_HTML", 200, "text/html", "<!doctype html><html><body>oops</body></html>", bad_observed),
            make_case("login", "HTTP_200_LOGIN_HTML", 200, "text/html", "<html><form><input type='password'>Log in</form></html>", bad_observed),
            make_case("mislabeled", "HTTP_200_MISLABELED_HTML", 200, "application/json", "<!--x--><html><body>oops</body></html>", bad_observed),
            make_case("http503", "HTTP_NON_2XX", 503, "application/json", '{"error":"down"}', "ERROR"),
            make_case("rpcerr", "JSON_RPC_ERROR", 200, "application/json", rpc_error, "ERROR"),
            make_case("toolerr", "MCP_TOOL_ERROR", 200, "application/json", tool_error, "ERROR"),
            make_case("wrapped", "MCP_WRAPPED_HTML", 200, "application/json", wrapped, bad_observed),
            make_case("malformed", "MALFORMED_JSON", 200, "application/json", '{"jsonrpc":', "ERROR"),
            make_case("control", "VALID_CONTROL", 200, "application/json", valid, "SUCCESS"),
        ],
    }


class ProofTests(unittest.TestCase):
    def test_complete_healthy_matrix_survives(self):
        proof = p.compile_proof(complete_bundle(vulnerable=False))
        self.assertEqual(proof["proof"]["decision"], "SURVIVED")
        self.assertEqual(proof["proof"]["missing_families"], [])
        self.assertTrue(p.verify_proof(complete_bundle(vulnerable=False), proof))

    def test_false_success_is_detected(self):
        proof = p.compile_proof(complete_bundle(vulnerable=True))
        self.assertEqual(proof["proof"]["decision"], "FALSE_SUCCESS_DETECTED")
        self.assertEqual(set(proof["proof"]["false_success_case_ids"]), {"html", "login", "mislabeled", "wrapped"})

    def test_missing_family_holds(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"] = [c for c in bundle["cases"] if c["family"] != "MCP_WRAPPED_HTML"]
        proof = p.compile_proof(bundle)
        self.assertEqual(proof["proof"]["decision"], "HOLD_INCOMPLETE_MATRIX")
        self.assertIn("MCP_WRAPPED_HTML", proof["proof"]["missing_families"])

    def test_family_cannot_be_self_asserted(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][0]["family"] = "VALID_CONTROL"
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_duplicate_case_id_rejected(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][1]["id"] = bundle["cases"][0]["id"]
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_unknown_key_rejected(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][0]["surprise"] = True
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_secret_bearing_headers_cannot_enter_schema(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][0]["headers"] = {"Authorization": "Bearer do-not-publish"}
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_bool_status_rejected(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][0]["status"] = True
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_bad_digest_rejected(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][0]["source_sha256"] = "ABC"
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_noncanonical_timestamp_rejected(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["captured_at"] = "2026-09-14T04:00:00+00:00"
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_oversized_body_rejected(self):
        bundle = complete_bundle(vulnerable=False)
        bundle["cases"][0]["body_base64"] = base64.b64encode(b"x" * (p.MAX_BODY_BYTES + 1)).decode()
        with self.assertRaises(p.SchemaError):
            p.compile_proof(bundle)

    def test_duplicate_json_key_rejected(self):
        raw = '{"schema":"x","schema":"y"}'
        with self.assertRaises(p.SchemaError):
            p.loads_strict(raw)

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(p.SchemaError):
            p.loads_strict('{"x":NaN}')

    def test_html_after_comment_detected(self):
        c = p.classify_exchange(200, "application/json", b"<!-- proxy banner -->\n<html><body>x</body></html>")
        self.assertEqual(c.decision, "REJECT")
        self.assertIn("HTTP_200_MISLABELED_HTML", c.tags)

    def test_wrapped_html_detected(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"isError": False, "content": [{"type": "text", "text": "<!doctype html><html><body>x</body></html>"}]}}).encode()
        c = p.classify_exchange(200, "application/json", body)
        self.assertEqual(c.decision, "REJECT")
        self.assertIn("MCP_WRAPPED_HTML", c.tags)

    def test_mcp_iserror_bool_is_strict(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"isError": 1, "content": []}}).encode()
        c = p.classify_exchange(200, "application/json", body)
        self.assertEqual(c.decision, "REJECT")
        self.assertIn("MCP_IS_ERROR_NOT_BOOL", c.reasons)

    def test_json_rpc_error_rejected(self):
        body = b'{"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"x"}}'
        c = p.classify_exchange(200, "application/json", body)
        self.assertEqual(c.decision, "REJECT")
        self.assertIn("JSON_RPC_ERROR", c.tags)

    def test_valid_sse_control_is_supported(self):
        payload = '{"jsonrpc":"2.0","id":1,"result":{"isError":false,"content":[{"type":"text","text":"ok"}]}}'
        body = ("event: message\ndata: " + payload + "\n\n").encode()
        c = p.classify_exchange(200, "text/event-stream", body)
        self.assertEqual(c.decision, "ACCEPT")
        self.assertIn("VALID_CONTROL", c.tags)

    def test_wrong_success_media_type_rejected(self):
        c = p.classify_exchange(200, "text/plain", b"ok")
        self.assertEqual(c.decision, "REJECT")
        self.assertIn("UNSUPPORTED_SUCCESS_MEDIA_TYPE", c.reasons)

    def test_proof_tamper_fails_verify(self):
        bundle = complete_bundle(vulnerable=False)
        proof = p.compile_proof(bundle)
        proof["proof"]["decision"] = "FALSE_SUCCESS_DETECTED"
        self.assertFalse(p.verify_proof(bundle, proof))

    def test_resealed_proof_tamper_still_fails_verify(self):
        bundle = complete_bundle(vulnerable=False)
        proof = p.compile_proof(bundle)
        proof["proof"]["decision"] = "CLIENT_MISMATCH"
        proof["proof_sha256"] = p.sha256_bytes(p.canonical_bytes(proof["proof"]))
        self.assertFalse(p.verify_proof(bundle, proof))

    def test_body_tamper_breaks_exact_proof(self):
        bundle = complete_bundle(vulnerable=False)
        proof = p.compile_proof(bundle)
        changed = copy.deepcopy(bundle)
        body = base64.b64decode(changed["cases"][-1]["body_base64"])
        changed["cases"][-1]["body_base64"] = base64.b64encode(body.replace(b"ok=1", b"ok=2")).decode()
        self.assertFalse(p.verify_proof(changed, proof))

    def test_client_event_replay_changes_receipt(self):
        bundle = complete_bundle(vulnerable=False)
        proof1 = p.compile_proof(bundle)
        changed = copy.deepcopy(bundle)
        changed["cases"][-1]["client_event_sha256"] = digest("different-event")
        proof2 = p.compile_proof(changed)
        self.assertNotEqual(proof1["proof_sha256"], proof2["proof_sha256"])

    def test_raw_bodies_not_published(self):
        bundle = complete_bundle(vulnerable=True)
        proof = p.compile_proof(bundle)
        serialized = json.dumps(proof)
        self.assertNotIn("Sign in", serialized)
        self.assertNotIn("password", serialized)
        self.assertNotIn("body_base64", serialized)

    def test_external_send_authority_is_never_minted(self):
        proof = p.compile_proof(complete_bundle(vulnerable=False))
        self.assertIs(proof["proof"]["external_send_authorized"], False)
        self.assertIs(proof["proof"]["production_certified"], False)

    def test_cli_demo_fixture(self):
        fixture = Path(__file__).with_name("fixtures") / "synthetic_capture.json"
        result = subprocess.run(
            [sys.executable, "-m", "revenue.agent_false_success_survival", "demo", str(fixture)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "FALSE_SUCCESS_DETECTED")

    def test_cli_compile_is_create_exclusive_and_verify_roundtrip(self):
        fixture = Path(__file__).with_name("fixtures") / "synthetic_capture.json"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "proof.json"
            first = subprocess.run(
                [sys.executable, "-m", "revenue.agent_false_success_survival", "compile", str(fixture), "--out", str(out)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = subprocess.run(
                [sys.executable, "-m", "revenue.agent_false_success_survival", "compile", str(fixture), "--out", str(out)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second.returncode, 2)
            verify = subprocess.run(
                [sys.executable, "-m", "revenue.agent_false_success_survival", "verify", str(fixture), str(out)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_cli_rejects_symlink_input(self):
        fixture = Path(__file__).with_name("fixtures") / "synthetic_capture.json"
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "capture.json"
            try:
                os.symlink(fixture.resolve(), link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            result = subprocess.run(
                [sys.executable, "-m", "revenue.agent_false_success_survival", "demo", str(link)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
