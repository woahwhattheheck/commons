#!/usr/bin/env python3
"""Offline DORA five-metric calculator for UIOWA-064.

This tool implements a transparent local operationalization of DORA's current five
software-delivery performance metrics. It never produces individual scores or peer
percentiles. Metrics are calculated per service/application only.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Iterable

DORA_GUIDE = "https://dora.dev/guides/dora-metrics/"
DORA_GUIDE_LAST_UPDATED = "2026-01-05"
REQUIRED_COLUMNS = {
    "deployment_id",
    "service",
    "window_start",
    "window_end",
    "environment",
    "deployed_at",
    "commit_id",
    "committed_at",
    "successful_change_at",
    "requires_immediate_intervention",
    "failure_detected_at",
    "recovery_completed_at",
    "is_unplanned_rework",
    "rework_cause",
    "notes",
}
TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n", ""}


class DataError(ValueError):
    """Input data cannot support a trustworthy calculation."""


def parse_bool(value: str, *, field: str, row_no: int) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise DataError(f"row {row_no}: {field} must be a boolean, got {value!r}")


def parse_ts(value: str, *, field: str, row_no: int, required: bool = False) -> datetime | None:
    value = value.strip()
    if not value:
        if required:
            raise DataError(f"row {row_no}: {field} is required")
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataError(f"row {row_no}: invalid {field} timestamp {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise DataError(f"row {row_no}: {field} must include a timezone")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class Deployment:
    deployment_id: str
    service: str
    window_start: datetime
    window_end: datetime
    environment: str
    deployed_at: datetime
    commit_id: str
    committed_at: datetime | None
    successful_change_at: datetime | None
    requires_immediate_intervention: bool
    failure_detected_at: datetime | None
    recovery_completed_at: datetime | None
    is_unplanned_rework: bool
    rework_cause: str
    notes: str

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def load_deployments(path: Path) -> list[Deployment]:
    if not path.is_file():
        raise DataError(f"input not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise DataError(f"missing required columns: {sorted(missing)}")
        raw_rows = list(reader)

    deployments: list[Deployment] = []
    seen_ids: set[str] = set()
    for row_no, row in enumerate(raw_rows, start=2):
        deployment_id = row["deployment_id"].strip()
        service = row["service"].strip()
        environment = row["environment"].strip()
        if not deployment_id:
            raise DataError(f"row {row_no}: deployment_id is required")
        if deployment_id in seen_ids:
            raise DataError(f"row {row_no}: duplicate deployment_id {deployment_id!r}")
        seen_ids.add(deployment_id)
        if not service:
            raise DataError(f"row {row_no}: service is required")
        if not environment:
            raise DataError(f"row {row_no}: environment is required")

        window_start = parse_ts(row["window_start"], field="window_start", row_no=row_no, required=True)
        window_end = parse_ts(row["window_end"], field="window_end", row_no=row_no, required=True)
        deployed_at = parse_ts(row["deployed_at"], field="deployed_at", row_no=row_no, required=True)
        committed_at = parse_ts(row["committed_at"], field="committed_at", row_no=row_no)
        successful_change_at = parse_ts(
            row["successful_change_at"], field="successful_change_at", row_no=row_no
        )
        failure_detected_at = parse_ts(
            row["failure_detected_at"], field="failure_detected_at", row_no=row_no
        )
        recovery_completed_at = parse_ts(
            row["recovery_completed_at"], field="recovery_completed_at", row_no=row_no
        )
        requires_intervention = parse_bool(
            row["requires_immediate_intervention"],
            field="requires_immediate_intervention",
            row_no=row_no,
        )
        is_rework = parse_bool(
            row["is_unplanned_rework"], field="is_unplanned_rework", row_no=row_no
        )
        rework_cause = row["rework_cause"].strip()

        assert window_start is not None and window_end is not None and deployed_at is not None
        if window_end <= window_start:
            raise DataError(f"row {row_no}: window_end must be after window_start")
        if deployed_at < window_start or deployed_at >= window_end:
            raise DataError(
                f"row {row_no}: deployed_at must be inside [window_start, window_end)"
            )
        if committed_at and successful_change_at and successful_change_at < committed_at:
            raise DataError(f"row {row_no}: successful_change_at precedes committed_at")
        if requires_intervention:
            if failure_detected_at is None or recovery_completed_at is None:
                raise DataError(
                    f"row {row_no}: failed deployment requires failure_detected_at and recovery_completed_at"
                )
            if failure_detected_at < deployed_at:
                raise DataError(f"row {row_no}: failure_detected_at precedes deployed_at")
            if recovery_completed_at < failure_detected_at:
                raise DataError(f"row {row_no}: recovery_completed_at precedes failure_detected_at")
        elif failure_detected_at or recovery_completed_at:
            raise DataError(
                f"row {row_no}: recovery timestamps supplied but requires_immediate_intervention is false"
            )
        if is_rework and not rework_cause:
            raise DataError(f"row {row_no}: unplanned rework requires rework_cause")

        deployments.append(
            Deployment(
                deployment_id=deployment_id,
                service=service,
                window_start=window_start,
                window_end=window_end,
                environment=environment,
                deployed_at=deployed_at,
                commit_id=row["commit_id"].strip(),
                committed_at=committed_at,
                successful_change_at=successful_change_at,
                requires_immediate_intervention=requires_intervention,
                failure_detected_at=failure_detected_at,
                recovery_completed_at=recovery_completed_at,
                is_unplanned_rework=is_rework,
                rework_cause=rework_cause,
                notes=row["notes"].strip(),
            )
        )
    return deployments


def hours(delta_seconds: float) -> float:
    return round(delta_seconds / 3600.0, 3)


def pct(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return round(num * 100.0 / den, 3)


def metric_status(*, eligible: int, measured: int) -> str:
    if eligible == 0:
        return "not_observed"
    if measured == 0:
        return "insufficient_evidence"
    if measured < eligible:
        return "measured_partial"
    return "measured"


def summarize_service(service: str, rows: list[Deployment]) -> dict[str, object]:
    production = [row for row in rows if row.is_production]
    if not production:
        raise DataError(f"service {service!r}: no production deployments in input")

    windows = {(row.window_start, row.window_end) for row in production}
    if len(windows) != 1:
        raise DataError(f"service {service!r}: inconsistent observation windows")
    window_start, window_end = next(iter(windows))
    window_days = (window_end - window_start).total_seconds() / 86400.0
    if window_days <= 0:
        raise DataError(f"service {service!r}: invalid observation window")

    deployment_count = len(production)
    deployment_frequency = {
        "status": "measured",
        "deployment_count": deployment_count,
        "window_days": round(window_days, 3),
        "deployments_per_day": round(deployment_count / window_days, 3),
        "deployments_per_week": round(deployment_count / window_days * 7.0, 3),
        "definition": "number of production deployments over the stated observation window",
    }

    lead_eligible = [row for row in production if row.successful_change_at is not None]
    lead_measured = [
        row for row in lead_eligible if row.committed_at is not None and row.commit_id
    ]
    lead_hours = [
        hours((row.successful_change_at - row.committed_at).total_seconds())
        for row in lead_measured
        if row.successful_change_at is not None and row.committed_at is not None
    ]
    change_lead_time = {
        "status": metric_status(eligible=len(lead_eligible), measured=len(lead_measured)),
        "eligible_changes": len(lead_eligible),
        "measured_changes": len(lead_measured),
        "missing_change_linkage": len(lead_eligible) - len(lead_measured),
        "median_hours": round(median(lead_hours), 3) if lead_hours else None,
        "min_hours": min(lead_hours) if lead_hours else None,
        "max_hours": max(lead_hours) if lead_hours else None,
        "coverage_percent": pct(len(lead_measured), len(lead_eligible)),
        "definition": "time from commit to the change successfully running in production",
        "aggregation_note": "median/min/max are this tool's transparent local summary, not a DORA-required aggregation formula",
    }

    failed = [row for row in production if row.requires_immediate_intervention]
    recovery_measured = [
        row
        for row in failed
        if row.failure_detected_at is not None and row.recovery_completed_at is not None
    ]
    recovery_hours = [
        hours((row.recovery_completed_at - row.failure_detected_at).total_seconds())
        for row in recovery_measured
        if row.failure_detected_at is not None and row.recovery_completed_at is not None
    ]
    recovery = {
        "status": metric_status(eligible=len(failed), measured=len(recovery_measured)),
        "failed_deployments": len(failed),
        "measured_recoveries": len(recovery_measured),
        "median_hours": round(median(recovery_hours), 3) if recovery_hours else None,
        "min_hours": min(recovery_hours) if recovery_hours else None,
        "max_hours": max(recovery_hours) if recovery_hours else None,
        "definition": "time from detected impairment caused by a deployment to completed recovery",
        "aggregation_note": "median/min/max are this tool's transparent local summary, not a DORA-required aggregation formula",
    }

    change_fail_rate = {
        "status": "measured",
        "failed_deployments": len(failed),
        "production_deployments": deployment_count,
        "percent": pct(len(failed), deployment_count),
        "definition": "share of production deployments requiring immediate intervention such as rollback, hotfix, fix-forward, or patch",
    }

    rework = [row for row in production if row.is_unplanned_rework]
    deployment_rework_rate = {
        "status": "measured",
        "unplanned_rework_deployments": len(rework),
        "production_deployments": deployment_count,
        "percent": pct(len(rework), deployment_count),
        "rework_causes": sorted({row.rework_cause for row in rework if row.rework_cause}),
        "definition": "share of production deployments that were unplanned and performed because of a production incident or user-facing bug",
    }

    return {
        "service": service,
        "window_start": window_start.isoformat().replace("+00:00", "Z"),
        "window_end": window_end.isoformat().replace("+00:00", "Z"),
        "nonproduction_rows_excluded": len(rows) - len(production),
        "metrics": {
            "deployment_frequency": deployment_frequency,
            "change_lead_time": change_lead_time,
            "failed_deployment_recovery_time": recovery,
            "change_fail_rate": change_fail_rate,
            "deployment_rework_rate": deployment_rework_rate,
        },
    }


def calculate(deployments: Iterable[Deployment]) -> dict[str, object]:
    by_service: dict[str, list[Deployment]] = {}
    for row in deployments:
        by_service.setdefault(row.service, []).append(row)
    if not by_service:
        raise DataError("input contains no deployment rows")
    services = [summarize_service(service, by_service[service]) for service in sorted(by_service)]
    return {
        "schema_version": "uiowa-dora-five-v1",
        "source": {
            "name": "DORA software delivery performance metrics",
            "url": DORA_GUIDE,
            "guide_last_updated": DORA_GUIDE_LAST_UPDATED,
        },
        "guardrails": [
            "Metrics are calculated per application/service; no cross-service aggregate score is produced.",
            "No individual productivity score or ranking is produced.",
            "No peer percentile or DORA Quick Check score is inferred from event logs.",
            "Missing change linkage remains missing; it is not imputed.",
            "A service with no failed deployment has recovery status not_observed, not zero recovery time.",
        ],
        "services": services,
    }


def write_summary_csv(result: dict[str, object], path: Path) -> None:
    rows: list[dict[str, object]] = []
    for service in result["services"]:
        name = service["service"]
        for metric, payload in service["metrics"].items():
            rows.append(
                {
                    "service": name,
                    "metric": metric,
                    "status": payload.get("status"),
                    "value": (
                        payload.get("deployments_per_week")
                        if metric == "deployment_frequency"
                        else payload.get("median_hours")
                        if metric in {"change_lead_time", "failed_deployment_recovery_time"}
                        else payload.get("percent")
                    ),
                    "unit": (
                        "deployments_per_week"
                        if metric == "deployment_frequency"
                        else "hours"
                        if metric in {"change_lead_time", "failed_deployment_recovery_time"}
                        else "percent"
                    ),
                    "definition": payload.get("definition"),
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["service", "metric", "status", "value", "unit", "definition"]
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args(argv)
    try:
        deployments = load_deployments(args.input_csv)
        result = calculate(deployments)
    except DataError as exc:
        parser.error(str(exc))
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    if args.csv_out:
        write_summary_csv(result, args.csv_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
