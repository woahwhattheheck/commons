#!/usr/bin/env python3
"""Deterministic fakes for the Grok Slack connector."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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
CAPACITY = {
    "state": "AVAILABLE",
    "evidence": "authenticated grok.com usage indicator shows capacity",
    "observed_at": "2026-08-30T05:15:00Z",
}


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


class RejectPostFailSlack(FakeSlack):
    """Slack accepts CLAIMED/status but refuses the rejected delivery row."""

    def chat_postMessage(self, **kwargs: Any) -> dict[str, Any]:
        text = str(kwargs.get("text") or "")
        if "rejected" in text.casefold():
            raise RuntimeError("rejected delivery failed")
        return super().chat_postMessage(**kwargs)


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


class ReadOnlyGitHub(FakeGitHub):
    """Public readback without a write token — materialize must not invent a blob."""

    def put(self, path: str, payload: Any, sha: str | None = None) -> None:
        if path.startswith(("p/", "wake_jobs/", "actions/")):
            raise bridge.BridgeError("github write requires token")
        super().put(path, payload, sha)


class OfflineGitHub(bridge.GitHubReadback):
    """Production GitHubReadback class: no write token, no network, no FakeGitHub.put."""

    def __init__(self) -> None:
        super().__init__(token="")

    def current_main_sha(self) -> str:
        raise bridge.BridgeError("github unavailable")

    def read_path(self, path: str, sha: str) -> bytes:
        raise FileNotFoundError(path)

    def put(self, path: str, payload: Any, sha: str | None = None) -> None:
        if path.startswith(("p/", "wake_jobs/", "actions/")):
            raise bridge.BridgeError("github write requires token")


def _git_in(cwd: Path, args: list[str], check: bool = True, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_AUTHOR_NAME"] = "commons-test"
    env["GIT_AUTHOR_EMAIL"] = "commons-test@example.test"
    env["GIT_COMMITTER_NAME"] = "commons-test"
    env["GIT_COMMITTER_EMAIL"] = "commons-test@example.test"
    completed = subprocess.run(["git", *args], cwd=str(cwd), env=env, capture_output=True, check=False, **kwargs)
    if check and completed.returncode != 0:
        raise AssertionError("git %s failed: %s" % (args, completed.stderr.decode("utf-8", "replace")))
    return completed


def make_bare_commons_clone(directory: str) -> tuple[Path, Path]:
    """Faithful local origin: bare remote + working clone with .git and action_executor.py."""
    root = Path(directory)
    bare = root / "origin.git"
    seed = root / "seed"
    clone = root / "clone"
    _git_in(root, ["init", "--bare", "-b", "main", str(bare)])
    _git_in(root, ["clone", str(bare), str(seed)])
    (seed / "action_executor.py").write_text("# commons test fixture\n", encoding="utf-8")
    (seed / "p").mkdir()
    (seed / "wake_jobs").mkdir()
    (seed / "p" / ".gitkeep").write_text("", encoding="utf-8")
    (seed / "wake_jobs" / ".gitkeep").write_text("", encoding="utf-8")
    (seed / "README.md").write_text("commons test origin\n", encoding="utf-8")
    _git_in(seed, ["add", "-A"])
    _git_in(seed, ["-c", "commit.gpgsign=false", "commit", "-m", "seed commons clone"])
    _git_in(seed, ["push", "origin", "HEAD:main"])
    _git_in(root, ["clone", str(bare), str(clone)])
    return bare, clone


def remote_commit_files(bare: Path, commit: str) -> set[str]:
    listing = _git_in(bare, ["diff-tree", "--no-commit-id", "--name-only", "-r", commit])
    return {line.strip() for line in listing.stdout.decode("utf-8").splitlines() if line.strip()}


def remote_head(bare: Path) -> str:
    return _git_in(bare, ["rev-parse", "refs/heads/main"]).stdout.decode("utf-8").strip()


def remote_blob(bare: Path, spec: str) -> bytes:
    return _git_in(bare, ["cat-file", "-p", spec]).stdout


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
            if self.fire_mode == "timeout-after-wake":
                self._queue(arguments)
                raise TimeoutError("fire_action ambiguous after wake")
            if self.fire_mode == "crash-after":
                self._queue(arguments)
                raise RuntimeError("killed after fire_action")
            if self.fire_mode == "refuse":
                raise ConnectionError("pre-send failure")
            if self.fire_mode == "pending":
                return self._pending(arguments)
            if self.fire_mode == "pending-id-only":
                ident = str(arguments.get("id") or "")
                raise bridge.McpToolError({
                    "ok": False,
                    "isError": True,
                    "state": "DURABLE_ACTION_PENDING",
                    "code": "ACTION_RESULT_PENDING",
                    "message": "the action record is durable but its executor result is still pending",
                    "id": ident,
                    "action_record": {"id": ident},
                })
            if self.fire_mode == "pending-unlanded":
                ident = str(arguments.get("id") or "")
                raise bridge.McpToolError({
                    "ok": False,
                    "isError": True,
                    "state": "DURABLE_ACTION_PENDING",
                    "code": "ACTION_RESULT_PENDING",
                    "message": "the action record is durable but its executor result is still pending",
                    "id": ident,
                    "git_sha": MAIN_SHA,
                    "action_record": {
                        "ok": True,
                        "id": ident,
                        "git_sha": MAIN_SHA,
                        "path": f"p/{ident}.md",
                    },
                    "result_path": f"actions/results/{ident}.json",
                })
            if self.fire_mode == "schema":
                ident = str(arguments.get("id") or "")
                raise bridge.McpToolError({
                    "ok": False,
                    "isError": True,
                    "state": "INGEST_ERROR",
                    "code": "SCHEMA",
                    "message": "body must not be empty",
                    "id": ident,
                })
            return self._queue(arguments)
        raise AssertionError("unexpected tool " + name)

    def _pending(self, arguments: dict[str, Any]) -> dict[str, Any]:
        ident = str(arguments.get("id") or "")
        page = f"p/{ident}.md"
        self.github.put(page, f"from: UNSEATED\nto: TOOLS\nid: {ident}\n---\nBUILD\n")
        return {
            "ok": False,
            "isError": True,
            "state": "DURABLE_ACTION_PENDING",
            "code": "ACTION_RESULT_PENDING",
            "message": "the action record is durable but its executor result is still pending",
            "id": ident,
            "git_sha": MAIN_SHA,
            "action_record": {
                "ok": True,
                "state": "DURABLE_PAGE",
                "id": ident,
                "git_sha": MAIN_SHA,
                "path": page,
            },
            "result_path": f"actions/results/{ident}.json",
            "verify_tool": "verify_durability",
        }

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
        git_root=extra.get("git_root"),
        grokcom_capacity=extra.get("grokcom_capacity", CAPACITY),
    )
    return service, slack, github, mcp, store


class GrokSlackBridgeTests(unittest.TestCase):
    def test_unverified_capacity_is_silent_and_does_not_fire(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, slack, _github, mcp, store = build_bridge(directory, grokcom_capacity={})
            result = service.handle_event("Ev-no-capacity", event_payload("do not claim this"))
            self.assertEqual(result["state"], "WAITING_CAPACITY")
            self.assertFalse(result["submit"])
            self.assertEqual(store.get("Ev-no-capacity").phase, "WAITING_CAPACITY")
            self.assertEqual(slack.posts, [])
            self.assertEqual([name for name, _ in mcp.calls if name == "fire_action"], [])
            self.assertEqual(service.recover_pending(), 0)
            store.close()

    def test_bridge_owned_windows_subprocesses_never_open_terminal_windows(self) -> None:
        windows = bridge.subprocess_window_kwargs("win32")
        self.assertEqual(windows["creationflags"] & 0x08000000, 0x08000000)
        self.assertEqual(bridge.subprocess_window_kwargs("linux"), {})

        completed = subprocess.CompletedProcess(["git", "status"], 0, b"", b"")
        with mock.patch.object(bridge, "subprocess_window_kwargs", return_value=windows):
            with mock.patch.object(bridge.subprocess, "run", return_value=completed) as runner:
                result = bridge.run_git(["status"], cwd=Path.cwd())
        self.assertIs(result, completed)
        self.assertEqual(runner.call_args.kwargs["creationflags"] & 0x08000000, 0x08000000)

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
            service = bridge.GrokSlackBridge(store, mcp, github, sink, bot_user_id="UBOT", poll_budget=2, sleeper=lambda _s: None, grokcom_capacity=CAPACITY)
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
            service = bridge.GrokSlackBridge(store, mcp, github, sink, bot_user_id="UBOT", poll_budget=2, sleeper=lambda _s: None, grokcom_capacity=CAPACITY)
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
            }, "grokcom_capacity": CAPACITY})
            self.assertEqual(result["task_id"], packet["task_id"])
            self.assertEqual(result["job_id"], packet["grokcom"]["executor_job"]["job_id"])
            self.assertEqual(result["run_key"], packet["grokcom"]["run_key"])
            fires = [call for call in mcp.calls if call[0] == "fire_action"]
            self.assertEqual(fires[0][1], packet["grokcom"]["executor_job"]["arguments"])
            self.assertEqual(fires[0][1]["verb"], "BUILD")
            self.assertEqual(fires[0][1]["act"], "BUILD")
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

    def test_fire_action_pending_with_durable_record_is_observing_not_failed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="pending")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-pending", event_payload("accepted pending"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertNotEqual(result["state"], "FAILED")
            self.assertEqual(store.get("Ev-pending").phase, "OBSERVING")
            self.assertEqual(store.get("Ev-pending").fire_action_calls, 1)
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack.posts))
            fires = [name for name, _ in mcp.calls if name == "fire_action"]
            self.assertEqual(len(fires), 1)
            ident = store.get("Ev-pending").job_id
            run_key = store.get("Ev-pending").run_key
            FakeMcp(github)._queue({"id": ident, "payload": json.dumps({"run_key": run_key, "origin": {"thread_id": "1787871538.126989"}})})
            recovered = service.recover_pending()
            self.assertGreaterEqual(recovered, 1)
            self.assertEqual(store.get("Ev-pending").phase, "DELIVERED")
            self.assertEqual(store.get("Ev-pending").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            store.close()

    def test_fire_action_schema_rejection_posts_one_retryable_reply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="schema")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-schema", event_payload("true rejection"))
            self.assertEqual(result["state"], "FAILED")
            self.assertEqual(result.get("kind"), "rejected")
            self.assertTrue(result.get("retryable"))
            self.assertEqual(store.get("Ev-schema").phase, "FAILED")
            self.assertEqual(store.get("Ev-schema").fire_action_calls, 1)
            rejected = [row for row in slack.posts if "rejected" in (row.get("text") or "").casefold() and "SCHEMA" in (row.get("text") or "")]
            self.assertEqual(len(rejected), 1)
            self.assertIn("retryable", (rejected[0].get("text") or "").casefold())
            again = service.handle_event("Ev-schema", event_payload("true rejection"))
            self.assertEqual(again["state"], "FAILED")
            self.assertEqual(again.get("submit"), False)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            rejected_again = [row for row in slack.posts if "rejected" in (row.get("text") or "").casefold() and "SCHEMA" in (row.get("text") or "")]
            self.assertEqual(len(rejected_again), 1)
            store.close()

    def test_fire_action_timeout_with_wake_is_not_false_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="timeout-after-wake")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-to-wake", event_payload("timeout after wake"))
            self.assertEqual(result["state"], "DELIVERED")
            self.assertNotEqual(result["state"], "FAILED")
            self.assertEqual(store.get("Ev-to-wake").fire_action_calls, 1)
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack.posts))
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            store.close()

    def test_fire_action_timeout_without_wake_is_unknown_not_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="timeout")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-to-none", event_payload("timeout ambiguity"))
            self.assertEqual(result["state"], "FIRE_ACTION_UNKNOWN")
            self.assertNotEqual(result.get("kind"), "rejected")
            self.assertEqual(store.get("Ev-to-none").phase, "FIRE_ACTION_UNKNOWN")
            self.assertEqual(store.get("Ev-to-none").fire_action_calls, 1)
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack.posts))
            store.close()
            service2, _slack2, github, mcp2, store2 = build_bridge(directory, github=github, mcp=FakeMcp(github, fire_mode="timeout"))
            service2.recover_pending()
            self.assertEqual(len([name for name, _ in mcp2.calls if name == "fire_action"]), 0)
            self.assertEqual(store2.get("Ev-to-none").fire_action_calls, 1)
            store2.close()

    def test_restart_after_accepted_pending_does_not_replay_fire_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="pending")
            service, _slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-restart", event_payload("restart pending"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(store.get("Ev-restart").fire_action_calls, 1)
            ident = store.get("Ev-restart").job_id
            run_key = store.get("Ev-restart").run_key
            store.close()
            FakeMcp(github)._queue({"id": ident, "payload": json.dumps({"run_key": run_key, "origin": {}})})
            mcp2 = FakeMcp(github, fire_mode="pending")
            service2, _slack2, github, mcp2, store2 = build_bridge(directory, github=github, mcp=mcp2)
            service2.recover_pending()
            self.assertEqual(store2.get("Ev-restart").phase, "DELIVERED")
            self.assertEqual(len([name for name, _ in mcp2.calls if name == "fire_action"]), 0)
            self.assertEqual(store2.get("Ev-restart").fire_action_calls, 1)
            store2.close()

    def test_mcp_client_preserves_structured_pending_from_http_400(self) -> None:
        from urllib.error import HTTPError

        pending = {
            "ok": False,
            "state": "DURABLE_ACTION_PENDING",
            "code": "ACTION_RESULT_PENDING",
            "id": "job-pending-01",
            "git_sha": MAIN_SHA,
            "action_record": {"ok": True, "id": "job-pending-01", "git_sha": MAIN_SHA, "path": "p/job-pending-01.md"},
        }
        body = json.dumps(pending).encode("utf-8")

        def opener(request: Any, timeout: int = 0) -> Any:
            raise HTTPError(request.full_url, 400, "tool error", {}, io.BytesIO(body))

        client = bridge.CommonsMcpClient(opener=opener)
        with self.assertRaises(bridge.McpToolError) as raised:
            client.call_tool("fire_action", {"id": "job-pending-01"})
        payload = raised.exception.payload
        self.assertEqual(payload["code"], "ACTION_RESULT_PENDING")
        self.assertEqual(payload["state"], "DURABLE_ACTION_PENDING")
        self.assertTrue(bridge.has_durable_action_record(payload))
        classified = bridge.classify_fire_action(payload, raised.exception)
        self.assertEqual(classified["kind"], "accepted_pending")
        self.assertEqual(classified["phase"], "OBSERVING")
        self.assertFalse(classified["replay"])

    def test_id_only_action_record_is_not_accepted_pending(self) -> None:
        payload = {
            "ok": False,
            "isError": True,
            "state": "DURABLE_ACTION_PENDING",
            "code": "ACTION_RESULT_PENDING",
            "id": "job-id-only-01",
            "action_record": {"id": "job-id-only-01", "ok": True},
        }
        self.assertFalse(bridge.has_durable_action_record(payload))
        classified = bridge.classify_fire_action(payload, None)
        self.assertNotEqual(classified["kind"], "accepted_pending")
        self.assertEqual(classified["kind"], "pending_unverified")
        self.assertFalse(classified["replay"])
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="pending-id-only")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-id-only", event_payload("id only pending"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertNotEqual(result.get("code"), "DURABILITY_NEVER_APPEARED")
            ident = store.get("Ev-id-only").job_id
            self.assertTrue(any(path == f"wake_jobs/{ident}.json" for path, _sha in github.files))
            self.assertTrue(any(path == f"p/{ident}.md" for path, _sha in github.files))
            self.assertEqual(store.get("Ev-id-only").phase, "OBSERVING")
            self.assertEqual(store.get("Ev-id-only").fire_action_calls, 1)
            posted = [row for row in slack.posts if "DURABILITY_NEVER_APPEARED" in (row.get("text") or "")]
            self.assertEqual(len(posted), 0)
            again = service.handle_event("Ev-id-only", event_payload("id only pending"))
            self.assertEqual(again["state"], "OBSERVING")
            self.assertNotEqual(again.get("submit"), True)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            store.close()

    def test_unlanded_structured_pending_materializes_wake_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="pending-unlanded")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-unlanded", event_payload("unlanded structured pending"))
            self.assertEqual(result["state"], "OBSERVING")
            ident = store.get("Ev-unlanded").job_id
            self.assertTrue(any(path == f"wake_jobs/{ident}.json" for path, _sha in github.files))
            self.assertTrue(any(path == f"p/{ident}.md" for path, _sha in github.files))
            self.assertEqual(store.get("Ev-unlanded").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertFalse(any("DURABILITY_NEVER_APPEARED" in (row.get("text") or "") for row in slack.posts))
            store.close()

    def test_unlanded_structured_pending_stays_observing_without_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = ReadOnlyGitHub()
            github.files[("carriers/catalog.json", MAIN_SHA)] = json.dumps({"carriers": []}).encode("utf-8")
            mcp = FakeMcp(github, fire_mode="pending-unlanded")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-unlanded", event_payload("unlanded structured pending"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(result.get("reason"), "DURABILITY_PENDING")
            self.assertTrue(result.get("retryable"))
            self.assertFalse(result.get("submit", True))
            self.assertEqual(store.get("Ev-unlanded").phase, "OBSERVING")
            self.assertEqual(store.get("Ev-unlanded").fire_action_calls, 1)
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack.posts))
            self.assertTrue(
                any(str(item).startswith("materialize:") for item in service.work_log),
                "silent materialize failure: %s" % service.work_log,
            )
            inspected = {path for path, _sha in github.reads if path != "carriers/catalog.json"}
            ident = store.get("Ev-unlanded").job_id
            for path in bridge.durable_action_paths(ident):
                self.assertIn(path, inspected)
            store.close()

            mcp2 = FakeMcp(github, fire_mode="pending-unlanded")
            service2, slack2, github, mcp2, store2 = build_bridge(directory, github=github, mcp=mcp2)
            recovered = service2.recover_pending()
            self.assertEqual(recovered, 0)
            self.assertEqual(len([name for name, _ in mcp2.calls if name == "fire_action"]), 0)
            self.assertEqual(store2.get("Ev-unlanded").fire_action_calls, 1)
            self.assertEqual(store2.get("Ev-unlanded").phase, "OBSERVING")
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack2.posts))
            store2.close()

    def test_accepted_pending_still_one_fire_action_call(self) -> None:
        payload = {
            "ok": False,
            "code": "ACTION_RESULT_PENDING",
            "state": "DURABLE_ACTION_PENDING",
            "id": "job-pending-01",
            "git_sha": MAIN_SHA,
            "action_record": {"ok": True, "id": "job-pending-01", "git_sha": MAIN_SHA, "path": "p/job-pending-01.md"},
        }
        self.assertTrue(bridge.has_durable_action_record(payload))
        self.assertEqual(bridge.classify_fire_action(payload, None)["kind"], "accepted_pending")
        with tempfile.TemporaryDirectory() as directory:
            github = FakeGitHub()
            github.put("carriers/catalog.json", {"carriers": []})
            mcp = FakeMcp(github, fire_mode="pending")
            service, slack, github, mcp, store = build_bridge(directory, github=github, mcp=mcp)
            result = service.handle_event("Ev-one-call", event_payload("one call pending"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(store.get("Ev-one-call").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertFalse(any("DURABILITY_NEVER_APPEARED" in (row.get("text") or "") for row in slack.posts))
            again = service.handle_event("Ev-one-call", event_payload("one call pending"))
            self.assertEqual(again["state"], "OBSERVING")
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            store.close()

    def test_pending_durability_recovery_never_rejects_or_refires(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            github = ReadOnlyGitHub()
            github.files[("carriers/catalog.json", MAIN_SHA)] = json.dumps({"carriers": []}).encode("utf-8")
            mcp = FakeMcp(github, fire_mode="pending-unlanded")
            slack = RejectPostFailSlack()
            service, slack, github, mcp, store = build_bridge(directory, slack=slack, github=github, mcp=mcp)
            result = service.handle_event("Ev-dur-pending", event_payload("durability missing"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(result.get("reason"), "DURABILITY_PENDING")
            self.assertTrue(result.get("retryable"))
            self.assertEqual(store.get("Ev-dur-pending").phase, "OBSERVING")
            self.assertEqual(store.get("Ev-dur-pending").fire_action_calls, 1)
            self.assertFalse(store.has_sent_rejected_delivery("Ev-dur-pending"))
            self.assertTrue(any("QUEUED" in (row.get("text") or "") for row in slack.posts))
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack.posts))
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            pending = store.pending()
            self.assertEqual([row.event_id for row in pending], ["Ev-dur-pending"])
            store.close()

            slack2 = FakeSlack()
            mcp2 = FakeMcp(github, fire_mode="pending-unlanded")
            service2, slack2, github, mcp2, store2 = build_bridge(directory, slack=slack2, github=github, mcp=mcp2)
            recovered = service2.recover_pending()
            self.assertEqual(recovered, 0)
            self.assertEqual(len([name for name, _ in mcp2.calls if name == "fire_action"]), 0)
            self.assertEqual(store2.get("Ev-dur-pending").fire_action_calls, 1)
            self.assertEqual(store2.get("Ev-dur-pending").phase, "OBSERVING")
            self.assertFalse(store2.has_sent_rejected_delivery("Ev-dur-pending"))
            self.assertFalse(any("rejected" in (row.get("text") or "").casefold() for row in slack2.posts))
            store2.close()

    def test_git_clone_materialize_lands_atomic_commit_on_moving_bare_remote(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin_root = Path(directory) / "git"
            origin_root.mkdir()
            bare, clone = make_bare_commons_clone(str(origin_root))
            _git_in(clone, ["checkout", "--detach", "HEAD"])
            (clone / "dirty-untracked.txt").write_text("leave me", encoding="utf-8")
            (clone / "staged-extra.txt").write_text("already staged", encoding="utf-8")
            _git_in(clone, ["add", "staged-extra.txt"])
            github = OfflineGitHub()
            mcp = FakeMcp(FakeGitHub(), fire_mode="pending-unlanded")
            service, slack, _github, mcp, store = build_bridge(
                directory, github=github, mcp=mcp, git_root=clone,
            )
            result = service.handle_event("Ev-git-clone", event_payload("clean clone git materialize"))
            self.assertEqual(result["state"], "OBSERVING", service.work_log)
            self.assertNotEqual(result.get("code"), "DURABILITY_NEVER_APPEARED")
            ident = store.get("Ev-git-clone").job_id
            self.assertTrue(ident)
            head = remote_head(bare)
            names = remote_commit_files(bare, head)
            self.assertEqual(names, {f"p/{ident}.md", f"wake_jobs/{ident}.json"})
            page = remote_blob(bare, "HEAD:p/%s.md" % ident)
            job = remote_blob(bare, "HEAD:wake_jobs/%s.json" % ident)
            self.assertIn(ident.encode("utf-8"), page)
            self.assertIn(b"commons-grok-executor-job/v1", job)
            self.assertIn("git:materialize_wake_job", service.work_log)
            self.assertEqual(store.get("Ev-git-clone").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertFalse(any("DURABILITY_NEVER_APPEARED" in (row.get("text") or "") for row in slack.posts))
            status = _git_in(clone, ["status", "--porcelain"]).stdout.decode("utf-8")
            self.assertIn("staged-extra.txt", status)
            self.assertIn("dirty-untracked.txt", status)
            branch = _git_in(clone, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.decode("utf-8").strip()
            self.assertEqual(branch, "HEAD")
            again = service.handle_event("Ev-git-clone", event_payload("clean clone git materialize"))
            self.assertEqual(again["state"], "OBSERVING")
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertEqual(store.get("Ev-git-clone").fire_action_calls, 1)
            self.assertEqual(remote_head(bare), head)
            store.close()

    def test_git_clone_materialize_retries_when_origin_main_moves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin_root = Path(directory) / "git"
            origin_root.mkdir()
            bare, clone = make_bare_commons_clone(str(origin_root))
            hook = bare / "hooks" / "pre-receive"
            hook.write_text(
                "#!/bin/sh\n"
                "marker=\"%s\"\n"
                "if [ ! -f \"$marker\" ]; then\n"
                "  touch \"$marker\"\n"
                "  parent=$(git rev-parse refs/heads/main)\n"
                "  tree=$(git rev-parse 'refs/heads/main^{tree}')\n"
                "  moved=$(GIT_AUTHOR_NAME=llms GIT_AUTHOR_EMAIL=llms@example.test "
                "GIT_COMMITTER_NAME=llms GIT_COMMITTER_EMAIL=llms@example.test "
                "git commit-tree \"$tree\" -p \"$parent\" -m 'origin moved')\n"
                "  git update-ref refs/heads/main \"$moved\"\n"
                "  echo 'non-fast-forward: origin/main moved' >&2\n"
                "  exit 1\n"
                "fi\n"
                "exit 0\n" % (bare / "hooks" / "moved-once"),
                encoding="utf-8",
            )
            hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            github = OfflineGitHub()
            mcp = FakeMcp(FakeGitHub(), fire_mode="pending-unlanded")
            service, slack, _github, mcp, store = build_bridge(
                directory, github=github, mcp=mcp, git_root=clone,
            )
            result = service.handle_event("Ev-git-move", event_payload("moving origin git materialize"))
            self.assertEqual(result["state"], "OBSERVING", service.work_log)
            ident = store.get("Ev-git-move").job_id
            head = remote_head(bare)
            names = remote_commit_files(bare, head)
            self.assertEqual(names, {f"p/{ident}.md", f"wake_jobs/{ident}.json"})
            self.assertTrue(any("git_push_rejected" in str(item) for item in service.work_log), service.work_log)
            self.assertIn("git:materialize_wake_job", service.work_log)
            self.assertEqual(store.get("Ev-git-move").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertFalse(any("DURABILITY_NEVER_APPEARED" in (row.get("text") or "") for row in slack.posts))
            parents = _git_in(bare, ["rev-list", "--parents", "-n", "1", head]).stdout.decode("utf-8").strip().split()
            self.assertGreaterEqual(len(parents), 2)
            store.close()

    def test_git_materialize_exception_is_observable_not_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin_root = Path(directory) / "git"
            origin_root.mkdir()
            _bare, clone = make_bare_commons_clone(str(origin_root))
            github = OfflineGitHub()
            mcp = FakeMcp(FakeGitHub(), fire_mode="pending-unlanded")
            service, slack, _github, mcp, store = build_bridge(
                directory, github=github, mcp=mcp, git_root=clone,
            )

            def boom(*_args: Any, **_kwargs: Any) -> Any:
                raise RuntimeError("hidden-git-failure")

            service._git = boom  # type: ignore[method-assign]
            result = service.handle_event("Ev-git-boom", event_payload("silent exception must fail the test"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(result.get("reason"), "DURABILITY_PENDING")
            self.assertEqual(store.get("Ev-git-boom").phase, "OBSERVING")
            self.assertEqual(store.get("Ev-git-boom").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            logged = [str(item) for item in service.work_log]
            self.assertTrue(
                any("git_exception" in item and "hidden-git-failure" in item for item in logged),
                "silent exception is a test failure: %s" % logged,
            )
            self.assertTrue(any(item.startswith("materialize:") for item in logged), logged)
            store.close()

    def test_git_clone_materialize_survives_eight_origin_main_moves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin_root = Path(directory) / "git"
            origin_root.mkdir()
            bare, clone = make_bare_commons_clone(str(origin_root))
            count_file = bare / "hooks" / "move-count"
            hook = bare / "hooks" / "pre-receive"
            hook.write_text(
                "#!/bin/sh\n"
                "count_file=\"%s\"\n"
                "count=0\n"
                "if [ -f \"$count_file\" ]; then\n"
                "  count=$(cat \"$count_file\")\n"
                "fi\n"
                "if [ \"$count\" -lt 8 ]; then\n"
                "  echo $((count + 1)) > \"$count_file\"\n"
                "  parent=$(git rev-parse refs/heads/main)\n"
                "  tree=$(git rev-parse 'refs/heads/main^{tree}')\n"
                "  moved=$(GIT_AUTHOR_NAME=llms GIT_AUTHOR_EMAIL=llms@example.test "
                "GIT_COMMITTER_NAME=llms GIT_COMMITTER_EMAIL=llms@example.test "
                "git commit-tree \"$tree\" -p \"$parent\" -m 'origin moved')\n"
                "  git update-ref refs/heads/main \"$moved\"\n"
                "  echo 'non-fast-forward: origin/main moved' >&2\n"
                "  exit 1\n"
                "fi\n"
                "exit 0\n" % count_file,
                encoding="utf-8",
            )
            hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            github = OfflineGitHub()
            mcp = FakeMcp(FakeGitHub(), fire_mode="pending-unlanded")
            service, slack, _github, mcp, store = build_bridge(
                directory, github=github, mcp=mcp, git_root=clone,
            )
            result = service.handle_event("Ev-git-8move", event_payload("eight origin moves"))
            self.assertEqual(result["state"], "OBSERVING", service.work_log)
            ident = store.get("Ev-git-8move").job_id
            head = remote_head(bare)
            names = remote_commit_files(bare, head)
            self.assertEqual(names, {f"p/{ident}.md", f"wake_jobs/{ident}.json"})
            rejected = [item for item in service.work_log if "git_push_rejected" in str(item)]
            self.assertGreaterEqual(len(rejected), 8, service.work_log)
            self.assertIn("git:materialize_wake_job", service.work_log)
            self.assertEqual(store.get("Ev-git-8move").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertFalse(any("DURABILITY_NEVER_APPEARED" in (row.get("text") or "") for row in slack.posts))
            self.assertTrue(count_file.is_file())
            self.assertGreaterEqual(int(count_file.read_text(encoding="utf-8").strip() or "0"), 8)
            store.close()

    def test_git_materialize_uses_env_git_root_despite_cwd_and_git_dir_decoy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin_root = Path(directory) / "git"
            origin_root.mkdir()
            bare, clone = make_bare_commons_clone(str(origin_root))
            decoy = Path(directory) / "decoy.git"
            _git_in(Path(directory), ["init", "--bare", str(decoy)])
            cwd = Path(directory) / "scheduler-cwd"
            cwd.mkdir()
            github = OfflineGitHub()
            mcp = FakeMcp(FakeGitHub(), fire_mode="pending-unlanded")
            old_cwd = os.getcwd()
            old_git_dir = os.environ.get("GIT_DIR")
            old_root = os.environ.get("COMMONS_GROK_SLACK_GIT_ROOT")
            try:
                os.chdir(cwd)
                os.environ["GIT_DIR"] = str(decoy)
                os.environ["COMMONS_GROK_SLACK_GIT_ROOT"] = str(clone)
                env = bridge.git_env()
                self.assertEqual(env.get("GCM_INTERACTIVE"), "Never")
                self.assertEqual(env.get("GIT_TERMINAL_PROMPT"), "0")
                self.assertNotIn("GIT_DIR", env)
                service, slack, _github, mcp, store = build_bridge(
                    directory, github=github, mcp=mcp,
                )
                result = service.handle_event("Ev-git-env", event_payload("scheduled process env"))
            finally:
                os.chdir(old_cwd)
                if old_git_dir is None:
                    os.environ.pop("GIT_DIR", None)
                else:
                    os.environ["GIT_DIR"] = old_git_dir
                if old_root is None:
                    os.environ.pop("COMMONS_GROK_SLACK_GIT_ROOT", None)
                else:
                    os.environ["COMMONS_GROK_SLACK_GIT_ROOT"] = old_root
            self.assertEqual(result["state"], "OBSERVING", service.work_log)
            ident = store.get("Ev-git-env").job_id
            head = remote_head(bare)
            names = remote_commit_files(bare, head)
            self.assertEqual(names, {f"p/{ident}.md", f"wake_jobs/{ident}.json"})
            self.assertIn("git:materialize_wake_job", service.work_log)
            self.assertEqual(store.get("Ev-git-env").fire_action_calls, 1)
            self.assertEqual(len([name for name, _ in mcp.calls if name == "fire_action"]), 1)
            self.assertFalse(any("DURABILITY_NEVER_APPEARED" in (row.get("text") or "") for row in slack.posts))
            store.close()

    def test_materialize_diagnostics_survive_store_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin_root = Path(directory) / "git"
            origin_root.mkdir()
            _bare, clone = make_bare_commons_clone(str(origin_root))
            github = OfflineGitHub()
            mcp = FakeMcp(FakeGitHub(), fire_mode="pending-unlanded")
            state_path = Path(directory) / "state.sqlite3"
            store = bridge.BridgeStore(state_path)
            service, slack, _github, mcp, store = build_bridge(
                directory, github=github, mcp=mcp, git_root=clone, store=store,
            )

            def boom(*_args: Any, **_kwargs: Any) -> Any:
                raise RuntimeError("hidden-git-failure")

            service._git = boom  # type: ignore[method-assign]
            result = service.handle_event("Ev-git-diag", event_payload("diagnostics must persist"))
            self.assertEqual(result["state"], "OBSERVING")
            self.assertEqual(result.get("reason"), "DURABILITY_PENDING")
            row = store.get("Ev-git-diag")
            self.assertIsNotNone(row)
            self.assertIn("git_exception", row.diagnostics)
            self.assertIn("hidden-git-failure", row.diagnostics)
            sidecar = store.materialize_log_path()
            self.assertTrue(sidecar.is_file(), sidecar)
            self.assertIn("hidden-git-failure", sidecar.read_text(encoding="utf-8"))
            self.assertFalse(any("rejected" in (item.get("text") or "").casefold() for item in slack.posts))
            store.close()
            store2 = bridge.BridgeStore(state_path)
            again = store2.get("Ev-git-diag")
            self.assertIsNotNone(again)
            self.assertIn("git_exception", again.diagnostics)
            self.assertIn("hidden-git-failure", again.diagnostics)
            self.assertEqual(again.fire_action_calls, 1)
            store2.close()


class ScheduledCwdImportTests(unittest.TestCase):
    """Task Scheduler launches bridge.py with an empty/foreign WorkingDirectory."""

    def test_load_grok_executor_queue_uses_explicit_git_root(self) -> None:
        Queue = bridge.load_grok_executor_queue(Path(__file__).resolve().parent)
        self.assertEqual(Queue.__name__, "GrokExecutorQueue")
        loaded = Path(sys.modules["integrations.grok_executor_queue"].__file__).resolve()
        expected = (Path(__file__).resolve().parent / "integrations" / "grok_executor_queue.py").resolve()
        self.assertEqual(loaded, expected)

    def test_cwd_import_never_inserts_cwd(self) -> None:
        import integrations.grok_slack.cwd_import as cwd_import
        with tempfile.TemporaryDirectory() as directory:
            decoy = Path(directory)
            (decoy / "integrations").mkdir()
            (decoy / "integrations" / "__init__.py").write_text("", encoding="utf-8")
            (decoy / "integrations" / "grok_executor_queue.py").write_text(
                "class GrokExecutorQueue:\n    decoy = True\n",
                encoding="utf-8",
            )
            old = os.getcwd()
            try:
                os.chdir(decoy)
                root = cwd_import.ensure_integrations_import_path(
                    Path(__file__).resolve().parent,
                    bridge_file=MODULE_PATH,
                )
            finally:
                os.chdir(old)
            self.assertNotEqual(Path(root).resolve(), decoy.resolve())
            self.assertNotIn(str(decoy.resolve()), sys.path)
            self.assertNotIn(str(decoy), sys.path)

    def test_foreign_cwd_child_builds_materialize_blobs_against_decoy(self) -> None:
        repo = Path(__file__).resolve().parent
        child = r'''
import json
import os
import sys
from pathlib import Path

decoy = Path(sys.argv[1])
git_root = Path(sys.argv[2])
bridge_py = Path(sys.argv[3])
os.chdir(decoy)
os.environ["COMMONS_GROK_SLACK_GIT_ROOT"] = str(git_root)
script_dir = str(bridge_py.parent)
# Simulate `python integrations/grok_slack/bridge.py`: sys.path[0] is the script dir.
# Cwd (decoy) is also searchable, as on some scheduled launches.
sys.path = [script_dir, str(decoy), ""] + [p for p in sys.path if p not in {script_dir, str(decoy), ""}]
while str(git_root) in sys.path:
    sys.path.remove(str(git_root))
import importlib.util
spec = importlib.util.spec_from_file_location("grok_slack_bridge_child", bridge_py)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class Stub:
    def __init__(self):
        self.posts = []
    def chat_postMessage(self, **kwargs):
        return {"ok": True, "ts": "1.1"}
    def conversations_replies(self, **kwargs):
        return {"ok": True, "messages": []}

store = mod.BridgeStore(decoy / "state.sqlite3")
sink = mod.SlackTransport(Stub(), store, sleeper=lambda _s: None)
service = mod.GrokSlackBridge(store, Stub(), Stub(), sink, git_root=git_root)
page, blob = service._build_materialize_blobs(
    "job-cwd-import-01",
    {
        "from": "UNSEATED",
        "payload": json.dumps({
            "exact_prompts": ["scheduled cwd import proof"],
            "run_key": "rk-cwd-import-01",
        }),
    },
)
queue_file = Path(sys.modules["integrations.grok_executor_queue"].__file__).resolve()
want = (git_root / "integrations" / "grok_executor_queue.py").resolve()
decoy_queue = (decoy / "integrations" / "grok_executor_queue.py").resolve()
print(json.dumps({
    "ok": bool(page and blob),
    "page_len": len(page or ""),
    "blob_len": len(blob or b""),
    "queue_file": str(queue_file),
    "want": str(want),
    "used_decoy": queue_file == decoy_queue,
    "cwd_on_path": str(decoy) in sys.path or "" in sys.path,
    "work_log": list(service.work_log),
}))
'''
        with tempfile.TemporaryDirectory() as directory:
            decoy = Path(directory) / "scheduler-cwd"
            decoy.mkdir()
            integ = decoy / "integrations"
            integ.mkdir()
            (integ / "__init__.py").write_text("# decoy package\n", encoding="utf-8")
            (integ / "grok_executor_queue.py").write_text(
                "raise ImportError('decoy integrations.grok_executor_queue must not be used')\n",
                encoding="utf-8",
            )
            script = Path(directory) / "child.py"
            script.write_text(child, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(script), str(decoy), str(repo), str(MODULE_PATH)],
                cwd=str(decoy),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if completed.returncode != 0:
                self.fail(
                    "child failed rc=%s stdout=%s stderr=%s"
                    % (completed.returncode, completed.stdout, completed.stderr)
                )
            payload = json.loads(completed.stdout.strip().splitlines()[-1])
            self.assertTrue(payload["ok"], payload)
            self.assertFalse(payload["used_decoy"], payload)
            self.assertEqual(payload["queue_file"], payload["want"])
            self.assertGreater(payload["page_len"], 20)
            self.assertGreater(payload["blob_len"], 20)
            self.assertFalse(any("blob_exception" in str(item) for item in payload["work_log"]), payload)


if __name__ == "__main__":
    unittest.main()
