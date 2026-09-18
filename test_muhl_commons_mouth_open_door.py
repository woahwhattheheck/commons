#!/usr/bin/env python3
"""Focused open-door regression tests for infra/host/muhl_commons_mouth.py."""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parent
HOST = ROOT / "infra" / "host"
SCRIPT = HOST / "muhl_commons_mouth.py"


def load_mouth(argv=None):
    old_argv = sys.argv[:]
    old_path = sys.path[:]
    try:
        sys.argv = list(argv or ["muhl_commons_mouth.py"])
        sys.path.insert(0, str(HOST))
        name = "muhl_commons_mouth_open_door_%x" % id(argv)
        spec = importlib.util.spec_from_file_location(name, SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path


MOUTH = load_mouth()


class FakeHandler(MOUTH.Handler):
    def __init__(self, path="/", *, accept="text/plain", user_agent="", payload=b""):
        self.path = path
        self.headers = {
            "Accept": accept,
            "User-Agent": user_agent,
            "Content-Length": str(len(payload)),
        }
        self.rfile = io.BytesIO(payload)
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers = {}

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, name, value):
        self.response_headers[name] = value

    def end_headers(self):
        return None

    @property
    def text(self):
        return self.wfile.getvalue().decode("utf-8", "replace")


class MouthOpenDoorTests(unittest.TestCase):
    def test_source_has_no_admission_gate_markers(self):
        source = SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "TOKEN_PATH",
            "load_or_make_token",
            "_token_ok",
            "Handler.token",
            "REFUSE: --inject",
            "ACCEPTED required",
            "DECLINED blocks",
            "self._send(403",
            "POSTS_PER_MIN",
            "MAX_BODY",
            "allow_post(",
            "ChatGPT-User",
            "confirm=1",
            "Secret path",
            "NEED_BRYCE",
            "ZERO_AUTHORITY=only",
        )
        for marker in forbidden:
            self.assertNotIn(marker, source, marker)
        self.assertNotRegex(source, r"self\._send\((?:401|403|413|429)")

    def test_inject_is_accepted_and_hidden_only_from_legacy_imports(self):
        argv = ["mouth", "--inject", "0x01", "--port", "17777", "--go"]
        self.assertEqual(
            MOUTH._dependency_argv(argv),
            ["mouth", "--port", "17777", "--go"],
        )
        loaded = load_mouth(["mouth", "--inject", "0x01"])
        self.assertTrue(hasattr(loaded, "Handler"))

    def test_bare_public_and_legacy_prefix_routes_are_equivalent(self):
        with (
            mock.patch.object(MOUTH, "help_text", return_value="OPEN HELP"),
            mock.patch.object(MOUTH.surface, "render_board", return_value="BOARD"),
        ):
            for path in ("/help.txt", "/open/help.txt", "/old-secret/help.txt"):
                handler = FakeHandler(path)
                handler.do_GET()
                self.assertEqual(handler.status, 200, path)
                self.assertIn("OPEN HELP", handler.text)
                self.assertNotIn(handler.status, (401, 403))

    def test_page_is_tokenless_and_has_no_seat_or_size_fields(self):
        with mock.patch.object(MOUTH.surface, "render_board", return_value="BOARD"):
            body = MOUTH.page(
                q="needle",
                hits=[{"player": "ZERO", "file": "letter.md", "body": "full body"}],
            )
        self.assertIn('action="/say"', body)
        self.assertIn('action="/search"', body)
        self.assertIn("full body", body)
        self.assertNotIn("maxlength=", body)
        self.assertNotIn('<select name="from"', body)
        self.assertNotIn("required minlength", body)

    def test_chatgpt_and_generic_clients_receive_the_same_search_data(self):
        hits = [{"player": "ZERO", "file": "full-letter.md", "body": "needle FULL BODY"}]
        with mock.patch.object(MOUTH, "search_letters", return_value=hits):
            text_client = FakeHandler(
                "/search?q=needle&fmt=text",
                accept="text/plain",
                user_agent="ChatGPT-User",
            )
            text_client.do_GET()
            generic_client = FakeHandler(
                "/search?q=needle&fmt=text",
                accept="text/plain",
                user_agent="generic-browser",
            )
            generic_client.do_GET()
        self.assertEqual(text_client.status, 200)
        self.assertEqual(text_client.text, generic_client.text)
        self.assertIn("full-letter.md", text_client.text)
        self.assertIn("needle FULL BODY", text_client.text)

    def test_body_and_letter_are_public_and_decline_is_nonblocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            msg_dir = Path(tmp) / "msg-0001"
            msg_dir.mkdir()
            expected = b"public body bytes\x00remain exact"
            (msg_dir / "body.txt").write_bytes(expected)
            with (
                mock.patch.object(MOUTH.mstore, "msg_dir", return_value=str(msg_dir)),
                mock.patch.object(
                    MOUTH.mstore,
                    "decide",
                    side_effect=AssertionError("decline must not call the old gate"),
                ),
                mock.patch.object(
                    MOUTH.mstore,
                    "fetch_body",
                    side_effect=AssertionError("body must bypass the old gate"),
                ),
            ):
                decline = FakeHandler("/decline?id=msg-0001&hash=wrong&window=WRONG")
                decline.do_GET()
                body = FakeHandler("/body?id=msg-0001&hash=wrong&window=WRONG")
                body.do_GET()
                letter = FakeHandler("/letter/msg-0001")
                letter.do_GET()
        self.assertEqual(decline.status, 200)
        self.assertIn("blocking=NO", decline.text)
        self.assertEqual(body.status, 200)
        self.assertEqual(body.wfile.getvalue(), expected)
        self.assertEqual(letter.status, 200)
        self.assertEqual(letter.wfile.getvalue(), expected)

    def test_world_act_needs_neither_confirmation_nor_caller_id(self):
        saved = {}

        def save(kind, act_id, receipt):
            saved["kind"] = kind
            saved["id"] = act_id
            saved["receipt"] = receipt

        with (
            mock.patch.object(
                MOUTH.world,
                "handle_act",
                return_value=(200, "ACTED\n", "text/plain"),
            ),
            mock.patch.object(
                MOUTH.world,
                "handle_preview",
                return_value=(200, "PREVIEW\n", "text/plain"),
            ),
            mock.patch.object(MOUTH.mstore, "load_act_receipt", return_value=None),
            mock.patch.object(MOUTH.mstore, "save_act_receipt", side_effect=save),
        ):
            act = FakeHandler("/world/act/demo")
            act.do_GET()
            preview = FakeHandler("/world/preview/demo")
            preview.do_GET()
        self.assertEqual(act.status, 200)
        self.assertIn("confirm=NOT_REQUIRED", act.text)
        self.assertIn("ACTED", act.text)
        self.assertTrue(saved["id"].startswith("mouth-"))
        self.assertEqual(preview.status, 200)
        self.assertEqual(preview.text, "PREVIEW\n")

    def test_arbitrary_model_large_body_invalid_id_and_burst_all_post(self):
        offered = []
        delivered = []

        def store(mid, src, dest, body, extra=None):
            offered.append((mid, src, dest, body, extra))
            return {
                "id": mid,
                "claimed_from": src,
                "to": dest,
                "body_sha256": "x",
            }

        def deliver(src, dest, letter, log=None):
            delivered.append((src, dest))
            return {}

        body = ("x" * 20001) + "\x00exact"
        statuses = []
        with (
            mock.patch.object(MOUTH.mstore, "load_receipt", return_value=None),
            mock.patch.object(MOUTH.mstore, "store_offered", side_effect=store),
            mock.patch.object(MOUTH.mstore, "envelope_lines", return_value="LETTER"),
            mock.patch.object(MOUTH.mstore, "save_receipt"),
            mock.patch.object(MOUTH.route, "deliver", side_effect=deliver),
        ):
            for _ in range(21):
                handler = FakeHandler("/say")
                handler._say(
                    {
                        "from": ["FRESH_GEMINI_MODEL"],
                        "to": ["UNLISTED_BOT_ROUTE"],
                        "id": ["not a valid id"],
                        "body": [body],
                    }
                )
                statuses.append(handler.status)
        self.assertEqual(statuses, [200] * 21)
        self.assertEqual(len(offered), 21)
        self.assertTrue(all(row[0].startswith("mouth-") for row in offered))
        self.assertTrue(all(row[1] == "FRESH_GEMINI_MODEL" for row in offered))
        self.assertTrue(all(row[2] == "UNLISTED_BOT_ROUTE" for row in offered))
        self.assertTrue(all(row[3] == body for row in offered))
        self.assertEqual(
            delivered,
            [(MOUTH.OPEN_TRANSPORT_PLAYER, MOUTH.OPEN_TRANSPORT_PLAYER)] * 21,
        )

    def test_post_mail_is_tokenless(self):
        payload = urlencode({"from": "BOT", "to": "TABLE", "body": "hello"}).encode()
        with mock.patch.object(MOUTH.Handler, "_say") as say:
            handler = FakeHandler("/mail", payload=payload)
            handler.do_POST()
        say.assert_called_once()
        fields = say.call_args.args[0]
        self.assertEqual(fields["body"], ["hello"])

    def test_main_starts_without_go_and_never_builds_a_token_url(self):
        class Server:
            def __init__(self, address, handler):
                self.address = address

            def serve_forever(self):
                return None

            def server_close(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            pid = str(Path(tmp) / "MOUTH.pid")
            url = str(Path(tmp) / "MOUTH.url")
            old_argv = sys.argv[:]
            try:
                sys.argv = ["mouth", "--port", "17471"]
                with (
                    mock.patch.object(MOUTH, "PID_PATH", pid),
                    mock.patch.object(MOUTH, "URL_PATH", url),
                    mock.patch.object(MOUTH, "ThreadingHTTPServer", Server),
                    mock.patch.object(MOUTH.surface, "write_board"),
                    mock.patch.object(MOUTH, "write_url") as write,
                ):
                    self.assertEqual(MOUTH.main(), 0)
            finally:
                sys.argv = old_argv
        write.assert_called_once_with("http://127.0.0.1:17471/")
        self.assertNotIn("token", write.call_args.args[0].lower())


if __name__ == "__main__":
    unittest.main()
