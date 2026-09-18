import io
import json
import os
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from integrations import frantic_profile_client as f


class _State:
    token = "fr_agent_TESTSECRET"
    kid = "agent-df56d0"
    situation = None
    patch_count = 0
    seen_body = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def _json(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/v1/hire/agents":
            agents = []
            if _State.situation and _State.situation["open"]:
                s = _State.situation
                agents.append({
                    "kid": _State.kid,
                    "pitch": s["pitch"],
                    "floor_usd": None if s["floor_cents"] is None else s["floor_cents"] / 100,
                    "wants": [{"id": x, "label": x, "proven": False} for x in s["wants"]],
                })
            self._json(200, {"ok": True, "open_count": len(agents), "agents": agents})
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def do_PATCH(self):
        if self.path != f"/v1/agents/{_State.kid}/profile":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        body = json.loads(raw)
        _State.seen_body = body
        if body.get("agent_token") != _State.token:
            self._json(401, {"ok": False, "error": "unauthorized"})
            return
        _State.patch_count += 1
        _State.situation = body["situation"]
        self._json(200, {"ok": True, "receipt": "profile-test-receipt"})


class ServerFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _State.situation = None
        _State.patch_count = 0
        _State.seen_body = None

    def test_validate_rejects_markup_contact_url_and_bad_wants(self):
        good = dict(open=True, floor_cents=20000, wants=("github_contribution_v1",))
        for pitch in ["see https://example.com", "mail me a@b.com", "**markup**", "line1\nline2"]:
            with self.subTest(pitch=pitch), self.assertRaises(f.FranticError):
                f.Situation(pitch=pitch, **good).validate()
        with self.assertRaises(f.FranticError):
            f.Situation(True, "safe", 20000, ("not_real",)).validate()

    def test_apply_and_exact_public_readback(self):
        s = f.Situation(True, "Evidence-backed delivery with exact receipts.", 20000,
                        ("github_contribution_v1", "protocol_conformance_v1", "published_artifact_v1"))
        result = f.apply_profile(self.base, _State.kid, s, token=_State.token)
        self.assertTrue(result["ok"])
        census = f.verify_public_listing(self.base, _State.kid, s)
        self.assertTrue(census["listed"])
        self.assertEqual(_State.patch_count, 1)
        self.assertEqual(_State.seen_body["agent_token"], _State.token)

    def test_bad_token_fails_without_public_state_change(self):
        s = f.Situation(True, "Evidence-backed delivery with exact receipts.", 20000,
                        ("github_contribution_v1",))
        with self.assertRaises(f.FranticError):
            f.apply_profile(self.base, _State.kid, s, token="fr_agent_WRONG")
        self.assertEqual(_State.patch_count, 0)
        self.assertFalse(f.inspect_listing(self.base, _State.kid)["listed"])

    def test_plan_never_reads_token_or_mutates(self):
        old = os.environ.get(f.TOKEN_ENV)
        os.environ[f.TOKEN_ENV] = _State.token
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = f.main(["--base-url", self.base])
        finally:
            if old is None:
                os.environ.pop(f.TOKEN_ENV, None)
            else:
                os.environ[f.TOKEN_ENV] = old
        self.assertEqual(rc, 0)
        self.assertEqual(_State.patch_count, 0)
        self.assertNotIn(_State.token, stdout.getvalue() + stderr.getvalue())
        obj = json.loads(stdout.getvalue())
        self.assertFalse(obj["provider_mutation"])

    def test_apply_output_redacts_token(self):
        old = os.environ.get(f.TOKEN_ENV)
        os.environ[f.TOKEN_ENV] = _State.token
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = f.main(["--base-url", self.base, "--apply",
                             "--pitch", "Evidence-backed delivery with exact receipts."])
        finally:
            if old is None:
                os.environ.pop(f.TOKEN_ENV, None)
            else:
                os.environ[f.TOKEN_ENV] = old
        self.assertEqual(rc, 0)
        self.assertNotIn(_State.token, stdout.getvalue() + stderr.getvalue())
        self.assertEqual(_State.patch_count, 1)

    def test_close_requires_public_absence(self):
        open_s = f.Situation(True, "Evidence-backed delivery with exact receipts.", 20000,
                             ("github_contribution_v1",))
        closed_s = f.Situation(False, "Evidence-backed delivery with exact receipts.", 20000,
                               ("github_contribution_v1",))
        f.apply_profile(self.base, _State.kid, open_s, token=_State.token)
        self.assertTrue(f.inspect_listing(self.base, _State.kid)["listed"])
        f.apply_profile(self.base, _State.kid, closed_s, token=_State.token)
        self.assertFalse(f.verify_public_listing(self.base, _State.kid, closed_s)["listed"])


if __name__ == "__main__":
    unittest.main()
