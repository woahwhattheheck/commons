#!/usr/bin/env python3
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest import mock

import ntfy_relays


class Response:
    def __init__(self, body=b"", status=200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def event(post_id, host, body="body", *, event_id="event", carrier_origin=None):
    payload = {"id": post_id, "body": body}
    if carrier_origin:
        payload["carrier_origin"] = carrier_origin
    message = json.dumps(payload)
    return {
        "id": post_id,
        "message": message,
        "payload": payload,
        "host": host,
        "source_host": host,
        "carrier_origin": carrier_origin or host,
        "event_id": event_id,
    }


class NtfyRelaysTests(unittest.TestCase):
    def test_poll_parses_messages_and_preserves_transport_origin(self):
        rows = [
            {"event": "open", "id": "open"},
            {"event": "message", "id": "one", "message": json.dumps({"id": "post-a", "body": "A"})},
            {
                "event": "message",
                "id": "two",
                "message": json.dumps(
                    {"id": "post-b", "body": "B", "carrier_origin": "https://origin.example/"}
                ),
            },
            {"event": "message", "id": "three", "message": "not-json"},
        ]
        raw = ("not-json\n" + "\n".join(json.dumps(row) for row in rows)).encode()
        with mock.patch.object(
            ntfy_relays.urllib.request, "urlopen", return_value=Response(raw)
        ) as urlopen:
            with redirect_stdout(io.StringIO()):
                got = ntfy_relays.poll("https://relay.example/")

        self.assertEqual([row["id"] for row in got], ["post-a", "post-b", None])
        self.assertEqual(got[0]["source_host"], "https://relay.example")
        self.assertEqual(got[0]["carrier_origin"], "https://relay.example")
        self.assertEqual(got[1]["carrier_origin"], "https://origin.example")
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://relay.example/woahwhattheheck-commons-board/json?poll=1&since=24h",
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 30)

    def test_poll_failure_paths_are_empty_and_mocked(self):
        failures = [
            urllib.error.URLError("offline"),
            TimeoutError("late"),
            OSError("socket"),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with mock.patch.object(
                    ntfy_relays.urllib.request, "urlopen", side_effect=failure
                ):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(ntfy_relays.poll("https://relay.example"), [])

    def test_union_is_deterministic_by_post_id_and_keeps_all_origins(self):
        rows = [
            event("post-z", "https://z.example", event_id="2"),
            event("post-a", "https://b.example", event_id="9"),
            event("post-z", "https://a.example", event_id="1"),
            {"id": None, "message": "ignored", "host": "https://c.example"},
        ]
        forward = ntfy_relays.union_events(rows)
        reverse = ntfy_relays.union_events(list(reversed(rows)))

        self.assertEqual(forward, reverse)
        self.assertEqual([row["id"] for row in forward], ["post-a", "post-z"])
        merged = forward[1]
        self.assertEqual(merged["source_host"], "https://a.example")
        self.assertEqual(
            merged["source_hosts"], ["https://a.example", "https://z.example"]
        )
        self.assertEqual(
            merged["carrier_origins"], ["https://a.example", "https://z.example"]
        )

    def test_relay_message_preserves_id_body_and_origin_as_data(self):
        row = event(
            "caller-stable-id",
            "https://relay.example",
            body="same body",
            carrier_origin="https://first.example",
        )
        row["source_hosts"] = ["https://relay.example"]
        row["carrier_origins"] = ["https://first.example", "https://relay.example"]

        payload = json.loads(ntfy_relays.relay_message(row))

        self.assertEqual(payload["id"], "caller-stable-id")
        self.assertEqual(payload["body"], "same body")
        self.assertEqual(payload["source_host"], "https://relay.example")
        self.assertEqual(payload["carrier_origin"], "https://first.example")
        self.assertNotIn("relay.example", payload["id"])

    def test_relay_message_refuses_to_rewrite_an_inconsistent_id(self):
        row = event("caller-stable-id", "https://relay.example")
        row["id"] = "different-id"
        with self.assertRaises(ValueError):
            ntfy_relays.relay_message(row)

    def test_replay_success_http_failure_and_network_failures_are_mocked(self):
        with mock.patch.object(
            ntfy_relays.urllib.request, "urlopen", return_value=Response(status=202)
        ) as urlopen:
            self.assertTrue(ntfy_relays.replay('{"id":"same-id"}'))
            request = urlopen.call_args.args[0]
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.data, b'{"id":"same-id"}')
            self.assertEqual(urlopen.call_args.kwargs["timeout"], 20)

        with mock.patch.object(
            ntfy_relays.urllib.request, "urlopen", return_value=Response(status=503)
        ):
            self.assertFalse(ntfy_relays.replay("body"))

        for failure in [
            urllib.error.URLError("offline"),
            TimeoutError("late"),
            OSError("socket"),
        ]:
            with self.subTest(failure=type(failure).__name__):
                with mock.patch.object(
                    ntfy_relays.urllib.request, "urlopen", side_effect=failure
                ):
                    with redirect_stdout(io.StringIO()):
                        self.assertFalse(ntfy_relays.replay("body"))

    def test_main_polls_every_host_unions_once_and_skips_home_and_canonical(self):
        hosts = ["https://home.example", "https://b.example", "https://a.example"]
        polled = {
            hosts[0]: [event("on-home", hosts[0])],
            hosts[1]: [event("needs-relay", hosts[1]), event("already-landed", hosts[1])],
            hosts[2]: [event("needs-relay", hosts[2])],
        }

        with mock.patch.object(ntfy_relays, "HOSTS", hosts), mock.patch.object(
            ntfy_relays, "HOME", hosts[0]
        ), mock.patch.object(
            ntfy_relays, "poll", side_effect=lambda host: polled[host]
        ) as poll, mock.patch.object(
            ntfy_relays, "already", side_effect=lambda post_id: post_id == "already-landed"
        ), mock.patch.object(
            ntfy_relays, "replay", return_value=True
        ) as replay:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ntfy_relays.main(), 0)

        self.assertEqual([call.args[0] for call in poll.call_args_list], hosts)
        replay.assert_called_once()
        payload = json.loads(replay.call_args.args[0])
        self.assertEqual(payload["id"], "needs-relay")
        self.assertEqual(payload["source_host"], "https://a.example")
        self.assertEqual(
            payload["source_hosts"], ["https://a.example", "https://b.example"]
        )

    def test_record_relay_drop_writes_one_stable_failed_posts_row(self):
        stable = event(
            "same-id-every-time",
            "https://relay.example/",
            event_id="carrier-event",
        )
        stable["payload"].update({"from": "UNSEATED", "to": "TABLE"})
        with tempfile.TemporaryDirectory() as tmp:
            rejects_path = os.path.join(tmp, "rejects.json")
            with open(rejects_path, "w", encoding="utf-8") as handle:
                json.dump([{"id": "older", "reason": "bad-id"}], handle)
            with mock.patch.object(ntfy_relays, "REJECTS_PATH", rejects_path), mock.patch.object(
                ntfy_relays, "HOME", "https://home.example/"
            ), mock.patch.object(
                ntfy_relays, "_now_ts", return_value="2026-08-30T06:30:00Z"
            ):
                self.assertTrue(ntfy_relays.record_relay_drop(stable))
                self.assertFalse(ntfy_relays.record_relay_drop(stable))

            with open(rejects_path, encoding="utf-8") as handle:
                rows = json.load(handle)

        self.assertEqual(len(rows), 2)
        row = rows[0]
        self.assertEqual(row["id"], "same-id-every-time")
        self.assertEqual(row["pid"], "same-id-every-time")
        self.assertEqual(row["reason"], "relay-drop")
        self.assertEqual(row["host"], "https://relay.example")
        self.assertEqual(row["destination_host"], "https://home.example")
        self.assertEqual(row["event_id"], "carrier-event")
        self.assertEqual(row["from"], "UNSEATED")
        self.assertEqual(row["to"], "TABLE")
        self.assertEqual(row["state"], "INGEST_ERROR")
        self.assertIn("next run retries same-id-every-time", row["message"])
        self.assertEqual(rows[1]["id"], "older")

    def test_failed_replay_retries_the_same_id_on_the_next_run(self):
        stable = event("same-id-every-time", "https://relay.example")
        with tempfile.TemporaryDirectory() as tmp:
            rejects_path = os.path.join(tmp, "rejects.json")
            with mock.patch.object(ntfy_relays, "HOSTS", ["https://relay.example"]), mock.patch.object(
                ntfy_relays, "HOME", "https://home.example"
            ), mock.patch.object(ntfy_relays, "REJECTS_PATH", rejects_path), mock.patch.object(
                ntfy_relays, "poll", return_value=[stable]
            ), mock.patch.object(
                ntfy_relays, "already", return_value=False
            ), mock.patch.object(
                ntfy_relays, "replay", return_value=False
            ) as replay, mock.patch.object(
                ntfy_relays, "_now_ts", return_value="2026-08-30T06:30:00Z"
            ):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(ntfy_relays.main(), 0)
                    self.assertEqual(ntfy_relays.main(), 0)

            with open(rejects_path, encoding="utf-8") as handle:
                rejects = json.load(handle)

        self.assertEqual(replay.call_count, 2)
        self.assertEqual(
            [json.loads(call.args[0])["id"] for call in replay.call_args_list],
            ["same-id-every-time", "same-id-every-time"],
        )
        self.assertEqual(len(rejects), 1)
        self.assertEqual(rejects[0]["reason"], "relay-drop")
        self.assertEqual(rejects[0]["pid"], "same-id-every-time")


if __name__ == "__main__":
    unittest.main()
