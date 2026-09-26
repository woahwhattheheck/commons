"""Compact operator read model, published beside the canonical event ledger.

This view never grants custody. Its ages describe ``projected_at``; readers that
need a dispatch decision must use the runtime and its current provider/seat
reconciliation. Building the view is deliberately separate from deciding
whether a ledger write is necessary, so time alone cannot create a commit.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json

from .projector import project
from .routing import status

SCHEMA = "commons-swarm-status/v1"
STATUS_PATH = "holdings/swarm-status.json"
MAX_TASKS = 5000
UNKNOWN = "UNKNOWN"

_CORE = ("task_key", "state", "worker", "recoverable", "dispatchable", "lease")
_FIELDS = (
    "title", "repo", "issue", "pr", "model", "harness", "created_at", "started_at",
    "heartbeat", "latest_activity", "last_activity_at", "closed_at", "owner_liveness",
    "feed_cursor", "base_sha", "current_base_sha", "head_sha", "branch", "merge_sha",
    "artifact", "artifact_sha", "landed_sha", "needs_rebase", "blocker", "next_action",
    "superseded_by", "shipment_source", "shipment_kind", "shipment_claim", "priority",
    "required_capabilities", "source", "sources", "source_event_ids", "collision_count",
    "provider_state", "provider_observed_at", "provider_source", "provider_activity_at",
    "provider_freshness", "provider_age_s", "provider_reconciliation_pending",
    "reconciliation_needed", "previous_worker", "recovered_at",
)


def _known(value):
    return value is not None and value != UNKNOWN and value != "" and value != [] and value != {}


def _compact_task(task):
    # Keep evidence objects and identifiers intact; omit only unknown/empty
    # optional fields. The projector already bounds provenance to 32 IDs.
    row = {field: copy.deepcopy(task.get(field, UNKNOWN)) for field in _CORE}
    row.update({field: copy.deepcopy(task[field]) for field in _FIELDS
                if field in task and _known(task[field])})
    return row


def build(ledger_bytes, now=None, branch="state/claims", max_tasks=MAX_TASKS):
    """Project exactly these persisted ledger bytes without IO or mutation.

    The digest includes the ledger's original encoding/newline bytes, not a
    reserialization. This lets an operator bind the view to its sibling source.
    The task array is bounded; all summary counts cover the full projection.
    """
    raw = ledger_bytes.encode("utf-8") if isinstance(ledger_bytes, str) else ledger_bytes
    if not isinstance(raw, bytes):
        raise ValueError("status snapshot requires exact UTF-8 ledger bytes")
    if isinstance(max_tasks, bool) or not isinstance(max_tasks, int) or not 0 <= max_tasks <= MAX_TASKS:
        raise ValueError("status snapshot max_tasks must be between 0 and 5000")
    try:
        state = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("status snapshot ledger is not valid UTF-8 JSON") from exc
    if not isinstance(state, dict) or state.get("schema") != "commons-swarm-runtime/v1":
        raise ValueError("status snapshot requires a canonical swarm runtime ledger")
    moment = now if now is not None else dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(moment, dt.datetime):
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=dt.timezone.utc)
        moment = moment.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    # Runtime owns seat overlay semantics. Import only when invoked, after the
    # runtime/store modules have finished initializing.
    from .runtime import _seats

    seats = _seats(state)
    view = project(state.get("events", []), now=moment, seats=seats,
                   provider_facts=state.get("provider_facts", {}))
    keys = sorted(view["tasks"])
    rows = [_compact_task(view["tasks"][key]) for key in keys[:max_tasks]]
    return {
        "schema": SCHEMA,
        "authority": branch,
        "source_ledger_sha256": hashlib.sha256(raw).hexdigest(),
        "projected_at": moment,
        "tasks": rows,
        "total": len(keys),
        "truncated": len(rows) < len(keys),
        "summary": status(view["tasks"], seats, moment),
        "collisions": copy.deepcopy(view.get("collisions", [])[-50:]),
        "coverage": copy.deepcopy(state.get("coverage", {})),
        "feed_cursor": state.get("cursors", {}).get("commons", {}).get("feed_cursor") or UNKNOWN,
    }
