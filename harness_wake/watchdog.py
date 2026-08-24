"""Cheap Commons job watchdog. Never invokes a model."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from independent_commons_mcp.jobs import JobStore

from .cursor_adapter import deliver_ntfy, should_ring_issue_1316


def run(
    jobs_dir: str | Path | None = None,
    *,
    deliver: bool = False,
    worker_id: str = "gh-watchdog",
    now: str | None = None,
    http=None,
) -> dict[str, Any]:
    store = JobStore(jobs_dir)
    summary = store.tick_all(worker_id=worker_id, now=now)
    deliveries = []
    if deliver:
        for row in summary.get("jobs") or []:
            if row.get("action") != "WAKE":
                continue
            job = (row.get("job") or {})
            harness = str(job.get("harness") or "")
            if should_ring_issue_1316(harness):
                receipt = {
                    "job_id": row["job_id"],
                    "attempt_id": row.get("attempt_id"),
                    "road": "issue_1316",
                    "note": "Desktop Grok Bot doorbell. This watchdog does not edit issue 1316 from a Slack-cloud job.",
                    "ok": False,
                    "state": "NOT_THIS_HARNESS",
                }
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
