"""Bounded Commons → Cursor leftover inbound.

Reads durable leftover / wake records and upserts a Cursor-owned named
job when missing. Never remints an existing job_id. Never invokes a
model. Never mails Cursor ntfy. Never reassigns issue 1316. Never
invents ChatGPT/Claude jobs. Never claims live resume of another bc-.
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable

from independent_commons_mcp.envelope import ACTOR_RE, ID_RE, parse_frontmatter
from independent_commons_mcp.jobs import JobError, JobStore, iso, parse_ts, utc_now

from .cursor_adapter import is_cursor_harness, is_cursor_owner_claim
from .idle_resume import probe_idle_resume


LEFTOVER_KINDS = frozenset({"LEFTOVER", "WAKE_JOB", "HARNESS_WAKE"})
SKIP_KINDS = frozenset({
    "SHIP_RECEIPT",
    "DURABLE_PAGE",
    "SLACK_MESSAGE",
    "SLACK_THREAD_REPLY",
    "MEMORY_CREATE",
    "MEMORY_APPEND",
})
FOREIGN_HARNESS_MARKERS = (
    "chatgpt",
    "openai",
    "claude",
    "anthropic",
)
LEFTOVER_NAME_MARKERS = ("leftover", "wake-job", "wake_job")
LEFTOVER_PEEK = (
    b"kind: leftover",
    b"kind: wake_job",
    b"kind: harness_wake",
    b"kind: LEFTOVER",
    b"kind: WAKE_JOB",
    b"kind: HARNESS_WAKE",
    b"job_id:",
    b'"job_id"',
    b"leftover:",
    b'"leftover"',
    b"wake_job:",
)
DEFAULT_DEADLINE_DAYS = 14


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_record_dirs(root: str | Path | None = None) -> list[Path]:
    base = Path(root) if root else repo_root()
    out = []
    leftovers = base / "leftovers"
    if leftovers.is_dir():
        out.append(leftovers)
    posts = base / "p"
    if posts.is_dir():
        out.append(posts)
    return out


def normalize_actor(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if ACTOR_RE.fullmatch(text):
        return text
    return ""


def is_foreign_harness(harness: str) -> bool:
    normalized = "".join(ch for ch in str(harness or "").lower() if ch.isalnum())
    return any(marker in normalized for marker in FOREIGN_HARNESS_MARKERS)


def is_cursor_owned(record: dict[str, Any]) -> bool:
    harness = str(record.get("harness") or "")
    owner = normalize_actor(record.get("owner_claim") or record.get("from"))
    if is_foreign_harness(harness):
        return False
    return is_cursor_harness(harness) or is_cursor_owner_claim(owner)


def is_leftover_record(record: dict[str, Any]) -> bool:
    kind = str(record.get("kind") or "").strip().upper().replace("-", "_")
    if kind in SKIP_KINDS:
        return False
    state = str(record.get("state") or "").strip().upper()
    if state in {"DURABLE_PAGE", "DONE", "CANCELLED", "EXHAUSTED"}:
        return False
    if kind in LEFTOVER_KINDS:
        return True
    if record.get("job_id") or record.get("leftover") or record.get("wake_job"):
        return True
    return False


def leftover_job_id(record: dict[str, Any]) -> str:
    for key in ("job_id", "leftover", "wake_job", "id"):
        value = str(record.get(key) or "").strip()
        if ID_RE.fullmatch(value):
            return value
    return ""


def _cheap_leftover_path(path: Path, *, peek_all: bool) -> bool:
    name = path.name.lower()
    if path.suffix == ".json" and not name.startswith("_"):
        return True
    if any(marker in name for marker in LEFTOVER_NAME_MARKERS):
        return True
    if not peek_all or path.suffix != ".md":
        return False
    try:
        head = path.read_bytes()[:2048]
    except OSError:
        return False
    lowered = head.lower()
    return any(marker in head or marker.lower() in lowered for marker in LEFTOVER_PEEK)


def iter_record_paths(records_dir: str | Path, *, peek_all: bool) -> list[Path]:
    root = Path(records_dir)
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("_") or path.name in {"README.md", ".gitkeep"}:
            continue
        if path.suffix not in {".md", ".json"}:
            continue
        if _cheap_leftover_path(path, peek_all=peek_all):
            out.append(path)
    return out


def parse_record(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if path.suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        data.setdefault("source_path", str(path))
        return data
    meta, _body = parse_frontmatter(text)
    if not meta:
        return None
    meta["source_path"] = str(path)
    return meta


def leftover_upsert_fields(record: dict[str, Any], *, now: str) -> dict[str, Any] | None:
    job_id = leftover_job_id(record)
    owner = normalize_actor(record.get("owner_claim") or record.get("from"))
    harness = str(record.get("harness") or "").strip()
    if not job_id or not owner or not harness:
        return None
    if not is_cursor_owned(record):
        return None
    objective = str(
        record.get("objective")
        or record.get("subject")
        or record.get("leftover")
        or ("Cursor leftover %s" % job_id)
    ).strip().replace("\n", " ")
    if not objective:
        objective = "Cursor leftover %s" % job_id
    due = record.get("next_wake_at") or now
    if parse_ts(str(due)) is None:
        due = now
    deadline = record.get("deadline")
    if parse_ts(str(deadline or "")) is None:
        stamp = parse_ts(now) or parse_ts(utc_now())
        deadline = iso(stamp + timedelta(days=DEFAULT_DEADLINE_DAYS)) if stamp else now
    fields: dict[str, Any] = {
        "job_id": job_id,
        "owner_claim": owner,
        "harness": harness,
        "objective": objective[:1000],
        "next_wake_at": due,
        "deadline": deadline,
        "completion_predicate": record.get("completion_predicate") or {"type": "status_done"},
    }
    result = str(record.get("result_address") or "").strip()
    if ID_RE.fullmatch(result):
        fields["result_address"] = result
    if "checkpoint" in record and isinstance(record.get("checkpoint"), dict):
        fields["checkpoint"] = record["checkpoint"]
    return fields


def ingest_cursor_leftovers(
    records_dirs: Iterable[str | Path] | str | Path | None,
    jobs_dir: str | Path | None = None,
    *,
    now: str | None = None,
    peek_all: bool | None = None,
) -> dict[str, Any]:
    """Upsert missing Cursor leftover jobs. Existing job_id is not reminted."""
    if records_dirs is None:
        dirs: list[Path] = []
    elif isinstance(records_dirs, (str, Path)):
        dirs = [Path(records_dirs)]
    else:
        dirs = [Path(item) for item in records_dirs]
    store = JobStore(jobs_dir)
    now_text = now or utc_now()
    upserted: list[str] = []
    existing: list[str] = []
    ignored: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    for records_dir in dirs:
        scan_all = True if peek_all is True else (False if peek_all is False else records_dir.name != "p")
        for path in iter_record_paths(records_dir, peek_all=scan_all):
            record = parse_record(path)
            if record is None:
                ignored.append({"path": str(path), "reason": "UNPARSEABLE"})
                continue
            if not is_leftover_record(record):
                ignored.append({"path": str(path), "reason": "NOT_LEFTOVER"})
                continue
            if not is_cursor_owned(record):
                ignored.append({
                    "path": str(path),
                    "reason": "NOT_CURSOR",
                    "harness": str(record.get("harness") or ""),
                })
                continue
            fields = leftover_upsert_fields(record, now=now_text)
            if fields is None:
                ignored.append({"path": str(path), "reason": "SCHEMA"})
                continue
            job_id = fields["job_id"]
            if job_id in seen:
                continue
            seen.add(job_id)
            if store.path_for(job_id).is_file():
                existing.append(job_id)
                continue
            try:
                created = store.upsert(fields)
            except JobError as exc:
                errors.append({"path": str(path), "job_id": job_id, "code": exc.code, "message": str(exc)})
                continue
            upserted.append(created.get("job", {}).get("job_id") or job_id)
    return {
        "ok": True,
        "state": "INGESTED",
        "upserted": upserted,
        "existing": existing,
        "ignored": ignored,
        "errors": errors,
        "invoke_model": False,
        "live_resume": False,
        "process_model_invocations": 0,
        "ntfy_sent": False,
        "issue_1316": False,
        "note": (
            "Cursor leftover inbound only. Missing jobs are upserted. "
            "Existing job_id is not reminted. Attempt ids stay receipts."
        ),
    }


def inbound_does_not_resume_other_bc(bc_id: str) -> dict[str, Any]:
    """Named idle other-bc resume stays fail-closed. Not a live inbound."""
    probe = probe_idle_resume(bc_id)
    probe["inbound"] = "grokbot_seth"
    probe["live_resume"] = False
    probe["invoke_model"] = False
    return probe
