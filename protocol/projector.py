"""Deterministic Commons Observatory projector.

Converts protocol events plus existing legacy bakes (presence, lastseen,
pulse, jobs, claims, cash, grok captures) into one snapshot. The snapshot
is a bake. Raw history is not destroyed. Quiet presence is preserved.
Slack authors are not sessions. Missing evidence is UNKNOWN.
"""
from __future__ import annotations

import hashlib
from typing import Any

from protocol.events import canonical_json, classify_runtime, parse_event, parse_events
from protocol.schema import (
    ACTIVE_JOB_STATUSES,
    ATTENTION_KINDS,
    CLASSIFICATIONS,
    COLLISION_KINDS,
    DEFAULT_STALE_AFTER_SECONDS,
    EVIDENCE_GRADES,
    EVENT_KINDS,
    JOB_STATUS_TO_STATE,
    PROTOCOL_ID,
    PROTOCOL_VERSION,
    SESSION_STATES,
    SNAPSHOT_SCHEMA,
    TERMINAL_EVENT_KINDS,
    UNKNOWN,
    WORKING_EVENT_KINDS,
)

GROK_URL_PREFIX = "https://grok.com/c/"
GROK_EXECUTOR_SCHEMA = "commons-grok-executor-job/v1"
GROK_POST_SUBMIT = frozenset({"SUBMITTING", "SUBMITTED", "RESULT_CAPTURED"})
GROK_PRE_SUBMIT = frozenset({"NOT_SUBMITTED", "CAPTURE_STARTED"})
EXPECTED_NEXT = {
    "WORKING": "CHECKPOINT or HEARTBEAT",
    "ACTIVE": "CHECKPOINT or HEARTBEAT",
    "IDLE": "START or HEARTBEAT",
    "BLOCKED": "ATTENTION_REQUESTED, RELEASE, or typed recovery",
    "STALE": "HANDOFF or lineage-linked continuation (new run_id)",
    "RELEASED": "optional later START on the same session_id",
    "TERMINAL": "none; do not replay a finished prompt",
    "SUPERSEDED": "none; read supersession evidence",
    "UNKNOWN": "UNKNOWN",
}


def _parse_ts(value: str) -> float:
    text = (value or "").strip()
    if not text or text == UNKNOWN:
        return 0.0
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        from datetime import datetime
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def _age_seconds(ts: str, now: str) -> float | None:
    start = _parse_ts(ts)
    end = _parse_ts(now)
    if start <= 0 or end <= 0:
        return None
    return max(0.0, end - start)


def _canon_url(url: str) -> str:
    text = (url or "").strip()
    if not text.startswith(GROK_URL_PREFIX):
        return text
    rid = text[len(GROK_URL_PREFIX):].split("?", 1)[0].split("#", 1)[0]
    return GROK_URL_PREFIX + rid if rid else text


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unknown_session_label(event: dict[str, Any]) -> str:
    """Do not mint a session from missing metadata."""
    return UNKNOWN


def _job_session_id(job: dict[str, Any]) -> str:
    return "job." + str(job.get("job_id") or "unknown")[:64]


def _evidence(source: str, grade: str, **extra: Any) -> dict[str, Any]:
    row = {"source": source, "grade": grade if grade in EVIDENCE_GRADES else UNKNOWN}
    row.update(extra)
    return row


def grade_artifact(art: dict[str, Any], *, now: str, event_ts: str, stale_after: int) -> str:
    if art.get("grade") in EVIDENCE_GRADES and art.get("grade") != UNKNOWN:
        return art["grade"]
    if art.get("provider_private") and not art.get("sha256"):
        return "PRIVATE_ARTIFACT_NOT_EXTRACTED"
    if art.get("sha256") and art.get("size_bytes") is not None:
        return "REPRODUCIBLE"
    if art.get("sha256"):
        return "OBSERVED"
    age = _age_seconds(event_ts, now)
    if age is not None and age > stale_after:
        return "STALE"
    return UNKNOWN


def apply_event_to_session(session: dict[str, Any], event: dict[str, Any], now: str, stale_after: int) -> None:
    session["events"].append(event["event_id"])
    session["last_event_id"] = event["event_id"]
    session["last_kind"] = event["kind"]
    if event["ts"] != UNKNOWN:
        prev = _parse_ts(session.get("last_ts") or "")
        cur = _parse_ts(event["ts"])
        if cur >= prev:
            session["last_ts"] = event["ts"]
    if event["model"] != UNKNOWN:
        session["model"] = event["model"]
        session["model_grade"] = "OBSERVED"
    if event["harness"] != UNKNOWN:
        session["harness"] = event["harness"]
    if event["classification"] != UNKNOWN:
        session["classification"] = event["classification"]
    if event["tools"]:
        merged = list(session.get("tools") or [])
        for tool in event["tools"]:
            if tool not in merged:
                merged.append(tool)
        session["tools"] = merged
    if event["objective"] != UNKNOWN:
        session["objective"] = event["objective"]
    if event["task_id"] != UNKNOWN:
        session["task_id"] = event["task_id"]
    if event["run_id"] != UNKNOWN:
        session["run_id"] = event["run_id"]
    if event["claimed_paths"]:
        paths = list(session.get("claimed_paths") or [])
        for path in event["claimed_paths"]:
            if path not in paths:
                paths.append(path)
        session["claimed_paths"] = paths
    if event["semantic_area"] != UNKNOWN:
        session["semantic_area"] = event["semantic_area"]
    if event["dedupe_key"] != UNKNOWN:
        session["dedupe_key"] = event["dedupe_key"]
    if event["checkpoint"] != UNKNOWN:
        session["checkpoint"] = event["checkpoint"]
    if event["grok_url"]:
        session["grok_url"] = _canon_url(event["grok_url"])
    if event["lease"]["lease_id"] != UNKNOWN:
        session["lease"] = event["lease"]
    session["evidence"].append(_evidence("event", "OBSERVED", event_id=event["event_id"], kind=event["kind"]))
    kind = event["kind"]
    if kind == "BLOCKED":
        session["state"] = "BLOCKED"
        session["blocker"] = event["blocker"]
    elif kind == "LEASE_EXPIRED":
        session["state"] = "STALE"
    elif kind == "SUPERSEDED":
        session["state"] = "SUPERSEDED"
        session["supersedes"] = event["supersedes"]
    elif kind == "RELEASE":
        session["state"] = "RELEASED"
    elif kind in {"TERMINAL", "LANDING"}:
        prior = session.get("terminal_disposition")
        session["state"] = "TERMINAL"
        session["terminal_disposition"] = event["terminal_disposition"]
        if prior not in {None, "", UNKNOWN} and event["terminal_disposition"] not in {UNKNOWN, prior}:
            session["contradiction"] = True
            session["evidence"].append(_evidence("event", "CONTRADICTED", event_id=event["event_id"], prior=prior))
    elif kind in WORKING_EVENT_KINDS:
        session["state"] = "WORKING"
        session["blocker"] = {"type": UNKNOWN, "detail": UNKNOWN}
    age = _age_seconds(session.get("last_ts") or "", now)
    if session["state"] in {"WORKING", "ACTIVE", "IDLE"} and age is not None and age > stale_after:
        session["state"] = "STALE"
        session["state_reason"] = "last observed event older than stale_after_seconds"
    elif session["state"] == "WORKING" and kind == "HEARTBEAT" and (age is None or age <= stale_after):
        session["state"] = "ACTIVE"


def empty_session(session_id: str, *, provenance: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "label": session_id,
        "state": "UNKNOWN",
        "classification": UNKNOWN,
        "model": UNKNOWN,
        "model_grade": UNKNOWN,
        "harness": UNKNOWN,
        "tools": [],
        "objective": UNKNOWN,
        "task_id": UNKNOWN,
        "run_id": UNKNOWN,
        "claimed_paths": [],
        "semantic_area": UNKNOWN,
        "dedupe_key": UNKNOWN,
        "checkpoint": UNKNOWN,
        "blocker": {"type": UNKNOWN, "detail": UNKNOWN},
        "lease": {"lease_id": UNKNOWN, "holder": UNKNOWN, "until": UNKNOWN, "descriptive_only": True},
        "grok_url": "",
        "last_ts": UNKNOWN,
        "last_kind": UNKNOWN,
        "last_event_id": UNKNOWN,
        "events": [],
        "provenance": provenance,
        "existence": "SESSION",
        "evidence": [],
    }


def derive_collisions(sessions: list[dict[str, Any]], tasks: list[dict[str, Any]], head_sha: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def add(kind: str, **payload: Any) -> None:
        if kind not in COLLISION_KINDS:
            kind = UNKNOWN
        findings.append({
            "kind": kind,
            "advisory": True,
            "blocks_participation": False,
            **payload,
        })

    live = [row for row in sessions if row["state"] in {"ACTIVE", "WORKING", "IDLE", "BLOCKED", "STALE"}]
    path_owners: dict[str, list[str]] = {}
    dir_owners: dict[str, list[str]] = {}
    area_owners: dict[str, list[str]] = {}
    dedupe_owners: dict[str, list[str]] = {}
    run_owners: dict[str, list[str]] = {}
    url_owners: dict[str, list[str]] = {}
    for row in live:
        sid = row["session_id"]
        for path in row.get("claimed_paths") or []:
            path_owners.setdefault(path, []).append(sid)
            if "/" in path:
                directory = path.rsplit("/", 1)[0] + "/"
                dir_owners.setdefault(directory, []).append(sid)
        if row.get("semantic_area") and row["semantic_area"] != UNKNOWN:
            area_owners.setdefault(row["semantic_area"], []).append(sid)
        if row.get("dedupe_key") and row["dedupe_key"] != UNKNOWN:
            dedupe_owners.setdefault(row["dedupe_key"], []).append(sid)
        if row.get("run_id") and row["run_id"] != UNKNOWN:
            run_owners.setdefault(row["run_id"], []).append(sid)
        if row.get("grok_url"):
            url_owners.setdefault(_canon_url(row["grok_url"]), []).append(sid)
        lease_until = (row.get("lease") or {}).get("until") or UNKNOWN
        if lease_until != UNKNOWN and row["state"] in {"WORKING", "ACTIVE", "BLOCKED"}:
            # Descriptive only: a past until is a stale-lease finding, not a lock.
            if _parse_ts(lease_until) and _parse_ts(row.get("last_ts") or "") and _parse_ts(lease_until) < _parse_ts(row.get("last_ts") or ""):
                add("STALE_LEASE", session_id=sid, lease=row.get("lease"), evidence=[_evidence("lease", "OBSERVED", session_id=sid)])
    for path, owners in path_owners.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("EXACT_PATH", path=path, sessions=uniq, evidence=[_evidence("claimed_paths", "OBSERVED", path=path)])
    for directory, owners in dir_owners.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("DIRECTORY", directory=directory, sessions=uniq, evidence=[_evidence("claimed_paths", "OBSERVED", directory=directory)])
    for area, owners in area_owners.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("SEMANTIC_AREA", semantic_area=area, sessions=uniq, evidence=[_evidence("semantic_area", "OBSERVED", semantic_area=area)])
    for key, owners in dedupe_owners.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("DUPLICATE_DEDUPE_KEY", dedupe_key=key, sessions=uniq)
    for key, owners in run_owners.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("DUPLICATE_RUN_KEY", run_id=key, sessions=uniq)
    for url, owners in url_owners.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("DUPLICATE_GROK_URL", grok_url=url, sessions=uniq)
    objectives: dict[str, list[str]] = {}
    for row in live:
        obj = (row.get("objective") or UNKNOWN).strip().lower()
        if obj and obj != UNKNOWN.lower():
            objectives.setdefault(obj, []).append(row["session_id"])
    for obj, owners in objectives.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            add("EQUIVALENT_WORK", objective=obj, sessions=uniq)
    if head_sha:
        for row in live + tasks:
            sha = row.get("head_sha") or ""
            if sha and sha != head_sha:
                add("BRANCH_DIVERGENCE", session_id=row.get("session_id") or row.get("task_id"), observed_sha=sha, main_sha=head_sha)
    findings.sort(key=lambda row: (row["kind"], canonical_json(row)))
    return findings


def derive_attention(sessions: list[dict[str, Any]], collisions: list[dict[str, Any]], events: list[dict[str, Any]], economy: dict[str, Any]) -> list[dict[str, Any]]:
    items = []

    def add(kind: str, **payload: Any) -> None:
        if kind not in ATTENTION_KINDS:
            kind = "HUMAN_REQUESTED"
        items.append({"kind": kind, "advisory": True, "blocks_participation": False, **payload})

    for event in events:
        if event["kind"] == "ATTENTION_REQUESTED":
            add("HUMAN_REQUESTED", event_id=event["event_id"], reason=event.get("attention_reason"), session_id=event.get("session_id"))
        if event["kind"] == "BLOCKED" and (event.get("blocker") or {}).get("type") == "external_authority":
            add("EXTERNAL_BLOCKER", event_id=event["event_id"], session_id=event.get("session_id"), blocker=event.get("blocker"))
        for art in event.get("artifacts") or []:
            if art.get("provider_private") and not art.get("sha256"):
                add("PRIVATE_ARTIFACT", event_id=event["event_id"], path=art.get("path"))
        if event.get("cost", {}).get("grade") == "PROVIDER_REPORTED" and not event.get("cost", {}).get("visible"):
            add("UNSUPPORTED_CLAIM", event_id=event["event_id"], detail="cost claimed without visible evidence")
        if event["kind"] == "TERMINAL" and event.get("terminal_disposition") in {UNKNOWN, ""}:
            add("AMBIGUOUS_COMPLETION", event_id=event["event_id"], session_id=event.get("session_id"))
        provider = event.get("provider") if isinstance(event.get("provider"), dict) else {}
        if event["kind"] in {"LANDING", "TERMINAL"} and provider.get("needs_gpt_review"):
            add("AMBIGUOUS_COMPLETION", event_id=event["event_id"], session_id=event.get("session_id"), detail="provider output without GPT review")
    pr_by_task: dict[str, set[str]] = {}
    for event in events:
        if event["kind"] != "LANDING":
            continue
        task = event.get("task_id") or UNKNOWN
        for art in event.get("artifacts") or []:
            url = str(art.get("url") or "")
            if "/pull/" in url or "/pulls/" in url:
                pr_by_task.setdefault(task, set()).add(url.split("?")[0])
    for task, urls in pr_by_task.items():
        if len(urls) > 1:
            add("AMBIGUOUS_COMPLETION", task_id=task, detail="same task landed under different PRs", prs=sorted(urls))
    for row in sessions:
        if row["state"] == "BLOCKED":
            add("EXTERNAL_BLOCKER", session_id=row["session_id"], blocker=row.get("blocker"))
        if row.get("contradiction"):
            add("UNSUPPORTED_CLAIM", session_id=row["session_id"], detail="contradictory receipts")
        if row.get("provider_uncertainty"):
            add("PROVIDER_UNCERTAINTY", session_id=row["session_id"], detail=row.get("provider_uncertainty"))
    for hit in collisions:
        if hit["kind"] in {"EXACT_PATH", "DUPLICATE_GROK_URL", "DUPLICATE_RUN_KEY", "EQUIVALENT_WORK"}:
            add("IRRECONCILABLE_COLLISION", collision=hit)
    cash = economy.get("collected_cash_usd")
    if cash not in (0, 0.0, None) and economy.get("cash_state") != "LANDED":
        add("MONEY_DECISION", detail="non-zero cash claimed without LANDED cash_state", evidence=economy.get("evidence"))
    if economy.get("next_economic_action"):
        # Visible; not auto-send.
        pass
    items.sort(key=lambda row: (row["kind"], canonical_json(row)))
    return items


def project_economy(legacy: dict[str, Any]) -> dict[str, Any]:
    recovery = legacy.get("recovery") if isinstance(legacy.get("recovery"), dict) else {}
    offer = recovery.get("offer") if isinstance(recovery.get("offer"), dict) else {}
    truth = recovery.get("truth") if isinstance(recovery.get("truth"), dict) else {}
    cash = truth.get("collected_cash_usd")
    if cash is None:
        cash = offer.get("collected_cash_usd")
    if not isinstance(cash, (int, float)) or isinstance(cash, bool):
        cash = 0
    replies = truth.get("replies_observed")
    if not isinstance(replies, int) or isinstance(replies, bool):
        replies = 0
    contacts = truth.get("distinct_contacts_sent")
    if not isinstance(contacts, int) or isinstance(contacts, bool):
        contacts = 0
    return {
        "loop": "observed need → independently verified buyer → bounded offer → authorized contact → delivered transport → human reply → accepted scope → delivery → acceptance → payment → cash",
        "collected_cash_usd": cash,
        "cash_state": offer.get("cash_state") or truth.get("bank_available") or "NOT_LANDED",
        "bank_available": truth.get("bank_available") or "NOT_LANDED",
        "buyer": truth.get("buyer") or UNKNOWN,
        "replies_observed": replies,
        "distinct_contacts_sent": contacts,
        "provider_transports_observed": truth.get("provider_transports_observed") if isinstance(truth.get("provider_transports_observed"), int) else 0,
        "never_counted_as_revenue": [
            "draft", "intent", "invoice", "checkout_page", "sandbox_stripe",
            "wallet_capability", "token_balance", "unverified_buyer_interest",
        ],
        "next_economic_action": "Keep USD 0 visible. Do not send outreach or spend from this projector.",
        "evidence": [
            _evidence("revenue/payment_ready/recovery.json", "VERIFIED" if recovery else "UNKNOWN", field="truth.collected_cash_usd"),
        ],
    }


def route_work(sessions: list[dict[str, Any]], need: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Advisory executor router. Not a queue. Never a gate."""
    need = need or {}
    required = [item.upper() for item in (need.get("capabilities") or need.get("need") or []) if isinstance(item, str)]
    candidates = []
    for row in sessions:
        state = row.get("state")
        health = "UNKNOWN"
        if state in {"WORKING", "ACTIVE", "IDLE"}:
            health = "HEALTHY"
        elif state == "BLOCKED":
            health = "BLOCKED"
        elif state == "STALE":
            health = "STALE"
        caps = [str(item).upper() for item in row.get("tools") or []]
        caps.append(str(row.get("classification") or UNKNOWN))
        if row.get("harness") and row["harness"] != UNKNOWN:
            caps.append(str(row["harness"]).upper())
        missing = [item for item in required if item not in caps and item not in {row.get("classification")}]
        if health == "BLOCKED":
            reason = "typed blocker present; advisory skip"
            rank = 90
        elif missing:
            reason = "declared tools do not include " + ",".join(missing)
            rank = 80
        elif health == "STALE":
            reason = "stale session; continuation possible after heartbeat"
            rank = 70
        elif row.get("classification") == "LOCAL" and "BROWSER" in required:
            reason = "local session is not the default browser executor"
            rank = 60
        elif health == "HEALTHY":
            reason = "healthy session with matching declared capability"
            rank = 10
        else:
            reason = "capability UNKNOWN; still visible"
            rank = 50
        candidates.append({
            "session_id": row["session_id"],
            "state": state,
            "health": health,
            "classification": row.get("classification"),
            "rank": rank,
            "reason": reason,
            "advisory": True,
            "authority": False,
            "continuation": {
                "recommend": "lineage-linked continuation" if row.get("run_id") not in {None, UNKNOWN, ""} else "new START with new run_id",
                "run_id": row.get("run_id"),
                "replay_finished_prompt": False,
            },
        })
    candidates.sort(key=lambda row: (row["rank"], row["session_id"]))
    return candidates


def briefing_from(snapshot_parts: dict[str, Any]) -> dict[str, Any]:
    cockpit = snapshot_parts["cockpit"]["lines"]
    statements = []
    for line in cockpit:
        statements.append({"text": line, "evidence": snapshot_parts["cockpit"].get("evidence") or []})
    economy = snapshot_parts["economy"]
    statements.append({
        "text": "Commons revenue remains USD %s." % economy["collected_cash_usd"],
        "evidence": economy["evidence"],
    })
    landings = [row for row in snapshot_parts["timeline"] if row.get("kind") == "LANDING"]
    blocked = [row for row in snapshot_parts["sessions"] if row.get("state") == "BLOCKED"]
    return {
        "schema": "commons-briefing/v0.1",
        "deterministic": True,
        "language_model_required": False,
        "architecture": "Presence is existence. Protocol events and jobs are work. Observatory is a bake.",
        "active_commitments": [row["session_id"] for row in snapshot_parts["sessions"] if row["state"] in {"WORKING", "ACTIVE", "BLOCKED"}],
        "unfinished_work": [row["task_id"] for row in snapshot_parts["work_map"] if row["state"] not in {"TERMINAL", "RELEASED", "SUPERSEDED"}],
        "blocked_work": [row["session_id"] for row in blocked],
        "recent_landings": [row.get("event_id") for row in landings[-8:]],
        "economic_truth": "USD %s collected_cash; bank_available=%s" % (economy["collected_cash_usd"], economy["bank_available"]),
        "highest_leverage_next": snapshot_parts.get("routes")[:3] if snapshot_parts.get("routes") else [],
        "statements": statements,
        "handoff": {
            "read_this": cockpit,
            "snapshot": SNAPSHOT_SCHEMA,
            "continue_tool": "continue_from_observation",
        },
    }


def _presence_rows(legacy: dict[str, Any], now: str, stale_after: int) -> list[dict[str, Any]]:
    rows = []
    presence = legacy.get("presence") or []
    lastseen = {str(item.get("from")): item for item in (legacy.get("lastseen") or []) if isinstance(item, dict)}
    if not isinstance(presence, list):
        return rows
    for item in presence:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("from") or UNKNOWN)
        seen = lastseen.get(claim) or {}
        ts = str(seen.get("ts") or item.get("ts") or UNKNOWN)
        age = _age_seconds(ts, now)
        motion = "IDLE"
        if age is None:
            motion = UNKNOWN
        elif age <= stale_after:
            motion = "ACTIVE"
        else:
            motion = "IDLE"
        rows.append({
            "claim": claim,
            "presence": item.get("presence") or "PRESENT",
            "id": item.get("id") or UNKNOWN,
            "ts": ts,
            "last_to": seen.get("to") or UNKNOWN,
            "motion": motion,
            "existence": "PRESENT" if item.get("presence") != "LEAVING" else "LEAVING",
            "is_session": False,
            "slack_author_is_session": False,
            "evidence": [_evidence("presence.json", "OBSERVED", claim=claim, id=item.get("id"))],
        })
    rows.sort(key=lambda row: (row["claim"], row["id"]))
    return rows


def _jobs_as_work(legacy: dict[str, Any], now: str, stale_after: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    jobs = legacy.get("jobs") or []
    work = []
    sessions = []
    if not isinstance(jobs, list):
        return work, sessions
    for job in jobs:
        if not isinstance(job, dict) or not job.get("job_id"):
            continue
        status = str(job.get("status") or UNKNOWN).upper()
        state = JOB_STATUS_TO_STATE.get(status, UNKNOWN)
        harness = str(job.get("harness") or UNKNOWN)
        checkpoint_obj = job.get("checkpoint") if isinstance(job.get("checkpoint"), dict) else {}
        is_grok = checkpoint_obj.get("schema") == GROK_EXECUTOR_SCHEMA
        execution = checkpoint_obj.get("execution") if isinstance(checkpoint_obj.get("execution"), dict) else {}
        origin = checkpoint_obj.get("origin") if isinstance(checkpoint_obj.get("origin"), dict) else {}
        classification = classify_runtime("", harness, [])
        grok_url = ""
        run_id = UNKNOWN
        session_id = _job_session_id(job)
        provider_uncertainty = ""
        if is_grok:
            classification = "BROWSER"
            if harness == UNKNOWN:
                harness = "grok.com authenticated browser via Commons MCP"
            grok_url = _canon_url(str(
                checkpoint_obj.get("conversation_url")
                or (checkpoint_obj.get("result") or {}).get("conversation_url")
                or execution.get("conversation_url")
                or ""
            ))
            run_id = str(checkpoint_obj.get("run_key") or job.get("run_id") or UNKNOWN)
            if origin.get("session_id"):
                session_id = str(origin.get("session_id"))
            submission = str(execution.get("submission_state") or "")
            exec_state = str(execution.get("state") or "")
            blockers = execution.get("blockers") if isinstance(execution.get("blockers"), list) else []
            if blockers:
                state = "BLOCKED"
            elif submission in GROK_POST_SUBMIT and not (checkpoint_obj.get("result") or execution.get("result")):
                state = "BLOCKED"
                provider_uncertainty = "stall after prompt submission; output-only recovery; do not replay"
            elif submission == "CAPTURE_STARTED" or exec_state in {"CLAIMED", "RUNNING"}:
                state = "WORKING"
            elif submission in GROK_PRE_SUBMIT or exec_state in {"QUEUED", ""}:
                if status == "OPEN":
                    state = "IDLE"
            if status == "DONE":
                state = "TERMINAL"
            if status == "CANCELLED":
                state = "RELEASED"
        task = {
            "task_id": str(job.get("job_id")),
            "objective": job.get("objective") or checkpoint_obj.get("task") or UNKNOWN,
            "state": state,
            "owner_claim": job.get("owner_claim") or UNKNOWN,
            "session_id": session_id,
            "harness": harness,
            "classification": classification,
            "checkpoint": job.get("checkpoint") if not isinstance(job.get("checkpoint"), dict) else canonical_json(job.get("checkpoint")),
            "lease": job.get("lease") or {"descriptive_only": True},
            "blocker": job.get("blocker") or ({"type": "PROVIDER_UNCERTAINTY", "detail": provider_uncertainty} if provider_uncertainty else None),
            "result_address": job.get("result_address") or UNKNOWN,
            "claimed_paths": job.get("claimed_paths") or [],
            "semantic_area": job.get("semantic_area") or UNKNOWN,
            "lineage": job.get("parent_ids") or (checkpoint_obj.get("lineage") or []),
            "run_id": run_id,
            "grok_url": grok_url,
            "expected_next": EXPECTED_NEXT.get(state, UNKNOWN),
            "provenance": "GROK_EXECUTOR" if is_grok else "JOBSTORE",
            "replay_finished_prompt": False,
            "evidence": [_evidence("wake_jobs/%s.json" % job.get("job_id"), "OBSERVED", job_id=job.get("job_id"), status=status, grok_executor=is_grok)],
        }
        work.append(task)
        live_states = {"WORKING", "IDLE", "BLOCKED", "STALE", "ACTIVE"}
        if status in ACTIVE_JOB_STATUSES or (is_grok and state in live_states):
            session = empty_session(session_id, provenance="GROK_EXECUTOR" if is_grok else "JOBSTORE")
            session["label"] = "%s %s" % (job.get("owner_claim") or ("GROK" if is_grok else "JOB"), job.get("job_id"))
            if is_grok and state in live_states:
                session["state"] = state
            else:
                session["state"] = "WORKING" if status == "LEASED" else ("BLOCKED" if status == "BLOCKED" else "IDLE")
            session["classification"] = classification
            session["harness"] = harness
            session["model"] = job.get("model") or UNKNOWN
            session["objective"] = task["objective"]
            session["task_id"] = task["task_id"]
            session["run_id"] = run_id
            session["claimed_paths"] = list(task["claimed_paths"] or [])
            session["semantic_area"] = task["semantic_area"]
            session["checkpoint"] = task["checkpoint"]
            session["grok_url"] = grok_url
            if run_id != UNKNOWN:
                session["dedupe_key"] = run_id
            session["last_ts"] = str(job.get("updated_at") or job.get("created_at") or UNKNOWN)
            session["provider_uncertainty"] = provider_uncertainty
            session["lease"] = {
                "lease_id": (job.get("lease") or {}).get("lease_id") if isinstance(job.get("lease"), dict) else UNKNOWN,
                "holder": (job.get("lease") or {}).get("holder") if isinstance(job.get("lease"), dict) else UNKNOWN,
                "until": (job.get("lease") or {}).get("until") if isinstance(job.get("lease"), dict) else UNKNOWN,
                "descriptive_only": True,
            }
            age = _age_seconds(session["last_ts"], now)
            if session["state"] in {"WORKING", "IDLE", "ACTIVE"} and age is not None and age > stale_after:
                session["state"] = "STALE"
            session["evidence"] = task["evidence"]
            sessions.append(session)
    return work, sessions


def _captures_as_events(legacy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for cap in legacy.get("grok_captures") or []:
        if not isinstance(cap, dict):
            continue
        state = str(cap.get("state") or "")
        kind = "HEARTBEAT"
        if state in {"CAPTURE_STARTED", "GROK_CONTINUE"}:
            kind = "START"
        elif state in {"VERIFIED_COMPLETE", "RECEIPT_EMITTED"}:
            kind = "LANDING"
        elif state in {"FAILED", "PAGE_UNCONFIRMED", "CONNECTOR_UNAVAILABLE"}:
            kind = "BLOCKED"
        elif state == "PARTIAL":
            kind = "CHECKPOINT"
        origin = cap.get("origin") if isinstance(cap.get("origin"), dict) else {}
        rows.append(parse_event({
            "kind": kind,
            "event_id": "cap-" + str(cap.get("run_id") or cap.get("run_key") or "unknown")[:60],
            "run_id": cap.get("run_key") or cap.get("run_id"),
            "session_id": origin.get("session_id") or cap.get("run_id"),
            "task_id": origin.get("task_id"),
            "ts": (cap.get("timestamps") or {}).get("last_observed_at") or (cap.get("timestamps") or {}).get("started_at"),
            "classification": "BROWSER",
            "harness": "grok.com",
            "model": (cap.get("provider") or {}).get("model"),
            "grok_url": cap.get("conversation_url"),
            "dedupe_key": cap.get("run_key") or cap.get("conversation_url"),
            "origin": origin,
            "artifacts": cap.get("artifacts") or [],
            "blocker": cap.get("failure"),
            "terminal_disposition": cap.get("completion_state") or state,
        }))
    return rows


def project(
    events: Any = None,
    *,
    now: str = "2026-08-28T09:30:00Z",
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    legacy: dict[str, Any] | None = None,
    head_sha: str = "",
    need: dict[str, Any] | None = None,
) -> dict[str, Any]:
    legacy = legacy or {}
    parsed = parse_events(events)
    parsed.extend(_captures_as_events(legacy))
    # Dedupe exact event_id: first wins. Later copies stay as duplicate receipts.
    seen_ids: dict[str, dict[str, Any]] = {}
    duplicates = []
    ordered = []
    for event in parsed:
        eid = event["event_id"]
        if eid in seen_ids:
            duplicates.append(eid)
            continue
        seen_ids[eid] = event
        ordered.append(event)
    ordered.sort(key=lambda row: (_parse_ts(row.get("ts") or ""), row["event_id"]))

    sessions: dict[str, dict[str, Any]] = {}
    tasks: dict[str, dict[str, Any]] = {}
    timeline = []
    for event in ordered:
        timeline.append({
            "event_id": event["event_id"],
            "kind": event["kind"],
            "ts": event["ts"],
            "session_id": event["session_id"],
            "task_id": event["task_id"],
            "harness": event["harness"],
            "classification": event["classification"],
            "path": (event.get("claimed_paths") or [UNKNOWN])[0] if event.get("claimed_paths") else UNKNOWN,
            "blocker": (event.get("blocker") or {}).get("type"),
            "cost": event.get("cost"),
            "parse_state": event.get("parse_state"),
            "evidence": event.get("evidence"),
        })
        sid = event["session_id"]
        if sid == UNKNOWN:
            # Visible on the timeline only. Do not fabricate a session.
            pass
        else:
            if sid not in sessions:
                sessions[sid] = empty_session(sid, provenance="PROTOCOL_EVENT")
            apply_event_to_session(sessions[sid], event, now, stale_after_seconds)
        if event["task_id"] != UNKNOWN:
            task = tasks.setdefault(event["task_id"], {
                "task_id": event["task_id"],
                "state": UNKNOWN,
                "objective": event.get("objective") or UNKNOWN,
                "session_id": sid,
                "claimed_paths": list(event.get("claimed_paths") or []),
                "semantic_area": event.get("semantic_area") or UNKNOWN,
                "checkpoint": event.get("checkpoint") or UNKNOWN,
                "lineage": list(event.get("parent_ids") or []),
                "blocker": event.get("blocker"),
                "last_kind": event["kind"],
                "last_ts": event["ts"],
                "provenance": "PROTOCOL_EVENT",
                "head_sha": event.get("head_sha") or "",
                "expected_next": EXPECTED_NEXT.get(UNKNOWN, UNKNOWN),
                "evidence": list(event.get("evidence") or []),
            })
            if event["kind"] in TERMINAL_EVENT_KINDS:
                task["state"] = "TERMINAL" if event["kind"] != "RELEASE" else "RELEASED"
                if event["kind"] == "SUPERSEDED":
                    task["state"] = "SUPERSEDED"
            elif event["kind"] == "BLOCKED":
                task["state"] = "BLOCKED"
            elif event["kind"] in WORKING_EVENT_KINDS:
                task["state"] = "WORKING"
            if event.get("objective") and event["objective"] != UNKNOWN:
                task["objective"] = event["objective"]
            if sid != UNKNOWN:
                task["session_id"] = sid
            task["expected_next"] = EXPECTED_NEXT.get(task["state"], UNKNOWN)

    job_work, job_sessions = _jobs_as_work(legacy, now, stale_after_seconds)
    for task in job_work:
        tasks.setdefault(task["task_id"], task)
    for session in job_sessions:
        sessions.setdefault(session["session_id"], session)

    presence = _presence_rows(legacy, now, stale_after_seconds)
    session_list = [sessions[key] for key in sorted(sessions)]
    work_list = [tasks[key] for key in sorted(tasks)]
    collisions = derive_collisions(session_list, work_list, head_sha or str((legacy.get("pulse") or {}).get("head") or ""))
    economy = project_economy(legacy)
    attention = derive_attention(session_list, collisions, ordered, economy)
    routes = route_work(session_list, need)

    counts = {name: 0 for name in SESSION_STATES}
    class_counts = {name: 0 for name in CLASSIFICATIONS}
    for row in session_list:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
        class_counts[row["classification"]] = class_counts.get(row["classification"], 0) + 1
    confirmed_active = counts["ACTIVE"] + counts["WORKING"]
    # Quiet presence is existence, not a session.
    lines = [
        "%s session%s confirmed active." % (confirmed_active, "" if confirmed_active == 1 else "s"),
        "%s working; %s blocked." % (counts["WORKING"], counts["BLOCKED"]),
        "%s collision%s need%s reconciliation." % (
            len(collisions),
            "" if len(collisions) == 1 else "s",
            "s" if len(collisions) == 1 else "",
        ),
        "%s claims present (existence, not sessions)." % len(presence),
        "No verified positive replies." if economy["replies_observed"] == 0 else "%s human replies observed." % economy["replies_observed"],
        "Commons revenue remains USD %s." % economy["collected_cash_usd"],
    ]
    if counts["STALE"]:
        lines.insert(2, "%s stale." % counts["STALE"])

    pulse = legacy.get("pulse") if isinstance(legacy.get("pulse"), dict) else {}
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "protocol": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "state": "BAKE",
        "now": now,
        "stale_after_seconds": stale_after_seconds,
        "head": {
            "sha": head_sha or pulse.get("head") or UNKNOWN,
            "pulse_seq": pulse.get("seq"),
            "post_count": pulse.get("post_count"),
            "evidence": [_evidence("pulse.json", "OBSERVED" if pulse else "UNKNOWN")],
        },
        "cockpit": {
            "lines": lines,
            "counts": {
                "sessions": len(session_list),
                "confirmed_active": confirmed_active,
                "states": counts,
                "classifications": class_counts,
                "presence_claims": len(presence),
                "collisions": len(collisions),
                "attention": len(attention),
                "work": len(work_list),
            },
            "evidence": [_evidence("projector", "OBSERVED", protocol=PROTOCOL_ID)],
        },
        "presence": presence,
        "sessions": session_list,
        "work_map": work_list,
        "collisions": collisions,
        "attention": attention,
        "timeline": timeline,
        "economy": economy,
        "routes": routes,
        "duplicates_ignored": sorted(set(duplicates)),
        "open_door": {
            "authentication": False,
            "authorization": False,
            "leases_are_descriptive": True,
            "collisions_are_advisory": True,
            "capability_is_optional_metadata": True,
        },
    }
    snapshot["briefing"] = briefing_from({
        "cockpit": snapshot["cockpit"],
        "sessions": session_list,
        "work_map": work_list,
        "timeline": timeline,
        "economy": economy,
        "routes": routes,
    })
    snapshot["digest"] = _digest({key: snapshot[key] for key in snapshot if key != "digest"})
    return snapshot


def project_bytes(snapshot: dict[str, Any]) -> bytes:
    return (canonical_json(snapshot) + "\n").encode("utf-8")
