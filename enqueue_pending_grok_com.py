#!/usr/bin/env python3
"""Queue pending GROK.COM ACTION pages into wake_jobs. Never invokes a model.

commons-action-executor is starved by a cancelled workflow_run backlog, so a
landed p/{id}.md never becomes wake_jobs/{id}.json. The scheduled job-watchdog
tick materializes only this addressable grok.com boundary.
"""
from __future__ import annotations

import json

import action_executor as ae


def enqueue_pending_grok_com() -> dict:
    queued: list[str] = []
    for rec in ae.pending("github"):
        if not ae.is_grok_com_target(rec["target"]) or rec["verb"] in {"POST", "REPLY"}:
            continue
        ident = rec["meta"]["id"]
        result = ae.queue_grok_com_task(rec["meta"], rec["verb"], rec["payload"], ident)
        queued.append(str(result.get("job_path") or ("wake_jobs/%s.json" % ident)))
    return {"ok": True, "queued": queued}


def main() -> int:
    print(json.dumps(enqueue_pending_grok_com(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
