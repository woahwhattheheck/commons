"""Reuse bounded Slack reads and honor provider cooldowns across local callers.

Only sanitized successful read responses are cached, in memory, for ten seconds.
The existing command-center budget persists cooldowns, never message contents or
credentials. This does not change the hosted Slack MCP connector's rate limits.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from integrations.command_center.request_budget import RequestBudget, RequestDeferred

CACHED_METHODS = frozenset({"conversations.history", "conversations.replies", "chat.getPermalink"})
READ_METHODS = CACHED_METHODS | {"auth.test"}


def _iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat().replace("+00:00", "Z")


class SlackReadCoordinator:
    def __init__(self, state_dir=None, *, clock=time.time, ttl_seconds=10,
                 max_bytes=8 * 1024 * 1024, max_entries=64):
        self.clock, self.ttl = clock, ttl_seconds
        self.max_bytes, self.max_entries = max_bytes, max_entries
        if state_dir is not None:
            Path(state_dir).mkdir(parents=True, exist_ok=True)
        self.budget = RequestBudget(state_dir, clock=clock)
        self._cache = OrderedDict()
        self._bytes = 0
        self._generation = 0
        self._guard = threading.RLock()
        # Bounded lock striping coalesces identical concurrent reads without an
        # ever-growing per-request lock registry. Writes never use these locks.
        self._reads = tuple(threading.RLock() for _ in range(64))

    def _cached(self, key):
        with self._guard:
            entry = self._cache.get(key)
            if entry is None:
                return None
            observed, body = entry
            if self.clock() - observed >= self.ttl or self.clock() < observed:
                self._bytes -= len(body)
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            result = json.loads(body)
            result["commons_read"] = {"observed_at": _iso(observed), "cached": True,
                "age_seconds": max(0, self.clock() - observed), "ttl_seconds": self.ttl}
            return result

    def _remember(self, key, result, observed, generation):
        body = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if self.ttl <= 0 or len(body) > min(self.max_bytes, 2 * 1024 * 1024):
            return
        with self._guard:
            if generation != self._generation:
                return
            prior = self._cache.pop(key, None)
            if prior is not None:
                self._bytes -= len(prior[1])
            self._cache[key] = (observed, body)
            self._bytes += len(body)
            while self._cache and (self._bytes > self.max_bytes or len(self._cache) > self.max_entries):
                _, (_, removed) = self._cache.popitem(last=False)
                self._bytes -= len(removed)

    def call(self, method, payload, token, runner, *, fresh=False):
        # Account/token rotation separates observations; only a one-way scope
        # fingerprint is retained in the cooldown ledger, never the credential.
        account = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
        scope = "slack:" + account + ":" + method
        key = hashlib.sha256(json.dumps([scope, payload], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

        def invoke():
            cacheable = method in CACHED_METHODS
            if cacheable and not fresh:
                cached = self._cached(key)
                if cached is not None:
                    return cached
            try:
                self.budget.acquire(scope)
            except RequestDeferred as exc:
                deadline = datetime.fromisoformat(exc.retry_not_before.replace("Z", "+00:00")).timestamp()
                return {"ok": False, "error": "ratelimited", "status": 429,
                    "uncertain": False, "provider_contacted": False,
                    "deferral_reason": "provider_cooldown",
                    "retry_after": max(1, math.ceil(deadline - self.clock())),
                    "retry_not_before": exc.retry_not_before}
            with self._guard:
                generation = self._generation
            result = runner()
            if not isinstance(result, dict):
                return result
            if result.get("status") == 429 or result.get("error") == "ratelimited":
                retry = self.budget.rate_limited(scope, result.get("retry_after"))
                return {**result, "status": 429, "provider_contacted": True,
                    "retry_after": max(1, math.ceil(retry["retry_after_seconds"])),
                    "retry_not_before": retry["retry_not_before"]}
            if result.get("ok") is True and cacheable:
                observed = self.clock()
                self._remember(key, result, observed, generation)
                result = {**result, "commons_read": {"observed_at": _iso(observed),
                    "cached": False, "age_seconds": 0, "ttl_seconds": self.ttl}}
            # A successful mutation can make a previously cached conversation
            # obsolete. Invalidating is cheap and never fabricates an effect.
            elif result.get("ok") is True and method not in READ_METHODS:
                with self._guard:
                    self._generation += 1
                    self._cache.clear()
                    self._bytes = 0
            return result

        if method in CACHED_METHODS:
            with self._reads[int(key[:8], 16) % len(self._reads)]:
                return invoke()
        return invoke()


_default = None
_default_lock = threading.Lock()


def default_coordinator():
    global _default
    with _default_lock:
        if _default is None:
            _default = SlackReadCoordinator(Path.home() / ".commons" / "command-center")
        return _default
