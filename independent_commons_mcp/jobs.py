"""Wake / job state contract for the independent Commons MCP.

Cheap ticks never invoke a model. Attempt IDs and Slack ts are event receipts.
The caller-supplied job_id is stable across Commons and every carrier.
Harness adapters live outside this pack.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .envelope import ACTOR_RE, ID_RE, redact


TERMINAL = frozenset({"DONE", "CANCELLED", "EXHAUSTED"})
BLOCKER_KINDS = frozenset({"external_authority", "unavailable_state"})
PREDICATE_TYPES = frozenset({"status_done", "checkpoint_equals", "result_address_on_head"})
FORBIDDEN_COMPLETION = frozenset({
    "claimed", "sent", "pr_open", "pr open", "pr-open", "accepted", "2xx", "carrier_2xx",
})
RESERVED_NAMES = frozenset({"README.md", "_last_tick.json", ".gitkeep"})
DEFAULT_BACKOFF = 60
DEFAULT_MAX_BACKOFF = 3600
DEFAULT_LEASE = 60
DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_BUDGET = 100000


class JobError(Exception):
    def __init__(self, code: str, message: str, state: str = "ERROR", **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.state = state
        self.details = details

    def payload(self) -> dict[str, Any]:
        return redact({
            "ok": False,
            "state": self.state,
            "code": self.code,
            "message": self.message,
            **self.details,
        })


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_ts(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fingerprint(value: Any) -> str:
    blob = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def default_jobs_dir() -> Path:
    env = os.environ.get("COMMONS_JOBS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "wake_jobs"


class JobStore:
    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory) if directory else default_jobs_dir()

    def path_for(self, job_id: str) -> Path:
        return self.directory / ("%s.json" % job_id)

    def list_ids(self) -> list[str]:
        if not self.directory.is_dir():
            return []
        out = []
        for name in sorted(os.listdir(self.directory)):
            if not name.endswith(".json") or name in RESERVED_NAMES or name.startswith("_"):
                continue
            ident = name[:-5]
            if ID_RE.fullmatch(ident):
                out.append(ident)
        return out

    def get(self, job_id: str) -> dict[str, Any]:
        ident = _job_id(job_id)
        path = self.path_for(ident)
        if not path.is_file():
            raise JobError("NOT_FOUND", "no job %s" % ident, state="NOT_FOUND", job_id=ident)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise JobError("CORRUPT", "job file is not JSON", state="ERROR", job_id=ident) from exc
        if not isinstance(data, dict) or data.get("job_id") != ident:
            raise JobError("CORRUPT", "job_id inside the file must match the filename", state="ERROR", job_id=ident)
        return data

    def upsert(self, fields: dict[str, Any]) -> dict[str, Any]:
        ident = _job_id(fields.get("job_id") or fields.get("id"))
        existing = None
        path = self.path_for(ident)
        if path.is_file():
            existing = self.get(ident)
        job = existing or {}
        if existing and fields.get("job_id") and fields.get("job_id") != ident:
            raise JobError("ID_REMINTED", "job_id is stable; do not remint", state="ID_REMINTED", job_id=ident)
        owner = _actor(fields.get("owner_claim") or (existing or {}).get("owner_claim"))
        harness = _plain(fields.get("harness") or (existing or {}).get("harness"), "harness")
        objective = _plain(fields.get("objective") or (existing or {}).get("objective"), "objective", 1000)
        next_wake = _ts(fields.get("next_wake_at") or (existing or {}).get("next_wake_at"), "next_wake_at")
        deadline = _ts(fields.get("deadline") or (existing or {}).get("deadline"), "deadline")
        pred = fields.get("completion_predicate")
        if pred is None:
            pred = (existing or {}).get("completion_predicate") or {"type": "status_done"}
        _predicate(pred)
        if existing and existing.get("status") in TERMINAL:
            raise JobError("TERMINAL", "job is %s; terminal transitions are complete/cancel/exhaust only" % existing["status"], state=existing["status"], job_id=ident)
        requested = fields.get("status")
        if requested in {"DONE", "CANCELLED", "EXHAUSTED", "LEASED"}:
            raise JobError("SCHEMA", "upsert cannot set %s; use complete/cancel/tick" % requested, state="SCHEMA", job_id=ident)
        status = str((existing or {}).get("status") or "OPEN")
        if requested in {"OPEN", "BLOCKED"}:
            status = str(requested)
        if status not in {"OPEN", "LEASED", "BLOCKED"}:
            status = "OPEN"
        old_tokens = int((existing or {}).get("tokens_used") or 0)
        tokens_used = old_tokens
        if "tokens_used" in fields:
            tokens_used = _int(fields.get("tokens_used"), 0, "tokens_used")
            if tokens_used < old_tokens:
                raise JobError("SCHEMA", "tokens_used is monotonic", state="SCHEMA", job_id=ident)
        job.update({
            "job_id": ident,
            "owner_claim": owner,
            "harness": harness,
            "objective": objective,
            "checkpoint": fields["checkpoint"] if "checkpoint" in fields else (existing or {}).get("checkpoint") or {},
            "next_wake_at": next_wake,
            "deadline": deadline,
            "backoff_seconds": _int(fields.get("backoff_seconds"), (existing or {}).get("backoff_seconds") or DEFAULT_BACKOFF, "backoff_seconds"),
            "max_backoff_seconds": _int(fields.get("max_backoff_seconds"), (existing or {}).get("max_backoff_seconds") or DEFAULT_MAX_BACKOFF, "max_backoff_seconds"),
            "lease_seconds": _int(fields.get("lease_seconds"), (existing or {}).get("lease_seconds") or DEFAULT_LEASE, "lease_seconds"),
            "max_attempts": _int(fields.get("max_attempts"), (existing or {}).get("max_attempts") or DEFAULT_MAX_ATTEMPTS, "max_attempts"),
            "attempt_count": (existing or {}).get("attempt_count") or 0,
            "budget_tokens": _int(fields.get("budget_tokens"), (existing or {}).get("budget_tokens") or DEFAULT_BUDGET, "budget_tokens"),
            "tokens_used": tokens_used,
            "completion_predicate": pred,
            "result_address": _optional_id(fields.get("result_address"), (existing or {}).get("result_address") or ""),
            "status": status,
            "event_receipts": list((existing or {}).get("event_receipts") or []),
            "lease": (existing or {}).get("lease"),
            "blocker": fields["blocker"] if "blocker" in fields else (existing or {}).get("blocker"),
            "no_progress_count": (existing or {}).get("no_progress_count") or 0,
            "in_backoff": (existing or {}).get("in_backoff") or False,
            "updated_at": utc_now(),
        })
        if not existing:
            job["created_at"] = utc_now()
            job["woke_once"] = False
            job["no_progress_count"] = 0
            job["in_backoff"] = False
        self._save(job)
        return redact({"ok": True, "state": job["status"], "job": public_job(job)})

    def tick(
        self,
        job_id: str,
        *,
        now: str | None = None,
        worker_id: str = "watchdog",
        page_exists: Callable[[str], bool] | None = None,
    ) -> dict[str, Any]:
        job = self.get(job_id)
        now_text = now or utc_now()
        now_dt = parse_ts(now_text)
        if now_dt is None:
            raise JobError("SCHEMA", "now must be ISO-8601", state="SCHEMA", job_id=job_id)
        worker = _plain(worker_id, "worker_id", 80)

        if (
            job.get("status") not in TERMINAL
            and self._predicate_satisfied(job, page_exists)
        ):
            if job.get("result_address"):
                job["status"] = "DONE"
                job["lease"] = None
                job["completed_at"] = now_text
                job["updated_at"] = now_text
                job.setdefault("event_receipts", []).append({
                    "attempt_id": "%s-auto-done" % job["job_id"],
                    "ts": now_text,
                    "event": "auto_complete",
                    "worker_id": worker,
                    "result_address": job["result_address"],
                })
                self._save(job)

        if job.get("status") in TERMINAL:
            return stop_result(job, job["status"], now_text)

        deadline = parse_ts(job.get("deadline") or "")
        if deadline and now_dt >= deadline:
            return self._exhaust(job, "DEADLINE", now_text)

        budget = int(job.get("budget_tokens") or 0)
        used = int(job.get("tokens_used") or 0)
        if budget > 0 and used >= budget:
            return self._exhaust(job, "BUDGET", now_text)

        blocker = job.get("blocker")
        if job.get("status") == "BLOCKED" or blocker:
            fp = (blocker or {}).get("fingerprint") or fingerprint(blocker or {})
            last = job.get("last_blocker_fingerprint")
            kind = (blocker or {}).get("kind") or ""
            if kind in BLOCKER_KINDS and last and fp == last:
                return stop_result(job, "BLOCKED_UNCHANGED", now_text)
            if kind in BLOCKER_KINDS and not last:
                job["last_blocker_fingerprint"] = fp
                job["status"] = "BLOCKED"
                self._save(job)
                return stop_result(job, "BLOCKED_UNCHANGED", now_text)
            if kind in BLOCKER_KINDS and last and fp != last:
                job["last_blocker_fingerprint"] = fp
                job["status"] = "OPEN"
                job["blocker"] = None
                self._save(job)
                job = self.get(job_id)
            elif job.get("status") == "BLOCKED" and not blocker:
                return stop_result(job, "BLOCKED_UNCHANGED", now_text)

        lease = job.get("lease") or {}
        lease_until = parse_ts(lease.get("until") or "") if lease else None
        holder = str(lease.get("holder") or "")
        if lease_until and now_dt < lease_until and holder and holder != worker:
            return stop_result(job, "LEASE_HELD", now_text)

        due = parse_ts(job.get("next_wake_at") or "")
        if due and now_dt < due:
            return stop_result(job, "NOT_DUE", now_text)

        if int(job.get("attempt_count") or 0) >= int(job.get("max_attempts") or DEFAULT_MAX_ATTEMPTS):
            return self._exhaust(job, "MAX_ATTEMPTS", now_text)

        fp = fingerprint(job.get("checkpoint"))
        if job.get("woke_once") and job.get("last_wake_checkpoint_fp") == fp:
            if job.get("in_backoff"):
                job["in_backoff"] = False
            else:
                no_progress = int(job.get("no_progress_count") or 0) + 1
                job["no_progress_count"] = no_progress
                if no_progress >= int(job.get("max_attempts") or DEFAULT_MAX_ATTEMPTS):
                    return self._exhaust(job, "NO_PROGRESS", now_text)
                backoff = min(
                    int(job.get("backoff_seconds") or DEFAULT_BACKOFF) * 2,
                    int(job.get("max_backoff_seconds") or DEFAULT_MAX_BACKOFF),
                )
                job["backoff_seconds"] = backoff
                job["next_wake_at"] = iso(now_dt + timedelta(seconds=backoff))
                job["in_backoff"] = True
                job["status"] = "OPEN"
                job["lease"] = None
                self._save(job)
                return redact({
                    "ok": True,
                    "state": "TICKED",
                    "job_id": job["job_id"],
                    "action": "BACKOFF",
                    "invoke_model": False,
                    "reason": "UNCHANGED_CHECKPOINT",
                    "now": now_text,
                    "job": public_job(job),
                })

        lease_id = "lease-" + uuid.uuid4().hex[:12]
        attempt_n = int(job.get("attempt_count") or 0) + 1
        attempt_id = "%s-a%02d" % (job["job_id"], attempt_n)
        job["attempt_count"] = attempt_n
        job["woke_once"] = True
        job["last_wake_at"] = now_text
        job["last_wake_checkpoint_fp"] = fp
        job["lease"] = {
            "lease_id": lease_id,
            "holder": worker,
            "until": iso(now_dt + timedelta(seconds=int(job.get("lease_seconds") or DEFAULT_LEASE))),
        }
        job["status"] = "LEASED"
        job["in_backoff"] = False
        job.setdefault("event_receipts", []).append({
            "attempt_id": attempt_id,
            "ts": now_text,
            "event": "wake",
            "worker_id": worker,
            "lease_id": lease_id,
        })
        self._save(job)
        return redact({
            "ok": True,
            "state": "TICKED",
            "job_id": job["job_id"],
            "action": "WAKE",
            "invoke_model": True,
            "reason": "RUNNABLE",
            "lease_id": lease_id,
            "attempt_id": attempt_id,
            "now": now_text,
            "note": "This tick does not invoke a model. The owning harness may, once.",
            "job": public_job(job),
        })

    def tick_all(
        self,
        *,
        now: str | None = None,
        worker_id: str = "watchdog",
        page_exists: Callable[[str], bool] | None = None,
    ) -> dict[str, Any]:
        rows = []
        for ident in self.list_ids():
            rows.append(self.tick(ident, now=now, worker_id=worker_id, page_exists=page_exists))
        wake = sum(1 for row in rows if row.get("action") == "WAKE")
        stop = sum(1 for row in rows if row.get("action") == "STOP")
        backoff = sum(1 for row in rows if row.get("action") == "BACKOFF")
        invoke = sum(1 for row in rows if row.get("invoke_model"))
        summary = {
            "ok": True,
            "state": "TICKED",
            "jobs": rows,
            "wake_count": wake,
            "stop_count": stop,
            "backoff_count": backoff,
            "invoke_model_count": invoke,
            "process_model_invocations": 0,
            "note": "Watchdog process never invokes a model. invoke_model_count is a signal to the owning harness.",
        }
        self._write_last_tick(summary)
        return redact(summary)

    def checkpoint(
        self,
        job_id: str,
        checkpoint: Any,
        *,
        next_wake_at: str | None = None,
        tokens_used: int | None = None,
        worker_id: str = "watchdog",
        now: str | None = None,
    ) -> dict[str, Any]:
        job = self.get(job_id)
        if job.get("status") in TERMINAL:
            raise JobError("TERMINAL", "job is %s" % job["status"], state=job["status"], job_id=job_id)
        lease = job.get("lease") or {}
        holder = str(lease.get("holder") or "")
        now_text = now or utc_now()
        now_dt = parse_ts(now_text)
        until = parse_ts(lease.get("until") or "") if lease else None
        lease_active = bool(holder and until and now_dt and now_dt < until)
        if lease_active and holder != worker_id:
            raise JobError("LEASE_HELD", "lease belongs to %s" % holder, state="LEASE_HELD", job_id=job_id)
        job["checkpoint"] = checkpoint if isinstance(checkpoint, dict) else {"value": checkpoint}
        job["status"] = "OPEN"
        job["lease"] = None
        job["no_progress_count"] = 0
        job["in_backoff"] = False
        if next_wake_at:
            job["next_wake_at"] = _ts(next_wake_at, "next_wake_at")
        if tokens_used is not None:
            new_tokens = _int(tokens_used, 0, "tokens_used")
            old_tokens = int(job.get("tokens_used") or 0)
            if new_tokens < old_tokens:
                raise JobError("SCHEMA", "tokens_used is monotonic", state="SCHEMA", job_id=job_id)
            job["tokens_used"] = new_tokens
        job.setdefault("event_receipts", []).append({
            "attempt_id": "ckpt-%s" % fingerprint(job["checkpoint"]),
            "ts": now_text,
            "event": "checkpoint",
            "worker_id": worker_id,
        })
        job["updated_at"] = now_text
        self._save(job)
        return redact({"ok": True, "state": "OPEN", "job": public_job(job)})

    def complete(
        self,
        job_id: str,
        *,
        result: dict[str, Any],
        result_address: str,
        page_exists: Callable[[str], bool] | None = None,
        worker_id: str = "watchdog",
        now: str | None = None,
    ) -> dict[str, Any]:
        job = self.get(job_id)
        if job.get("status") in TERMINAL:
            raise JobError(
                "TERMINAL",
                "job is %s" % job["status"],
                state=job["status"],
                job_id=job_id,
            )
        addr = _job_id(result_address, field="result_address")
        if not isinstance(result, dict):
            raise JobError("SCHEMA", "result must be an object", state="SCHEMA", job_id=job_id)
        kind = str(result.get("kind") or result.get("status") or "").strip().lower()
        if kind in FORBIDDEN_COMPLETION:
            raise JobError(
                "NOT_DURABLE",
                "completion is a durable public result, not claimed/sent/PR-open/carrier 2xx",
                state="NOT_DURABLE",
                job_id=job_id,
            )
        if page_exists is None or not page_exists(addr):
            raise JobError(
                "NOT_DURABLE",
                "result_address is not a durable p/{id}.md page",
                state="NOT_DURABLE",
                job_id=job_id,
                result_address=addr,
            )
        pred = job.get("completion_predicate") or {"type": "status_done"}
        if pred.get("type") == "checkpoint_equals":
            path = pred.get("path") or "step"
            if (job.get("checkpoint") or {}).get(path) != pred.get("value"):
                raise JobError("PREDICATE", "checkpoint does not satisfy completion_predicate", state="PREDICATE", job_id=job_id)
        now_text = now or utc_now()
        job["result_address"] = addr
        job["result"] = result
        job["status"] = "DONE"
        job["lease"] = None
        job["completed_at"] = now_text
        job.setdefault("event_receipts", []).append({
            "attempt_id": "%s-done" % job["job_id"],
            "ts": now_text,
            "event": "complete",
            "worker_id": worker_id,
            "result_address": addr,
        })
        self._save(job)
        return redact({
            "ok": True,
            "state": "DONE",
            "job_id": job["job_id"],
            "result_address": addr,
            "job": public_job(job),
        })

    def cancel(self, job_id: str, *, reason: str = "", worker_id: str = "watchdog") -> dict[str, Any]:
        job = self.get(job_id)
        if job.get("status") in TERMINAL:
            raise JobError(
                "TERMINAL",
                "job is %s" % job["status"],
                state=job["status"],
                job_id=job_id,
            )
        job["status"] = "CANCELLED"
        job["lease"] = None
        job["cancel_reason"] = _plain(reason or "cancelled", "reason", 200)
        job["updated_at"] = utc_now()
        job.setdefault("event_receipts", []).append({
            "attempt_id": "%s-cancel" % job["job_id"],
            "ts": job["updated_at"],
            "event": "cancel",
            "worker_id": worker_id,
        })
        self._save(job)
        return redact({"ok": True, "state": "CANCELLED", "job": public_job(job)})

    def append_receipt(self, job_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        job = self.get(job_id)
        row = dict(receipt)
        row.setdefault("ts", utc_now())
        job.setdefault("event_receipts", []).append(row)
        job["updated_at"] = row["ts"]
        self._save(job)
        return redact({"ok": True, "state": job.get("status"), "job": public_job(job)})

    def record_blocker(self, job_id: str, kind: str, detail: str) -> dict[str, Any]:
        if kind not in BLOCKER_KINDS:
            raise JobError("SCHEMA", "blocker kind must be external_authority or unavailable_state", state="SCHEMA", job_id=job_id)
        job = self.get(job_id)
        if job.get("status") in TERMINAL:
            raise JobError(
                "TERMINAL",
                "job is %s" % job["status"],
                state=job["status"],
                job_id=job_id,
            )
        blocker = {"kind": kind, "detail": _plain(detail, "detail", 500)}
        blocker["fingerprint"] = fingerprint(blocker)
        job["blocker"] = blocker
        job["status"] = "BLOCKED"
        job["last_blocker_fingerprint"] = blocker["fingerprint"]
        job["lease"] = None
        job["updated_at"] = utc_now()
        self._save(job)
        return redact({"ok": True, "state": "BLOCKED", "job": public_job(job)})

    def _predicate_satisfied(self, job: dict[str, Any], page_exists: Callable[[str], bool] | None) -> bool:
        pred = job.get("completion_predicate") or {"type": "status_done"}
        kind = pred.get("type")
        if kind == "status_done":
            return job.get("status") == "DONE"
        if kind == "checkpoint_equals":
            path = pred.get("path") or "step"
            addr = job.get("result_address") or ""
            return (
                (job.get("checkpoint") or {}).get(path) == pred.get("value")
                and bool(addr and page_exists and page_exists(addr))
            )
        if kind == "result_address_on_head":
            addr = job.get("result_address") or ""
            return bool(addr and page_exists and page_exists(addr))
        return False

    def _exhaust(self, job: dict[str, Any], reason: str, now_text: str) -> dict[str, Any]:
        job["status"] = "EXHAUSTED"
        job["exhausted_reason"] = reason
        job["lease"] = None
        job["updated_at"] = now_text
        self._save(job)
        return stop_result(job, reason, now_text)

    def _save(self, job: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(job["job_id"])
        path.write_text(json.dumps(job, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_last_tick(self, summary: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        public = {
            "state": "TICKED",
            "ts": utc_now(),
            "wake_count": summary["wake_count"],
            "stop_count": summary["stop_count"],
            "backoff_count": summary["backoff_count"],
            "invoke_model_count": summary["invoke_model_count"],
            "process_model_invocations": 0,
            "wake_job_ids": [row["job_id"] for row in summary["jobs"] if row.get("action") == "WAKE"],
            "note": "Bake of the last cheap tick. Not the board. job_id is stable; attempt_id is a receipt.",
        }
        (self.directory / "_last_tick.json").write_text(
            json.dumps(public, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "job_id", "owner_claim", "harness", "objective", "checkpoint", "next_wake_at",
        "deadline", "backoff_seconds", "max_backoff_seconds", "lease_seconds",
        "max_attempts", "attempt_count", "budget_tokens", "tokens_used",
        "completion_predicate", "result_address", "status", "blocker",
        "lease", "created_at", "updated_at", "completed_at", "exhausted_reason",
        "event_receipts", "no_progress_count", "in_backoff",
    )
    return {key: job.get(key) for key in keep}


def stop_result(job: dict[str, Any], reason: str, now_text: str) -> dict[str, Any]:
    return redact({
        "ok": True,
        "state": "TICKED",
        "job_id": job["job_id"],
        "action": "STOP",
        "invoke_model": False,
        "reason": reason,
        "now": now_text,
        "job": public_job(job),
    })


def _job_id(value: Any, field: str = "job_id") -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise JobError("SCHEMA", "%s must be 8-80 characters: A-Z a-z 0-9 . _ -" % field, state="SCHEMA")
    return value


def _optional_id(value: Any, fallback: str) -> str:
    text = value if value is not None else fallback
    if not text:
        return ""
    return _job_id(text, "result_address")


def _actor(value: Any) -> str:
    if not isinstance(value, str) or not ACTOR_RE.fullmatch(value.strip()):
        raise JobError("SCHEMA", "owner_claim must be an uppercase Commons claim", state="SCHEMA")
    return value.strip()


def _plain(value: Any, field: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JobError("SCHEMA", "%s must be a non-empty string" % field, state="SCHEMA")
    text = value.strip()
    if "\n" in text or "\r" in text or len(text) > maximum:
        raise JobError("SCHEMA", "%s must be one line of at most %d characters" % (field, maximum), state="SCHEMA")
    return text


def _ts(value: Any, field: str) -> str:
    if not isinstance(value, str) or parse_ts(value) is None:
        raise JobError("SCHEMA", "%s must be ISO-8601 UTC" % field, state="SCHEMA")
    dt = parse_ts(value)
    return iso(dt) if dt else value


def _int(value: Any, fallback: int, field: str) -> int:
    if value is None:
        return int(fallback)
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise JobError("SCHEMA", "%s must be an integer" % field, state="SCHEMA") from exc
    if number < 0:
        raise JobError("SCHEMA", "%s must be >= 0" % field, state="SCHEMA")
    return number


def _predicate(value: Any) -> None:
    if not isinstance(value, dict) or value.get("type") not in PREDICATE_TYPES:
        raise JobError("SCHEMA", "completion_predicate.type must be status_done, checkpoint_equals, or result_address_on_head", state="SCHEMA")
