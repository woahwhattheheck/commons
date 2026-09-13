from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from .model import (
    ACCESSIBILITY,
    ACCESSIBILITY_EVIDENCE_FAILURE,
    DEFECT_CODES,
    HOLD,
    INTEGRATION,
    INTEGRATION_FIXTURE_MISMATCH,
    LINK_DOCUMENT,
    LINK_OR_DOCUMENT_FAILURE,
    MIGRATION,
    MIGRATION_DIGEST_MISMATCH,
    PACKET_READY_FOR_HUMAN_UAT,
    PASS,
    RECORD_SCHEMA,
    REDIRECT,
    REDIRECT_CHAIN_INVALID,
    RESTORE,
    RESTORE_EVIDENCE_INVALID,
    ROLE_PERMISSION,
    ROLE_PERMISSION_DRIFT,
    SCHEMA,
    canonical_bytes,
    digest,
    normalize_row,
    parse_time,
)


def _age_days(observed_at: str, as_of: datetime) -> float:
    observed = parse_time(observed_at, "observed_at")
    return (as_of - observed).total_seconds() / 86400.0


def defect_codes(row: Mapping[str, Any], *, as_of: datetime) -> list[str]:
    details = row["details"]
    kind = row["kind"]
    codes: list[str] = []
    if kind == MIGRATION:
        if details["expected_content_sha256"] != details["observed_content_sha256"]:
            codes.append(MIGRATION_DIGEST_MISMATCH)
    elif kind == REDIRECT:
        if (
            details["http_status"] not in {301, 308}
            or details["hop_count"] != 1
            or details["expected_target_path"] != details["observed_target_path"]
        ):
            codes.append(REDIRECT_CHAIN_INVALID)
    elif kind == LINK_DOCUMENT:
        if (
            details["http_status"] != 200
            or details["document_expected_sha256"] != details["document_observed_sha256"]
        ):
            codes.append(LINK_OR_DOCUMENT_FAILURE)
    elif kind == ACCESSIBILITY:
        if (
            details["critical_count"] != 0
            or details["serious_count"] != 0
            or _age_days(row["observed_at"], as_of) > details["max_age_days"]
        ):
            codes.append(ACCESSIBILITY_EVIDENCE_FAILURE)
    elif kind == INTEGRATION:
        if details["expected_result_sha256"] != details["observed_result_sha256"]:
            codes.append(INTEGRATION_FIXTURE_MISMATCH)
    elif kind == ROLE_PERMISSION:
        if details["expected_permissions"] != details["observed_permissions"]:
            codes.append(ROLE_PERMISSION_DRIFT)
    elif kind == RESTORE:
        if (
            details["backup_sha256"] != details["restored_sha256"]
            or details["restore_exit_code"] != 0
            or details["expected_item_count"] != details["restored_item_count"]
        ):
            codes.append(RESTORE_EVIDENCE_INVALID)
    return [code for code in DEFECT_CODES if code in codes]


def make_record(row: Mapping[str, Any], codes: Sequence[str], previous: str) -> dict[str, Any]:
    record = {
        "schema": RECORD_SCHEMA,
        **dict(row),
        "decision": PASS if not codes else HOLD,
        "codes": list(codes),
        "input_sha256": digest(canonical_bytes(row)),
        "previous_record_sha256": previous,
    }
    record["record_sha256"] = digest(canonical_bytes(record))
    return record


def render_markdown(manifest: Mapping[str, Any]) -> bytes:
    summary = manifest["summary"]
    lines = [
        "# Municipal website acceptance evidence packet",
        "",
        f"Release state: **{summary['release_state']}**",
        f"Evidence checks: **{summary['check_count']}**",
        f"PASS: **{summary['pass_count']}**",
        f"HOLD: **{summary['hold_count']}**",
        "",
        "This packet is reproducible QA evidence for human UAT. It is not an accessibility certification,",
        "compliance opinion, hosting acceptance, contract acceptance, or production release authorization.",
        "",
        "## Defect counts",
        "",
    ]
    for code in DEFECT_CODES:
        lines.append(f"- `{code}`: {summary['defect_counts'][code]}")
    held = [record for record in manifest["records"] if record["decision"] == HOLD]
    lines.extend(["", "## Held evidence", ""])
    if not held:
        lines.append("- None")
    else:
        for record in held:
            lines.append(
                f"- `{record['evidence_id']}` / `{record['kind']}` / `{record['resource_id']}`: "
                + ", ".join(f"`{code}`" for code in record["codes"])
            )
    return ("\n".join(lines) + "\n").encode("utf-8")


@dataclass(frozen=True)
class GateArtifacts:
    manifest: dict[str, Any]
    json_bytes: bytes
    markdown_bytes: bytes
    manifest_sha256: str
    markdown_sha256: str

    @property
    def pass_count(self) -> int:
        return int(self.manifest["summary"]["pass_count"])

    @property
    def hold_count(self) -> int:
        return int(self.manifest["summary"]["hold_count"])


def build_gate_artifacts(
    rows: Iterable[Mapping[str, Any]],
    *,
    as_of: datetime,
) -> GateArtifacts:
    if as_of.tzinfo is None:
        raise ValueError("as_of: timezone required")
    as_of = as_of.astimezone(timezone.utc)
    by_id: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = normalize_row(raw, as_of=as_of)
        existing = by_id.get(row["evidence_id"])
        if existing is None:
            by_id[row["evidence_id"]] = row
        elif existing != row:
            raise ValueError(f"conflicting duplicate evidence_id: {row['evidence_id']}")
    normalized = sorted(by_id.values(), key=lambda row: (row["sequence"], row["evidence_id"]))
    sequences = [row["sequence"] for row in normalized]
    if len(sequences) != len(set(sequences)):
        raise ValueError("duplicate sequence")

    counts = {code: 0 for code in DEFECT_CODES}
    records: list[dict[str, Any]] = []
    previous = "0" * 64
    for row in normalized:
        codes = defect_codes(row, as_of=as_of)
        for code in codes:
            counts[code] += 1
        record = make_record(row, codes, previous)
        records.append(record)
        previous = record["record_sha256"]
    passed = sum(record["decision"] == PASS for record in records)
    held = len(records) - passed
    manifest = {
        "schema": SCHEMA,
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "authority": {
            "human_uat_required": True,
            "accessibility_certification_authorized": False,
            "compliance_certification_authorized": False,
            "production_release_authorized": False,
            "buyer_acceptance_claimed": False,
            "contract_authority": False,
            "payment_authority": False,
            "revenue_claimed": False,
        },
        "summary": {
            "check_count": len(records),
            "pass_count": passed,
            "hold_count": held,
            "release_state": PACKET_READY_FOR_HUMAN_UAT if held == 0 else HOLD,
            "defect_counts": counts,
            "last_record_sha256": previous,
        },
        "records": records,
    }
    payload = canonical_bytes(manifest)
    markdown = render_markdown(manifest)
    return GateArtifacts(manifest, payload, markdown, digest(payload), digest(markdown))


def verify_gate_artifacts(
    json_bytes: bytes,
    markdown_bytes: bytes,
    *,
    manifest_sha256: str,
    markdown_sha256: str,
) -> bool:
    if digest(json_bytes) != manifest_sha256 or digest(markdown_bytes) != markdown_sha256:
        return False
    try:
        manifest = json.loads(json_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if canonical_bytes(manifest) != json_bytes or manifest.get("schema") != SCHEMA:
        return False
    if set(manifest) != {"schema", "as_of", "authority", "summary", "records"}:
        return False
    if manifest["authority"] != {
        "human_uat_required": True,
        "accessibility_certification_authorized": False,
        "compliance_certification_authorized": False,
        "production_release_authorized": False,
        "buyer_acceptance_claimed": False,
        "contract_authority": False,
        "payment_authority": False,
        "revenue_claimed": False,
    }:
        return False
    try:
        as_of = parse_time(manifest["as_of"], "as_of")
    except ValueError:
        return False
    records = manifest.get("records")
    summary = manifest.get("summary")
    if not isinstance(records, list) or not isinstance(summary, dict):
        return False
    expected_summary_keys = {
        "check_count", "pass_count", "hold_count", "release_state", "defect_counts", "last_record_sha256"
    }
    if set(summary) != expected_summary_keys:
        return False
    counts = {code: 0 for code in DEFECT_CODES}
    previous = "0" * 64
    ids: set[str] = set()
    sequences: set[int] = set()
    passed = 0
    for record in records:
        if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA:
            return False
        if record["previous_record_sha256"] != previous:
            return False
        unsigned = dict(record)
        recorded_hash = unsigned.pop("record_sha256", None)
        if not isinstance(recorded_hash, str) or digest(canonical_bytes(unsigned)) != recorded_hash:
            return False
        if record["evidence_id"] in ids or record["sequence"] in sequences:
            return False
        ids.add(record["evidence_id"])
        sequences.add(record["sequence"])
        base_row = {
            key: record[key]
            for key in (
                "sequence", "evidence_id", "kind", "resource_id", "source_ref",
                "observed_at", "source_snapshot_sha256", "details"
            )
        }
        try:
            normalized = normalize_row(base_row, as_of=as_of)
        except ValueError:
            return False
        if normalized != base_row:
            return False
        codes = defect_codes(base_row, as_of=as_of)
        if record.get("codes") != codes:
            return False
        expected_decision = PASS if not codes else HOLD
        if record.get("decision") != expected_decision:
            return False
        if record.get("input_sha256") != digest(canonical_bytes(base_row)):
            return False
        for code in codes:
            counts[code] += 1
        passed += expected_decision == PASS
        previous = recorded_hash
    held = len(records) - passed
    expected_summary = {
        "check_count": len(records),
        "pass_count": passed,
        "hold_count": held,
        "release_state": PACKET_READY_FOR_HUMAN_UAT if held == 0 else HOLD,
        "defect_counts": counts,
        "last_record_sha256": previous,
    }
    return summary == expected_summary and render_markdown(manifest) == markdown_bytes
