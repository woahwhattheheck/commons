"""Task runtime adapter on the existing command-center and equipment roads."""
from __future__ import annotations

import os
from pathlib import Path
import threading

from .schema import CoreError


def _feed(center, engine):
    """Expose canonical events through the existing retained command-center feed."""
    import hashlib
    import json
    tip, state = engine.store.read(refresh=False)
    with center._db() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT data FROM records WHERE kind='usage' AND id='swarm-feed-cursor'").fetchone()
        consumed = json.loads(row["data"]).get("seq", 0) if row else 0
        for event in state.get("events", []):
            if event.get("seq", 0) <= consumed:
                continue
            ident = "swarm-event:" + hashlib.sha256(event["id"].encode()).hexdigest()
            stamp = event.get("at") or "UNKNOWN"
            item = {"id": ident, "kind": "swarm-task", "observed_at": stamp,
                    "title": event["action"] + ": " + event["task_key"],
                    "body": "Worker: " + str(event.get("worker", "UNKNOWN")),
                    "source_url": "", "source_ref": event["id"],
                    "task_key": event["task_key"], "claim_tip": tip,
                    "summary": {"action": event["action"], "feed_cursor": event.get("feed_cursor", "UNKNOWN")}}
            db.execute("INSERT OR IGNORE INTO source_events(id,observed_at,data) VALUES(?,?,?)",
                       (ident, stamp, json.dumps(item)))
            consumed = max(consumed, event.get("seq", 0))
        db.execute("INSERT OR REPLACE INTO records(kind,id,data) VALUES('usage','swarm-feed-cursor',?)",
                   (json.dumps({"seq": consumed}),))


def runtime(center):
    # Shared gateway/server instances share the Git claims authority and the same
    # state-directory provider cache. No process-local store can grant custody.
    if not hasattr(center, "_swarm_runtime"):
        from host.swarm_runtime.runtime import Runtime
        root = Path(os.environ.get("COMMONS_REPO_ROOT", str(Path(__file__).resolve().parents[2])))
        center._swarm_runtime = Runtime(root, state_dir=center.state_dir)
    return center._swarm_runtime


def call(center, payload):
    payload = dict(payload)
    action = payload.pop("action", "status")
    try:
        engine = runtime(center)
        if action == "status":
            result = engine.read(refresh=bool(payload.get("refresh", False)),
                                 worker=payload.get("worker"), limit=payload.get("limit", 100))
        elif action == "sync":
            # Source collection is already coalesced by refresh_work(). This
            # consumes its shared snapshot, never launches one reader per seat.
            snapshot = payload.pop("work_snapshot", None)
            if snapshot is None:
                snapshot = center._work_store_instance().state()
            result = engine.sync(work_snapshot=snapshot,
                provider_facts=payload.get("provider_facts"), events=payload.get("events"),
                max_calls=payload.get("max_calls", 4),
                refresh_providers=payload.get("refresh_providers", True))
        else:
            result = engine.operate(action, payload)
        if result.get("ok") and result.get("published", True):
            _feed(center, engine)
        return result
    except ValueError as exc:
        raise CoreError(400, str(exc)) from None
    except Exception as exc:
        from host.swarm_runtime.store import StoreError
        if isinstance(exc, StoreError):
            return exc.as_dict()
        raise


def after_ingest(center):
    """Existing provider/peer ingestion mechanically refreshes task projection.

    A nonblocking lock collapses simultaneous source batches. The next batch or
    explicit sync retries after contention; a failed task sync never falsifies
    the already-stored provider observation.
    """
    from host.swarm_runtime.locks import LockUnavailable, release, take
    try:
        handle = take(center.state_dir / "swarm-ingest.lock")
    except LockUnavailable:
        return {"started": False, "reason": "ingest_lock_unavailable"}
    if handle is None:
        return {"started": False, "reason": "already_running"}

    def run():
        try:
            result = call(center, {"action": "sync", "refresh_providers": False, "max_calls": 0})
            import json
            # Operational error classification only, never provider payloads.
            outcome = {key: result.get(key) for key in ("ok", "tip", "error", "published")}
            (center.state_dir / "swarm-last-sync.json").write_text(json.dumps(outcome), encoding="utf-8")
        except Exception as exc:
            import json
            (center.state_dir / "swarm-last-sync.json").write_text(
                json.dumps({"ok": False, "error": type(exc).__name__}), encoding="utf-8")
        finally:
            release(handle)
    try:
        threading.Thread(target=run, daemon=True, name="commons-swarm-ingest").start()
    except Exception:
        release(handle)
        return {"started": False, "reason": "sync_start_failed"}
    return {"started": True}


def tool():
    return {"name": "command_center_swarm_tasks",
            "description": "Canonical task status, sync, take, heartbeat, ship, block and next. Atomic shared claims, provider reconciliation and automatic next-task routing; no review queue. Reuse operation_id on retries.",
            "inputSchema": {"type": "object", "required": ["action"],
                "properties": {"action": {"type": "string", "enum": ["status", "sync", "open", "take", "heartbeat", "ship", "block", "abandon", "next"]},
                               "operation_id": {"type": "string"}, "task_key": {"type": "string"},
                               "worker": {"type": "string"}, "seat": {"type": "object"},
                               "max_calls": {"type": "integer", "minimum": 0, "maximum": 20}},
                "additionalProperties": True}}
