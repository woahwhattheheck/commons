"""Private work snapshots and owner direction; no provider dispatch or inference.

Collectors pass selected metadata, never raw provider responses or message bodies.
Source observation time and actual work activity remain separate from VM telemetry.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .core import CoreError, _json, _metadata, _no_secret_fields

SOURCE_FIELDS = {
    "id", "provider", "label", "sync_mode", "observed_at", "activity_as_of",
    "scope", "coverage", "status", "error", "stale_after_seconds",
    "metadata", "refs", "url",
}
ITEM_FIELDS = {
    "id", "kind", "title", "status", "owner", "project", "updated_at",
    "activity_observed_at", "url", "summary", "next_action", "refs", "actions",
    "row_type", "control", "stage", "metadata", "tags", "labels", "type",
    "countable", "priority", "created_at", "due_at", "amount", "currency", "record_type",
    "provider_id", "source_ref", "needs_attention", "attention_reason",
}
FORBIDDEN_FIELDS = {
    "body", "raw_body", "raw_message", "raw_mail", "raw_email", "raw_response",
    "provider_response", "provider_result", "raw_result", "transcript",
}
ERROR_STATUSES = {"error", "failed", "offline", "unavailable", "blocked"}


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(value, name):
    # Preserve IDs exactly, including provider punctuation and Unicode.
    if (not isinstance(value, str) or not value or len(value) > 512
            or any(ord(char) < 32 for char in value)):
        raise CoreError(400, name + " must be a nonempty stable string ID.")
    return value


def _stamp(value, name, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise CoreError(400, name + " must be a timezone-aware ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.timestamp()
    except (ValueError, OverflowError):
        raise CoreError(400, name + " must be a timezone-aware ISO timestamp.") from None


def _safe(value):
    _no_secret_fields(value)

    def inspect(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).lower() in FORBIDDEN_FIELDS:
                    raise CoreError(400, "Work snapshots accept selected metadata, not raw bodies or provider results.")
                inspect(child)
        elif isinstance(item, list):
            for child in item:
                inspect(child)
    inspect(value)
    return _metadata(value)


def _record(value, allowed, name):
    if not isinstance(value, dict):
        raise CoreError(400, name + " must be an object.")
    if set(value) - allowed:
        raise CoreError(400, name + " contains unsupported fields.")
    clean = _safe(value)
    for key in ("id", "provider"):
        if key in value and clean.get(key) != value[key]:
            raise CoreError(400, "Stable IDs cannot contain credential values.")
    return clean


class WorkstreamStore:
    def __init__(self, state_dir):
        self.state_dir = Path(state_dir).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "workstreams.sqlite3"
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS work_sources(
                    source_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                    last_attempt_at TEXT NOT NULL, last_success_at TEXT,
                    last_good_observed_at TEXT, last_good_coverage TEXT,
                    retained_last_good INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS work_items(
                    source_id TEXT NOT NULL, item_id TEXT NOT NULL,
                    payload TEXT NOT NULL, first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY(source_id, item_id));
                CREATE TABLE IF NOT EXISTS owner_work(
                    source_id TEXT NOT NULL, item_id TEXT NOT NULL,
                    payload TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(source_id, item_id));
                CREATE TABLE IF NOT EXISTS work_operations(
                    operation_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL, result TEXT NOT NULL,
                    created_at TEXT NOT NULL);
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _operation(self, db, payload, kind):
        operation_id = _id(payload.get("operation_id"), "operation_id")
        digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
        old = db.execute("SELECT * FROM work_operations WHERE operation_id=?",
                         (operation_id,)).fetchone()
        if old:
            if old["kind"] != kind or old["payload_sha256"] != digest:
                raise CoreError(409, "Operation ID already records a different payload.")
            result = json.loads(old["result"])
            result["replayed"] = True
            return operation_id, digest, result
        return operation_id, digest, None

    @staticmethod
    def _finish(db, operation_id, kind, digest, result, now):
        db.execute("INSERT INTO work_operations VALUES(?,?,?,?,?)",
                   (operation_id, kind, digest, _json(result), now))
        return result

    def ingest(self, payload):
        if not isinstance(payload, dict) or set(payload) - {"operation_id", "source", "items"}:
            raise CoreError(400, "Snapshot requires operation_id, source and items.")
        source = _record(payload.get("source"), SOURCE_FIELDS, "source")
        source_id = _id(source.get("id"), "source.id")
        _id(source.get("provider"), "source.provider")
        observed = _stamp(source.get("observed_at"), "source.observed_at")
        _stamp(source.get("activity_as_of"), "source.activity_as_of", nullable=True)
        stale_after = source.get("stale_after_seconds", 900)
        if stale_after is not None and (isinstance(stale_after, bool)
                or not isinstance(stale_after, (int, float)) or stale_after < 0):
            raise CoreError(400, "stale_after_seconds must be a nonnegative number or null.")
        coverage = source.get("coverage")
        if not isinstance(coverage, dict) or type(coverage.get("complete")) is not bool:
            raise CoreError(400, "source.coverage.complete must explicitly be true or false.")
        if set(coverage) - {"complete", "pagination_remaining", "notes"}:
            raise CoreError(400, "Unsupported coverage fields.")
        if coverage["complete"] and coverage.get("pagination_remaining") not in (None, False, 0):
            raise CoreError(400, "Complete coverage cannot have remaining pages.")
        raw_items = payload.get("items", [])
        if not isinstance(raw_items, list) or len(raw_items) > 10000:
            raise CoreError(400, "items must be a list of at most 10000 metadata records.")
        items = []
        ids = set()
        for raw in raw_items:
            item = _record(raw, ITEM_FIELDS, "item")
            item_id = _id(item.get("id"), "item.id")
            if item_id in ids:
                raise CoreError(400, "Duplicate item ID within one source snapshot.")
            ids.add(item_id)
            for field in ("updated_at", "activity_observed_at", "created_at", "due_at"):
                # Preserve provider timestamps without inventing work activity.
                if field in item:
                    _stamp(item[field], "item." + field, nullable=True)
            if "control" in item and type(item["control"]) is not bool:
                raise CoreError(400, "item.control must be a boolean.")
            if "countable" in item and type(item["countable"]) is not bool:
                raise CoreError(400, "item.countable must be a boolean.")
            items.append(item)
        failed = str(source.get("status", "")).lower() in ERROR_STATUSES or bool(source.get("error"))
        now = _now()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            operation_id, digest, replay = self._operation(db, payload, "ingest")
            if replay:
                return replay
            previous = db.execute("SELECT * FROM work_sources WHERE source_id=?", (source_id,)).fetchone()
            prior = json.loads(previous["payload"]) if previous else None
            if failed and prior and source.get("activity_as_of") is None:
                source["activity_as_of"] = prior.get("activity_as_of")
            if prior and prior["provider"] != source["provider"]:
                raise CoreError(409, "A source ID cannot change provider.")
            if prior and prior.get("scope") != source.get("scope"):
                raise CoreError(409, "Use a distinct source ID for a different collection scope.")
            if prior and observed < _stamp(prior["observed_at"], "stored observed_at"):
                raise CoreError(409, "Older source snapshots cannot replace newer observations.")
            old_items = {r["item_id"]: r["payload"] for r in db.execute(
                "SELECT item_id,payload FROM work_items WHERE source_id=?", (source_id,))}
            changed = removed = 0
            if not failed:
                for item in items:
                    encoded = _json(item)
                    if old_items.get(item["id"]) != encoded:
                        changed += 1
                    db.execute("""
                        INSERT INTO work_items VALUES(?,?,?,?,?)
                        ON CONFLICT(source_id,item_id) DO UPDATE SET
                          payload=excluded.payload,last_seen_at=excluded.last_seen_at
                    """, (source_id, item["id"], encoded, now, now))
                if coverage["complete"]:
                    for missing in old_items.keys() - ids:
                        db.execute("DELETE FROM work_items WHERE source_id=? AND item_id=?", (source_id, missing))
                        removed += 1
            retained = len(old_items) if failed else len(old_items.keys() - ids) if not coverage["complete"] else 0
            db.execute("""
                INSERT INTO work_sources VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                  payload=excluded.payload,last_attempt_at=excluded.last_attempt_at,
                  last_success_at=excluded.last_success_at,
                  last_good_observed_at=excluded.last_good_observed_at,
                  last_good_coverage=excluded.last_good_coverage,
                  retained_last_good=excluded.retained_last_good
            """, (source_id, _json(source), now,
                  previous["last_success_at"] if failed and previous else None if failed else now,
                  previous["last_good_observed_at"] if failed and previous else None if failed else source["observed_at"],
                  previous["last_good_coverage"] if failed and previous else None if failed else _json(coverage),
                  int(failed and bool(old_items))))
            result = {"ok": True, "operation_id": operation_id, "source_id": source_id,
                      "status": "source_error" if failed else "ingested",
                      "received": len(items), "changed": changed, "removed": removed,
                      "retained": retained, "coverage": coverage, "replayed": False}
            return self._finish(db, operation_id, "ingest", digest, result, now)

    def update_work(self, payload):
        allowed = {"operation_id", "source_id", "item_id", "priority", "next_action", "job"}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise CoreError(400, "Unsupported work update fields.")
        if not set(payload) & {"priority", "next_action", "job"}:
            raise CoreError(400, "Provide priority, next_action or a prepared job.")
        clean = _safe(payload)
        source_id = _id(clean.get("source_id"), "source_id")
        item_id = _id(clean.get("item_id"), "item_id")
        if "priority" in clean and clean["priority"] is not None and not isinstance(clean["priority"], (str, int, float)):
            raise CoreError(400, "priority must be text, a number, or null.")
        if "next_action" in clean and clean["next_action"] is not None and not isinstance(clean["next_action"], str):
            raise CoreError(400, "next_action must be text or null.")
        job = clean.get("job")
        if job is not None and not isinstance(job, dict):
            raise CoreError(400, "job must be a prepared packet object or null.")
        if job and (job.get("status") not in (None, "prepared")
                    or job.get("dispatch_status") not in (None, "not_dispatched")):
            raise CoreError(400, "Work packets do not establish provider dispatch.")
        now = _now()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            operation_id, digest, replay = self._operation(db, payload, "update_work")
            if replay:
                return replay
            if not db.execute("SELECT 1 FROM work_items WHERE source_id=? AND item_id=?",
                              (source_id, item_id)).fetchone():
                raise CoreError(404, "Work item not found in this source.")
            previous = db.execute("SELECT payload FROM owner_work WHERE source_id=? AND item_id=?",
                                  (source_id, item_id)).fetchone()
            work = json.loads(previous["payload"]) if previous else {}
            for key in ("priority", "next_action"):
                if key in clean:
                    work[key] = clean[key]
            if "job" in clean:
                work["job"] = None if job is None else {
                    **job, "id": operation_id + "/job", "status": "prepared",
                    "dispatch_status": "not_dispatched", "created_at": now,
                    "source_id": source_id, "item_id": item_id}
            db.execute("""
                INSERT INTO owner_work VALUES(?,?,?,?)
                ON CONFLICT(source_id,item_id) DO UPDATE SET
                  payload=excluded.payload,updated_at=excluded.updated_at
            """, (source_id, item_id, _json(work), now))
            result = {"ok": True, "operation_id": operation_id, "source_id": source_id,
                      "item_id": item_id, "work": work, "replayed": False}
            return self._finish(db, operation_id, "update_work", digest, result, now)

    def state(self):
        now = _now()
        now_epoch = _stamp(now, "now")
        with self._db() as db:
            db.execute("BEGIN")
            sources = []
            for row in db.execute("SELECT * FROM work_sources ORDER BY source_id"):
                source = json.loads(row["payload"])
                threshold = source.get("stale_after_seconds", 900)
                age = max(0, now_epoch - _stamp(source["observed_at"], "observed_at"))
                good_age = None if not row["last_good_observed_at"] else max(
                    0, now_epoch - _stamp(row["last_good_observed_at"], "last_good_observed_at"))
                source.update({
                    "age_seconds": age, "stale": None if threshold is None else age > threshold,
                    "last_attempt_at": row["last_attempt_at"], "last_success_at": row["last_success_at"],
                    "last_good_observed_at": row["last_good_observed_at"],
                    "last_good_coverage": json.loads(row["last_good_coverage"]) if row["last_good_coverage"] else None,
                    "retained_last_good": bool(row["retained_last_good"]),
                    "data_stale": None if threshold is None or good_age is None else good_age > threshold})
                sources.append(source)
            providers = {source["id"]: source["provider"] for source in sources}
            work = {(row["source_id"], row["item_id"]): {
                **json.loads(row["payload"]), "updated_at": row["updated_at"]}
                for row in db.execute("SELECT * FROM owner_work")}
            items = []
            for row in db.execute("SELECT * FROM work_items ORDER BY source_id,item_id"):
                item = json.loads(row["payload"])
                item.update({"source_id": row["source_id"], "provider": providers[row["source_id"]],
                             "first_seen_at": row["first_seen_at"], "last_seen_at": row["last_seen_at"],
                             "owner_work": work.get((row["source_id"], row["item_id"]))})
                items.append(item)
        controls = sum(bool(item.get("control") or item.get("row_type") == "control"
                            or str(item.get("record_type", "")).lower() == "control"
                            or item.get("countable") is False) for item in items)
        return {"ok": True, "observed_at": now, "sources": sources, "items": items,
                "counts": {"sources": len(sources), "items": len(items),
                           "work_items": len(items) - controls, "control_rows": controls},
                "dispatch": {"implemented": False, "note": "Prepared job packets require an existing real tool route."}}
