"""Cursor-owned adapter for the Commons wake/job contract.

This is not the independent Commons MCP pack. The MCP exposes job state.
This adapter names the inbound roads this harness can actually measure.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


TOPIC = "woahwhattheheck-commons-board"
NTFY_HOSTS = (
    "https://ntfy.sh/" + TOPIC,
    "https://ntfy.envs.net/" + TOPIC,
)
ISSUE_1316 = 1316
THIS_BC = "bc-263a6b3f-4492-5dab-9927-49a856e551e0"
SLACK_CHANNEL = "C0BRGMDQB6G"
CURSOR_QUOTA_HOLD = True


def is_cursor_harness(harness: str) -> bool:
    text = str(harness or "").lower()
    normalized = "".join(ch for ch in text if ch.isalnum())
    return (
        "cursor" in normalized
        or "grokbot" in normalized
        or "issue1316" in normalized
    )

CLAIMED_PATHS = {
    "slack_cursor_app": {
        "road": "Installed Cursor Slack app @Cursor in TokenJunkieLabs #commons",
        "behavior": "Starts a NEW cloud agent from the thread. Spawn, not resume of a named idle bc-.",
        "measured": True,
        "enabled": False,
        "state": "CURSOR_QUOTA_HOLD",
        "this_session": "source=slack " + THIS_BC,
    },
    "subscribe_timer": {
        "road": "cursor-subscriptions subscribe_timer",
        "behavior": "Enqueues a follow-up on THIS bc- when the agent is free. Resume of the named running session, not a fresh contextless chat.",
        "measured": True,
        "enabled": False,
        "state": "CURSOR_QUOTA_HOLD",
        "note": "Does not resume a different idle bc-.",
    },
    "issue_1316": {
        "road": "GitHub issue 1316 reassignment via harness-ping.yml",
        "behavior": "Desktop Grok Bot doorbell. Not this Slack-launched cloud session.",
        "measured": True,
        "enabled": False,
        "state": "CURSOR_QUOTA_HOLD",
        "harness": "cursor-desktop",
    },
    "ntfy_poll": {
        "road": "ntfy topic " + TOPIC,
        "behavior": "Mail. A running agent that polls can hear. An idle other bc- cannot. ntfy 200 is mail.",
        "measured": True,
        "enabled": False,
        "state": "CURSOR_QUOTA_HOLD",
    },
    "gh_watchdog": {
        "road": ".github/workflows/job-watchdog.yml + python3 -m harness_wake",
        "behavior": "Cheap tick of wake_jobs/*.json. Never invokes a model. Writes wake_jobs/_last_tick.json.",
        "measured": True,
    },
}

UNMEASURED = {
    "named_idle_bc_resume": {
        "road": "cursor-cloud MCP follow-up on another bc-",
        "behavior": "cursor-cloud can list/inspect. It cannot enqueue a follow-up or resume IDLE on another run. get-message-queue is this run only.",
        "measured": False,
    },
    "claude_slack_app": {
        "road": "Claude Slack app",
        "behavior": "Disconnected. Do not claim it.",
        "measured": False,
        "claimed": False,
    },
}

HARNESS = "cursor-slack"
STOP_PREDICATE = (
    "DONE, CANCELLED, EXHAUSTED (deadline/budget/max_attempts), NOT_DUE, "
    "LEASE_HELD, BLOCKED_UNCHANGED, UNCHANGED_CHECKPOINT backoff"
)


def claimed_paths() -> dict[str, Any]:
    return {
        "claimed": CLAIMED_PATHS,
        "unmeasured": UNMEASURED,
        "harness": HARNESS,
        "cursor_quota_hold": CURSOR_QUOTA_HOLD,
    }


def ntfy_payload(job: dict[str, Any], attempt_id: str) -> dict[str, Any]:
    job_id = job["job_id"]
    return {
        "from": "COMMONS",
        "to": job.get("owner_claim") or "TABLE",
        "id": job_id,
        "job_id": job_id,
        "attempt_id": attempt_id,
        "harness": job.get("harness") or HARNESS,
        "body": (
            "WAKE job_id=%s attempt_id=%s. Attempt ids are receipts. "
            "Open the checkpoint and resume the owning harness only. "
            "Do not bounce this to Bryce because a turn ended."
        ) % (job_id, attempt_id),
    }


def deliver_ntfy(job: dict[str, Any], attempt_id: str, *, http=None) -> dict[str, Any]:
    if is_cursor_harness(str(job.get("harness") or "")):
        return {
            "ok": True,
            "state": "CURSOR_QUOTA_HOLD",
            "job_id": job["job_id"],
            "attempt_id": attempt_id,
            "note": "Owner quota hold: no Cursor wake mail was sent.",
        }
    payload = json.dumps(ntfy_payload(job, attempt_id)).encode("utf-8")
    last = {"ok": False, "state": "UNSENT", "job_id": job["job_id"], "attempt_id": attempt_id}
    poster = http or _http_post
    for url in NTFY_HOSTS:
        result = poster(url, payload)
        last = {
            "ok": result.get("status") == 200,
            "state": "MAIL" if result.get("status") == 200 else "FAILED",
            "http_status": result.get("status"),
            "host": url,
            "job_id": job["job_id"],
            "attempt_id": attempt_id,
            "note": "ntfy 200 is mail. job_id is unchanged. attempt_id is the event receipt.",
        }
        if last["ok"]:
            return last
    return last


def should_ring_issue_1316(harness: str) -> bool:
    # Historical compatibility name. Owner quota hold disables the doorbell.
    return False


def _http_post(url: str, data: bytes) -> dict[str, Any]:
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=12) as resp:
            return {"status": int(resp.status), "body": resp.read()[:200].decode("utf-8", "replace")}
    except Exception as exc:
        return {"status": 0, "body": "", "error": type(exc).__name__}
