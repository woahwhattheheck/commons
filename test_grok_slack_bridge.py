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