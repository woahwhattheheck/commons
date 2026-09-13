from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .common import (
    INPUT_SCHEMA, OUTPUT_SCHEMA, MAX_REQUIRED_WORKFLOWS, RED_CONCLUSIONS, REPO_RE, SHA_RE,
    ZERO_STEP_WAIT_STATUSES, EvidenceError, _format_time, _require_list,
    _require_text, _sha256, _time, _validate_exact_fields,
)
from .model import _parse_run

def _job_zero_step_unassigned(job: dict[str, Any]) -> bool:
    return (
        job["runner_name"] is None
        and job["started_at"] is None
        and job["steps"] in (None, [])
        and (
            job["status"] in ZERO_STEP_WAIT_STATUSES
            or (job["status"] == "completed" and job["conclusion"] == "cancelled")
        )
    )


def _run_classification(run: dict[str, Any]) -> tuple[str, str]:
    status = run["status"]
    conclusion = run["conclusion"]
    jobs = run["jobs"]

    if status == "completed" and conclusion == "success":
        if not jobs:
            return "HOLD", "successful workflow has no job evidence"
        bad = [job for job in jobs if job["conclusion"] not in {"success", "skipped"}]
        if bad:
            return "HOLD", "workflow success conflicts with non-success job evidence"
        if not any(job["conclusion"] == "success" for job in jobs):
            return "HOLD", "workflow success has no successful executed job"
        return "GREEN", "workflow and job evidence are terminal success"

    if status == "completed" and conclusion in RED_CONCLUSIONS:
        return "RED", f"workflow completed with {conclusion}"

    if status == "completed" and conclusion == "cancelled":
        if jobs and all(_job_zero_step_unassigned(job) for job in jobs):
            return "BACKLOG", "cancelled before any runner/step execution"
        return "HOLD", "cancelled workflow has execution or incomplete zero-step evidence"

    if status == "completed" and conclusion in {"neutral", "skipped"}:
        return "HOLD", f"required workflow concluded {conclusion}, not success"

    if status in ZERO_STEP_WAIT_STATUSES:
        if jobs and all(_job_zero_step_unassigned(job) for job in jobs):
            return "BACKLOG", "queued/unassigned with zero executed steps"
        return "WAIT", "workflow has not completed"

    if status == "in_progress":
        return "WAIT", "workflow is executing"

    return "WAIT", "workflow has not reached terminal authority"


def classify(payload: dict[str, Any], *, now: datetime | None = None, max_age_seconds: int = 1800, max_future_skew_seconds: int = 300) -> dict[str, Any]:
    _validate_exact_fields(payload, {"schema_version", "repository", "head_sha", "captured_at", "required_workflows", "runs"}, "input")
    if payload.get("schema_version") != INPUT_SCHEMA:
        raise EvidenceError(f"schema_version must equal {INPUT_SCHEMA}")
    repository = _require_text(payload.get("repository"), "repository")
    if not REPO_RE.fullmatch(repository):
        raise EvidenceError("repository must be owner/name")
    head_sha = _require_text(payload.get("head_sha"), "head_sha", maximum=40).lower()
    if not SHA_RE.fullmatch(head_sha):
        raise EvidenceError("head_sha must be exactly 40 lowercase hex characters")
    captured_at = _time(payload.get("captured_at"), "captured_at")
    if type(max_age_seconds) is not int or not 0 <= max_age_seconds <= 604800:
        raise EvidenceError("max_age_seconds must be an integer between 0 and 604800")
    if type(max_future_skew_seconds) is not int or not 0 <= max_future_skew_seconds <= 86400:
        raise EvidenceError("max_future_skew_seconds must be an integer between 0 and 86400")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if captured_at > now + timedelta(seconds=max_future_skew_seconds):
        raise EvidenceError("captured_at is implausibly in the future")
    if now - captured_at > timedelta(seconds=max_age_seconds):
        raise EvidenceError("evidence snapshot is stale")

    required_raw = _require_list(payload.get("required_workflows"), "required_workflows", maximum=MAX_REQUIRED_WORKFLOWS)
    if not required_raw:
        raise EvidenceError("required_workflows must not be empty")
    required: list[str] = []
    for index, value in enumerate(required_raw):
        name = _require_text(value, f"required_workflows[{index}]")
        if name in required:
            raise EvidenceError(f"duplicate required workflow: {name}")
        required.append(name)

    runs_raw = _require_list(payload.get("runs"), "runs", maximum=MAX_REQUIRED_WORKFLOWS * 4)
    runs = [_parse_run(row, f"runs[{index}]", head_sha) for index, row in enumerate(runs_raw)]
    snapshot_ceiling = captured_at + timedelta(seconds=max_future_skew_seconds)
    for run in runs:
        run_times = [run["created_at"], run["started_at"], run["completed_at"]]
        for job in run["jobs"]:
            run_times.extend((job["started_at"], job["completed_at"]))
        if any(value is not None and value > snapshot_ceiling for value in run_times):
            raise EvidenceError(f"run {run['run_id']} contains timestamps after the evidence capture")
    run_ids = [run["run_id"] for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise EvidenceError("runs contains duplicate run ids")

    by_workflow: dict[str, list[dict[str, Any]]] = {name: [] for name in required}
    extras: list[str] = []
    for run in runs:
        if run["workflow"] in by_workflow:
            by_workflow[run["workflow"]].append(run)
        else:
            extras.append(run["workflow"])

    workflow_receipts: list[dict[str, Any]] = []
    states: list[str] = []
    for workflow in required:
        candidates = by_workflow[workflow]
        if not candidates:
            state, reason = "MISSING", "no exact-head run supplied"
            run_id = None
        elif len(candidates) > 1:
            raise EvidenceError(f"multiple exact-head runs supplied for required workflow {workflow}; select one authoritative attempt explicitly")
        else:
            run = candidates[0]
            state, reason = _run_classification(run)
            run_id = run["run_id"]
        states.append(state)
        workflow_receipts.append({"workflow": workflow, "run_id": run_id, "state": state, "reason": reason})

    if "RED" in states:
        overall = "TERMINAL_RED"
    elif "HOLD" in states:
        overall = "HOLD"
    elif all(state == "GREEN" for state in states):
        overall = "TERMINAL_GREEN"
    elif "WAIT" in states:
        overall = "WAIT_EXECUTION"
    elif "MISSING" in states:
        overall = "WAIT_MISSING"
    elif all(state in {"GREEN", "BACKLOG"} for state in states) and "BACKLOG" in states:
        overall = "WAIT_RUNNER_BACKLOG"
    else:
        overall = "HOLD"

    receipt: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA,
        "repository": repository,
        "head_sha": head_sha,
        "captured_at": _format_time(captured_at),
        "evaluated_at": _format_time(now),
        "evidence_digest": f"sha256:{_sha256(payload)}",
        "decision": overall,
        "merge_authorized": overall == "TERMINAL_GREEN",
        "runner_exception_candidate": overall == "WAIT_RUNNER_BACKLOG",
        "side_effects_authorized": False,
        "required_workflows": workflow_receipts,
        "ignored_extra_workflows": sorted(set(extras)),
    }
    digest_subject = {key: value for key, value in receipt.items() if key != "evaluated_at"}
    receipt["receipt_digest"] = f"sha256:{_sha256(digest_subject)}"
    return receipt
