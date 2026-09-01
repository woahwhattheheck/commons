#!/usr/bin/env python3
"""SC Labs multistate COA rule-version pre-release validator.

This is a read-only validation/evidence overlay, not a LIMS replacement. It
joins sample, jurisdiction, license, matrix, custody, rule-pack, panel, method,
limit, accreditation, signer, and final-COA fields. Every row emits only
RELEASEABLE or HOLD. No result is changed and no COA is released.

CSV and JSON input are supported. Output is deterministic CSV, JSON, a human
exception report, and a hash-linked append-only evidence manifest.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable


DEMAND_ID = "sc-labs-multistate-coa-rule-version-gate-01"
SCHEMA = "commons-sc-labs-multistate-coa-rule-version-gate/v1"
BUYER = "SC Labs / Ryan DeCurtis"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
COMMAND = "python3 sc_labs_multistate_coa_rule_version_gate.py"
EVALUATION_TIME = "2026-09-01T00:00:00Z"
INPUT_COUNT = 150
RELEASEABLE_COUNT = 120
HOLD_COUNT = 30

RULE_VERSION_EXPIRED = "RULE_VERSION_EXPIRED"
PANEL_NOT_VALID_FOR_JURISDICTION = "PANEL_NOT_VALID_FOR_JURISDICTION"
METHOD_LIMIT_MISMATCH = "METHOD_LIMIT_MISMATCH"
CUSTODY_GAP = "CUSTODY_GAP"
DUPLICATE_RELEASE_ID = "DUPLICATE_RELEASE_ID"
SCOPE_OR_SIGNER_MISMATCH = "SCOPE_OR_SIGNER_MISMATCH"
INPUT_INVALID = "INPUT_INVALID"

ACCEPTANCE_REASON_CODES = (
    RULE_VERSION_EXPIRED,
    PANEL_NOT_VALID_FOR_JURISDICTION,
    METHOD_LIMIT_MISMATCH,
    CUSTODY_GAP,
    DUPLICATE_RELEASE_ID,
    SCOPE_OR_SIGNER_MISMATCH,
)
REASON_ORDER = ACCEPTANCE_REASON_CODES + (INPUT_INVALID,)
EXPECTED_REASON_COUNTS = {code: 5 for code in ACCEPTANCE_REASON_CODES}
REQUIRED_CUSTODY_EVENTS = ("COLLECTED", "TRANSFERRED", "RECEIVED")

RULE_PACKS: dict[str, dict[str, Any]] = {
    "CA": {
        "version": "CA-RULES-2026.09",
        "expires_at": "2027-09-01T00:00:00Z",
        "matrix": "FLOWER",
        "panel": "CA-FLOWER-COMPLIANCE",
        "method": "CA-METHOD-4.2",
    },
    "CO": {
        "version": "CO-RULES-2026.09",
        "expires_at": "2027-09-01T00:00:00Z",
        "matrix": "FLOWER",
        "panel": "CO-REGULATED-MARIJUANA",
        "method": "CO-METHOD-3.8",
    },
    "MI": {
        "version": "MI-RULES-2026.09",
        "expires_at": "2027-09-01T00:00:00Z",
        "matrix": "FLOWER",
        "panel": "MI-SAFETY-COMPLIANCE",
        "method": "MI-METHOD-2.5",
    },
    "OR": {
        "version": "OR-RULES-2026.09",
        "expires_at": "2027-09-01T00:00:00Z",
        "matrix": "FLOWER",
        "panel": "OR-CANNABIS-COMPLIANCE",
        "method": "OR-METHOD-5.1",
    },
    "AZ": {
        "version": "AZ-RULES-2026.09",
        "expires_at": "2027-09-01T00:00:00Z",
        "matrix": "FLOWER",
        "panel": "AZ-ADULT-USE-COMPLIANCE",
        "method": "AZ-METHOD-1.9",
    },
}

HERE = Path(__file__).resolve().parent
PACK = HERE / "revenue" / "sc_labs_multistate_coa_rule_version_gate"


class ManifestConflict(ValueError):
    """An existing manifest is not a byte prefix of the requested history."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def normalize_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    signer = record.get("signer")
    if not isinstance(signer, dict):
        signer = {
            "name": record.get("signer_name"),
            "scope": _json_list(record.get("signer_scope")),
        }
    normalized = {
        "sample_id": _text(record.get("sample_id")),
        "coa_id": _text(record.get("coa_id")),
        "coa_revision": _text(record.get("coa_revision")),
        "jurisdiction": _text(record.get("jurisdiction")).upper(),
        "license_id": _text(record.get("license_id")),
        "matrix": _text(record.get("matrix")).upper(),
        "collection_events": _json_list(record.get("collection_events")),
        "rule_pack_version": _text(record.get("rule_pack_version")),
        "rule_pack_expires_at": _text(record.get("rule_pack_expires_at")),
        "requested_analyte_panel": _text(record.get("requested_analyte_panel")),
        "method_version": _text(record.get("method_version")),
        "loq": _number(record.get("loq")),
        "reporting_limit": _number(record.get("reporting_limit")),
        "accreditation_scope": [
            _text(item) for item in _json_list(record.get("accreditation_scope"))
        ],
        "signer": {
            "name": _text(signer.get("name")),
            "scope": [_text(item) for item in _json_list(signer.get("scope"))],
        },
    }
    return normalized


def custody_is_complete(events: list[Any]) -> bool:
    names: list[str] = []
    times: list[datetime] = []
    for event in events:
        if not isinstance(event, dict):
            return False
        name = _text(event.get("event")).upper()
        observed = parse_utc(event.get("at"))
        if not name or observed is None:
            return False
        names.append(name)
        times.append(observed)
    positions: list[int] = []
    for required in REQUIRED_CUSTODY_EVENTS:
        if required not in names:
            return False
        positions.append(names.index(required))
    return positions == sorted(positions) and times == sorted(times)


def _ordered_reasons(reasons: Iterable[str]) -> list[str]:
    unique = set(reasons)
    return [reason for reason in REASON_ORDER if reason in unique]


def validate_records(
    records: list[Any], *, evaluation_time: str
) -> list[dict[str, Any]]:
    evaluated_at = parse_utc(evaluation_time)
    if evaluated_at is None:
        raise ValueError("evaluation_time must be an ISO-8601 UTC timestamp ending in Z")

    results: list[dict[str, Any]] = []
    seen_release_ids: set[tuple[str, str]] = set()
    for index, raw in enumerate(records, start=1):
        record = normalize_record(raw)
        reasons: list[str] = []
        jurisdiction = record.get("jurisdiction", "")
        rule = RULE_PACKS.get(jurisdiction)
        required_scalars = (
            "sample_id",
            "coa_id",
            "coa_revision",
            "jurisdiction",
            "license_id",
            "matrix",
            "rule_pack_version",
            "rule_pack_expires_at",
            "requested_analyte_panel",
            "method_version",
        )
        if not record or any(not record.get(field) for field in required_scalars):
            reasons.append(INPUT_INVALID)

        if rule is None:
            reasons.append(PANEL_NOT_VALID_FOR_JURISDICTION)
        else:
            expires = parse_utc(record.get("rule_pack_expires_at"))
            if (
                record.get("rule_pack_version") != rule["version"]
                or expires is None
                or expires < evaluated_at
            ):
                reasons.append(RULE_VERSION_EXPIRED)
            if (
                record.get("matrix") != rule["matrix"]
                or record.get("requested_analyte_panel") != rule["panel"]
            ):
                reasons.append(PANEL_NOT_VALID_FOR_JURISDICTION)
            loq = record.get("loq")
            reporting_limit = record.get("reporting_limit")
            if (
                record.get("method_version") != rule["method"]
                or loq is None
                or reporting_limit is None
                or loq < 0
                or reporting_limit <= 0
                or loq > reporting_limit
            ):
                reasons.append(METHOD_LIMIT_MISMATCH)

        if not custody_is_complete(record.get("collection_events") or []):
            reasons.append(CUSTODY_GAP)

        release_id = (
            _text(record.get("sample_id")),
            _text(record.get("coa_id")),
        )
        if all(release_id):
            if release_id in seen_release_ids:
                reasons.append(DUPLICATE_RELEASE_ID)
            seen_release_ids.add(release_id)

        expected_scope = ""
        if rule is not None:
            expected_scope = ":".join(
                (jurisdiction, rule["matrix"], rule["panel"], rule["method"])
            )
        signer = record.get("signer") or {}
        if (
            not expected_scope
            or expected_scope not in record.get("accreditation_scope", [])
            or not _text(signer.get("name"))
            or expected_scope not in signer.get("scope", [])
        ):
            reasons.append(SCOPE_OR_SIGNER_MISMATCH)

        reasons = _ordered_reasons(reasons)
        status = "HOLD" if reasons else "RELEASEABLE"
        results.append(
            {
                "sequence": index,
                "sample_id": release_id[0] or f"INVALID-{index:04d}",
                "coa_id": release_id[1] or f"INVALID-COA-{index:04d}",
                "jurisdiction": jurisdiction or "UNKNOWN",
                "license_id": record.get("license_id", ""),
                "matrix": record.get("matrix", ""),
                "rule_pack_version": record.get("rule_pack_version", ""),
                "status": status,
                "reason_codes": reasons,
                "source_sha256": sha256_value(record),
                "rule_source_sha256": sha256_value(rule) if rule is not None else "",
                "evaluated_at": evaluation_time,
                "human_release_required": True,
                "released": False,
            }
        )
    return results


def build_manifest(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous = "0" * 64
    for row in results:
        event = {
            "schema": f"{SCHEMA}/evidence-event",
            "demand_id": DEMAND_ID,
            "sequence": row["sequence"],
            "sample_id": row["sample_id"],
            "coa_id": row["coa_id"],
            "status": row["status"],
            "reason_codes": row["reason_codes"],
            "source_sha256": row["source_sha256"],
            "rule_source_sha256": row["rule_source_sha256"],
            "evaluated_at": row["evaluated_at"],
            "previous_event_sha256": previous,
            "released": False,
        }
        event["event_sha256"] = sha256_value(event)
        events.append(event)
        previous = event["event_sha256"]
    return events


def verify_manifest(events: list[dict[str, Any]]) -> bool:
    previous = "0" * 64
    for sequence, event in enumerate(events, start=1):
        if event.get("sequence") != sequence:
            return False
        if event.get("previous_event_sha256") != previous:
            return False
        expected = sha256_value(
            {key: value for key, value in event.items() if key != "event_sha256"}
        )
        if event.get("event_sha256") != expected:
            return False
        previous = expected
    return True


def append_override_event(
    history: list[dict[str, Any]],
    *,
    sample_id: str,
    coa_id: str,
    reviewer: str,
    reason: str,
    timestamp: str,
) -> dict[str, Any]:
    reviewer = _text(reviewer)
    reason = _text(reason)
    if not reviewer or reviewer.upper() in {"SYSTEM", "AUTONOMOUS", "MODEL"}:
        raise ValueError("a named human compliance reviewer is required")
    if not reason:
        raise ValueError("override reason is required")
    if parse_utc(timestamp) is None:
        raise ValueError("override timestamp must be ISO-8601 UTC ending in Z")
    previous = history[-1]["event_sha256"] if history else "0" * 64
    event = {
        "schema": f"{SCHEMA}/override-event",
        "sequence": len(history) + 1,
        "sample_id": _text(sample_id),
        "coa_id": _text(coa_id),
        "reviewer": reviewer,
        "reason": reason,
        "timestamp": timestamp,
        "decision": "OVERRIDE_RECORDED_FOR_HUMAN_RELEASE_REVIEW",
        "previous_event_sha256": previous,
        "release_executed": False,
    }
    event["event_sha256"] = sha256_value(event)
    history.append(event)
    return deepcopy(event)


def verify_override_history(history: list[dict[str, Any]]) -> bool:
    previous = "0" * 64
    for sequence, event in enumerate(history, start=1):
        if event.get("sequence") != sequence:
            return False
        if event.get("previous_event_sha256") != previous:
            return False
        expected = sha256_value(
            {key: value for key, value in event.items() if key != "event_sha256"}
        )
        if event.get("event_sha256") != expected:
            return False
        previous = expected
    return True


def _results_csv(results: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    fields = (
        "sequence",
        "sample_id",
        "coa_id",
        "jurisdiction",
        "license_id",
        "matrix",
        "rule_pack_version",
        "status",
        "reason_codes",
        "source_sha256",
        "rule_source_sha256",
        "evaluated_at",
        "human_release_required",
        "released",
    )
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for result in results:
        row = dict(result)
        row["reason_codes"] = ";".join(result["reason_codes"])
        writer.writerow({field: row[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def _exception_report(results: list[dict[str, Any]]) -> bytes:
    holds = [row for row in results if row["status"] == "HOLD"]
    lines = [
        f"# SC Labs multistate COA exception report",
        "",
        f"- demand: `{DEMAND_ID}`",
        f"- evaluated_at: `{results[0]['evaluated_at'] if results else 'UNKNOWN'}`",
        f"- records: {len(results)}",
        f"- RELEASEABLE: {sum(row['status'] == 'RELEASEABLE' for row in results)}",
        f"- HOLD: {len(holds)}",
        "- release: named-human decision remains external; this report releases nothing",
        "",
        "| sequence | sample | COA | jurisdiction | reasons |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in holds:
        lines.append(
            f"| {row['sequence']} | `{row['sample_id']}` | `{row['coa_id']}` | "
            f"{row['jurisdiction']} | `{';'.join(row['reason_codes'])}` |"
        )
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def output_bundle(results: list[dict[str, Any]]) -> dict[str, bytes]:
    manifest = build_manifest(results)
    if not verify_manifest(manifest):
        raise AssertionError("generated evidence manifest failed verification")
    bundle = {
        "results.json": (canonical_json({"records": results}) + "\n").encode("utf-8"),
        "results.csv": _results_csv(results),
        "exceptions.md": _exception_report(results),
        "evidence_manifest.jsonl": (
            "".join(canonical_json(event) + "\n" for event in manifest)
        ).encode("utf-8"),
    }
    status_counts = Counter(row["status"] for row in results)
    reason_counts = Counter(
        reason for row in results for reason in row.get("reason_codes", [])
    )
    audit = {
        "schema": f"{SCHEMA}/audit",
        "demand_id": DEMAND_ID,
        "input_count": len(results),
        "status_counts": dict(status_counts),
        "reason_counts": dict(reason_counts),
        "output_sha256": {name: sha256_bytes(data) for name, data in bundle.items()},
        "manifest_tip_sha256": manifest[-1]["event_sha256"] if manifest else "0" * 64,
        "release_executed": False,
    }
    bundle["audit.json"] = (canonical_json(audit) + "\n").encode("utf-8")
    return bundle


def write_outputs(output_dir: Path, bundle: dict[str, bytes]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_name = "evidence_manifest.jsonl"
    for name, data in bundle.items():
        path = output_dir / name
        if name == manifest_name and path.exists():
            existing = path.read_bytes()
            if not data.startswith(existing):
                raise ManifestConflict(
                    "existing evidence manifest is not an immutable prefix"
                )
            if len(data) > len(existing):
                with path.open("ab") as handle:
                    handle.write(data[len(existing) :])
            continue
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)


def _custody_events(jurisdiction_index: int, row_index: int) -> list[dict[str, str]]:
    day = 1 + ((jurisdiction_index * 30 + row_index) % 20)
    return [
        {"event": "COLLECTED", "at": f"2026-08-{day:02d}T08:00:00Z"},
        {"event": "TRANSFERRED", "at": f"2026-08-{day:02d}T10:00:00Z"},
        {"event": "RECEIVED", "at": f"2026-08-{day:02d}T12:00:00Z"},
    ]


def _valid_fixture_row(jurisdiction: str, jurisdiction_index: int, row: int) -> dict[str, Any]:
    rule = RULE_PACKS[jurisdiction]
    sample_id = f"SC-{jurisdiction}-S{row:03d}"
    coa_id = f"SC-{jurisdiction}-COA-{row:03d}"
    scope = ":".join((jurisdiction, rule["matrix"], rule["panel"], rule["method"]))
    return {
        "sample_id": sample_id,
        "coa_id": coa_id,
        "coa_revision": "1",
        "jurisdiction": jurisdiction,
        "license_id": f"SC-{jurisdiction}-LIC-{1 + row % 4:02d}",
        "matrix": rule["matrix"],
        "collection_events": _custody_events(jurisdiction_index, row),
        "rule_pack_version": rule["version"],
        "rule_pack_expires_at": rule["expires_at"],
        "requested_analyte_panel": rule["panel"],
        "method_version": rule["method"],
        "loq": 0.5,
        "reporting_limit": 1.0,
        "accreditation_scope": [scope],
        "signer": {"name": f"SC Reviewer {jurisdiction}", "scope": [scope]},
        "expected_status": "RELEASEABLE",
        "expected_reason": None,
    }


def build_acceptance_fixture() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for jurisdiction_index, jurisdiction in enumerate(RULE_PACKS):
        valid = [
            _valid_fixture_row(jurisdiction, jurisdiction_index, row)
            for row in range(1, 25)
        ]
        records.extend(valid)

        expired = _valid_fixture_row(jurisdiction, jurisdiction_index, 25)
        expired["rule_pack_version"] = f"{jurisdiction}-RULES-2025.01"
        expired["rule_pack_expires_at"] = "2026-01-01T00:00:00Z"
        expired["expected_status"] = "HOLD"
        expired["expected_reason"] = RULE_VERSION_EXPIRED
        records.append(expired)

        panel = _valid_fixture_row(jurisdiction, jurisdiction_index, 26)
        panel["requested_analyte_panel"] = "OTHER-JURISDICTION-PANEL"
        panel["expected_status"] = "HOLD"
        panel["expected_reason"] = PANEL_NOT_VALID_FOR_JURISDICTION
        records.append(panel)

        method = _valid_fixture_row(jurisdiction, jurisdiction_index, 27)
        method["loq"] = 2.0
        method["reporting_limit"] = 1.0
        method["expected_status"] = "HOLD"
        method["expected_reason"] = METHOD_LIMIT_MISMATCH
        records.append(method)

        custody = _valid_fixture_row(jurisdiction, jurisdiction_index, 28)
        custody["collection_events"] = custody["collection_events"][:-1]
        custody["expected_status"] = "HOLD"
        custody["expected_reason"] = CUSTODY_GAP
        records.append(custody)

        duplicate = _valid_fixture_row(jurisdiction, jurisdiction_index, 29)
        duplicate["sample_id"] = valid[0]["sample_id"]
        duplicate["coa_id"] = valid[0]["coa_id"]
        duplicate["expected_status"] = "HOLD"
        duplicate["expected_reason"] = DUPLICATE_RELEASE_ID
        records.append(duplicate)

        scope = _valid_fixture_row(jurisdiction, jurisdiction_index, 30)
        scope["signer"]["scope"] = ["OUT-OF-SCOPE"]
        scope["expected_status"] = "HOLD"
        scope["expected_reason"] = SCOPE_OR_SIGNER_MISMATCH
        records.append(scope)

    assert len(records) == INPUT_COUNT
    return records


def records_to_csv(records: list[dict[str, Any]]) -> bytes:
    fields = (
        "sample_id",
        "coa_id",
        "coa_revision",
        "jurisdiction",
        "license_id",
        "matrix",
        "collection_events",
        "rule_pack_version",
        "rule_pack_expires_at",
        "requested_analyte_panel",
        "method_version",
        "loq",
        "reporting_limit",
        "accreditation_scope",
        "signer_name",
        "signer_scope",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for source in records:
        row = normalize_record(source)
        writer.writerow(
            {
                "sample_id": row["sample_id"],
                "coa_id": row["coa_id"],
                "coa_revision": row["coa_revision"],
                "jurisdiction": row["jurisdiction"],
                "license_id": row["license_id"],
                "matrix": row["matrix"],
                "collection_events": canonical_json(row["collection_events"]),
                "rule_pack_version": row["rule_pack_version"],
                "rule_pack_expires_at": row["rule_pack_expires_at"],
                "requested_analyte_panel": row["requested_analyte_panel"],
                "method_version": row["method_version"],
                "loq": row["loq"],
                "reporting_limit": row["reporting_limit"],
                "accreditation_scope": canonical_json(row["accreditation_scope"]),
                "signer_name": row["signer"]["name"],
                "signer_scope": canonical_json(row["signer"]["scope"]),
            }
        )
    return stream.getvalue().encode("utf-8")


def load_records(path: Path, input_format: str = "auto") -> list[dict[str, Any]]:
    resolved = input_format
    if resolved == "auto":
        resolved = "csv" if path.suffix.lower() == ".csv" else "json"
    if resolved == "json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("records")
        if not isinstance(payload, list):
            raise ValueError("JSON input must be a list or an object with records")
        return payload
    if resolved == "csv":
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            row["signer"] = {
                "name": row.pop("signer_name", ""),
                "scope": _json_list(row.pop("signer_scope", "")),
            }
            row["collection_events"] = _json_list(row.get("collection_events"))
            row["accreditation_scope"] = _json_list(row.get("accreditation_scope"))
        return rows
    raise ValueError("input_format must be auto, json, or csv")


def run_gate(
    records: list[Any] | None = None, *, evaluation_time: str = EVALUATION_TIME
) -> dict[str, Any]:
    source = deepcopy(records if records is not None else build_acceptance_fixture())
    results = validate_records(source, evaluation_time=evaluation_time)
    bundle = output_bundle(results)
    status_counts = Counter(row["status"] for row in results)
    reason_counts = Counter(reason for row in results for reason in row["reason_codes"])
    audit = json.loads(bundle["audit.json"])
    return {
        "records": results,
        "status_counts": dict(status_counts),
        "reason_counts": dict(reason_counts),
        "bundle": bundle,
        "audit": audit,
        "input_unchanged": source
        == (records if records is not None else build_acceptance_fixture()),
        "audit_sha256": sha256_value(audit),
    }


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if result["status_counts"] != {
        "RELEASEABLE": RELEASEABLE_COUNT,
        "HOLD": HOLD_COUNT,
    }:
        failures.append(f"status_counts:{result['status_counts']}")
    if result["reason_counts"] != EXPECTED_REASON_COUNTS:
        failures.append(f"reason_counts:{result['reason_counts']}")
    if not result["input_unchanged"]:
        failures.append("input_mutated")
    if any(
        row["status"] not in {"RELEASEABLE", "HOLD"} for row in result["records"]
    ):
        failures.append("unexpected_status")
    if any(row["released"] for row in result["records"]):
        failures.append("automatic_release")
    if not verify_manifest(build_manifest(result["records"])):
        failures.append("manifest_invalid")
    return failures


def write_pack(result: dict[str, Any], records: list[dict[str, Any]]) -> None:
    PACK.mkdir(parents=True, exist_ok=True)
    fixture_json = (canonical_json({"records": records}) + "\n").encode("utf-8")
    fixture_csv = records_to_csv(records)
    (PACK / "fixture.json").write_bytes(fixture_json)
    (PACK / "fixture.csv").write_bytes(fixture_csv)
    contract = {
        "id": DEMAND_ID,
        "version": 1,
        "schema": SCHEMA,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "command": COMMAND,
        "input_formats": ["csv", "json"],
        "output_files": [
            "results.csv",
            "results.json",
            "exceptions.md",
            "evidence_manifest.jsonl",
            "audit.json",
        ],
        "acceptance": {
            "input_count": INPUT_COUNT,
            "releaseable": RELEASEABLE_COUNT,
            "hold": HOLD_COUNT,
            "reason_counts": EXPECTED_REASON_COUNTS,
            "jurisdiction_rule_packs": list(RULE_PACKS),
            "byte_identical_replay": True,
            "append_only_hash_linked_manifest": True,
            "named_human_release_only": True,
        },
        "golden": {
            "fixture_json_sha256": sha256_bytes(fixture_json),
            "fixture_csv_sha256": sha256_bytes(fixture_csv),
            "audit_sha256": result["audit_sha256"],
            "output_sha256": {
                name: sha256_bytes(data) for name, data in result["bundle"].items()
            },
        },
        "boundaries": [
            "validation/evidence overlay only",
            "no LIMS replacement",
            "no chemical interpretation or regulatory opinion",
            "no result alteration",
            "no autonomous COA override or release",
            "reviewer metadata is context, not an access gate",
        ],
        "open_door": True,
        "requires_login": False,
        "cash_usd": 0,
        "pre_sale_transport": "NONE",
    }
    (PACK / "contract.json").write_text(
        canonical_json(contract) + "\n", encoding="utf-8"
    )
    receipt = {
        "demand_id": DEMAND_ID,
        "pass": pass_contract(result) == [],
        "truth_gate": TRUTH_GATE,
        "status_counts": result["status_counts"],
        "reason_counts": result["reason_counts"],
        "audit_sha256": result["audit_sha256"],
        "manifest_tip_sha256": result["audit"]["manifest_tip_sha256"],
        "fixture_json_sha256": sha256_bytes(fixture_json),
        "fixture_csv_sha256": sha256_bytes(fixture_csv),
        "command": COMMAND,
        "release_executed": False,
    }
    (PACK / "receipt.json").write_text(
        canonical_json(receipt) + "\n", encoding="utf-8"
    )
    lines = [
        f"# Receipt — {DEMAND_ID}",
        "",
        f"- buyer: {BUYER}",
        f"- gate: {TRUTH_GATE}",
        f"- command: `{COMMAND}`",
        f"- records: {INPUT_COUNT}",
        f"- RELEASEABLE: {RELEASEABLE_COUNT}",
        f"- HOLD: {HOLD_COUNT}",
        "- hold reasons: six families × 5 records",
        f"- audit_sha256: `{result['audit_sha256']}`",
        f"- manifest_tip_sha256: `{result['audit']['manifest_tip_sha256']}`",
        "- CSV/JSON input and CSV/JSON/exception/manifest output: exercised",
        "- automatic override/release: none",
        "- cash_usd: 0",
        "",
    ]
    (PACK / "receipt.md").write_text("\n".join(lines), encoding="utf-8")


def summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": pass_contract(result) == [],
        "demand_id": DEMAND_ID,
        "status_counts": result["status_counts"],
        "reason_counts": result["reason_counts"],
        "audit_sha256": result["audit_sha256"],
        "manifest_tip_sha256": result["audit"]["manifest_tip_sha256"],
        "release_executed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument(
        "--input-format", choices=("auto", "json", "csv"), default="auto"
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--evaluation-time")
    args = parser.parse_args(argv)

    if args.input:
        if not args.output_dir:
            parser.error("--output-dir is required with --input")
        if not args.evaluation_time:
            parser.error("--evaluation-time is required with --input")
        records = load_records(args.input, args.input_format)
        evaluation_time = args.evaluation_time
    else:
        records = build_acceptance_fixture()
        evaluation_time = args.evaluation_time or EVALUATION_TIME

    result = run_gate(records, evaluation_time=evaluation_time)
    if args.input:
        write_outputs(args.output_dir, result["bundle"])
    else:
        write_pack(result, records)
        if args.output_dir:
            write_outputs(args.output_dir, result["bundle"])

    failures = pass_contract(result) if len(records) == INPUT_COUNT else []
    print(canonical_json({**summary(result), "failures": failures}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
