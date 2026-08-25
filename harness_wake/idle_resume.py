"""Fail-closed probe for named idle bc- resume of a different run.

This harness can list and inspect cloud agents. It has no resume or
enqueue tool for another bc-. get-message-queue is this run only.
Do not claim a live resume. Do not invoke a model. Do not poke parallel
idle runs.

A separately running named-harness adapter may replace this probe only
when it supplies a canonical callback receipt. In-process callables are
not evidence and are deliberately not accepted by this API.
"""
from __future__ import annotations

import re

from .cursor_adapter import THIS_BC

BC_RE = re.compile(r"^bc-[0-9a-fA-F-]{8,}$")

# Measured 2026-08-24 in a Cursor cloud session: cursor-cloud MCP listed
# idle named runs and exposed list/inspect/queue-for-this-run tools only.
# No resume or follow-up enqueue tool was in the catalog. Those idle runs
# were not resumed.
RESUME_ROADS_IN_THIS_HARNESS: tuple[str, ...] = ()


def probe_idle_resume(
    bc_id: str,
    *,
    this_bc: str = THIS_BC,
) -> dict[str, object]:
    ident = (bc_id or "").strip()
    out: dict[str, object] = {
        "ok": False,
        "action": "STOP",
        "invoke_model": False,
        "measured": False,
        "live_resume": False,
        "bc_id": ident,
        "this_bc": this_bc,
        "resume_roads": list(RESUME_ROADS_IN_THIS_HARNESS),
    }
    if not ident or not BC_RE.match(ident):
        out["state"] = "BAD_ID"
        out["reason"] = "bc_id must look like bc-..."
        return out
    if ident == this_bc:
        out["state"] = "NOT_OTHER_RUN"
        out["reason"] = "this is the current session, not a different idle run"
        return out
    out["state"] = "UNMEASURED"
    out["reason"] = (
        "no resume/enqueue road in this harness; list/inspect only; "
        "get-message-queue is this run only"
    )
    return out
