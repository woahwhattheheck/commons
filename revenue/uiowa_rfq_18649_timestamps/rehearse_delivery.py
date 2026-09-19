#!/usr/bin/env python3
"""Execute the real sibling UIOWA-064 calculator through the timestamp bridge."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__:
    from .csv_bridge import convert_rows, read_rows
    from .timestamp_adapter import InputError
else:
    from csv_bridge import convert_rows, read_rows
    from timestamp_adapter import InputError

ROOT = Path(__file__).resolve().parent
DEPENDENCY = ROOT.parent / "uiowa_rfq_18649_delivery_metrics"


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rehearse(expected_calculator_blob: str | None = None) -> dict:
    calculator = DEPENDENCY / "calculator.py"
    fixture = DEPENDENCY / "fixtures/synthetic_deployments.csv"
    if not calculator.is_file() or not fixture.is_file():
        raise InputError("full checkout required: sibling delivery_metrics calculator/fixture is missing")
    blobs = {str(p.relative_to(ROOT.parent)): git_blob(p) for p in (calculator, fixture)}
    if expected_calculator_blob and blobs["uiowa_rfq_18649_delivery_metrics/calculator.py"] != expected_calculator_blob:
        raise InputError("calculator revision drift: supplied expected blob does not match this checkout")
    name = "_uiowa129_real_delivery_calculator"
    spec = importlib.util.spec_from_file_location(name, calculator)
    if spec is None or spec.loader is None:
        raise InputError("could not load sibling calculator")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module  # dataclass resolves its defining module during import.
    try:
        spec.loader.exec_module(module)
        window = {"window_start": datetime(2026, 9, 1, tzinfo=timezone.utc),
                  "window_end": datetime(2026, 9, 15, tzinfo=timezone.utc),
                  "service": "synthetic-registration"}
        original = module.calculate(module.load_deployments(fixture), **window)
        fields, rows = read_rows(fixture)
        audit = convert_rows(rows)
        if audit["status"] != "ready":
            raise InputError("published fixture unexpectedly fails timestamp normalization")
        with tempfile.TemporaryDirectory(prefix="uiowa129-") as temporary:
            temporary = Path(temporary)
            normalized = temporary / "normalized.csv"
            _write(normalized, fields, audit["normalized_rows"])
            round_trip = module.calculate(module.load_deployments(normalized), **window)
            # Re-express the same real fixture instants in three numerical offsets.
            mixed = []
            offsets = [timezone(timedelta(hours=5, minutes=30)), timezone(timedelta(hours=-4)), timezone.utc]
            for index, row in enumerate(rows):
                converted = dict(row)
                for field in ("commit_at", "deployed_at", "recovered_at"):
                    if row[field]:
                        instant = datetime.fromisoformat(row[field].replace("Z", "+00:00"))
                        converted[field] = instant.astimezone(offsets[index % 3]).isoformat()
                mixed.append(converted)
            mixed_audit = convert_rows(mixed)
            if mixed_audit["status"] != "ready":
                raise InputError("mixed-zone equivalent fixture unexpectedly unresolved")
            mixed_path = temporary / "mixed.csv"
            _write(mixed_path, fields, mixed_audit["normalized_rows"])
            mixed_report = module.calculate(module.load_deployments(mixed_path), **window)
            dst_fields, dst_rows = read_rows(ROOT / "fixtures/delivery_dst.csv")
            dst_audit = convert_rows(dst_rows)
            if dst_audit["status"] != "ready":
                raise InputError("DST fixture unresolved; inspect installed timezone data")
            dst_path = temporary / "dst.csv"
            _write(dst_path, dst_fields, dst_audit["normalized_rows"])
            dst_report = module.calculate(module.load_deployments(dst_path),
                window_start=datetime(2026, 11, 1, tzinfo=timezone.utc),
                window_end=datetime(2026, 11, 2, tzinfo=timezone.utc), service="synthetic-dst")
            # Missing fold evidence must prevent a normalized CSV, not guess a recovery.
            ambiguous = [dict(dst_rows[0], recovered_at_fold="")]
            ambiguous_audit = convert_rows(ambiguous)
        checks = {
            "original_fixture_metric_identity": round_trip == original,
            "mixed_offset_metric_identity": mixed_report == original,
            "published_fixture_count_eight": original["scope"]["deployment_count"] == 8,
            "dst_lead_one_hour": dst_report["metrics"]["change_lead_time"]["median"] == 1.0,
            "dst_recovery_one_hour": dst_report["metrics"]["failed_deployment_recovery_time"]["median"] == 1.0,
            "ambiguous_recovery_blocks_conversion": ambiguous_audit["status"] == "unresolved" and ambiguous_audit["normalized_rows"] is None,
        }
        return {"schema_version": 1, "synthetic": True, "status": "passed" if all(checks.values()) else "failed",
                "dependency_blobs": blobs, "checks": checks, "native_original_report": original,
                "native_dst_report": dst_report, "dst_time_audit": dst_audit["audit"],
                "ambiguous_recovery_diagnostics": [e for e in ambiguous_audit["audit"] if e["normalization"]["status"] != "resolved"],
                "boundary": "Executed synthetic compatibility rehearsal, not a University finding or proof of recovery."}
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-calculator-blob")
    args = parser.parse_args(argv)
    try:
        report = rehearse(args.expect_calculator_blob)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (InputError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
