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


class StaleLiveRouteMcp(FakeMcp):
    """Deployed MCP advertises route_grokcom_revenue_work but still queues work without capacity."""

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "route_grokcom_revenue_work":
            self.calls.append((name, arguments))
            self.network_calls += 1
            forced = dict(arguments)
            forced["grokcom_capacity"] = CAPACITY
            return orchestrate(forced)
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
            self.assertEqual([name for name, _ in mcp.calls if name == "route_grokcom_revenue_work"], [])
            self.assertEqual(service.recover_pending(), 0)
            retry = service.handle_event("Ev-no-capacity", event_payload("do not claim this"))
            self.assertEqual(retry["state"], "WAITING_CAPACITY")
            self.assertFalse(retry["submit"])
            self.assertEqual(slack.posts, [])
            self.assertEqual([name for name, _ in mcp.calls if name == "fire_action"], [])
            store.close()

    def test_stale_live_mcp_unverified_capacity_never_fires(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mcp = StaleLiveRouteMcp(FakeGitHub())
            service, slack, _github, mcp, store = build_bridge(
                directory,
                mcp=mcp,
                grokcom_capacity={},
            )
            result = service.handle_event("Ev-stale-mcp", event_payload("still dry"))
            self.assertEqual(result["state"], "WAITING_CAPACITY")
            self.assertFalse(result["submit"])
            self.assertEqual(store.get("Ev-stale-mcp").phase, "WAITING_CAPACITY")
            self.assertEqual(store.get("Ev-stale-mcp").fire_action_calls, 0)
            self.assertEqual(slack.posts, [])
            self.assertEqual([name for name, _ in mcp.calls if name == "fire_action"], [])
            self.assertEqual([name for name, _ in mcp.calls if name == "route_grokcom_revenue_work"], [])
            self.assertEqual(service.recover_pending(), 0)
            store.close()

    def test_exhausted_capacity_never_calls_stale_live_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mcp = StaleLiveRouteMcp(FakeGitHub())
            service, slack, _github, mcp, store = build_bridge(
                directory,
                mcp=mcp,
                grokcom_capacity={
                    "state": "EXHAUSTED",
                    "evidence": "authenticated surface reports no remaining tokens",
                    "observed_at": "2026-08-30T05:15:00Z",
                },
            )
            result = service.handle_event("Ev-exhausted", event_payload("do not queue grok.com"))
            self.assertEqual(result["state"], "WAITING_CAPACITY")
            self.assertFalse(result["submit"])
            self.assertEqual(slack.posts, [])
            self.assertEqual([name for name, _ in mcp.calls if name == "fire_action"], [])
            self.assertEqual([name for name, _ in mcp.calls if name == "route_grokcom_revenue_work"], [])
            store.close()

    def test_incomplete_available_capacity_is_unknown_and_silent(self) -> None:
        cases = (
            {"state": "AVAILABLE", "observed_at": "2026-08-30T05:15:00Z"},
            {"state": "AVAILABLE", "evidence": "capacity shown"},
        )
        for index, capacity in enumerate(cases):
            with tempfile.TemporaryDirectory() as directory:
                service, slack, _github, mcp, store = build_bridge(
                    directory,
                    grokcom_capacity=capacity,
                )
                event_id = f"Ev-incomplete-{index}"
                result = service.handle_event(event_id, event_payload("incomplete available"))
                self.assertEqual(result["state"], "WAITING_CAPACITY")
                self.assertFalse(result["submit"])
                self.assertEqual(slack.posts, [])
                self.assertEqual([name for name, _ in mcp.calls if name == "fire_action"], [])
                store.close()

    def test_capacity_gate_helper_matches_orchestrator_can_submit(self) -> None:
        self.assertFalse(bridge.grokcom_capacity_allows_submit({}))
        self.assertFalse(bridge.grokcom_capacity_allows_submit({"state": "UNKNOWN"}))
        self.assertFalse(bridge.grokcom_capacity_allows_submit({"state": "EXHAUSTED", "evidence": "dry", "observed_at": "t"}))
        self.assertFalse(bridge.grokcom_capacity_allows_submit({"state": "AVAILABLE", "evidence": "shown"}))
        self.assertTrue(bridge.grokcom_capacity_allows_submit(CAPACITY))

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
