import base64
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parent / "integrations" / "gemini_slack" / "upstream_turn.py"
SPEC = importlib.util.spec_from_file_location("gemini_upstream_turn", MODULE_PATH)
turn = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = turn
SPEC.loader.exec_module(turn)


def _completed(request_id, text):
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return {
        "ok": True,
        "request_id": request_id,
        "event": {
            "request_id": request_id,
            "status": "completed",
            "reply": text,
            "reply_utf8_base64": encoded,
        },
    }


class UpstreamTurnTests(unittest.TestCase):
    def test_submit_once_and_return_completed_reply(self):
        posts = []
        gets = []

        def post_json(url, payload, *, timeout):
            posts.append((url, payload, timeout))
            return {"ok": True, "request_id": "abc_1"}

        def get_json(url, *, timeout):
            gets.append((url, timeout))
            return _completed("abc_1", "snowman ☃")

        reply = turn.wait_peer_turn(
            "http://127.0.0.1:8866/",
            "TESSERA",
            "look around",
            post_json=post_json,
            get_json=get_json,
        )
        self.assertEqual(reply, "snowman ☃")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][0], "http://127.0.0.1:8866/v1/message")
        self.assertIs(posts[0][1]["async"], True)
        self.assertNotIn("message", posts[0][1])
        decoded = base64.b64decode(posts[0][1]["message_utf8_base64"]).decode("utf-8")
        self.assertEqual(decoded, "look around")
        self.assertEqual(len(gets), 1)
        self.assertTrue(gets[0][0].startswith("http://127.0.0.1:8866/v1/requests/abc_1?"))

    def test_status_failures_retry_the_same_handle_without_resubmit(self):
        posts = []
        gets = []

        def post_json(url, payload, *, timeout):
            posts.append(payload)
            return {"ok": True, "request_id": "keep-me"}

        def get_json(url, *, timeout):
            gets.append(url)
            if len(gets) < 3:
                raise OSError("temporary")
            return _completed("keep-me", "recovered")

        with mock.patch.object(turn.time, "sleep"):
            reply = turn.wait_peer_turn(
                "http://127.0.0.1:9",
                "AURORA",
                "hi",
                post_json=post_json,
                get_json=get_json,
            )
        self.assertEqual(reply, "recovered")
        self.assertEqual(len(posts), 1)
        self.assertEqual(len(gets), 3)
        self.assertTrue(all("keep-me" in url for url in gets))

    def test_third_status_failure_keeps_handle_and_does_not_resubmit(self):
        posts = []

        def post_json(url, payload, *, timeout):
            posts.append(payload)
            return {"ok": True, "request_id": "lost-poll"}

        def get_json(url, *, timeout):
            raise TimeoutError("status down")

        with mock.patch.object(turn.time, "sleep"):
            with self.assertRaises(turn.UpstreamTurnError) as raised:
                turn.wait_peer_turn(
                    "http://127.0.0.1:9",
                    "AURORA",
                    "hi",
                    post_json=post_json,
                    get_json=get_json,
                )
        self.assertEqual(len(posts), 1)
        details = raised.exception.details
        self.assertEqual(details["upstream_request_id"], "lost-poll")
        self.assertIn("/v1/requests/lost-poll", details["upstream_status_url"])
        self.assertIs(details["upstream_terminal"], False)
        self.assertIn("status reads failed", str(raised.exception))

    def test_lost_submit_response_is_not_replayed(self):
        posts = []

        def post_json(url, payload, *, timeout):
            posts.append(payload)
            raise OSError("connection reset after accept")

        def get_json(url, *, timeout):
            raise AssertionError("status must not be read without a handle")

        with self.assertRaises(turn.UpstreamTurnError) as raised:
            turn.wait_peer_turn(
                "http://127.0.0.1:9",
                "AURORA",
                "hi",
                post_json=post_json,
                get_json=get_json,
            )
        self.assertEqual(len(posts), 1)
        details = raised.exception.details
        self.assertIsNone(details["upstream_request_id"])
        self.assertIn("was not replayed", str(raised.exception))
        self.assertIs(details["upstream_terminal"], False)

    def test_terminal_upstream_error_keeps_handle(self):
        submitted = []

        def post_json(url, payload, *, timeout):
            submitted.append(True)
            return {"ok": True, "request_id": "err1"}

        def get_json(url, *, timeout):
            return {
                "ok": True,
                "request_id": "err1",
                "event": {
                    "request_id": "err1",
                    "status": "error",
                    "error": "ProviderTimeout",
                },
            }

        with self.assertRaises(turn.UpstreamTurnError) as raised:
            turn.wait_peer_turn(
                "http://127.0.0.1:9",
                "AURORA",
                "hi",
                post_json=post_json,
                get_json=get_json,
            )
        self.assertEqual(submitted, [True])
        details = raised.exception.details
        self.assertEqual(details["upstream_request_id"], "err1")
        self.assertEqual(details["upstream_status"], "error")
        self.assertIs(details["upstream_terminal"], True)
        self.assertEqual(details["upstream_error"], "ProviderTimeout")

    def test_cancel_after_submit_stops_observation_without_resubmit(self):
        posts = []
        state = {"cancel": False}

        def post_json(url, payload, *, timeout):
            posts.append(payload)
            state["cancel"] = True
            return {"ok": True, "request_id": "live1"}

        def get_json(url, *, timeout):
            raise AssertionError("cancelled observer must not poll")

        with self.assertRaises(InterruptedError):
            turn.wait_peer_turn(
                "http://127.0.0.1:9",
                "AURORA",
                "hi",
                post_json=post_json,
                get_json=get_json,
                cancelled=lambda: state["cancel"],
                on_submitted=lambda details: self.assertEqual(
                    details["upstream_request_id"], "live1"
                ),
            )
        self.assertEqual(len(posts), 1)


if __name__ == "__main__":
    unittest.main()
