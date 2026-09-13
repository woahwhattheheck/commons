#!/usr/bin/env python3
"""Read-only layout revision-to-print evidence compiler.

Compiles field evidence into deterministic evidence packets. It has no robot,
printer, tracker, file-deletion, model-approval, certification, or field-release
actions. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable


def _nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _fault(code: str, input_class: str, field: str, detail: str) -> dict[str, str]:
    return {"reason_code": code, "input_class": input_class, "field": field, "detail": detail}


def _nested(job: dict[str, Any], key: str) -> dict[str, Any]:
    value = job.get(key)
    return value if isinstance(value, dict) else {}


def validate_design_source(job: dict[str, Any]) -> dict[str, str] | None:
    d = _nested(job, "design")
    if not _nonempty(d.get("file_sha256")):
        return _fault("DESIGN_HASH_MISSING", "design_source", "$.design.file_sha256", "BIM/CAD file SHA-256 is required")
    if not _nonempty(d.get("revision")) or not _nonempty(d.get("released_revision")):
        return _fault("DESIGN_REVISION_MISSING", "design_source", "$.design.revision|released_revision", "design revision and released revision are required")
    if d.get("revision") != d.get("released_revision"):
        return _fault("DESIGN_REVISION_MISMATCH", "design_source", "$.design.revision", "working design revision does not equal released revision")
    return None


def validate_trade_signoffs(job: dict[str, Any]) -> dict[str, str] | None:
    design = _nested(job, "design")
    signoffs = job.get("trade_signoffs")
    if not isinstance(signoffs, list) or not signoffs:
        return _fault("TRADE_SIGNOFFS_MISSING", "trade_signoffs", "$.trade_signoffs", "at least one trade signoff is required")
    for i, s in enumerate(signoffs):
        if not isinstance(s, dict) or not _nonempty(s.get("trade")) or not _nonempty(s.get("signer")):
            return _fault("TRADE_SIGNOFF_INVALID", "trade_signoffs", f"$.trade_signoffs[{i}]", "trade and signer are required")
        if s.get("status") != "SIGNED":
            return _fault("TRADE_SIGNOFF_NOT_SIGNED", "trade_signoffs", f"$.trade_signoffs[{i}].status", "trade signoff status must equal SIGNED")
        if s.get("revision") != design.get("revision"):
            return _fault("TRADE_SIGNOFF_STALE", "trade_signoffs", f"$.trade_signoffs[{i}].revision", "trade signoff revision must match design revision")
    return None


def validate_unit_scale(job: dict[str, Any]) -> dict[str, str] | None:
    m = _nested(job, "unit_scale")
    if m.get("model_unit") not in {"mm", "in", "ft", "m"} or m.get("field_unit") not in {"mm", "in", "ft", "m"}:
        return _fault("UNIT_METADATA_INVALID", "unit_scale_metadata", "$.unit_scale", "model_unit and field_unit must be declared supported units")
    scale = m.get("scale")
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or scale <= 0:
        return _fault("SCALE_INVALID", "unit_scale_metadata", "$.unit_scale.scale", "scale must be a positive number")
    if m.get("verified") is not True:
        return _fault("UNIT_SCALE_UNVERIFIED", "unit_scale_metadata", "$.unit_scale.verified", "unit/scale metadata must be verified")
    return None


def validate_control_point_survey(job: dict[str, Any]) -> dict[str, str] | None:
    survey = _nested(job, "control_point_survey")
    if not _nonempty(survey.get("version")):
        return _fault("SURVEY_VERSION_MISSING", "control_point_survey", "$.control_point_survey.version", "survey version is required")
    if not _nonempty(survey.get("sha256")):
        return _fault("SURVEY_HASH_MISSING", "control_point_survey", "$.control_point_survey.sha256", "survey SHA-256 is required")
    if survey.get("version") != survey.get("released_version"):
        return _fault("SURVEY_VERSION_STALE", "control_point_survey", "$.control_point_survey.version", "control-point survey version must equal released version")
    return None


def validate_station_verification(job: dict[str, Any]) -> dict[str, str] | None:
    station = _nested(job, "station_verification")
    survey = _nested(job, "control_point_survey")
    if station.get("result") != "PASS":
        return _fault("STATION_VERIFICATION_NOT_PASS", "station_verification", "$.station_verification.result", "station verification result must equal PASS")
    if station.get("survey_version") != survey.get("version"):
        return _fault("STATION_SURVEY_MISMATCH", "station_verification", "$.station_verification.survey_version", "station verification must reference current survey version")
    if not _nonempty(station.get("verification_id")):
        return _fault("STATION_VERIFICATION_ID_MISSING", "station_verification", "$.station_verification.verification_id", "verification_id is required")
    return None


def validate_portal_preview(job: dict[str, Any]) -> dict[str, str] | None:
    p = _nested(job, "portal_preview")
    if not _nonempty(p.get("preview_sha256")) or not _nonempty(p.get("qr_sha256")):
        return _fault("PORTAL_CHECKSUM_MISSING", "portal_preview_qr", "$.portal_preview", "preview and QR checksums are required")
    if p.get("preview_sha256") != p.get("qr_sha256"):
        return _fault("PORTAL_QR_CHECKSUM_MISMATCH", "portal_preview_qr", "$.portal_preview.qr_sha256", "QR checksum must match Portal preview checksum")
    if p.get("design_revision") != _nested(job, "design").get("revision"):
        return _fault("PORTAL_PREVIEW_STALE", "portal_preview_qr", "$.portal_preview.design_revision", "Portal preview must reference current design revision")
    return None


def validate_printer_app_version(job: dict[str, Any]) -> dict[str, str] | None:
    v = _nested(job, "printer_app")
    if not _nonempty(v.get("printer_version")) or not _nonempty(v.get("app_version")):
        return _fault("PRINTER_APP_VERSION_MISSING", "printer_app_version", "$.printer_app", "printer and app versions are required")
    if v.get("capture_state") != "RECORDED":
        return _fault("PRINTER_APP_VERSION_UNRECORDED", "printer_app_version", "$.printer_app.capture_state", "version evidence must be recorded")
    return None


def validate_final_report(job: dict[str, Any]) -> dict[str, str] | None:
    r = _nested(job, "final_job_report")
    d = _nested(job, "design")
    s = _nested(job, "station_verification")
    p = _nested(job, "portal_preview")
    if r.get("status") != "COMPLETE":
        return _fault("FINAL_REPORT_INCOMPLETE", "final_job_report", "$.final_job_report.status", "final job report status must equal COMPLETE")
    checks = (
        ("job_id", job.get("job_id"), "FINAL_REPORT_JOB_MISMATCH"),
        ("design_sha256", d.get("file_sha256"), "FINAL_REPORT_DESIGN_HASH_MISMATCH"),
        ("design_revision", d.get("revision"), "FINAL_REPORT_REVISION_MISMATCH"),
        ("station_verification_id", s.get("verification_id"), "FINAL_REPORT_STATION_MISMATCH"),
        ("portal_preview_sha256", p.get("preview_sha256"), "FINAL_REPORT_PREVIEW_MISMATCH"),
    )
    for key, expected, code in checks:
        if r.get(key) != expected:
            return _fault(code, "final_job_report", f"$.final_job_report.{key}", f"final report {key} must match source evidence")
    return None


VALIDATORS: tuple[Callable[[dict[str, Any]], dict[str, str] | None], ...] = (
    validate_design_source,
    validate_trade_signoffs,
    validate_unit_scale,
    validate_control_point_survey,
    validate_station_verification,
    validate_portal_preview,
    validate_printer_app_version,
    validate_final_report,
)

LINEAGE_PATHS = (
    "$.job_id",
    "$.design",
    "$.trade_signoffs",
    "$.unit_scale",
    "$.control_point_survey",
    "$.station_verification",
    "$.portal_preview",
    "$.printer_app",
    "$.final_job_report",
)


def resolve_path(job: dict[str, Any], path: str) -> Any:
    if not path.startswith("$."):
        raise ValueError(path)
    value: Any = job
    for part in path[2:].split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def _canonical(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def compile_job(job: dict[str, Any], record_index: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    faults = [f for validator in VALIDATORS if (f := validator(job)) is not None]
    job_ref = job.get("job_id") if _nonempty(job.get("job_id")) else job.get("record_id", f"record-{record_index:03d}")
    exceptions = [
        {"job_ref": job_ref, **f, "control_commands_emitted": 0, "field_release": None}
        for f in faults
    ]
    if exceptions:
        return None, exceptions
    lineage = {path: {"source": path, "value": resolve_path(job, path)} for path in LINEAGE_PATHS}
    packet = {
        "schema": "layout-revision-to-print-evidence/v1",
        "job_id": job["job_id"],
        "evidence_status": "COMPLETE",
        "lineage": lineage,
        "evidence_sha256": hashlib.sha256(_canonical(lineage)).hexdigest(),
        "control_commands_emitted": 0,
        "field_release": None,
        "boundary": "evidence compilation only; no robot motion/printing, tracker setup, model approval, certification, or field release",
    }
    return packet, []


def compile_run(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    packets: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    for i, job in enumerate(jobs):
        if not isinstance(job, dict):
            exceptions.append({"job_ref": f"record-{i:03d}", "reason_code": "RECORD_NOT_OBJECT", "input_class": "record_envelope", "field": "$", "detail": "record must be an object", "control_commands_emitted": 0, "field_release": None})
            continue
        packet, errs = compile_job(job, i)
        if packet is not None:
            packets.append(packet)
        exceptions.extend(errs)
    counts = Counter(e["input_class"] for e in exceptions)
    return {
        "summary": {
            "input_jobs": len(jobs),
            "complete_packets": len(packets),
            "exceptions": len(exceptions),
            "unique_exception_jobs": len({e["job_ref"] for e in exceptions}),
            "exception_counts_by_input_class": dict(sorted(counts.items())),
            "control_commands_emitted": 0,
        },
        "packets": packets,
        "exceptions": exceptions,
    }


def write_bundle(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    packet_dir = output_dir / "packets"
    packet_dir.mkdir(exist_ok=True)
    for packet in result["packets"]:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", packet["job_id"])[:80]
        (packet_dir / f"{safe}.json").write_bytes(_canonical(packet) + b"\n")
    (output_dir / "exceptions.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in result["exceptions"]), encoding="ascii")
    (output_dir / "summary.json").write_text(json.dumps(result["summary"], sort_keys=True, indent=2) + "\n", encoding="ascii")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out"))
    args = ap.parse_args()
    jobs = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(jobs, list):
        raise SystemExit("input must be a JSON array")
    result = compile_run(jobs)
    write_bundle(result, args.out)
    print(json.dumps(result["summary"], sort_keys=True))
    return 0 if not result["exceptions"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
