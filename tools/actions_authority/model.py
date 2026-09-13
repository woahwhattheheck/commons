from __future__ import annotations

from datetime import timedelta
from typing import Any

from .common import (
    CONCLUSIONS,
    MAX_JOBS_PER_RUN,
    MAX_REQUIRED_WORKFLOWS,
    MAX_STEPS_PER_JOB,
    POLICY_SCHEMA,
    POLICY_SOURCE_KINDS,
    RUN_STATUSES,
    SHA256_RE,
    SHA_RE,
    EvidenceError,
    _optional_text,
    _optional_time,
    _require_bool,
    _require_dict,
    _require_int,
    _require_list,
    _require_text,
    _time,
    _validate_exact_fields,
)


def _workflow_path(value: Any, label: str) -> str:
    path = _require_text(value, label, maximum=256)
    if not path.startswith(".github/workflows/"):
        raise EvidenceError(f"{label} must be under .github/workflows/")
    if path.endswith("/") or "\\" in path or "//" in path or "%" in path:
        raise EvidenceError(f"{label} is not a canonical workflow path")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise EvidenceError(f"{label} is not a canonical workflow path")
    if not path.endswith((".yml", ".yaml")):
        raise EvidenceError(f"{label} must end in .yml or .yaml")
    return path


def _base_ref(value: Any, label: str) -> str:
    ref = _require_text(value, label, maximum=256)
    prefix = "refs/heads/"
    if not ref.startswith(prefix):
        raise EvidenceError(f"{label} must be a refs/heads/* ref")
    suffix = ref[len(prefix):]
    if not suffix or suffix.startswith("/") or suffix.endswith("/"):
        raise EvidenceError(f"{label} is not canonical")
    if ".." in suffix or "//" in suffix or "\\" in suffix or any(ch.isspace() for ch in suffix):
        raise EvidenceError(f"{label} is not canonical")
    return ref


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
    job_fields = {
        "job_id", "name", "status", "conclusion", "runner_id", "runner_name",
        "started_at", "completed_at", "steps",
    }
    _validate_exact_fields(job, job_fields, label)
    missing = job_fields - set(job)
    if missing:
        raise EvidenceError(f"{label} is missing fields: {', '.join(sorted(missing))}")
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
    runner_id_raw = job.get("runner_id")
    if runner_id_raw is None or (type(runner_id_raw) is int and runner_id_raw == 0):
        runner_id = None
    else:
        runner_id = _require_int(runner_id_raw, f"{label}.runner_id", minimum=1)
    runner_name_raw = job.get("runner_name")
    runner_name = None if runner_name_raw in (None, "") else _require_text(
        runner_name_raw, f"{label}.runner_name"
    )
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
        "runner_id": runner_id,
        "runner_name": runner_name,
        "started_at": started_at,
        "completed_at": completed_at,
        "steps": steps,
    }


def _parse_run(raw: Any, label: str, expected_head: str) -> dict[str, Any]:
    run = _require_dict(raw, label)
    _validate_exact_fields(
        run,
        {
            "run_id", "run_number", "run_attempt", "workflow_id", "workflow_path", "workflow_name",
            "head_sha", "status", "conclusion", "created_at", "started_at", "completed_at",
            "jobs_inventory", "jobs",
        },
        label,
    )
    run_id = _require_int(run.get("run_id"), f"{label}.run_id", minimum=1)
    run_number = _require_int(run.get("run_number"), f"{label}.run_number", minimum=1)
    run_attempt = _require_int(run.get("run_attempt"), f"{label}.run_attempt", minimum=1)
    workflow_id = _require_int(run.get("workflow_id"), f"{label}.workflow_id", minimum=1)
    workflow_path = _workflow_path(run.get("workflow_path"), f"{label}.workflow_path")
    workflow_name = _require_text(run.get("workflow_name"), f"{label}.workflow_name")
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
    jobs_inventory = _parse_jobs_inventory(run.get("jobs_inventory"), f"{label}.jobs_inventory")
    jobs_raw = _require_list(run.get("jobs"), f"{label}.jobs", maximum=MAX_JOBS_PER_RUN)
    if jobs_inventory["total_count"] != len(jobs_raw):
        raise EvidenceError(f"{label}.jobs_inventory.total_count does not match supplied complete job inventory")
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
        "run_number": run_number,
        "run_attempt": run_attempt,
        "workflow_id": workflow_id,
        "workflow_path": workflow_path,
        "workflow_name": workflow_name,
        "head_sha": head_sha,
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "jobs_inventory": jobs_inventory,
        "jobs": jobs,
    }


def _parse_policy(raw: Any, label: str = "policy") -> dict[str, Any]:
    policy = _require_dict(raw, label)
    _validate_exact_fields(
        policy,
        {"schema_version", "source", "base_ref", "base_sha", "captured_at", "required_workflows"},
        label,
    )
    if policy.get("schema_version") != POLICY_SCHEMA:
        raise EvidenceError(f"{label}.schema_version must equal {POLICY_SCHEMA}")

    source_raw = _require_dict(policy.get("source"), f"{label}.source")
    _validate_exact_fields(source_raw, {"kind", "locator", "source_sha256"}, f"{label}.source")
    source_kind = _require_text(source_raw.get("kind"), f"{label}.source.kind")
    if source_kind not in POLICY_SOURCE_KINDS:
        raise EvidenceError(f"{label}.source.kind is unsupported: {source_kind}")
    source_locator = _require_text(source_raw.get("locator"), f"{label}.source.locator", maximum=512)
    source_sha256 = _require_text(source_raw.get("source_sha256"), f"{label}.source.source_sha256", maximum=71).lower()
    if not SHA256_RE.fullmatch(source_sha256):
        raise EvidenceError(f"{label}.source.source_sha256 must be sha256:<64 lowercase hex>")

    base_ref = _base_ref(policy.get("base_ref"), f"{label}.base_ref")
    base_sha = _require_text(policy.get("base_sha"), f"{label}.base_sha", maximum=40).lower()
    if not SHA_RE.fullmatch(base_sha):
        raise EvidenceError(f"{label}.base_sha must be exactly 40 lowercase hex characters")
    captured_at = _time(policy.get("captured_at"), f"{label}.captured_at")

    rows = _require_list(
        policy.get("required_workflows"),
        f"{label}.required_workflows",
        maximum=MAX_REQUIRED_WORKFLOWS,
    )
    if not rows:
        raise EvidenceError(f"{label}.required_workflows must not be empty")
    required: list[dict[str, Any]] = []
    for index, row_raw in enumerate(rows):
        row_label = f"{label}.required_workflows[{index}]"
        row = _require_dict(row_raw, row_label)
        _validate_exact_fields(row, {"workflow_id", "workflow_path", "workflow_name"}, row_label)
        required.append({
            "workflow_id": _require_int(row.get("workflow_id"), f"{row_label}.workflow_id", minimum=1),
            "workflow_path": _workflow_path(row.get("workflow_path"), f"{row_label}.workflow_path"),
            "workflow_name": _require_text(row.get("workflow_name"), f"{row_label}.workflow_name"),
        })

    for field in ("workflow_id", "workflow_path", "workflow_name"):
        values = [row[field] for row in required]
        if len(values) != len(set(values)):
            raise EvidenceError(f"{label}.required_workflows contains duplicate {field}")

    return {
        "schema_version": POLICY_SCHEMA,
        "source": {"kind": source_kind, "locator": source_locator, "source_sha256": source_sha256},
        "base_ref": base_ref,
        "base_sha": base_sha,
        "captured_at": captured_at,
        "required_workflows": required,
    }


def _parse_complete_inventory(raw: Any, label: str, expected_source: str) -> dict[str, Any]:
    inventory = _require_dict(raw, label)
    fields = {"source", "complete", "total_count", "pages", "next_url"}
    _validate_exact_fields(inventory, fields, label)
    missing = fields - set(inventory)
    if missing:
        raise EvidenceError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    source = _require_text(inventory.get("source"), f"{label}.source")
    if source != expected_source:
        raise EvidenceError(f"{label}.source must equal {expected_source}")
    complete = _require_bool(inventory.get("complete"), f"{label}.complete")
    if not complete:
        raise EvidenceError(f"{label}.complete must be true")
    total_count = _require_int(inventory.get("total_count"), f"{label}.total_count", minimum=0)
    pages = _require_int(inventory.get("pages"), f"{label}.pages", minimum=1)
    if inventory.get("next_url") is not None:
        raise EvidenceError(f"{label}.next_url must be null for a complete inventory")
    return {
        "source": source,
        "complete": complete,
        "total_count": total_count,
        "pages": pages,
        "next_url": None,
    }


def _parse_inventory(raw: Any, label: str = "inventory") -> dict[str, Any]:
    return _parse_complete_inventory(raw, label, "github-actions-runs")


def _parse_jobs_inventory(raw: Any, label: str) -> dict[str, Any]:
    return _parse_complete_inventory(raw, label, "github-actions-jobs")
