"""Atomic swarm state on the existing ``state/claims`` branch.

One transaction may ingest many events. Every writer replays its mutation on the
current remote parent after contention; local caches never decide custody. The
ledger lives under holdings/ so existing coordination_state writers carry its
blob forward. No checkout, HEAD, normal index, or unrelated holding is changed.

Mutators must be deterministic/replay-safe and perform no provider I/O. Generate
event IDs before calling update(). Events are never pruned here: future event
compaction must retain exact seen IDs and projection checkpoints together.
Task projections are computed from these facts, not serialized as a second
authority; read-relative lease ages must never churn the shared branch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time

from host.coordination_state import (
    Git, GitError, HOLDING_SCHEMA, _commit_env, _holding_live, _now,
    _parse_ts, _push_ref, _remote_tip, repository_claim_key,
)
from . import locks
from .snapshot import STATUS_PATH

SCHEMA = "commons-swarm-runtime/v1"
SNAPSHOT_SCHEMA = "commons-swarm-runtime-snapshot/v1"
STATE_PATH = "holdings/swarm-runtime.json"
NON_LEGACY_PATHS = {STATE_PATH, STATUS_PATH}


class StoreError(RuntimeError):
    """An observed failure, distinct from an absent claim or empty ledger."""

    def __init__(self, kind, message, retry_after=None):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after

    def as_dict(self):
        result = {"ok": False, "error": self.kind, "reason": str(self)}
        if self.retry_after is not None:
            result.update(deferred=True, retry_after=self.retry_after)
        return result


def _failure(message):
    text = str(message)
    lower = text.lower()
    if "shallow.lock" in lower and any(x in lower for x in ("file exists", "unable to create", "another git process")):
        return StoreError("local_fetch_in_progress", text, 3)
    if any(x in lower for x in ("index.lock", "fetch_head.lock", "config.lock")) and "file exists" in lower:
        return StoreError("workspace_busy", text, 3)
    if any(x in lower for x in ("non-fast-forward", "fetch first", "cannot lock ref", "stale info")):
        return StoreError("ref_contention", text, 3)
    if any(x in lower for x in ("429", "rate limit", "too many requests")):
        return StoreError("rate_limited", text, 60)
    if any(x in lower for x in ("authentication failed", "could not read username", "terminal prompts disabled", "401")):
        return StoreError("connector_unauthenticated", text)
    if any(x in lower for x in ("protected branch", "repository rule", "gh013", "gh006", "hook declined")):
        return StoreError("provider_policy", text)
    if any(x in lower for x in ("permission denied", "write access", "403", "access denied")):
        return StoreError("account_permission", text)
    if any(x in lower for x in ("could not resolve", "failed to connect", "timed out", "connection reset", "network", "unexpected disconnect", "hung up unexpectedly", "502", "503", "504")):
        return StoreError("network", text, 15)
    return StoreError("provider_failure", text, 15)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False) + "\n"


def empty_state():
    return {"schema": SCHEMA, "events": [], "cursors": {}, "workers": {},
            "provider_facts": {}, "tasks": {}}


def _state(value):
    if not isinstance(value, dict) or value.get("schema", SCHEMA) != SCHEMA:
        raise StoreError("invalid_state", "runtime ledger is not a supported JSON object")
    value = copy.deepcopy(value)
    for name, default in empty_state().items():
        value.setdefault(name, default)
        if type(value[name]) is not type(default):
            raise StoreError("invalid_state", "runtime field %s has an invalid type" % name)
    if isinstance(value.get("legacy_holdings"), dict):
        value["legacy_holdings"] = {path: row for path, row in value["legacy_holdings"].items()
                                    if path not in NON_LEGACY_PATHS}
    if isinstance(value.get("legacy_unreadable"), list):
        value["legacy_unreadable"] = [path for path in value["legacy_unreadable"]
                                     if path not in NON_LEGACY_PATHS]
    return value


def _persisted(state):
    result = _state(state)
    # Derived from sibling blobs at the same claims tip, not a second store.
    result.pop("legacy_holdings", None)
    result.pop("legacy_unreadable", None)
    # Runtime projects before every routing/mutation decision. In particular,
    # lease.age_s and provider_age_s vary with the reader's clock without any
    # new event. Persisting that view doubles the ledger and causes idle churn.
    result.pop("tasks", None)
    journal_ids = {event["id"] for event in result["events"]
                   if isinstance(event, dict) and isinstance(event.get("id"), str)}
    operations = result.get("operations", {})
    for operation in operations.values() if isinstance(operations, dict) else []:
        receipt = operation.get("result") if isinstance(operation, dict) else None
        if not isinstance(receipt, dict):
            continue
        for field in ("task", "next"):
            context = receipt.get(field)
            if not isinstance(context, dict) or context.get("task_key") in (None, "", "UNKNOWN"):
                continue
            # Retain every known assignment/outcome/error field. Events already
            # live in the immutable journal; keep exact receipt membership by
            # ID instead of copying their bodies into every heartbeat receipt.
            compact = {key: value for key, value in context.items() if value != "UNKNOWN"}
            events = compact.get("events")
            if isinstance(events, list) and all(
                    isinstance(event, dict) and isinstance(event.get("id"), str)
                    and event["id"] in journal_ids for event in events):
                compact["context_event_ids"] = [event["id"] for event in events]
                compact.pop("events")
            receipt[field] = compact
    return result


class _StoreGit(Git):
    def run(self, *args, env=None, **kwargs):
        # A missing shell credential is a diagnosed road, never an input prompt
        # that parks every dispatcher behind a hanging git subprocess.
        merged = {"GIT_TERMINAL_PROMPT": "0", "GIT_HTTP_LOW_SPEED_LIMIT": "1",
                  "GIT_HTTP_LOW_SPEED_TIME": "30"}
        merged.update(env or {})
        return super().run(*args, env=merged, **kwargs)


class GitStore:
    def __init__(self, root, remote="origin", branch="state/claims", cache_ttl=15):
        self._mutex = threading.RLock()
        self.git = _StoreGit(str(root))
        self.root, self.remote, self.branch = str(root), remote, branch
        self.cache_ttl = max(0, float(cache_ttl))
        self._cache = None
        self._blob_records = {}
        self._legacy_oids = {}
        git_dir = self.git.out("rev-parse", "--absolute-git-dir").strip()
        self._common_git_dir = Path(self.git.out("rev-parse", "--path-format=absolute", "--git-common-dir").strip())
        self._fetch_lock_path = self._common_git_dir / "swarm-runtime-fetch.lock"
        suffix = hashlib.sha256((remote + "\0" + branch).encode()).hexdigest()[:12]
        self._cache_path = Path(git_dir) / ("swarm-runtime-cache-" + suffix + ".json")

    def _cached(self):
        if self._cache is None:
            try:
                cached = json.loads(self._cache_path.read_text(encoding="utf-8"))
                if isinstance(cached, dict) and cached.get("schema") == SNAPSHOT_SCHEMA:
                    cached["state"] = _state(cached.get("state", {}))
                    self._cache = cached
                    self._legacy_oids = {path: blob for path, blob in cached.get("legacy_oids", {}).items()
                                         if path not in NON_LEGACY_PATHS}
                    cached["legacy_oids"] = self._legacy_oids
                    holdings = cached.get("state", {}).get("legacy_holdings", {})
                    self._blob_records = {blob: copy.deepcopy(holdings[path])
                                          for path, blob in self._legacy_oids.items()
                                          if path in holdings and isinstance(holdings[path], dict)}
            except (OSError, ValueError, TypeError, StoreError):
                pass
        return self._cache

    def _remember(self, tip, state):
        self._cache = {"schema": SNAPSHOT_SCHEMA, "tip": tip, "branch": self.branch,
                       "cached_at": time.time(), "state": copy.deepcopy(state),
                       "legacy_oids": self._legacy_oids}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self._cache_path.parent,
                                             prefix="swarm-cache-", delete=False) as out:
                temporary = out.name
                out.write(_json(self._cache))
            os.replace(temporary, self._cache_path)
        except (OSError, UnicodeError):
            # Status caching is an optimization; the remote result remains valid.
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass

    def _tip(self):
        try:
            return _remote_tip(self.git, self.branch, self.remote)
        except GitError as exc:
            raise _failure(exc) from exc

    def _remember_publication(self, tip, state, proposal):
        for item in proposal["files"]:
            if item["path"] not in NON_LEGACY_PATHS:
                self._legacy_oids[item["path"]] = item["blob"]
        self._remember(tip, state)

    def _fetch(self, objects, shallow=False):
        if not objects:
            return
        # No negotiation walk through the fleet's large partial history. The
        # ledger needs this exact commit/tree, not every preceding claim commit.
        args = ["-c", "fetch.negotiationAlgorithm=noop", "fetch", "--no-tags",
                "--no-write-fetch-head", "--no-auto-maintenance", "--no-recurse-submodules"]
        if shallow:
            # Bring the compact ledger and holdings with the tip. blob:none
            # required another provider round trip on every meaningful update.
            # Larger unrelated blobs remain deferred and are never fetched one
            # at a time by a local object lookup.
            args += ["--depth=1", "--filter=blob:limit=2097152"]
        # All worktrees share the shallow/object database. Serialize our fetches
        # with the existing crash-released lock primitive; an external git
        # writer can still contend and is reported as local workspace activity.
        with locks.held(self._fetch_lock_path) as acquired:
            if acquired == "busy":
                raise StoreError("local_fetch_in_progress", "another swarm process is fetching Git objects", 3)
            if acquired != "acquired":
                raise StoreError("local_lock_unavailable", "shared Git fetch lock could not be acquired", 15)
            if (self._common_git_dir / "shallow.lock").exists():
                raise StoreError("local_fetch_in_progress", "Git shallow state is locked by another operation", 3)
            done = self.git.run(*args, self.remote, *objects, check=False,
                                env={"GIT_TERMINAL_PROMPT": "0"})
        if done.returncode:
            raise _failure(done.stderr or done.stdout)

    def _blobs(self, blob_ids):
        """One batch read and at most one batch fetch, never one request per holding."""
        blob_ids = list(dict.fromkeys(blob_ids))
        if not blob_ids:
            return {}

        def read():
            done = self.git.run("cat-file", "--batch", input_text="\n".join(blob_ids) + "\n",
                                env={"GIT_NO_LAZY_FETCH": "1"})
            raw = done.stdout.encode("utf-8", "surrogateescape")
            result, cursor, missing = {}, 0, []
            for expected in blob_ids:
                end = raw.find(b"\n", cursor)
                header = raw[cursor:end].decode("ascii").split()
                cursor = end + 1
                if len(header) == 2 and header[1] == "missing":
                    missing.append(expected)
                    continue
                if len(header) != 3 or header[0] != expected or header[1] != "blob":
                    raise StoreError("invalid_state", "unexpected git object for holding " + expected)
                length = int(header[2])
                result[expected] = raw[cursor:cursor + length].decode("utf-8", "surrogateescape")
                cursor += length + 1
            return result, missing

        result, missing = read()
        if missing:
            self._fetch(missing)
            result, missing = read()
            if missing:
                raise StoreError("provider_failure", "claims blobs could not be materialized", 15)
        return result

    def _read_tip(self, tip):
        if not tip:
            return dict(empty_state(), legacy_holdings={})
        if not self.git.has_commit(tip):
            self._fetch([tip], shallow=True)
        entries = {}
        for row in self.git.out("ls-tree", "-r", "-z", tip, "--", "holdings/").split("\0"):
            if not row:
                continue
            meta, path = row.split("\t", 1)
            _mode, kind, blob = meta.split()
            if kind == "blob" and path.endswith(".json") and path != STATUS_PATH:
                entries[path] = blob
        wanted = [blob for path, blob in entries.items()
                  if path == STATE_PATH or blob not in self._blob_records]
        blobs = self._blobs(wanted)
        if STATE_PATH in entries:
            try:
                state = _state(json.loads(blobs[entries[STATE_PATH]]))
            except (ValueError, UnicodeError) as exc:
                raise StoreError("invalid_state", "runtime ledger contains invalid JSON") from exc
        else:
            state = empty_state()
        holdings, unreadable = {}, []
        current_records = {}
        for path, blob in sorted(entries.items()):
            if path in NON_LEGACY_PATHS:
                continue
            if blob in self._blob_records:
                record = self._blob_records[blob]
            else:
                try:
                    record = json.loads(blobs[blob])
                    if not isinstance(record, dict):
                        raise ValueError("holding is not an object")
                except (ValueError, UnicodeError):
                    record = {"state": "UNKNOWN", "unreadable": True, "blob": blob}
            current_records[blob] = record
            holdings[path] = copy.deepcopy(record)
            if record.get("unreadable"):
                unreadable.append(path)
        self._blob_records = current_records
        self._legacy_oids = {path: blob for path, blob in entries.items() if path not in NON_LEGACY_PATHS}
        state["legacy_holdings"] = holdings
        if unreadable:
            state["legacy_unreadable"] = unreadable
        return state

    def read(self, refresh=True):
        """Return (remote tip, state). Only status callers may set refresh=False."""
        # The command center shares this instance across request/sync threads.
        # Keep state, legacy object IDs and their cache publication one snapshot.
        with self._mutex:
            return self._read(refresh=refresh)

    def _read(self, refresh=True):
        cached = self._cached()
        if not refresh and cached and 0 <= time.time() - cached.get("cached_at", 0) < self.cache_ttl:
            return cached["tip"], copy.deepcopy(cached["state"])
        tip = self._tip()
        if not refresh and cached and cached.get("tip") == tip:
            state = copy.deepcopy(cached["state"])
        else:
            try:
                state = self._read_tip(tip)
            except GitError as exc:
                raise _failure(exc) from exc
        self._remember(tip, state)
        return tip, state

    def export(self, refresh=True):
        """JSON-compatible snapshot. Import it with prepare(snapshot=...) offline."""
        tip, state = self.read(refresh=refresh)
        return {"schema": SNAPSHOT_SCHEMA, "branch": self.branch, "tip": tip, "state": state}

    def _holding_updates(self, before, after):
        """Project task custody into the legacy claim road in the same CAS write."""
        from .identity import key_parts

        updates = {}
        holdings = before.get("legacy_holdings", {})
        old_tasks = before.get("tasks", {})
        now = _now()
        for key, task in sorted(after.get("tasks", {}).items()):
            if not key.startswith("github:"):
                continue
            parts = key_parts(key)
            holding_key = repository_claim_key(parts["kind"], parts["number"], parts["repo"])
            path = "holdings/" + holding_key + ".json"
            current = holdings.get(path, {})
            worker = task.get("worker")
            active = task.get("state") == "ACTIVE" and worker not in (None, "", "UNKNOWN")
            old = old_tasks.get(key, {})
            if task.get("state") == "ACTIVE" and task.get("recoverable"):
                # Historical custody is evidence for recovery, not a renewal.
                # Preserve even unreadable legacy blobs until an actual fresh
                # take or matching terminal transition needs to change them.
                continue
            if active:
                if current.get("unreadable"):
                    raise StoreError("legacy_unreadable", "current holding is unreadable: " + path)
                if _holding_live(current, now) and current.get("holder") != worker:
                    raise StoreError("legacy_collision", "%s is held by %s" %
                                     (key, current.get("holder")), 15)
                heartbeat = (task.get("lease") or {}).get("heartbeat")
                if _parse_ts(heartbeat) is None:
                    heartbeat = task.get("heartbeat")
                if _parse_ts(heartbeat) is None:
                    # An undated imported task is recoverable, not a new live lease.
                    continue
                record = dict(current)
                record.update(schema=HOLDING_SCHEMA, key=holding_key, holder=worker,
                              state="HELD", repository=parts["repo"], task_key=key,
                              runtime_managed=True, heartbeat_at=heartbeat, ttl_s=3600)
                started = task.get("started_at")
                if _parse_ts(started) is not None:
                    record["taken_at"] = started
                elif current.get("holder") != worker or "taken_at" not in current:
                    record["taken_at"] = heartbeat
                if current.get("holder") == worker:
                    # Same-worker TAKE events do not reset an ACTIVE task's
                    # original start. Keep a later direct claim generation and
                    # renewal intact when projecting that historical task.
                    for field in ("taken_at", "heartbeat_at"):
                        prior, proposed = _parse_ts(current.get(field)), _parse_ts(record.get(field))
                        if prior is not None and (proposed is None or prior > proposed):
                            record[field] = current[field]
            else:
                # Never release another worker's unrelated/newer legacy holding.
                owned_by = worker if worker not in (None, "", "UNKNOWN") else old.get("worker")
                if not current or current.get("state") != "HELD" or current.get("holder") != owned_by:
                    continue
                closed = _parse_ts(task.get("closed_at"))
                taken = _parse_ts(current.get("taken_at"))
                heartbeat = _parse_ts(current.get("heartbeat_at"))
                started = _parse_ts(task.get("started_at"))
                activity = [stamp for stamp in (taken, heartbeat) if stamp is not None]
                # A holder may take the same key again after its historical task
                # closed. Terminal projections ignore those later TAKE events;
                # worker equality alone therefore cannot prove current custody.
                if closed is None or not activity or max(activity) > closed:
                    continue
                if taken is not None and started is not None and taken > started:
                    continue
                record = dict(current, state="RELEASED", task_key=key, runtime_managed=True)
            if record != current:
                updates[path] = record
        return updates

    def _commit(self, tip, content, holdings=None):
        from .snapshot import build as build_status

        fd, index = tempfile.mkstemp(prefix="swarm-runtime-index-")
        os.close(fd)
        os.unlink(index)
        env = {"GIT_INDEX_FILE": index}
        try:
            if tip:
                self.git.run("read-tree", tip, env=env)
            else:
                self.git.run("read-tree", "--empty", env=env)
            files = {STATE_PATH: content}
            files.update({path: _json(record) for path, record in (holdings or {}).items()})
            # _prepare calls this only after a real ledger/holding change. The
            # projection clock therefore cannot create a no-op status commit.
            files[STATUS_PATH] = _json(build_status(content, branch=self.branch))
            blobs = {}
            for path, text in sorted(files.items()):
                blob = self.git.out("hash-object", "-w", "--stdin", input_text=text).strip()
                self.git.run("update-index", "--add", "--cacheinfo", "100644," + blob + "," + path, env=env)
                blobs[path] = blob
            # Unchanged parent blobs may deliberately be absent in a partial
            # clone. Their existing IDs are sufficient to construct this tree.
            tree = self.git.out("write-tree", "--missing-ok", env=env).strip()
            args = ["commit-tree", tree]
            if tip:
                args += ["-p", tip]
            args += ["-m", "Update canonical swarm work state"]
            commit = self.git.out(*args, env=_commit_env()).strip()
            return {"commit": commit, "tree": tree, "blob": blobs[STATE_PATH], "path": STATE_PATH,
                    "base_sha": tip, "branch": self.branch, "content": content,
                    "files": [{"path": path, "content": text, "blob": blobs[path]}
                              for path, text in sorted(files.items())]}
        finally:
            if os.path.exists(index):
                os.unlink(index)

    def _prepare(self, mutator, tip, state):
        previous = copy.deepcopy(state)
        before = _json(_persisted(state))
        result = mutator(state)
        _json(result)  # Catch an unusable result before publishing any state.
        # These inputs describe exact sibling blobs, not a writable second ledger.
        state["legacy_holdings"] = previous.get("legacy_holdings", {})
        if "legacy_unreadable" in previous:
            state["legacy_unreadable"] = previous["legacy_unreadable"]
        else:
            state.pop("legacy_unreadable", None)
        holdings = self._holding_updates(previous, state)
        state["legacy_holdings"].update(holdings)
        content = _json(_persisted(state))
        proposal = self._commit(tip, content, holdings) if content != before or holdings else None
        return result, proposal

    def prepare(self, mutator, snapshot=None):
        """Prepare a commit without publishing; a proposal never grants custody.

        An exported snapshot may be imported without network access when its
        parent objects are already local. Native GitHub publishers can use path,
        content and base_sha; they must enforce that exact parent and re-run the
        mutation against fresh state when the parent has changed.
        """
        with self._mutex:
            return self._prepare_snapshot(mutator, snapshot=snapshot)

    def _prepare_snapshot(self, mutator, snapshot=None):
        if snapshot is None:
            tip, state = self.read()
        else:
            if snapshot.get("schema") != SNAPSHOT_SCHEMA or snapshot.get("branch") != self.branch:
                raise StoreError("invalid_state", "snapshot schema or branch differs from this store")
            tip, state = snapshot.get("tip"), _state(snapshot.get("state"))
            if tip and not self.git.has_commit(tip):
                raise StoreError("offline_parent_missing", "snapshot parent objects are not local")
        result, proposal = self._prepare(mutator, tip, state)
        return {"ok": True, "published": False, "changed": proposal is not None,
                "tip": tip, "result": result, "proposal": proposal}

    def update(self, mutator, attempts=3, push=True):
        """Apply one atomic batch, returning publication status and callback result.

        Ref conflicts re-read and re-project; no provider/network retry loop or
        sleeping is hidden here. Deferred errors tell the dispatcher when to
        revisit work instead of tying up a seat. A push failure retains a native
        connector-ready proposal, but never reports the task as claimed.
        """
        with self._mutex:
            return self._update(mutator, attempts=attempts, push=push)

    def _update(self, mutator, attempts=3, push=True):
        if type(attempts) is not int or not 1 <= attempts <= 3:
            raise ValueError("attempts must be an integer from 1 to 3")
        if not push:
            return self.prepare(mutator)
        for attempt in range(attempts):
            try:
                tip, state = self.read(refresh=True)
                result, proposal = self._prepare(mutator, tip, state)
                if proposal is None:
                    return {"ok": True, "published": True, "changed": False,
                            "tip": tip, "previous_tip": tip, "result": result}
                if tip:
                    # send-pack may need parent blobs even with --no-thin.
                    # Materialize in one batch, not legacy's per-blob requests.
                    parent_blobs = []
                    for row in self.git.out("ls-tree", "-r", "-z", tip).split("\0"):
                        if row:
                            meta, _path = row.split("\t", 1)
                            _mode, kind, blob = meta.split()
                            if kind == "blob":
                                parent_blobs.append(blob)
                    self._blobs(parent_blobs)
                done = _push_ref(self.git, self.remote, proposal["commit"], self.branch, attempts=1)
                if done.returncode == 0:
                    self._remember_publication(proposal["commit"], state, proposal)
                    return {"ok": True, "published": True, "changed": True,
                            "tip": proposal["commit"], "previous_tip": tip, "result": result}
                failure = _failure(done.stderr or done.stdout)
                # A transport may fail after accepting the ref. Observe it once;
                # stable event IDs make subsequent caller retries harmless too.
                observed = None
                if failure.kind in ("network", "provider_failure"):
                    try:
                        observed = self._tip()
                    except StoreError:
                        pass
                if observed == proposal["commit"]:
                    self._remember_publication(observed, state, proposal)
                    return {"ok": True, "published": True, "changed": True,
                            "tip": observed, "previous_tip": tip, "result": result}
                if failure.kind == "ref_contention" and attempt + 1 < attempts:
                    continue
                return dict(failure.as_dict(), published=False, changed=False, tip=tip,
                            proposal=proposal, result=None, proposed_result=result)
            except (GitError, StoreError) as exc:
                failure = exc if isinstance(exc, StoreError) else _failure(exc)
                return dict(failure.as_dict(), published=False, changed=False, result=None)
        raise AssertionError("bounded update loop did not return")
