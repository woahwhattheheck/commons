from __future__ import annotations

from datetime import timedelta
from typing import Any

from .common import (
    CONCLUSIONS, MAX_JOBS_PER_RUN, MAX_STEPS_PER_JOB, RUN_STATUSES, EvidenceError,
    _optional_text, _optional_time, _require_dict, _require_int, _require_list,
    _require_text, _time, _validate_exact_fields,
)

def _parse_steps(value: Any, label: str) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    rows = _require_list(value, label, maximum=MAX_STEPS_PER_JOB)
    parsed: list[dict[str, Any]] = []
    for index, row_raw in enumerate(rows):
        row = _require_dict(row_raw, f"{label}[{index}]")
        _validate_exact_fields(row, {"name", "status", "conclusion"}, f"{label}[{index}]")
        name = _require_text(row.get("name"), f"{label}[{index}].name")
        status = _require_text(row.get("status"), f"{label}[{index}].status").lower()
        if status not in RUN_STATUSES:
            raise EvidenceError(f"{label}[{index}].status is unsupported: {status}")
        conclusion = _optional_text(row.get("conclusion"), f"{label}[{index}].conclusion")
        if conclusion is not None:
            conclusion = conclusion.lower()
            if conclusion not in CONCLUSIONS:
                raise EvidenceError(f"{label}[{index}].conclusion is unsupported: {conclusion}")
        parsed.append({"name": name, "status": status, "conclusion": conclusion})
    return parsed


def _parse_job(raw: Any, label: str) -> dict[str, Any]:
    job = _require_dict(raw, label)
    _validate_exact_fields(
        job,
        {"job_id", "name", "status", "conclusion", "runner_name", "started_at", "completed_at", "steps"},
        label,
    )
    job_id = _require_int(job.get("job_id"), f"{label}.job_id", minimum=1)
    name = _require_text(job.get("name"), f"{label}.name")
    status = _require_text(job.get("status"), f"{label}.status").lower()
    if status not in RUN_STATUSES:
        raise EvidenceError(f"{label}.status is unsupported: {status}")
    conclusion = _optional_text(job.get("conclusion"), f"{label}.conclusion")
    if conclusion is not None:
        conclusion = conclusion.lower()
        if conclusion not in CONCLUSIONS:
            raise EvidenceError(f"{label}.conclusion is unsupported: {conclusion}")
    runner_name = _optional_text(job.get("runner_name"), f"{label}.runner_name")
    started_at = _optional_time(job.get("started_at"), f"{label}.started_at")
    completed_at = _optional_time(job.get("completed_at"), f"{label}.completed_at")
    steps = _parse_steps(job.get("steps"), f"{label}.steps")

    if status == "completed" and conclusion is None:
        raise EvidenceError(f"{label} completed without a conclusion")
    if status != "completed" and conclusion is not None:
        raise EvidenceError(f"{label} has a conclusion before completion")
    if completed_at is not None and started_at is not None and completed_at < started_at:
        raise EvidenceError(f"{label}.completed_at precedes started_at")

    return {
        "job_id": job_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "runner_name": runner_name,
        "started_at": started_at,
        "completed_at": completed_at,
        "steps": steps,
    }


def _parse_run(raw: Any, label: str, expected_head: str) -> dict[str, Any]:
    run = _require_dict(raw, label)
    _validate_exact_fields(
        run,
        {"run_id", "workflow", "head_sha", "status", "conclusion", "created_at", "started_at", "completed_at", "jobs"},
        label,
    )
    run_id = _require_int(run.get("run_id"), f"{label}.run_id", minimum=1)
    workflow = _require_text(run.get("workflow"), f"{label}.workflow")
    head_sha = _require_text(run.get("head_sha"), f"{label}.head_sha", maximum=40).lower()
    if head_sha != expected_head:
        raise EvidenceError(f"{label}.head_sha does not match exact evidence head")
    status = _require_text(run.get("status"), f"{label}.status").lower()
    if status not in RUN_STATUSES:
        raise EvidenceError(f"{label}.status is unsupported: {status}")
    conclusion = _optional_text(run.get("conclusion"), f"{label}.conclusion")
    if conclusion is not None:
        conclusion = conclusion.lower()
        if conclusion not in CONCLUSIONS:
            raise EvidenceError(f"{label}.conclusion is unsupported: {conclusion}")
    created_at = _time(run.get("created_at"), f"{label}.created_at")
    started_at = _optional_time(run.get("started_at"), f"{label}.started_at")
    completed_at = _optional_time(run.get("completed_at"), f"{label}.completed_at")
    jobs_raw = _require_list(run.get("jobs"), f"{label}.jobs", maximum=MAX_JOBS_PER_RUN)
    jobs = [_parse_job(row, f"{label}.jobs[{index}]") for index, row in enumerate(jobs_raw)]
    ids = [job["job_id"] for job in jobs]
    if len(ids) != len(set(ids)):
        raise EvidenceError(f"{label}.jobs contains duplicate job ids")
    if status == "completed" and conclusion is None:
        raise EvidenceError(f"{label} completed without a conclusion")
    if status != "completed" and conclusion is not None:
        raise EvidenceError(f"{label} has a conclusion before completion")
    if completed_at is not None and started_at is not None and completed_at < started_at:
        raise EvidenceError(f"{label}.completed_at precedes started_at")
    if started_at is not None and started_at < created_at - timedelta(minutes=1):
        raise EvidenceError(f"{label}.started_at materially precedes created_at")
    return {
        "run_id": run_id,
        "workflow": workflow,
        "head_sha": head_sha,
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "jobs": jobs,
    }
