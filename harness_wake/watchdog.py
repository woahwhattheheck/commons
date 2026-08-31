"""Cheap Commons job watchdog. Never invokes a model."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from independent_commons_mcp.jobs import JobStore, public_job, utc_now
from independent_commons_mcp.truth import GitTruth

from .cursor_adapter import deliver_ntfy, is_cursor_harness
from .inbound import default_record_dirs, ingest_cursor_leftovers
from .seth_adapter import is_grokbot_seth_live, launch_or_reply


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
    records_dirs: list[str | Path] | str | Path | None = None,
) -> dict[str, Any]:
    store = JobStore(jobs_dir)
    inbound = {
        "ok": True,
        "state": "SKIPPED",
        "upserted": [],
        "existing": [],
        "ignored": [],
        "invoke_model": False,
        "live_resume": False,
        "process_model_invocations": 0,
        "ntfy_sent": False,
        "issue_1316": False,
        "note": "Inbound ingest runs on the default watchdog jobs dir or when records_dirs is passed.",
    }
    if records_dirs is not None or jobs_dir in (None, ""):
        sources = records_dirs if records_dirs is not None else default_record_dirs()
        inbound = ingest_cursor_leftovers(sources, store.directory, now=now)
    oracle = page_exists if page_exists is not None else pinned_head_oracle(truth=truth)
    rows = []
    for ident in store.list_ids():
        job = store.get(ident)
        harness = str(job.get("harness") or "")
        if is_cursor_harness(harness) and not is_grokbot_seth_live(harness):
            rows.append({
                "ok": True,
                "state": "TICKED",
                "job_id": ident,
                "action": "HOLD",
                "invoke_model": False,
                "reason": "CURSOR_QUOTA_HOLD",
                "now": now or utc_now(),
                "note": "Owner quota hold: this row cannot authorize model invocation.",
                "job": public_job(job),
            })
            continue
        rows.append(
            store.tick(ident, now=now, worker_id=worker_id, page_exists=oracle)
        )
    summary = {
        "ok": True,
        "state": "TICKED",
        "inbound": inbound,
        "jobs": rows,
        "wake_count": sum(1 for row in rows if row.get("action") == "WAKE"),
        "stop_count": sum(1 for row in rows if row.get("action") == "STOP"),
        "backoff_count": sum(1 for row in rows if row.get("action") == "BACKOFF"),
        "hold_count": sum(1 for row in rows if row.get("action") == "HOLD"),
        "invoke_model_count": sum(1 for row in rows if row.get("invoke_model")),
        "process_model_invocations": 0,
        "note": (
            "Watchdog never invokes a model. Generic Cursor Slack / ntfy / "
            "1316 rows stay held. grokbot_seth LIVE rows tick."
        ),
    }
    store._write_last_tick(summary)
    deliveries = []
    if deliver:
        for row in summary.get("jobs") or []:
            if row.get("action") == "HOLD" and row.get("reason") == "CURSOR_QUOTA_HOLD":
                job = row.get("job") or {}
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
                deliveries.append(receipt)
                continue
            if row.get("action") != "WAKE":
                continue
            job = (row.get("job") or {})
            harness = str(job.get("harness") or "")
            if is_grokbot_seth_live(harness):
                receipt = launch_or_reply(job)
                receipt = dict(receipt)
                receipt.setdefault("job_id", row["job_id"])
                receipt.setdefault("attempt_id", row.get("attempt_id"))
                store.append_receipt(row["job_id"], {
                    "attempt_id": row.get("attempt_id"),
                    "event": "deliver",
                    "ts": row.get("now"),
                    "carrier": receipt.get("state"),
                    "road": "grokbot_seth",
                    "action": receipt.get("action"),
                    "bc_id": receipt.get("bc_id") or "",
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
    try:
        from peer_wake.bus import attach_watchdog
    except ImportError:
        summary["peer_wake"] = {
            "ok": False,
            "state": "BUS_UNAVAILABLE",
            "live_wake": False,
            "invoke_model": False,
            "process_model_invocations": 0,
        }
    else:
        attach_watchdog(summary, deliver=deliver, http=http)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cheap Commons job watchdog. Never invokes a model.")
    parser.add_argument("--tick", action="store_true", help="tick every job (default)")
    parser.add_argument("--deliver", action="store_true", help="mail ntfy on WAKE after the cheap pre-check; still no model")
    parser.add_argument("--jobs-dir", default="")
    parser.add_argument("--records-dir", action="append", default=[], help="leftover p/ or wake records to ingest before tick")
    args = parser.parse_args(argv)
    summary = run(
        args.jobs_dir or None,
        deliver=args.deliver,
        records_dirs=args.records_dir or None,
    )
    json.dump(summary, sys.stdout, ensure_ascii=True, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0
