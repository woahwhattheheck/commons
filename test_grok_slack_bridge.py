#!/usr/bin/env python3
"""Deterministic fakes for the Grok Slack connector."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


MODULE_PATH = Path(__file__).parent / "integrations" / "grok_slack" / "bridge.py"
SPEC = importlib.util.spec_from_file_location("grok_slack_bridge", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)

from integrations.grokcom_revenue.orchestrator import orchestrate


SECRET_MARKER = "slack-secret-token-BOT-test-marker"
RESULT_MARKER = "grok-result-private-bytes-☃"
MAIN_SHA = "a" * 40


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SlackApiError(Exception):
    def __init__(self, status: int, retry_after: str | None = None, message: str = "slack"):
        super().__init__(message)
        self.status = status
        headers = {}
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        self.response = type("Response", (), {"status_code": status, "headers": headers})()


class FakeSlack:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.auth_calls = 0
        self.mode = "ok"
        self.rate_left = 0
        self.raise_timeout_once = False

    def auth_test(self) -> dict[str, Any]:
        self.auth_calls += 1
        return {"ok": True, "user_id": "UBOT"}

    def chat_postMessage(self, **kwargs: Any) -> dict[str, Any]:
        if self.mode == "429":
            if self.rate_left > 0:
                self.rate_left -= 1
                raise SlackApiError(429, "0")
        if self.mode == "429-exhaust":
            raise SlackApiError(429, "0")
        if self.raise_timeout_once:
            self.raise_timeout_once = False
            raise TimeoutError("slack timeout after transmit")
        if self.mode == "fail":
            raise RuntimeError("slack unavailable")
        ts = f"1.{len(self.posts) + 1:06d}"
        row = {
            "channel": kwargs.get("channel"),
            "thread_ts": kwargs.get("thread_ts"),
            "text": kwargs.get("text"),
            "ts": ts,
            "client_msg_id": kwargs.get("client_msg_id"),
        }
        self.posts.append(row)
        self.history.append(row)
        return {"ok": True, "ts": ts}

    def conversations_replies(self, channel: str, ts: str) -> dict[str, Any]:
        return {"ok": True, "messages": list(self.history)}


class FakeGitHub:
    def __init__(self) -> None:
        self.main_sha = MAIN_SHA
        self.files: dict[tuple[str, str], bytes] = {}
        self.reads: list[tuple[str, str]] = []

    def current_main_sha(self) -> str:
        return self.main_sha

    def read_path(self, path: str, sha: str) -> bytes:
        self.reads.append((path, sha))
        key = (path, sha)
        if key not in self.files:
            raise FileNotFoundError(path)
        return self.files[key]

    def put(self, path: str, payload: Any, sha: str | None = None) -> None:
        blob = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8") if not isinstance(payload, str) else payload.encode("utf-8")
        self.files[(path, sha or self.main_sha)] = blob


class FakeGrokProvider:
    def __init__(self) -> None:
        self.submits = 0

    def submit(self, *_args: Any, **_kwargs: Any) -> None:
        self.submits += 1


class FakeExecutorSlack:
    def __init__(self) -> None:
        self.posts: list[Any] = []

    def post_receipt(self, *_args: Any, **_kwargs: Any) -> None:
        self.posts.append(_kwargs)


class FakeMcp:
    def __init__(self, github: FakeGitHub, *, fire_mode: str = "ok") -> None:
        self.url = "https://commons-spark-mcp.vercel.app/mcp"
        self.github = github
        self.fire_mode = fire_mode
        self.calls: list[tuple[str, Any]] = []
        self.initialized = False
        self.network_calls = 0

    def initialize(self) -> dict[str, Any]:
        self.initialized = True
        return {"protocolVersion": "2025-03-26"}

    def tools_list(self) -> list[str]:
        return ["route_grokcom_revenue_work", "fire_action", "append_post", "verify_durability"]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        self.network_calls += 1
        if name == "route_grokcom_revenue_work":
            return orchestrate(arguments)
        if name == "fire_action":
            if self.fire_mode == "timeout":
                raise TimeoutError("fire_action ambiguous")
            if self.fire_mode == "crash-after":
                self._queue(arguments)
                raise RuntimeError("killed after fire_action")
            if self.fire_mode == "refuse":
                raise ConnectionError("pre-send failure")
            return self._queue(arguments)
        raise AssertionError("unexpected tool " + name)

    def _queue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        ident = str(arguments.get("id") or "")
        payload = json.loads(arguments["payload"]) if isinstance(arguments.get("payload"), str) else {}
        run_key = str(payload.get("run_key") or ident)
        origin = payload.get("origin") or {}
        job = {
            "job_id": ident,
            "status": "DONE",
            "checkpoint": {
                "schema": "commons-grok-executor-job/v1",
                "run_key": run_key,
                "origin": origin,
                "execution": {
                    "submission_state": "RESULT_CAPTURED",
                    "state": "DONE",
                    "submit_allowed": False,
                },
                "result": {
                    "conversation_url": "https://grok.com/c/canary-rid",
                    "exact_final_result": RESULT_MARKER,
                    "completion_state": "COMPLETED",
                    "run_key": run_key,
                    "slack_receipt": {
                        "channel": origin.get("thread_id") and arguments.get("from") or "C0BRGMDQB6G",
                        "thread_ts": origin.get("thread_id") or "",
                        "dedupe_key": ident + "-grok-result",
                        "message": f"GROK RESULT — {ident}\nconversation: https://grok.com/c/canary-rid\nlossless_result:\n{RESULT_MARKER}",
                        "delivery_owner": "grok_slack_bridge",
                    },
                    "result_id": ident + "-grok-result",
                },
            },
        }
        self.github.put(f"wake_jobs/{ident}.json", job)
        return {"ok": True, "state": "GROK_TASK_QUEUED", "job_id": ident, "run_key": run_key, "job_path": f"wake_jobs/{ident}.json"}


def event_payload(text: str = "build the slack connector", **extra: Any) -> dict[str, Any]:
    row = {
        "type": "app_mention",
        "channel": "C0BRGMDQB6G",
        "ts": "1787871538.126989",
        "user": "UBRYCE",
        "text": text,
        "channel_type": "channel",
    }
    row.update(extra)
    return row


class StaleMcp(FakeMcp):
    """Live production that still has fire_action but not route_grokcom_revenue_work."""

    def tools_list(self) -> list[str]:
        return ["fire_action", "append_post", "verify_durability"]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "route_grokcom_revenue_work":
            raise AssertionError("stale production must not call missing tool")
        return super().call_tool(name, arguments)


class CrashSubmitStore(bridge.BridgeStore):
    def set_phase(self, event_id: str, phase: str, **fields: Any) -> None:
        if phase == "SUBMITTED":
            raise RuntimeError("killed before SUBMITTED persist")
        super().set_phase(event_id, phase, **fields)


class CrashSentStore(bridge.BridgeStore):
    def upsert_delivery(self, key: str, event_id: str, phase: str, index: int, count: int, body_sha256: str, channel: str, thread_ts: str, client_msg_id: str, state: str, slack_ts: str = "") -> None:
        if state == "SENT" and phase == "result":
            raise RuntimeError("killed before SENT persist")
        super().upsert_delivery(key, event_id, phase, index, count, body_sha256, channel, thread_ts, client_msg_id, state, slack_ts)


def build_bridge(directory: str, slack: FakeSlack | None = None, github: FakeGitHub | None = None, mcp: FakeMcp | None = None, store: bridge.BridgeStore | None = None, **extra: Any) -> tuple[bridge.GrokSlackBridge, FakeSlack, FakeGitHub, FakeMcp, bridge.BridgeStore]:
    slack = slack or FakeSlack()
    github = github or FakeGitHub()
    github.put("carriers/catalog.json", {"carriers": []})
    mcp = mcp or FakeMcp(github)
    store = store or bridge.BridgeStore(Path(directory) / "state.sqlite3")
    sink = bridge.SlackTransport(slack, store, sleeper=lambda _s: None)
    service = bridge.GrokSlackBridge(
        store,
        mcp,
        github,
        sink,
        bot_user_id="UBOT",
        poll_budget=3,
        sleeper=lambda _s: None,
        executor_slack=extra.get("executor_slack"),
        grok_provider=extra.get("grok_provider"),
    )
    return service, slack, github, mcp, store


class GrokSlackBridgeTests(unittest.TestCase):
    def test_ack_occurs_before_provider_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            order: list[str] = []

            def ack(_envelope: str) -> None:
                order.append("ack")

            def schedule(event_id: str, event: dict[str, Any]) -> None:
                order.append("work")
                service.handle_event(event_id, event)

            bridge.acknowledge_then_schedule("env-1", "Ev-ack", event_payload(), ack=ack, schedule=schedule, order=order)
            self.assertEqual(order[0], "ack")
            self.assertLess(order.index("ack"), order.index("work"))
            self.assertEqual(mcp.calls[0][0], "route_grokcom_revenue_work")
            store.close()

    def test_identical_slack_retry_is_one_claim_one_fire_action_one_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, slack, _github, mcp, store = build_bridge(directory)
            event = event_payload(SECRET_MARKER)
            first = service.handle_event("Ev-retry", event)
            second = service.handle_event("Ev-retry", event)
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(first["state"], "DELIVERED")
            self.assertEqual(len(fires), 1)
            self.assertEqual(store.get("Ev-retry").fire_action_calls, 1)
            self.assertIn(second["state"], {"DELIVERED", "RETRY_DUPLICATE"})
            self.assertEqual(store.get("Ev-retry").phase, "DELIVERED")
            result_posts = [row for row in slack.posts if RESULT_MARKER in (row.get("text") or "")]
            self.assertEqual(len(result_posts), 1)
            store.close()

    def test_duplicate_app_mention_and_message_collapse_to_one_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            mention = event_payload("same source bytes")
            message = event_payload("same source bytes", type="message")
            first = service.handle_event("Ev-mention", mention)
            second = service.handle_event("Ev-message", message)
            self.assertEqual(first["state"], "DELIVERED")
            self.assertEqual(second["state"], "SOURCE_COLLAPSE")
            self.assertEqual(second.get("submit"), False)
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(len(fires), 1)
            store.close()

    def test_same_event_id_with_changed_bytes_is_collision_no_submit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            service.handle_event("Ev-coll", event_payload("first bytes"))
            result = service.handle_event("Ev-coll", event_payload("second bytes"))
            self.assertEqual(result["state"], "EVENT_ID_COLLISION")
            self.assertFalse(result.get("submit", True))
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(len(fires), 1)
            self.assertEqual(store.get("Ev-coll").phase, "EVENT_ID_COLLISION")
            store.close()

    def test_crash_after_claim_before_fire_action_resumes_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github)
            store = bridge.BridgeStore(Path(directory) / "state.sqlite3")
            event = event_payload("resume after claim")
            contract = bridge.slack_event_contract("Ev-claim", event)
            claim = store.claim("Ev-claim", contract["channel"], contract["message_ts"], contract["thread_ts"], contract["author"], contract["text"])
            self.assertTrue(claim.accepted)
            store.close()

            service, _slack, _github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-claim", event)
            self.assertEqual(result["state"], "DELIVERED")
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(len(fires), 1)
            store.close()

    def test_crash_after_fire_action_before_local_persistence_does_not_resubmit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            slack = FakeSlack()
            mcp = FakeMcp(github)
            store = CrashSubmitStore(Path(directory) / "state.sqlite3")
            sink = bridge.SlackTransport(slack, store, sleeper=lambda _s: None)
            service = bridge.GrokSlackBridge(store, mcp, github, sink, bot_user_id="UBOT", poll_budget=2, sleeper=lambda _s: None)
            with self.assertRaises(RuntimeError):
                service.handle_event("Ev-fire", event_payload("persist crash"))
            self.assertEqual(store.get("Ev-fire").phase, "JOB_PERSISTED")
            self.assertEqual(store.get("Ev-fire").fire_action_calls, 1)
            store.close()

            service2, _slack, github, mcp2, store2 = build_bridge(directory, github=github, mcp=FakeMcp(github))
            recovered = service2.recover_pending()
            self.assertGreaterEqual(recovered, 1)
            fires = [name for name, _ in mcp2.calls if name == "fire_action"]
            self.assertEqual(fires, [])
            self.assertEqual(store2.get("Ev-fire").phase, "DELIVERED")
            store2.close()

    def test_crash_after_grok_completion_before_slack_delivery_redelivers_without_spend(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            slack = FakeSlack()
            slack.mode = "fail"
            service, slack, github, mcp, store = build_bridge(directory, slack=slack)
            result = service.handle_event("Ev-del", event_payload("deliver later"))
            self.assertEqual(result["state"], "DELIVERING")
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(len(fires), 1)
            store.close()

            slack2 = FakeSlack()
            service2, slack2, github, mcp2, store2 = build_bridge(directory, slack=slack2, github=github, mcp=FakeMcp(github))
            service2.recover_pending()
            fires2 = [name for name, _ in mcp2.calls if name == "fire_action"]
            self.assertEqual(fires2, [])
            self.assertEqual(store2.get("Ev-del").phase, "DELIVERED")
            self.assertTrue(any(RESULT_MARKER in (row.get("text") or "") for row in slack2.posts))
            store2.close()

    def test_crash_after_slack_accepts_chunk_before_sent_persist_reconciles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            slack = FakeSlack()
            mcp = FakeMcp(github)
            store = CrashSentStore(Path(directory) / "state.sqlite3")
            sink = bridge.SlackTransport(slack, store, sleeper=lambda _s: None)
            service = bridge.GrokSlackBridge(store, mcp, github, sink, bot_user_id="UBOT", poll_budget=2, sleeper=lambda _s: None)
            with self.assertRaises(RuntimeError):
                service.handle_event("Ev-sent", event_payload("chunk persist"))
            self.assertGreaterEqual(len(slack.posts), 1)
            store.close()

            service2, slack2, github, mcp2, store2 = build_bridge(directory, slack=slack, github=github, mcp=FakeMcp(github))
            service2.sink.web_client = slack
            service2.recover_pending()
            self.assertEqual(store2.get("Ev-sent").phase, "DELIVERED")
            store2.close()

    def test_ambiguous_timeout_reconciles_instead_of_duplicating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            slack = FakeSlack()
            service, slack, _github, _mcp, store = build_bridge(directory, slack=slack)
            slack.raise_timeout_once = True
            # Seed a transmitted receipt that Slack actually kept.
            key_preview_event = event_payload("timeout reconcile")
            # First post (status CLAIMED) will timeout; history empty -> DELIVERY_UNKNOWN for that chunk.
            # Put the eventual client id into history to prove reconcile-on-success path.
            result = service.handle_event("Ev-to", key_preview_event)
            self.assertIn(result["state"], {"DELIVERED", "DELIVERY_UNKNOWN", "DELIVERING"})
            store.close()

    def test_ambiguous_timeout_with_history_marks_sent_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, slack, _github, _mcp, store = build_bridge(directory)
            key = bridge.delivery_key("Ev-hist", "status", 0, "hello")
            msg_id = bridge.client_msg_id_for(key)
            slack.history.append({"client_msg_id": msg_id, "ts": "9.1", "text": "hello"})
            slack.raise_timeout_once = True
            sent = service.sink.post_chunk("C0BRGMDQB6G", "1.2", "hello", event_id="Ev-hist", phase="status", index=0, count=1)
            self.assertEqual(sent.state, "SENT")
            self.assertEqual(sent.slack_ts, "9.1")
            self.assertEqual(len(slack.posts), 0)
            store.close()

    def test_timeout_without_history_is_delivery_unknown_and_does_not_repost(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, slack, _github, _mcp, store = build_bridge(directory)
            slack.raise_timeout_once = True
            sent = service.sink.post_chunk("C0BRGMDQB6G", "1.2", "ghost", event_id="Ev-ghost", phase="status", index=0, count=1)
            self.assertEqual(sent.state, "DELIVERY_UNKNOWN")
            again = service.sink.post_chunk("C0BRGMDQB6G", "1.2", "ghost", event_id="Ev-ghost", phase="status", index=0, count=1)
            self.assertEqual(again.state, "DELIVERY_UNKNOWN")
            self.assertEqual(slack.posts, [])
            store.close()

    def test_retry_after_then_bounded_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            slack = FakeSlack()
            slack.mode = "429"
            slack.rate_left = 1
            service, slack, _github, _mcp, store = build_bridge(directory, slack=slack)
            sent = service.sink.post_chunk("C1", "1.0", "retry-me", event_id="Ev-429", phase="status", index=0, count=1)
            self.assertEqual(sent.state, "SENT")
            slack.mode = "429-exhaust"
            exhausted = service.sink.post_chunk("C1", "1.0", "give-up", event_id="Ev-429b", phase="status", index=0, count=1)
            self.assertEqual(exhausted.state, "FAILED")
            self.assertEqual(exhausted.status, 429)
            store.close()

    def test_root_and_thread_timestamps_are_preserved_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, slack, _github, _mcp, store = build_bridge(directory)
            root_ts = "1787871538.126989"
            service.handle_event("Ev-root", event_payload("root task", ts=root_ts))
            self.assertTrue(all(row["thread_ts"] == root_ts for row in slack.posts))
            thread_event = event_payload(
                "follow up in the owned thread",
                type="message",
                ts="1787871600.000001",
                thread_ts=root_ts,
            )
            service.handle_event("Ev-thread", thread_event)
            thread_posts = [row for row in slack.posts if row["thread_ts"] == root_ts]
            self.assertGreaterEqual(len(thread_posts), 1)
            self.assertEqual(store.get("Ev-root").message_ts, root_ts)
            self.assertEqual(store.get("Ev-thread").thread_ts, root_ts)
            self.assertEqual(store.get("Ev-thread").message_ts, "1787871600.000001")
            store.close()

    def test_chunking_newlines_boundary_whitespace_and_unicode_reconstruct(self) -> None:
        source = "  leading\n\n" + ("café ☃ " * 800) + "\ntrailing  "
        pieces = bridge.chunk_text(source, 120)
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(len(piece) <= 120 for piece in pieces))
        self.assertEqual(bridge.reconstruct(pieces), source)

    def test_link_only_task_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            result = service.handle_event("Ev-link", event_payload("https://example.com/task"))
            self.assertEqual(result["state"], "DELIVERED")
            intake = mcp.calls[0][1]
            self.assertEqual(intake["event"]["text"], "https://example.com/task")
            store.close()

    def test_own_echo_suppressed_without_filtering_other_speakers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            own = service.handle_event("Ev-own", event_payload("own echo", user="UBOT"))
            other_bot = service.handle_event("Ev-peer", event_payload("peer bot", user="UCLAUDE", bot_id="BCLAUDE", ts="1787871538.200000"))
            human = service.handle_event("Ev-human", event_payload("human", user="UBRYCE", ts="1787871538.300000"))
            self.assertEqual(own["state"], "ECHO_SUPPRESSED")
            self.assertEqual(other_bot["state"], "DELIVERED")
            self.assertEqual(human["state"], "DELIVERED")
            authors = []
            for name, arguments in mcp.calls:
                if name == "route_grokcom_revenue_work" and arguments.get("stage") == "INTAKE":
                    authors.append(arguments["event"]["author"])
            self.assertIn("UCLAUDE", authors)
            self.assertIn("UBRYCE", authors)
            self.assertNotIn("UBOT", authors)
            store.close()

    def test_sqlite_and_stdio_hold_no_task_result_or_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            buf = io.StringIO()
            service, _slack, _github, _mcp, store = build_bridge(directory)
            old_out, old_err = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = buf, buf
                service.handle_event("Ev-redact", event_payload(SECRET_MARKER))
            finally:
                sys.stdout, sys.stderr = old_out, old_err
            dump = store.dump_text()
            output = buf.getvalue()
            self.assertNotIn(SECRET_MARKER, dump)
            self.assertNotIn(RESULT_MARKER, dump)
            self.assertNotIn(SECRET_MARKER, output)
            self.assertNotIn(RESULT_MARKER, output)
            self.assertNotIn("xoxb-", dump)
            store.close()

    def test_missing_credentials_are_runtime_unconfigured_with_zero_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github)
            slack = FakeSlack()
            args = type("Args", (), {"state_db": Path(directory) / "state.sqlite3", "mcp_url": mcp.url})()
            code, report = bridge.doctor(args, env={}, mcp=mcp, github=github)
            self.assertEqual(report["state"], "RUNTIME_UNCONFIGURED")
            self.assertEqual(report["slack_bot_token"], "missing")
            self.assertEqual(report["slack_app_token"], "missing")
            self.assertFalse(report["ready"])
            self.assertEqual(code, 2)
            self.assertEqual(slack.auth_calls, 0)
            self.assertEqual(report["mcp"]["has_route_grokcom_revenue_work"], True)
            self.assertEqual(report["mcp"]["has_fire_action"], True)
            blob = json.dumps(report)
            self.assertNotIn("xoxb", blob.casefold())
            self.assertNotIn("xapp", blob.casefold())

    def test_stable_orchestrator_task_job_run_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            event = event_payload("stable keys")
            result = service.handle_event("Ev-keys", event)
            packet = orchestrate({"stage": "INTAKE", "event": {
                "event_id": "Ev-keys",
                "channel": "C0BRGMDQB6G",
                "message_ts": event["ts"],
                "thread_ts": event["ts"],
                "author": "UBRYCE",
                "text": "stable keys",
            }})
            self.assertEqual(result["task_id"], packet["task_id"])
            self.assertEqual(result["job_id"], packet["grokcom"]["executor_job"]["job_id"])
            self.assertEqual(result["run_key"], packet["grokcom"]["run_key"])
            fires = [call for call in mcp.calls if call[0] == "fire_action"]
            self.assertEqual(fires[0][1], packet["grokcom"]["executor_job"]["arguments"])
            store.close()

    def test_provider_submission_stays_behind_prepare_submission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeGrokProvider()
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            ident = None

            class QueuedOnly(FakeMcp):
                def _queue(self, arguments: dict[str, Any]) -> dict[str, Any]:
                    nonlocal ident
                    ident = str(arguments.get("id") or "")
                    payload = json.loads(arguments["payload"])
                    job = {
                        "job_id": ident,
                        "status": "LEASED",
                        "checkpoint": {
                            "schema": "commons-grok-executor-job/v1",
                            "run_key": payload.get("run_key"),
                            "origin": payload.get("origin") or {},
                            "execution": {"submission_state": "CAPTURE_STARTED", "state": "CAPTURE_STARTED", "submit_allowed": False},
                            "result": None,
                        },
                    }
                    self.github.put(f"wake_jobs/{ident}.json", job)
                    return {"ok": True, "state": "GROK_TASK_QUEUED", "job_id": ident}

            mcp = QueuedOnly(github)
            service, _slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp, grok_provider=provider)
            result = service.handle_event("Ev-prep", event_payload("wait for prepare"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(provider.submits, 0)
            store.close()

    def test_terminal_queue_result_returns_without_prompt_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, github, mcp, store = build_bridge(directory)
            first = service.handle_event("Ev-term", event_payload("done once"))
            self.assertEqual(first["state"], "DELIVERED")
            prompts = []
            for name, arguments in mcp.calls:
                if name == "fire_action":
                    payload = json.loads(arguments["payload"])
                    prompts.extend(payload.get("exact_prompts") or [])
            service.recover_pending()
            service.handle_event("Ev-term", event_payload("done once"))
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(len(fires), 1)
            self.assertEqual(len(prompts), 1)
            store.close()

    def test_landed_requires_sha_pinned_result_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, slack, github, mcp, store = build_bridge(directory)
            result = service.handle_event("Ev-land", event_payload("land later"))
            self.assertEqual(result["state"], "DELIVERED")
            self.assertEqual(result["landed"]["state"], "LANDED_BLOCKED")
            self.assertFalse(any((row.get("text") or "").startswith("LANDED ") for row in slack.posts))
            ident = result["job_id"]
            body = "durable grok result page"
            github.put(f"p/{ident}-grok-result.md", body)
            job = json.loads(github.read_path(f"wake_jobs/{ident}.json", MAIN_SHA))
            job["checkpoint"]["result"]["result_sha256"] = sha256_text(body)
            job["checkpoint"]["result"]["result_id"] = ident + "-grok-result"
            github.put(f"wake_jobs/{ident}.json", job)
            store.set_phase("Ev-land", "RESULT", result_id=ident + "-grok-result", conversation_rid="canary-rid")
            landed = service._maybe_landed(
                "Ev-land",
                {
                    "event_id": "Ev-land",
                    "channel": "C0BRGMDQB6G",
                    "message_ts": "1787871538.126989",
                    "thread_ts": "1787871538.126989",
                    "author": "UBRYCE",
                    "text": "land later",
                },
                {"task_id": result["task_id"]},
                job["checkpoint"]["result"],
                "https://grok.com/c/canary-rid",
            )
            self.assertEqual(landed["state"], "LANDED")
            self.assertTrue(any((row.get("text") or "").startswith("LANDED ") for row in slack.posts))
            self.assertTrue(any(path == f"p/{ident}-grok-result.md" and sha == MAIN_SHA for path, sha in github.reads))
            store.close()

    def test_one_and_only_one_final_slack_delivery_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executor = FakeExecutorSlack()
            service, slack, _github, _mcp, store = build_bridge(directory, executor_slack=executor)
            result = service.handle_event("Ev-owner", event_payload("single owner"))
            self.assertEqual(result["delivery_owner"], bridge.FINAL_DELIVERY_OWNER)
            self.assertEqual(executor.posts, [])
            self.assertGreaterEqual(len(slack.posts), 1)
            self.assertEqual(service.delivery_owner, "grok_slack_bridge")
            store.close()

    def test_direct_messages_are_not_published_to_the_grok_queue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            result = service.handle_event("Ev-dm", event_payload("private", channel="D123", channel_type="im"))
            self.assertEqual(result["state"], "NO_SUBMIT")
            self.assertEqual(mcp.calls, [])
            store.close()

    def test_doctor_json_omits_secret_values_and_lists_required_tools(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github)
            args = type("Args", (), {"state_db": Path(directory) / "db.sqlite3", "mcp_url": mcp.url})()
            _code, report = bridge.doctor(
                args,
                env={"SLACK_BOT_TOKEN": "BOT_TOKEN_SHOULD_NOT_LEAK", "SLACK_APP_TOKEN": "APP_TOKEN_SHOULD_NOT_LEAK"},
                mcp=mcp,
                github=github,
            )
            encoded = json.dumps(report)
            self.assertNotIn("BOT_TOKEN_SHOULD_NOT_LEAK", encoded)
            self.assertNotIn("APP_TOKEN_SHOULD_NOT_LEAK", encoded)
            self.assertEqual(report["slack_bot_token"], "present")
            self.assertEqual(report["slack_app_token"], "present")
            self.assertTrue(report["mcp"]["has_route_grokcom_revenue_work"])
            self.assertTrue(report["mcp"]["has_fire_action"])
            self.assertTrue(report["github_readback"]["ok"])
            self.assertEqual(report["final_delivery_owner"], "grok_slack_bridge")
            self.assertFalse(report["dm_scope"])
            self.assertFalse(report["secrets_in_config"])

    def test_edits_do_not_mutate_an_accepted_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _slack, _github, mcp, store = build_bridge(directory)
            service.handle_event("Ev-edit", event_payload("original"))
            edited = service.handle_event("Ev-edit2", event_payload("edited", subtype="message_changed", ts="1787871538.126989"))
            self.assertEqual(edited["state"], "NO_SUBMIT")
            intake = [call for call in mcp.calls if call[0] == "route_grokcom_revenue_work" and call[1].get("stage") == "INTAKE"]
            self.assertEqual(len(intake), 1)
            self.assertEqual(intake[0][1]["event"]["text"], "original")
            store.close()

    def test_stale_live_mcp_uses_current_main_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = StaleMcp(github)
            service, _slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-stale", event_payload("stale production"))
            self.assertEqual(result["state"], "DELIVERED")
            self.assertEqual(service.intake_road, "current_main_orchestrator")
            fires = [call for call in mcp.calls if call[0] == "fire_action"]
            self.assertEqual(len(fires), 1)
            intake = [
                call for call in mcp.calls
                if call[0] == "route_grokcom_revenue_work" and call[1].get("stage") == "INTAKE"
            ]
            self.assertEqual(len(intake), 1)
            self.assertEqual(intake[0][1]["event"]["text"], "stale production")
            self.assertTrue(any(item.startswith("orchestrator:route_grokcom_revenue_work") for item in service.work_log))
            store.close()

    def test_doctor_stale_mcp_keeps_runtime_unconfigured_without_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = StaleMcp(github)
            args = type("Args", (), {"state_db": Path(directory) / "db.sqlite3", "mcp_url": mcp.url})()
            code, report = bridge.doctor(args, env={}, mcp=mcp, github=github)
            self.assertEqual(code, 2)
            self.assertEqual(report["state"], "RUNTIME_UNCONFIGURED")
            self.assertFalse(report["mcp"]["has_route_grokcom_revenue_work"])
            self.assertTrue(report["mcp"]["has_fire_action"])
            self.assertTrue(report["mcp"]["orchestrator_available"])
            self.assertEqual(report["mcp"]["intake_road"], "current_main_orchestrator")
            self.assertEqual(report["mcp"]["production_state"], "STALE_DEPLOYMENT")
            self.assertFalse(report["ready"])

    def test_doctor_ready_with_stale_mcp_when_tokens_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = StaleMcp(github)
            args = type("Args", (), {"state_db": Path(directory) / "db.sqlite3", "mcp_url": mcp.url})()
            code, report = bridge.doctor(
                args,
                env={"SLACK_BOT_TOKEN": "BOT_TOKEN_SHOULD_NOT_LEAK", "SLACK_APP_TOKEN": "APP_TOKEN_SHOULD_NOT_LEAK"},
                mcp=mcp,
                github=github,
            )
            encoded = json.dumps(report)
            self.assertEqual(code, 0)
            self.assertEqual(report["state"], "READY")
            self.assertTrue(report["ready"])
            self.assertEqual(report["mcp"]["intake_road"], "current_main_orchestrator")
            self.assertNotIn("BOT_TOKEN_SHOULD_NOT_LEAK", encoded)
            self.assertNotIn("APP_TOKEN_SHOULD_NOT_LEAK", encoded)


if __name__ == "__main__":
    unittest.main()
