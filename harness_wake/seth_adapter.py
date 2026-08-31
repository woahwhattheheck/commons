"""Bounded grokbot_seth LIVE adapter.

Launch a new named leftover or reply to this live grokbot_seth session.
Never Slack @Cursor spawn, ntfy Cursor mail, or issue 1316.
Named idle other-bc resume stays fail-closed via idle_resume.probe_idle_resume.
The watchdog process never invokes a model; this callable records
LAUNCH or REPLY for the owning Grok Bot harness.
"""
from __future__ import annotations

from typing import Any

from .idle_resume import BC_RE, probe_idle_resume

SETH_HARNESS = "grokbot_seth"
SETH_LIVE_HARNESS = "cursor-grokbot"
# This live grokbot_seth session road. Override per call when a job
# names the running/owned session. Not a resume of a different idle bc-.
SETH_THIS_BC = "bc-19a11efe-da1f-4338-8dc9-9dcb283d0c0d"

_LIVE_NORMALIZED = frozenset({
    "grokbotseth",
    "cursorgrokbot",
    "grokbot",
})


def _normalize(harness: str) -> str:
    return "".join(ch for ch in str(harness or "").lower() if ch.isalnum())


def is_grokbot_seth_live(harness: str) -> bool:
    """Narrow LIVE check. Generic Cursor Slack / wire / 1316 stay held."""
    normalized = _normalize(harness)
    if not normalized:
        return False
    if "grokbotseth" in normalized:
        return True
    return normalized in _LIVE_NORMALIZED


def extract_named_bc(job: dict[str, Any] | None) -> str:
    """Named bc- on the job or checkpoint. Empty when the leftover has none."""
    row = job or {}
    candidates = [
        row.get("bc_id"),
        row.get("named_bc"),
        row.get("bc"),
    ]
    checkpoint = row.get("checkpoint")
    if isinstance(checkpoint, dict):
        candidates.extend([
            checkpoint.get("bc_id"),
            checkpoint.get("named_bc"),
            checkpoint.get("bc"),
        ])
    for raw in candidates:
        text = str(raw or "").strip()
        if BC_RE.match(text):
            return text
    return ""


def launch_prompt(job: dict[str, Any] | None) -> str:
    row = job or {}
    job_id = str(row.get("job_id") or "").strip()
    objective = str(row.get("objective") or "named leftover").strip().replace("\n", " ")
    return "LAUNCH leftover job_id=%s. Objective: %s" % (job_id, objective[:1000])


def launch_or_reply(
    job: dict[str, Any] | None,
    *,
    this_bc: str | None = None,
) -> dict[str, Any]:
    """Decide LAUNCH (new spawn) or REPLY (this live session) for a named job.

    GH tick records the receipt. This callable does not Slack, ntfy,
    reassign issue 1316, or invoke a model.
    """
    row = dict(job or {})
    job_id = str(row.get("job_id") or "").strip()
    session = str(this_bc or SETH_THIS_BC).strip()
    named = extract_named_bc(row)
    base = {
        "job_id": job_id,
        "road": "grokbot_seth",
        "invoke_model": False,
        "live_resume": False,
        "process_model_invocations": 0,
        "ntfy_sent": False,
        "issue_1316": False,
        "slack_spawn": False,
    }
    if not named:
        prompt = launch_prompt(row)
        out = dict(base)
        out.update({
            "ok": True,
            "action": "LAUNCH",
            "state": "LAUNCH",
            "bc_id": "",
            "prompt": prompt,
            "note": (
                "No named bc-. Spawn a new grokbot_seth cloud agent for "
                "this leftover. Not other-bc resume. Not Slack @Cursor."
            ),
        })
        return out
    if named == session:
        out = dict(base)
        out.update({
            "ok": True,
            "action": "REPLY",
            "state": "REPLY",
            "bc_id": named,
            "this_bc": session,
            "note": (
                "Named bc- is this live grokbot_seth session. Follow-up "
                "enqueue on the running/owned road. Not idle other-run resume."
            ),
        })
        return out
    probe = probe_idle_resume(named, this_bc=session)
    probe.update(base)
    probe["bc_id"] = named
    probe["this_bc"] = session
    probe["ok"] = False
    probe["live_resume"] = False
    probe["invoke_model"] = False
    probe["action"] = "STOP"
    probe.setdefault("state", "UNMEASURED")
    probe["note"] = (
        "Named bc- is a different idle run. Fail-closed. "
        "Named idle other-bc resume stays UNMEASURED."
    )
    return probe
