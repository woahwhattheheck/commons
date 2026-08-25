"""Separate harness callback. Not invoked by tick(). Consumes a scheduler delivery."""
from __future__ import annotations

from typing import Any, Callable

from independent_commons_mcp.jobs import JobStore
from .cursor_adapter import is_cursor_harness


def _cursor_hold(store: JobStore, job_id: str) -> dict[str, Any] | None:
    job = store.get(job_id)
    if not is_cursor_harness(str(job.get("harness") or "")):
        return None
    return {
        "ok": True,
        "state": "CURSOR_QUOTA_HOLD",
        "invoke_model": False,
        "job_id": job_id,
        "note": "Owner quota hold: Cursor compute is not an execution lane.",
    }


def consume_delivery(
    store: JobStore,
    delivery: dict[str, Any],
    *,
    now: str,
    pages: set[str],
    worker_id: str = "cursor-callback",
    page_exists: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    if not delivery or delivery.get("state") != "MAIL":
        return {"ok": False, "state": "NO_MAIL", "invoke_model": False}
    job_id = str(delivery.get("job_id") or "")
    held = _cursor_hold(store, job_id)
    if held is not None:
        return held
    claimed = store.claim_attempt(
        job_id,
        str(delivery.get("attempt_id") or ""),
        worker_id=worker_id,
        now=now,
    )
    if claimed.get("state") != "CLAIMED":
        return {
            "ok": bool(claimed.get("ok")),
            "state": claimed.get("state"),
            "invoke_model": False,
            "step": claimed.get("step"),
            "job_id": job_id,
            "attempt_id": delivery.get("attempt_id"),
        }
    return {
        "ok": True,
        "state": "CLAIMED",
        "invoke_model": True,
        "step": int(claimed["step"]),
        "job_id": job_id,
        "attempt_id": delivery.get("attempt_id"),
        "lease": claimed.get("job", {}).get("lease"),
    }


def finish_delivery(
    store: JobStore,
    delivery: dict[str, Any],
    *,
    now: str,
    pages: set[str],
    worker_id: str = "cursor-callback",
    page_exists: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Commit checkpoint/ACK after the owning harness performed useful work."""
    if not delivery or delivery.get("state") != "MAIL":
        return {"ok": False, "state": "NO_MAIL", "invoke_model": False}
    job_id = str(delivery.get("job_id") or "")
    held = _cursor_hold(store, job_id)
    if held is not None:
        return held
    attempt_id = str(delivery.get("attempt_id") or "")
    job = store.get(job_id)
    claim = next((
        row for row in reversed(job.get("event_receipts") or [])
        if row.get("attempt_id") == attempt_id and row.get("event") == "delivery_claim"
    ), None)
    if claim is None:
        return {
            "ok": False,
            "state": "STALE_ATTEMPT",
            "invoke_model": False,
            "job_id": job_id,
            "attempt_id": attempt_id,
        }
    step = int(claim["step"])
    job = store.get(job_id)
    pred = job.get("completion_predicate") or {"type": "status_done"}
    should_complete = step >= 2
    if pred.get("type") == "checkpoint_equals":
        path = pred.get("path") or "step"
        should_complete = {"step": step}.get(path) == pred.get("value")
    if not should_complete:
        finished = store.finish_attempt(
            job_id,
            str(delivery.get("attempt_id") or ""),
            next_wake_at=now,
            worker_id=worker_id,
            carrier=str(delivery.get("state") or "MAIL"),
            now=now,
        )
        return {
            "ok": bool(finished.get("ok")),
            "state": finished.get("state"),
            "invoke_model": False,
            "step": finished.get("step"),
            "job_id": job_id,
        }
    addr = job.get("result_address") or ""
    pages.add(addr)
    checker = page_exists or (lambda ident: ident in pages)
    done = store.complete_attempt(
        job_id,
        str(delivery.get("attempt_id") or ""),
        result={"durable": True, "step": step, "kind": "page"},
        result_address=addr,
        page_exists=checker,
        worker_id=worker_id,
        now=now,
    )
    return {"ok": True, "state": "DONE", "invoke_model": False, "step": step, "job_id": job_id, "result_address": done.get("result_address")}
