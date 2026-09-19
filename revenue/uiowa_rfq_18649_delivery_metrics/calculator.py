#!/usr/bin/env python3
"""Offline DORA five-metric calculator for UIOWA-064 synthetic assessment use.

Service-scoped and descriptive only. No peer percentiles, maturity scores,
compliance verdicts, or individual productivity ratings are produced.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class DataError(ValueError):
    pass


@dataclass(frozen=True)
class Deployment:
    deployment_id: str
    service: str
    commit_at: datetime | None
    deployed_at: datetime
    intervention_required: bool | None
    recovered_at: datetime | None
    unplanned_rework: bool | None
    notes: str


def _parse_time(value: str, field: str, deployment_id: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DataError(
            f"{deployment_id}: {field} must be an ISO-8601 timestamp with offset"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DataError(f"{deployment_id}: {field} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _parse_bool(value: str, field: str, deployment_id: str) -> bool | None:
    value = value.strip().lower()
    if not value:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    raise DataError(f"{deployment_id}: {field} must be true, false, or blank")


def load_deployments(path: Path) -> list[Deployment]:
    required = {
        "deployment_id", "service", "commit_at", "deployed_at",
        "intervention_required", "recovered_at", "unplanned_rework", "notes",
    }
    deployments: list[Deployment] = []
    seen: set[str] = set()

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise DataError(f"missing CSV columns: {sorted(missing)}")

        for row_num, row in enumerate(reader, start=2):
            deployment_id = row["deployment_id"].strip()
            if not deployment_id:
                raise DataError(f"row {row_num}: deployment_id is required")
            if deployment_id in seen:
                raise DataError(f"duplicate deployment_id: {deployment_id}")
            seen.add(deployment_id)

            service = row["service"].strip()
            if not service:
                raise DataError(f"{deployment_id}: service is required")

            deployed_at = _parse_time(row["deployed_at"], "deployed_at", deployment_id)
            if deployed_at is None:
                raise DataError(f"{deployment_id}: deployed_at is required")
            commit_at = _parse_time(row["commit_at"], "commit_at", deployment_id)
            recovered_at = _parse_time(row["recovered_at"], "recovered_at", deployment_id)
            intervention = _parse_bool(
                row["intervention_required"], "intervention_required", deployment_id
            )
            rework = _parse_bool(
                row["unplanned_rework"], "unplanned_rework", deployment_id
            )

            if commit_at is not None and commit_at > deployed_at:
                raise DataError(f"{deployment_id}: commit_at occurs after deployed_at")
            if recovered_at is not None and recovered_at < deployed_at:
                raise DataError(f"{deployment_id}: recovered_at occurs before deployed_at")
            if intervention is False and recovered_at is not None:
                raise DataError(
                    f"{deployment_id}: recovered_at supplied while intervention_required=false"
                )

            deployments.append(
                Deployment(
                    deployment_id=deployment_id,
                    service=service,
                    commit_at=commit_at,
                    deployed_at=deployed_at,
                    intervention_required=intervention,
                    recovered_at=recovered_at,
                    unplanned_rework=rework,
                    notes=row["notes"].strip(),
                )
            )
    return deployments


def _hours(delta) -> float:
    return delta.total_seconds() / 3600.0


def _coverage(*, eligible: int, used: int, missing: int) -> dict:
    if eligible == 0:
        status = "NOT_OBSERVED"
    elif missing:
        status = "PARTIAL"
    else:
        status = "COMPLETE"
    return {"status": status, "eligible": eligible, "used": used, "missing": missing}


def _median_mean(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return round(statistics.median(values), 3), round(statistics.fmean(values), 3)


def calculate(
    deployments: Iterable[Deployment],
    *,
    window_start: datetime,
    window_end: datetime,
    service: str | None = None,
) -> dict:
    if window_start.tzinfo is None or window_end.tzinfo is None:
        raise DataError("window timestamps must be timezone-aware")
    window_start = window_start.astimezone(timezone.utc)
    window_end = window_end.astimezone(timezone.utc)
    if window_start >= window_end:
        raise DataError("window_start must be before window_end")

    rows = [d for d in deployments if window_start <= d.deployed_at < window_end]
    services = sorted({d.service for d in rows})
    if service is not None:
        rows = [d for d in rows if d.service == service]
    elif len(services) > 1:
        raise DataError(
            "multiple services are present in the window; pass --service so metrics remain service-scoped"
        )
    if not rows:
        raise DataError("no deployments match the selected service/window")

    rows.sort(key=lambda d: (d.deployed_at, d.deployment_id))
    selected_service = rows[0].service

    lead_values = [
        _hours(d.deployed_at - d.commit_at) for d in rows if d.commit_at is not None
    ]
    lead_missing = sum(d.commit_at is None for d in rows)
    lead_median, lead_mean = _median_mean(lead_values)

    intervals = [
        _hours(rows[i].deployed_at - rows[i - 1].deployed_at)
        for i in range(1, len(rows))
    ]
    median_interval = round(statistics.median(intervals), 3) if intervals else None
    window_days = (window_end - window_start).total_seconds() / 86400.0
    per_day = len(rows) / window_days
    per_week = per_day * 7.0

    failed_known = [d for d in rows if d.intervention_required is not None]
    failed_missing = len(rows) - len(failed_known)
    failed = [d for d in failed_known if d.intervention_required is True]
    recovery_values = [
        _hours(d.recovered_at - d.deployed_at)
        for d in failed
        if d.recovered_at is not None
    ]
    recovery_missing = sum(d.recovered_at is None for d in failed)
    recovery_median, recovery_mean = _median_mean(recovery_values)

    rework_known = [d for d in rows if d.unplanned_rework is not None]
    rework_missing = len(rows) - len(rework_known)
    rework_count = sum(d.unplanned_rework is True for d in rework_known)

    cfr_rate = (len(failed) / len(failed_known)) if failed_known else None
    rework_rate = (rework_count / len(rework_known)) if rework_known else None

    return {
        "scope": {
            "service": selected_service,
            "window_start": window_start.isoformat().replace("+00:00", "Z"),
            "window_end_exclusive": window_end.isoformat().replace("+00:00", "Z"),
            "deployment_count": len(rows),
        },
        "metrics": {
            "change_lead_time": {
                "unit": "hours",
                "median": lead_median,
                "mean": lead_mean,
                "coverage": _coverage(
                    eligible=len(rows), used=len(lead_values), missing=lead_missing
                ),
            },
            "deployment_frequency": {
                "deployment_count": len(rows),
                "window_days": round(window_days, 3),
                "deployments_per_day": round(per_day, 6),
                "deployments_per_week": round(per_week, 6),
                "median_interdeployment_hours": median_interval,
                "coverage": _coverage(eligible=len(rows), used=len(rows), missing=0),
            },
            "failed_deployment_recovery_time": {
                "unit": "hours",
                "median": recovery_median,
                "mean": recovery_mean,
                "coverage": _coverage(
                    eligible=len(failed),
                    used=len(recovery_values),
                    missing=recovery_missing,
                ),
            },
            "change_fail_rate": {
                "failed_deployments": len(failed),
                "known_deployments": len(failed_known),
                "rate": round(cfr_rate, 6) if cfr_rate is not None else None,
                "percent": round(cfr_rate * 100, 3) if cfr_rate is not None else None,
                "coverage": _coverage(
                    eligible=len(rows), used=len(failed_known), missing=failed_missing
                ),
            },
            "deployment_rework_rate": {
                "unplanned_rework_deployments": rework_count,
                "known_deployments": len(rework_known),
                "rate": round(rework_rate, 6) if rework_rate is not None else None,
                "percent": round(rework_rate * 100, 3) if rework_rate is not None else None,
                "coverage": _coverage(
                    eligible=len(rows), used=len(rework_known), missing=rework_missing
                ),
            },
        },
        "interpretation_boundary": {
            "service_scoped": True,
            "peer_percentile": False,
            "individual_productivity_rating": False,
            "maturity_score": False,
            "partial_metrics_must_be_labeled": True,
        },
    }


def _required_time(value: str, field: str) -> datetime:
    parsed = _parse_time(value, field, "arguments")
    if parsed is None:
        raise DataError(f"{field} is required")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--service")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = calculate(
            load_deployments(args.csv_path),
            window_start=_required_time(args.window_start, "window_start"),
            window_end=_required_time(args.window_end, "window_end"),
            service=args.service,
        )
    except (DataError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
