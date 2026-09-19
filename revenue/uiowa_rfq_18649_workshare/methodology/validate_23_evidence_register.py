#!/usr/bin/env python3
"""Structural validator for the UIOWA-023 synthetic evidence register."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REQUIRED = {
    "evidence_id", "observation_id", "finding_id", "group", "area",
    "source_type", "source_ref", "custodian_or_owner", "content_digest",
    "captured_at", "represented_period", "claim", "scope_limit", "directness",
    "recency", "representativeness", "corroboration", "evidence_state",
    "confidence", "conflict_group", "universe_definition",
    "enumerator_authority", "completeness_basis", "follow_up",
}
GROUPS = {"ESS", "RIS", "IAM"}
AREAS = {"SD", "SEC", "DEP", "AI"}
DIRECTNESS = {"DIRECT", "NEAR_DIRECT", "INDIRECT"}
RECENCY = {"CURRENT", "AGING", "STALE", "UNKNOWN"}
REPRESENTATIVENESS = {
    "POPULATION_BOUNDED", "SAMPLED", "SINGLE", "POPULATION_UNKNOWN", "UNKNOWN"
}
CORROBORATION = {
    "INDEPENDENT", "SAME_SYSTEM", "NO_CORROBORATION", "CONTRADICTED"
}
STATES = {
    "SUPPORTING", "CONFLICTING", "EVIDENCE_OF_ABSENCE", "NO_EVIDENCE_OBSERVED"
}
CONFIDENCE = {"HIGH", "MODERATE", "LOW", "UNRESOLVED", "NOT_EVIDENCED"}
UNKNOWN_CUSTODIAN = "UNKNOWN_SYNTHETIC_CUSTODIAN"
NOT_RETAINED_DIGEST = "NOT_RETAINED_SYNTHETIC_SOURCE"

EV_RE = re.compile(r"^EV-SYN-(ESS|RIS|IAM)-(SD|SEC|DEP|AI)-[A-Z]+-[0-9]{3}$")
OBS_RE = re.compile(r"^OBS-SYN-(ESS|RIS|IAM)-(SD|SEC|DEP|AI)-[0-9]{3}$")
FND_RE = re.compile(r"^FND-SYN-(ESS|RIS|IAM)-(SD|SEC|DEP|AI)-[0-9]{3}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


def _enum(row_num, field, value, allowed, errors):
    if value not in allowed:
        errors.append(f"row {row_num}: {field}={value!r} is invalid")


def validate(path: Path) -> list[str]:
    errors = []
    seen = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            return [f"missing required columns: {sorted(missing)}"]

        for row_num, row in enumerate(reader, start=2):
            evidence_id = row["evidence_id"].strip()
            observation_id = row["observation_id"].strip()
            finding_id = row["finding_id"].strip()

            if evidence_id in seen:
                errors.append(f"row {row_num}: duplicate evidence_id {evidence_id}")
            seen.add(evidence_id)

            if not EV_RE.fullmatch(evidence_id):
                errors.append(f"row {row_num}: malformed evidence_id {evidence_id}")
            if not OBS_RE.fullmatch(observation_id):
                errors.append(f"row {row_num}: malformed observation_id {observation_id}")
            if not FND_RE.fullmatch(finding_id):
                errors.append(f"row {row_num}: malformed finding_id {finding_id}")

            _enum(row_num, "group", row["group"], GROUPS, errors)
            _enum(row_num, "area", row["area"], AREAS, errors)
            _enum(row_num, "directness", row["directness"], DIRECTNESS, errors)
            _enum(row_num, "recency", row["recency"], RECENCY, errors)
            _enum(row_num, "representativeness", row["representativeness"], REPRESENTATIVENESS, errors)
            _enum(row_num, "corroboration", row["corroboration"], CORROBORATION, errors)
            _enum(row_num, "evidence_state", row["evidence_state"], STATES, errors)
            _enum(row_num, "confidence", row["confidence"], CONFIDENCE, errors)

            for field in (
                "source_type", "source_ref", "custodian_or_owner", "content_digest",
                "captured_at", "represented_period", "claim", "scope_limit", "follow_up"
            ):
                if not row[field].strip():
                    errors.append(f"row {row_num}: {field} must not be blank")

            content_digest = row["content_digest"].strip()
            if (
                content_digest
                and content_digest != NOT_RETAINED_DIGEST
                and not SHA256_RE.fullmatch(content_digest)
            ):
                errors.append(
                    f"row {row_num}: content_digest must be sha256:<64 hex> "
                    f"or {NOT_RETAINED_DIGEST}"
                )

            if row["recency"] == "STALE" and row["confidence"] == "HIGH":
                errors.append(f"row {row_num}: stale evidence cannot be HIGH confidence")

            if row["evidence_state"] == "CONFLICTING":
                if row["confidence"] != "UNRESOLVED":
                    errors.append(f"row {row_num}: CONFLICTING evidence must be UNRESOLVED")
                if not row["conflict_group"].strip():
                    errors.append(f"row {row_num}: CONFLICTING evidence requires conflict_group")

            if row["evidence_state"] == "NO_EVIDENCE_OBSERVED":
                if row["confidence"] != "NOT_EVIDENCED":
                    errors.append(
                        f"row {row_num}: NO_EVIDENCE_OBSERVED must use NOT_EVIDENCED confidence"
                    )

            if row["evidence_state"] == "EVIDENCE_OF_ABSENCE":
                for field in (
                    "universe_definition", "enumerator_authority", "completeness_basis"
                ):
                    if not row[field].strip():
                        errors.append(
                            f"row {row_num}: EVIDENCE_OF_ABSENCE requires {field}"
                        )

            group = row["group"]
            area = row["area"]
            if group and area:
                marker = f"-{group}-{area}-"
                if marker not in evidence_id:
                    errors.append(f"row {row_num}: evidence_id scope mismatch")
                if marker not in observation_id:
                    errors.append(f"row {row_num}: observation_id scope mismatch")
                if marker not in finding_id:
                    errors.append(f"row {row_num}: finding_id scope mismatch")

    return errors


def main(argv) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).with_name(
        "23-synthetic-evidence-register.csv"
    )
    errors = validate(path)
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    observations = {row["observation_id"] for row in rows}
    findings = {row["finding_id"] for row in rows}
    print(f"OK rows={len(rows)} observations={len(observations)} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
