"""Cheap Commons job watchdog. Never invokes a model."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from independent_commons_mcp.jobs import JobStore
from independent_commons_mcp.truth import GitTruth

from .cursor_adapter import deliver_ntfy, is_cursor_harness


def pinned_head_oracle(
    *,
    truth: Any | None = None,
    ls_remote: Callable[[], str] | None = None,
    http: Callable[..., dict[str, Any]] | None = None,
) -> Callable[[str], bool]:
    """One lazily SHA-pinned public HEAD page oracle for a single watchdog run.

    Official HEAD is resolved on first use, then reused for every page check.
    Constructing the oracle makes zero truth calls, so no-job and already
    terminal ticks stay silent.
    """
    source = truth
    pinned: dict[str, str | None] = {"sha": None}

    def page_exists(ident: str) -> bool:
        nonlocal source
        if source is None:
            source = GitTruth(http=http, ls_remote=ls_remote)
        if pinned["sha"] is None:
            pinned["sha"] = source.head_sha()
        status, text = source.read_at_sha("p/%s.md" % ident, pinned["sha"])
        return status == 200 and text is not None

    return page_exists


def run(
    jobs_dir: str | Path | None = None,
    *,
    deliver: bool = False,
    worker_id: str = "gh-watchdog",
    now: str | None = None,
    http=None,
    page_exists: Callable[[str], bool] | None = None,
    truth: Any | None = None,
) -> dict[str, Any]:
    store = JobStore(jobs_dir)
    oracle = page_exists if page_exists is not None else pinned_head_oracle(truth=truth)
    summary = store.tick_all(worker_id=worker_id, now=now, page_exists=oracle)
    deliveries = []
    if deliver:
        for row in summary.get("jobs") or []:
            if row.get("action") != "WAKE":
                continue
            job = (row.get("job") or {})
            harness = str(job.get("harness") or "")
            if is_cursor_harness(harness):
                receipt = {
                    "job_id": row["job_id"],
                    "attempt_id": row.get("attempt_id"),
                    "road": "none",
                    "note": (
                        "Owner quota hold: do not wake, resume, mail, or invoke "
                        "Cursor / Cursor Grok / Grok Bot."
                    ),
                    "ok": True,
                    "state": "CURSOR_QUOTA_HOLD",
                }
                store.append_receipt(row["job_id"], {
                    "attempt_id": row.get("attempt_id"),
                    "event": "cursor_quota_hold",
                    "ts": row.get("now"),
                    "carrier": "CURSOR_QUOTA_HOLD",
                    "id": job.get("job_id"),
                })
                deliveries.append(receipt)
                continue
            receipt = deliver_ntfy(job, str(row.get("attempt_id") or ""), http=http)
            store.append_receipt(row["job_id"], {
                "attempt_id": row.get("attempt_id"),
                "event": "deliver",
                "ts": row.get("now"),
                "carrier": receipt.get("state"),
                "host": receipt.get("host"),
                "http_status": receipt.get("http_status"),
                "id": job.get("job_id"),
            })
            deliveries.append(receipt)
    summary["deliveries"] = deliveries
    summary["delivered_count"] = sum(1 for row in deliveries if row.get("state") == "MAIL")
    summary["process_model_invocations"] = 0
    summary["invoke_model"] = False
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cheap Commons job watchdog. Never invokes a model.")
    parser.add_argument("--tick", action="store_true", help="tick every job (default)")
    parser.add_argument("--deliver", action="store_true", help="mail ntfy on WAKE after the cheap pre-check; still no model")
    parser.add_argument("--jobs-dir", default="")
    args = parser.parse_args(argv)
    summary = run(args.jobs_dir or None, deliver=args.deliver)
    json.dump(summary, sys.stdout, ensure_ascii=True, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0
