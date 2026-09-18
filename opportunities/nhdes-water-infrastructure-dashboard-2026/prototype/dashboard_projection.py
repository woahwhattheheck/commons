#!/usr/bin/env python3
"""Deterministic, fail-closed projection core for the NHDES dashboard prototype.

The prototype intentionally accepts synthetic/test data only. Buyer data is not bundled.
Money is represented as integer cents; coordinates are decimal strings; all output is
canonically ordered so the same input bytes produce the same projection bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

PROGRAMS = {"ARPA", "BIL", "DWSRF", "CWSRF", "OTHER"}
FUNDING_KINDS = {"grant", "loan", "mixed"}
PROJECT_TYPES = {
    "drinking_water", "wastewater", "stormwater", "dam", "asset_management",
    "planning", "cybersecurity", "energy", "other",
}
NH_LAT = (Decimal("42.69"), Decimal("45.31"))
NH_LON = (Decimal("-72.56"), Decimal("-70.60"))


class DataError(ValueError):
    pass


def _parse_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise DataError(f"non-finite JSON constant is forbidden: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal, parse_int=int, parse_constant=reject_constant)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DataError(f"{field} must be decimal-compatible") from exc
    if not d.is_finite():
        raise DataError(f"{field} must be finite")
    return d


def _text(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{field} must be non-empty text")
    return value.strip()


def validate_project(row: Any, seen: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise DataError("each project must be an object")
    project_id = _text(row, "project_id")
    if project_id in seen:
        raise DataError(f"duplicate project_id: {project_id}")
    seen.add(project_id)
    town = _text(row, "town")
    program = _text(row, "program").upper()
    if program not in PROGRAMS:
        raise DataError(f"unsupported program: {program}")
    funding_kind = _text(row, "funding_kind").lower()
    if funding_kind not in FUNDING_KINDS:
        raise DataError(f"unsupported funding_kind: {funding_kind}")
    project_type = _text(row, "project_type").lower()
    if project_type not in PROJECT_TYPES:
        raise DataError(f"unsupported project_type: {project_type}")
    cents = row.get("funding_cents")
    if isinstance(cents, bool) or not isinstance(cents, int) or cents < 0:
        raise DataError("funding_cents must be a non-negative integer")
    year = row.get("source_year")
    if isinstance(year, bool) or not isinstance(year, int) or not (1980 <= year <= 2100):
        raise DataError("source_year must be a plausible integer year")
    lat = _decimal(row.get("latitude"), "latitude")
    lon = _decimal(row.get("longitude"), "longitude")
    if not (NH_LAT[0] <= lat <= NH_LAT[1]):
        raise DataError(f"latitude outside NH validation envelope: {lat}")
    if not (NH_LON[0] <= lon <= NH_LON[1]):
        raise DataError(f"longitude outside NH validation envelope: {lon}")
    narrative = _text(row, "narrative")
    if len(narrative) > 4000:
        raise DataError("narrative exceeds prototype safety limit")
    media = row.get("media", [])
    if not isinstance(media, list):
        raise DataError("media must be an array")
    normalized_media = []
    for idx, item in enumerate(media):
        if not isinstance(item, dict):
            raise DataError(f"media[{idx}] must be an object")
        url = _text(item, "url")
        alt = _text(item, "alt")
        if not (url.startswith("https://") or url.startswith("http://")):
            raise DataError(f"media[{idx}].url must be http(s)")
        if len(alt) > 500:
            raise DataError(f"media[{idx}].alt is too long")
        normalized_media.append({"url": url, "alt": alt})
    return {
        "project_id": project_id, "town": town, "program": program,
        "funding_kind": funding_kind, "project_type": project_type,
        "funding_cents": cents, "source_year": year,
        "latitude": format(lat, "f"), "longitude": format(lon, "f"),
        "narrative": narrative, "media": normalized_media,
    }


def build_projection(raw_bytes: bytes, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list):
        raise DataError("top-level input must be an array of project objects")
    if not payload:
        raise DataError("at least one project is required")
    seen: set[str] = set()
    projects = [validate_project(row, seen) for row in payload]
    projects.sort(key=lambda p: p["project_id"])
    by_program: dict[str, int] = defaultdict(int)
    by_town: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    grant_cents = loan_cents = mixed_cents = total_cents = 0
    for p in projects:
        cents = p["funding_cents"]
        total_cents += cents
        by_program[p["program"]] += cents
        by_town[p["town"]] += cents
        by_type[p["project_type"]] += cents
        if p["funding_kind"] == "grant": grant_cents += cents
        elif p["funding_kind"] == "loan": loan_cents += cents
        else: mixed_cents += cents
    return {
        "schema_version": 1,
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "project_count": len(projects),
        "total_funding_cents": total_cents,
        "funding_kind_totals_cents": {"grant": grant_cents, "loan": loan_cents, "mixed": mixed_cents},
        "program_totals_cents": dict(sorted(by_program.items())),
        "town_totals_cents": dict(sorted(by_town.items(), key=lambda kv: kv[0].casefold())),
        "project_type_totals_cents": dict(sorted(by_type.items())),
        "projects": projects,
    }


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    try:
        payload = _parse_json(args.input)
        projection = build_projection(raw, payload)
    except (DataError, OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(projection))
    print(f"OK: {projection['project_count']} projects -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
