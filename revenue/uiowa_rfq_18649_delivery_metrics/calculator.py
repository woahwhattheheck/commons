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
from collections import Counter
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


def _text(value: str, field: str, identity: str, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise DataError(f"{identity}: {field} must be text")
    value = value.strip()
    if required and not value:
        raise DataError(f"{identity}: {field} is required")
    return value


def _checked_time(value: datetime, field: str, identity: str) -> datetime:
    if not isinstance(value, datetime):
        raise DataError(f"{identity}: {field} must be a timezone-aware datetime")
    try:
        if value.tzinfo is None or value.utcoffset() is None:
            raise DataError(f"{identity}: {field} must include a UTC offset")
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise DataError(f"{identity}: {field} must be a valid timezone-aware datetime") from exc


def _parse_time(value: str, field: str, deployment_id: str) -> datetime | None:
    value = _text(value, field, deployment_id)
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DataError(
            f"{deployment_id}: {field} must be an ISO-8601 timestamp with offset"
        ) from exc
    return _checked_time(parsed, field, deployment_id)


def _parse_bool(value: str, field: str, deployment_id: str) -> bool | None:
    value = _text(value, field, deployment_id).lower()
    if not value:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    raise DataError(f"{deployment_id}: {field} must be true, false, or blank")


def _validated_deployments(deployments: Iterable[Deployment]) -> list[Deployment]:
    """Apply the same contract to CSV and direct Python callers before filtering."""
    result: list[Deployment] = []
    seen: set[str] = set()
    try:
        iterator = iter(deployments)
    except TypeError as exc:
        raise DataError("deployments must be an iterable of Deployment records") from exc
    for position, row in enumerate(iterator, start=1):
        if not isinstance(row, Deployment):
            raise DataError(f"record {position}: expected a Deployment record")
        identity = _text(row.deployment_id, "deployment_id", f"record {position}", required=True)
        if identity in seen:
            raise DataError(f"duplicate deployment_id: {identity}")
        seen.add(identity)
        service = _text(row.service, "service", identity, required=True)
        notes = _text(row.notes, "notes", identity, required=True)
        deployed = _checked_time(row.deployed_at, "deployed_at", identity)
        commit = (_checked_time(row.commit_at, "commit_at", identity)
                  if row.commit_at is not None else None)
        recovered = (_checked_time(row.recovered_at, "recovered_at", identity)
                     if row.recovered_at is not None else None)
        for field in ("intervention_required", "unplanned_rework"):
            value = getattr(row, field)
            # Membership in (True, False, None) would silently accept integers 0/1.
            if value is not None and type(value) is not bool:
                raise DataError(f"{identity}: {field} must be bool or None")
        if commit is not None and commit > deployed:
            raise DataError(f"{identity}: commit_at occurs after deployed_at")
        if recovered is not None and recovered < deployed:
            raise DataError(f"{identity}: recovered_at occurs before deployed_at")
        if row.intervention_required is False and recovered is not None:
            raise DataError(f"{identity}: recovered_at supplied while intervention_required=false")
        result.append(Deployment(identity, service, commit, deployed,
                                 row.intervention_required, recovered,
                                 row.unplanned_rework, notes))
    return result


def load_deployments(path: Path) -> list[Deployment]:
    required = {
        "deployment_id", "service", "commit_at", "deployed_at",
        "intervention_required", "recovered_at", "unplanned_rework", "notes",
    }
    deployments: list[Deployment] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        try:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            if any(not header.strip() for header in headers):
                raise DataError("CSV headers must be non-empty")
            duplicates = sorted(name for name, count in Counter(headers).items() if count > 1)
            if duplicates:
                raise DataError(f"duplicate CSV columns: {duplicates}")
            missing = required - set(headers)
            if missing:
                raise DataError(f"missing CSV columns: {sorted(missing)}")
            for row in reader:
                # Extra unheaded cells and absent cells are not blank evidence.
                if None in row or any(value is None for value in row.values()):
                    raise DataError(f"CSV line {reader.line_num}: row width does not match header")
                identity = _text(row["deployment_id"], "deployment_id",
                                 f"CSV line {reader.line_num}", required=True)
                deployments.append(Deployment(
                    deployment_id=identity,
                    service=row["service"],
                    commit_at=_parse_time(row["commit_at"], "commit_at", identity),
                    deployed_at=_parse_time(row["deployed_at"], "deployed_at", identity),
                    intervention_required=_parse_bool(row["intervention_required"],
                                                      "intervention_required", identity),
                    recovered_at=_parse_time(row["recovered_at"], "recovered_at", identity),
                    unplanned_rework=_parse_bool(row["unplanned_rework"], "unplanned_rework", identity),
                    notes=row["notes"],
                ))
        except (csv.Error, UnicodeError) as exc:
            raise DataError(f"invalid UTF-8 CSV: {exc}") from exc
    return _validated_deployments(deployments)


def _hours(delta) -> float:
    return delta.total_seconds() / 3600.0


def _coverage(*, eligible: int, used: int, missing: int, eligibility_unknown: int = 0) -> dict:
    if missing or eligibility_unknown:
        status = "PARTIAL"
    elif eligible == 0:
        status = "NOT_OBSERVED"
    else:
        status = "COMPLETE"
    return {"status": status, "eligible": eligible, "used": used, "missing": missing}


def _median_mean(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return round(statistics.median(values), 3), round(statistics.fmean(values), 3)


def _rate_bounds(positive: int, unknown: int, total: int) -> dict:
    """Logical all-row bounds, not imputed rates or statistical confidence intervals."""
    return {
        "lower": round(positive / total, 6),
        "upper": round((positive + unknown) / total, 6),
        "population": total,
        "unknown_classifications": unknown,
        "kind": "MISSING_CLASSIFICATION_BOUNDS_NOT_CONFIDENCE_INTERVAL",
    }


def calculate(
    deployments: Iterable[Deployment],
    *,
    window_start: datetime,
    window_end: datetime,
    service: str | None = None,
    recovery_observed_through: datetime | None = None,
) -> dict:
    window_start = _checked_time(window_start, "window_start", "arguments")
    window_end = _checked_time(window_end, "window_end", "arguments")
    if service is not None:
        service = _text(service, "service", "arguments", required=True)
    if recovery_observed_through is not None:
        recovery_observed_through = _checked_time(
            recovery_observed_through, "recovery_observed_through", "arguments"
        )
        if recovery_observed_through < window_end:
            raise DataError("recovery_observed_through must be at or after window_end")
    if window_start >= window_end:
        raise DataError("window_start must be before window_end")

    rows = [d for d in _validated_deployments(deployments)
            if window_start <= d.deployed_at < window_end]
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
    missing_recovery = [d for d in failed if d.recovered_at is None]
    after_cutoff = [d for d in failed if d.recovered_at is not None
                    and recovery_observed_through is not None
                    and d.recovered_at > recovery_observed_through]
    observed_recovery = [d for d in failed if d.recovered_at is not None
                         and (recovery_observed_through is None
                              or d.recovered_at <= recovery_observed_through)]
    recovery_values = [_hours(d.recovered_at - d.deployed_at) for d in observed_recovery]
    recovery_missing = len(missing_recovery) + len(after_cutoff)
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
            "recovery_observed_through": (
                recovery_observed_through.isoformat().replace("+00:00", "Z")
                if recovery_observed_through is not None else None
            ),
            "recovery_follow_up_mode": (
                "EXPLICIT_RECOVERY_CUTOFF" if recovery_observed_through is not None
                else "ALL_SUPPLIED_RECORDS_RETROSPECTIVE"
            ),
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
                "coverage": {
                    **_coverage(eligible=len(failed), used=len(recovery_values),
                                missing=recovery_missing, eligibility_unknown=failed_missing),
                    "eligibility_unknown": failed_missing,
                },
                "evidence": {
                    "observed_recovery_ids": [d.deployment_id for d in observed_recovery],
                    "missing_recovery_timestamp_ids": [d.deployment_id for d in missing_recovery],
                    "recovered_after_cutoff_ids": [d.deployment_id for d in after_cutoff],
                    "unknown_failure_classification_ids": [d.deployment_id for d in rows
                                                           if d.intervention_required is None],
                    "known_non_failure_count": len(failed_known) - len(failed),
                },
            },
            "change_fail_rate": {
                "failed_deployments": len(failed),
                "denominator_basis": "KNOWN_CLASSIFICATION_ONLY",
                "full_cohort_rate_bounds": _rate_bounds(len(failed), failed_missing, len(rows)),
                "known_deployments": len(failed_known),
                "rate": round(cfr_rate, 6) if cfr_rate is not None else None,
                "percent": round(cfr_rate * 100, 3) if cfr_rate is not None else None,
                "coverage": _coverage(
                    eligible=len(rows), used=len(failed_known), missing=failed_missing
                ),
            },
            "deployment_rework_rate": {
                "unplanned_rework_deployments": rework_count,
                "denominator_basis": "KNOWN_CLASSIFICATION_ONLY",
                "full_cohort_rate_bounds": _rate_bounds(rework_count, rework_missing, len(rows)),
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
            "recovery_statistics_are_observed_case_only": True,
            "classification_as_of_verified": False,
            "source_export_completeness_verified": False,
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
    parser.add_argument("--recovery-observed-through",
                        help="Inclusive recovery timestamp cutoff; must be >= window end. "
                             "Omit for explicitly labeled retrospective use of all supplied records.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = calculate(
            load_deployments(args.csv_path),
            window_start=_required_time(args.window_start, "window_start"),
            window_end=_required_time(args.window_end, "window_end"),
            service=args.service,
            recovery_observed_through=(
                _required_time(args.recovery_observed_through, "recovery_observed_through")
                if args.recovery_observed_through is not None else None
            ),
        )
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            if (args.output.resolve() == args.csv_path.resolve()
                    or (args.output.exists() and args.output.samefile(args.csv_path))):
                raise DataError("output must not overwrite the input CSV")
            args.output.write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
    except (DataError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
