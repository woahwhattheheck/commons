"""Separate harness callback. Not invoked by tick(). Consumes a scheduler delivery."""
from __future__ import annotations

from typing import Any, Callable

from independent_commons_mcp.jobs import JobStore


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
    job = store.get(job_id)
    step = int((job.get("checkpoint") or {}).get("step") or 0) + 1
    store.checkpoint(job_id, {"step": step}, next_wake_at=now, worker_id=worker_id, now=now)
    store.append_receipt(job_id, {
        "attempt_id": delivery.get("attempt_id"),
        "event": "ack",
        "ts": now,
        "worker_id": worker_id,
        "carrier": delivery.get("state"),
    })
    if step < 2:
        return {"ok": True, "state": "CHECKPOINT", "invoke_model": True, "step": step, "job_id": job_id}
    addr = job.get("result_address") or ""
    pages.add(addr)
    checker = page_exists or (lambda ident: ident in pages)
    done = store.complete(
        job_id,
        result={"durable": True, "step": step, "kind": "page"},
        result_address=addr,
        page_exists=checker,
        worker_id=worker_id,
        now=now,
    )
    return {"ok": True, "state": "DONE", "invoke_model": True, "step": step, "job_id": job_id, "result_address": done.get("result_address")}
