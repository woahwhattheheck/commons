"""Deterministic Slack -> grok.com -> GPT review -> Git/revenue work packets.

This module is deliberately transport-neutral.  A Slack connector supplies an
event, grok.com or GPT supplies later-stage receipts, and the Commons MCP returns
the next packet.  It stores no credentials, performs no provider mutation, and
never upgrades an unverified sales or cash report into a fact.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


SCHEMA_VERSION = "grokcom-revenue-orchestrator/v1"
CONNECTOR_ORIGIN = "COMMONS_GROKCOM_REVENUE"
STAGES = frozenset({"INTAKE", "GROKCOM_RESULT", "GPT_REVIEW", "GIT_LAND", "SALES_OUTCOME"})
MODES = frozenset({"AUTO", "BUILD", "RESEARCH", "SALES", "OPERATE"})
REVIEW_CHECKS = (
    "artifact_readback",
    "focused_tests",
    "fresh_main_collision_audit",
    "diff_check",
    "secret_scan",
    "open_door_check",
    "zero_fabrication_check",
)
SALES_PROCESS = (
    "DISCOVER",
    "QUALIFY",
    "DRAFT",
    "GPT_REVIEW",
    "SEND_BY_CONNECTED_CARRIER",
    "REPLY",
    "DISCOVERY_CALL",
    "QUOTE",
    "ACCEPTANCE",
    "DELIVERY",
    "PROCESSOR_REFERENCE",
    "CASH_READBACK",
)
SALES_STAGES = frozenset(SALES_PROCESS)
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _object(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return dict(value)


def _string(value: Any, field: str, *, required: bool = False, maximum: int = 16_000) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return value


def _count(value: Any, field: str) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _mode(requested: Any, text: str) -> str:
    choice = _string(requested or "AUTO", "mode", maximum=16).upper()
    if choice not in MODES:
        choice = "AUTO"
    if choice != "AUTO":
        return choice
    lowered = text.casefold()
    if any(word in lowered for word in ("prospect", "find client", "find buyer", "research", "market", "lead")):
        return "RESEARCH"
    if any(word in lowered for word in ("revenue", "profit", "sell", "sales", "outreach", "quote", "payment", "client")):
        return "SALES"
    if any(word in lowered for word in ("build", "implement", "fix", "code", "commit", "pull request", " pr ")):
        return "BUILD"
    return "OPERATE"


def _event(value: Any) -> dict[str, str]:
    row = _object(value, "event")
    text = _string(
        row.get("text") or "Continue the highest-value open Commons revenue work.",
        "event.text",
        required=True,
    )
    channel = _string(row.get("channel") or row.get("channel_id") or "C0BRGMDQB6G", "event.channel", required=True, maximum=128)
    message_ts = _string(
        row.get("message_ts") or row.get("ts") or row.get("event_id") or "open-call",
        "event.message_ts",
        required=True,
        maximum=128,
    )
    thread_ts = _string(row.get("thread_ts") or message_ts, "event.thread_ts", required=True, maximum=128)
    author = _string(row.get("author") or row.get("user") or "UNSEATED", "event.author", required=True, maximum=128)
    origin = _string(row.get("connector_origin"), "event.connector_origin", maximum=128)
    event_id = _string(row.get("event_id") or f"slack-{channel}-{message_ts}", "event.event_id", required=True, maximum=256)
    return {
        "event_id": event_id,
        "channel": channel,
        "message_ts": message_ts,
        "thread_ts": thread_ts,
        "author": author,
        "text": text,
        "connector_origin": origin,
    }


def _truth(value: Any) -> dict[str, Any]:
    row = _object(value, "revenue")
    refs = row.get("evidence_refs") or []
    if not isinstance(refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in refs):
        raise ValueError("revenue.evidence_refs must be an array of non-empty strings")
    refs = [ref.strip() for ref in refs]
    stage = _string(row.get("stage") or "DISCOVER", "revenue.stage", maximum=64).upper()
    if stage not in SALES_STAGES:
        raise ValueError("revenue.stage must name a sales-process stage")
    facts = {
        "stage": stage,
        "prospects": _count(row.get("prospects"), "revenue.prospects"),
        "qualified": _count(row.get("qualified"), "revenue.qualified"),
        "contacts": _count(row.get("contacts"), "revenue.contacts"),
        "transports": _count(row.get("transports"), "revenue.transports"),
        "replies": _count(row.get("replies"), "revenue.replies"),
        "cash_usd": _count(row.get("cash_usd"), "revenue.cash_usd"),
        "evidence_refs": refs,
    }
    facts["evidence_state"] = "REFERENCED_NOT_INDEPENDENTLY_VERIFIED" if refs else "NO_EVIDENCE_ATTACHED"
    facts["cash_claimed"] = False
    facts["cash_state"] = "REQUIRES_PROCESSOR_AND_BANK_READBACK" if facts["cash_usd"] else "NOT_LANDED"
    return facts


def _sales_packet(truth: dict[str, Any]) -> dict[str, Any]:
    current = truth["stage"]
    index = SALES_PROCESS.index(current)
    next_stage = SALES_PROCESS[min(index + 1, len(SALES_PROCESS) - 1)]
    return {
        "process": list(SALES_PROCESS),
        "current_stage": current,
        "next_stage": next_stage,
        "truth": truth,
        "rules": [
            "Keep candidate, outreach, reply, acceptance, delivery, processor, and cash states distinct.",
            "Attach exact public URLs or durable receipt references; a search result is not outreach.",
            "Do not resend an existing contact without an explicit new owner instruction.",
            "Never report collected cash from a quote, payment link, processor reference, or owner report alone.",
        ],
    }


def _grok_prompt(task_id: str, mode: str, event: dict[str, str], sales: dict[str, Any]) -> str:
    mode_instruction = {
        "BUILD": "Implement the smallest complete change in the connected GitHub repository, test it, and return exact paths, blobs, base/head SHAs, and test output.",
        "RESEARCH": "Find current prospective clients or funded demand. Return source URLs, publication dates, buyer identity, demonstrated pain, budget/funding evidence, fit, and a non-duplicative next action.",
        "SALES": "Advance the evidence-backed sales process one stage. Draft useful copy or collateral, but do not claim outreach, replies, acceptance, payment, or cash without exact receipts.",
        "OPERATE": "Execute the request through the connected Commons/GitHub surfaces and return a compact artifact-and-evidence manifest.",
    }[mode]
    return "\n".join((
        f"WORK_PACKET {task_id}",
        "Surface: authenticated grok.com only. Use the owner's grok.com pool; do not substitute Cursor, Grokbot, or a local Grok CLI.",
        mode_instruction,
        "Read fresh origin/main and current Commons/Slack context before acting. Preserve unrelated work and the unrestricted open door.",
        "Do not fabricate tests, clients, outreach, replies, revenue, profitability, processor state, or cash.",
        "Return JSON with summary, exact_sources, exact_paths, base_sha, head_sha, tests, risks, and recommended_next_action.",
        f"Slack author: {event['author']}",
        f"Slack message: {event['text']}",
        f"Sales truth: {_canonical(sales['truth'])}",
    ))


def _review_packet(task_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_id": f"review-{task_id}",
        "reviewer": "GPT",
        "artifact": artifact,
        "required_checks": list(REVIEW_CHECKS),
        "instructions": (
            "Read the exact candidate bytes and independently run proportionate tests. "
            "Return APPROVE or REVISE plus per-check booleans and precise repair requests. "
            "An approval is not a merge receipt."
        ),
    }


def _review_decision(value: Any) -> tuple[str, dict[str, bool], list[str]]:
    row = _object(value, "review")
    decision = _string(row.get("decision") or "REVISE", "review.decision", maximum=16).upper()
    if decision not in {"APPROVE", "REVISE"}:
        raise ValueError("review.decision must be APPROVE or REVISE")
    checks_input = _object(row.get("checks"), "review.checks")
    checks = {name: checks_input.get(name) is True for name in REVIEW_CHECKS}
    issues = row.get("issues") or []
    if not isinstance(issues, list) or not all(isinstance(issue, str) and issue.strip() for issue in issues):
        raise ValueError("review.issues must be an array of non-empty strings")
    missing = [name for name, passed in checks.items() if not passed]
    if decision == "APPROVE" and missing:
        issues = [*issues, "Missing review checks: " + ", ".join(missing)]
        decision = "REVISE"
    return decision, checks, [issue.strip() for issue in issues]


def _landing(value: Any) -> dict[str, Any]:
    row = _object(value, "landing")
    base_sha = _string(row.get("base_sha"), "landing.base_sha", required=True, maximum=40)
    head_sha = _string(row.get("head_sha"), "landing.head_sha", required=True, maximum=40)
    main_sha = _string(row.get("main_sha"), "landing.main_sha", required=True, maximum=40)
    if not all(SHA40_RE.fullmatch(sha) for sha in (base_sha, head_sha, main_sha)):
        raise ValueError("landing base/head/main SHAs must be exact lowercase 40-hex values")
    blobs = row.get("blobs") or {}
    if not isinstance(blobs, dict) or not blobs:
        raise ValueError("landing.blobs must map at least one path to an exact sha256")
    if not all(isinstance(path, str) and path and isinstance(digest, str) and SHA256_RE.fullmatch(digest) for path, digest in blobs.items()):
        raise ValueError("landing.blobs must map non-empty paths to lowercase sha256 values")
    return {
        "base_sha": base_sha,
        "head_sha": head_sha,
        "main_sha": main_sha,
        "pr_url": _string(row.get("pr_url"), "landing.pr_url", required=True, maximum=2_000),
        "blobs": dict(sorted(blobs.items())),
        "tests": row.get("tests") if isinstance(row.get("tests"), list) else [],
    }


def orchestrate(arguments: Any) -> dict[str, Any]:
    """Return the next deterministic work packet for one Slack-originated task."""
    args = _object(arguments, "arguments")
    stage = _string(args.get("stage") or "INTAKE", "stage", maximum=32).upper()
    if stage not in STAGES:
        stage = "INTAKE"
    event = _event(args.get("event"))
    mode = _mode(args.get("mode"), event["text"])
    task_id = "grkrev-" + _digest({
        "event_id": event["event_id"],
        "channel": event["channel"],
        "message_ts": event["message_ts"],
        "text": event["text"],
    })[:24]
    truth = _truth(args.get("revenue"))
    sales = _sales_packet(truth)
    is_echo = event["connector_origin"] == CONNECTOR_ORIGIN
    response: dict[str, Any] = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "dedupe_key": event["event_id"],
        "source": {key: value for key, value in event.items() if key != "text"},
        "mode": mode,
        "connector": {
            "origin": CONNECTOR_ORIGIN,
            "reply_mode": "ALL_MESSAGES",
            "reply_target": {"channel": event["channel"], "thread_ts": event["thread_ts"]},
            "post_reply": not is_echo,
            "loop_disposition": "OWN_ECHO_NO_POST" if is_echo else "PROCESS_AND_REPLY",
        },
        "sales": sales,
        "cash_claimed": False,
    }
    if is_echo:
        response.update({"state": "ECHO_PROCESSED", "next": "NO_POST", "slack_reply": ""})
        return response
    if stage == "INTAKE":
        response.update({
            "state": "GROKCOM_WORK",
            "next": "SEND_TO_GROKCOM",
            "slack_reply": f"CLAIMED {task_id} | grok.com {mode.lower()} | GPT review follows the artifact receipt.",
            "grokcom": {
                "surface": "grok.com",
                "prompt": _grok_prompt(task_id, mode, event, sales),
                "return_stage": "GROKCOM_RESULT",
                "commons_mcp_url": "https://commons-spark-mcp.vercel.app/mcp",
            },
        })
        return response
    artifact = _object(args.get("artifact"), "artifact")
    if stage == "GROKCOM_RESULT":
        if not artifact:
            raise ValueError("GROKCOM_RESULT requires artifact")
        response.update({
            "state": "GPT_REVIEW",
            "next": "SEND_TO_GPT_REVIEW",
            "slack_reply": f"BUILT {task_id} | grok.com receipt captured | GPT independent review queued.",
            "gpt_review": _review_packet(task_id, artifact),
        })
        return response
    if stage == "GPT_REVIEW":
        if not artifact:
            raise ValueError("GPT_REVIEW requires the exact artifact manifest reviewed by GPT")
        decision, checks, issues = _review_decision(args.get("review"))
        if decision == "REVISE":
            response.update({
                "state": "GROKCOM_REVISION",
                "next": "SEND_TWEAKS_TO_GROKCOM",
                "slack_reply": f"REVISE {task_id} | GPT found {len(issues)} precise repair item(s) | returned to grok.com.",
                "grokcom": {
                    "surface": "grok.com",
                    "prompt": "Revise work packet %s. Repair exactly: %s. Return new exact bytes and rerun tests." % (task_id, "; ".join(issues) or "the failed review checks"),
                    "return_stage": "GROKCOM_RESULT",
                },
                "review": {"decision": decision, "checks": checks, "issues": issues},
                "artifact": artifact,
            })
        else:
            response.update({
                "state": "GIT_LAND",
                "next": "REFRESH_MAIN_COMMIT_PUSH_PR_MERGE_READBACK",
                "slack_reply": f"APPROVED {task_id} | all {len(REVIEW_CHECKS)} review checks pass | fresh-main landing queued.",
                "review": {"decision": decision, "checks": checks, "issues": issues},
                "artifact": artifact,
                "git": {
                    "force_push": False,
                    "preserve_unrelated_dirt": True,
                    "required_receipt": ["base_sha", "head_sha", "main_sha", "pr_url", "blobs", "tests"],
                },
            })
        return response
    if stage == "GIT_LAND":
        receipt = _landing(args.get("landing"))
        response.update({
            "state": "CONTINUE",
            "next": "TAKE_NEXT_SLACK_OR_REVENUE_ACTION",
            "slack_reply": f"LANDED {task_id} | main {receipt['main_sha'][:12]} | continuing the queue.",
            "landing": receipt,
        })
        return response
    response.update({
        "state": "CONTINUE",
        "next": "ADVANCE_SALES_PROCESS",
        "slack_reply": f"SALES {task_id} | {sales['current_stage']} recorded as {truth['evidence_state']} | next {sales['next_stage']}.",
    })
    return response
