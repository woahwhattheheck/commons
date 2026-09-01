#!/usr/bin/env python3
"""Synthetic MGA Alabama materials-program qualification LIMS.

Demand: mga-alabama-materials-program-lims-01
Buyer pairing: Marshall Houston / MGA Research

This fail-closed fixture engine binds request, specimen/coupon, and
conditioning-window evidence to a controlled lab/method/version/fixture
and environment setpoint, then to a raw value/source hash and a
review-stage qualification packet. It has no live adapter and performs
no production write or automatic packet release.

Materials coupons and qualification metadata only. No vehicle, weapons,
propulsion, mission, or controlled-design data.

Official acceptance:
    python test_mga_alabama_materials_program_lims.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

DEMAND_ID = "mga-alabama-materials-program-lims-01"
SCHEMA = "commons-mga-alabama-materials-program-lims/v1"
BUYER = "Marshall Houston / MGA Research"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
OFFICIAL_BINARY = "python mga_alabama_materials_program_lims.py"
OFFICIAL_TEST = "python test_mga_alabama_materials_program_lims.py"
LAB_ID = "MGA-AL-LAB-01"
DOMAIN = "MATERIALS_COUPON"

INPUT_COUNT = 100
READY_COUNT = 80
DUPLICATE_SPECIMEN_COUNT = 5
CONDITIONING_WINDOW_COUNT = 5
METHOD_MATERIAL_MISMATCH_COUNT = 5
UTM_ENVIRONMENT_QC_COUNT = 5
HOLD_COUNT = (
    DUPLICATE_SPECIMEN_COUNT
    + CONDITIONING_WINDOW_COUNT
    + METHOD_MATERIAL_MISMATCH_COUNT
    + UTM_ENVIRONMENT_QC_COUNT
)

HOLD_CODES = (
    "HOLD_DUPLICATE_SPECIMEN",
    "HOLD_CONDITIONING_WINDOW",
    "HOLD_METHOD_MATERIAL_MISMATCH",
    "HOLD_UTM_ENVIRONMENT_QC",
)
HOLD_COUNTS = {
    "HOLD_DUPLICATE_SPECIMEN": DUPLICATE_SPECIMEN_COUNT,
    "HOLD_CONDITIONING_WINDOW": CONDITIONING_WINDOW_COUNT,
    "HOLD_METHOD_MATERIAL_MISMATCH": METHOD_MATERIAL_MISMATCH_COUNT,
    "HOLD_UTM_ENVIRONMENT_QC": UTM_ENVIRONMENT_QC_COUNT,
}

LOAD_CELL_SPAN_LIMIT_PCT = 0.5
CHAMBER_TEMP_TOLERANCE_C = 1.0
CHAMBER_RH_TOLERANCE_PCT = 5.0
DEFAULT_REQUIRED_HOURS = 40.0
DEFAULT_ELAPSED_HOURS = 48.0
DEFAULT_OUT_OF_CHAMBER_MINUTES = 10.0
DEFAULT_MAX_OUT_OF_CHAMBER_MINUTES = 30.0

METHOD_CATALOG: dict[str, dict[str, Any]] = {
    "POLYMER": {
        "method": "ASTM D638",
        "version": "2022",
        "unit": "MPa",
        "fixture_id": "WEDGE-TYPE-IV",
        "instrument_id": "UTM-AL-POLY-01",
        "environment_setpoint_c": 23.0,
        "environment_setpoint_rh": 50.0,
    },
    "METAL": {
        "method": "ASTM E8",
        "version": "2024",
        "unit": "MPa",
        "fixture_id": "WEDGE-ROUND-E8",
        "instrument_id": "UTM-AL-METAL-01",
        "environment_setpoint_c": 23.0,
        "environment_setpoint_rh": 50.0,
    },
    "COMPOSITE": {
        "method": "ASTM D790",
        "version": "2017",
        "unit": "MPa",
        "fixture_id": "FLEX-3PT-D790",
        "instrument_id": "UTM-AL-COMP-01",
        "environment_setpoint_c": 23.0,
        "environment_setpoint_rh": 50.0,
    },
    "ELASTOMER": {
        "method": "ASTM D412",
        "version": "2016",
        "unit": "MPa",
        "fixture_id": "DIE-C-D412",
        "instrument_id": "UTM-AL-ELAST-01",
        "environment_setpoint_c": 23.0,
        "environment_setpoint_rh": 50.0,
    },
}

REVIEWER_DIRECTORY = {
    "SYN-HUMAN-MGA-REVIEWER-01": {
        "display_name": "Synthetic Named Reviewer One",
        "permissions": ("RELEASE_QUALIFICATION_PACKET",),
        "human": True,
    }
}
AUTOMATION_IDENTITIES = frozenset(
    {"", "SYSTEM", "AUTO", "AUTOMATION", "BOT", "MACHINE"}
)

UNIQUE_ID_FIELDS = (
    "request_id",
    "specimen_id",
    "coupon_id",
    "conditioning_id",
)


def _receipt_goldens() -> dict[str, str]:
    path = (
        Path(__file__).resolve().parent
        / "revenue"
        / "mga_alabama_materials_program_lims"
        / "receipt.json"
    )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = {}
    return {
        key: str(value.get(key) or "pending")
        for key in (
            "fixture_sha256",
            "manifest_sha256",
            "audit_sha256",
        )
    }


_GOLDENS = _receipt_goldens()
GOLDEN_FIXTURE_SHA256 = _GOLDENS["fixture_sha256"]
GOLDEN_MANIFEST_SHA256 = _GOLDENS["manifest_sha256"]
GOLDEN_AUDIT_SHA256 = _GOLDENS["audit_sha256"]


class InputError(ValueError):
    """Typed inbound-schema failure."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def state_sha256(journal: dict[str, Any]) -> str:
    return sha256_hex(journal)


def _text(value: Any, field: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise InputError(f"{field} must be a string")
    clean = value.strip()
    if not allow_empty and not clean:
        raise InputError(f"{field} is required")
    return clean


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise InputError(f"{field} must be a boolean")
    return value


def _number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{field} must be a finite number")
    if not math.isfinite(float(value)):
        raise InputError(f"{field} must be a finite number")
    return value


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{field} must be an object")
    return value


def _material_class_for_index(index: int) -> str:
    classes = ("POLYMER", "METAL", "COMPOSITE", "ELASTOMER")
    return classes[(index - 1) % 4]


def _job_id(specimen_id: str, method: str, version: str) -> str:
    return "MGA-JOB-" + sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "specimen_id": specimen_id,
            "method": method,
            "version": version,
        }
    )[:14]


def _result_id(specimen_id: str, source_uri: str) -> str:
    return "MGA-RES-" + sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "specimen_id": specimen_id,
            "source_uri": source_uri,
        }
    )[:14]


def _packet_id(specimen_id: str) -> str:
    return "MGA-PKT-" + sha256_hex(
        {"demand_id": DEMAND_ID, "specimen_id": specimen_id}
    )[:14]


def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": row["request_id"],
        "specimen_id": row["specimen_id"],
        "coupon_id": row["coupon_id"],
        "material_class": row["material_class"],
        "conditioning_id": row["conditioning_id"],
        "conditioning_required_hours": row["conditioning_required_hours"],
        "conditioning_elapsed_hours": row["conditioning_elapsed_hours"],
        "out_of_chamber_minutes": row["out_of_chamber_minutes"],
        "max_out_of_chamber_minutes": row["max_out_of_chamber_minutes"],
        "synthetic": row["synthetic"],
        "deidentified": row["deidentified"],
        "domain": row["domain"],
    }


def _method_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "lab_id": row["lab_id"],
        "method": row["method"],
        "method_version": row["method_version"],
        "fixture_id": row["fixture_id"],
        "instrument_id": row["instrument_id"],
        "environment_setpoint_c": row["environment_setpoint_c"],
        "environment_setpoint_rh": row["environment_setpoint_rh"],
    }


def _result_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "specimen_id": row["specimen_id"],
        "method": row["method"],
        "method_version": row["method_version"],
        "value": row["result_value"],
        "unit": row["result_unit"],
        "source_uri": row["raw_source_uri"],
        "source_revision": row["raw_source_revision"],
    }


def _derived_hashes(row: dict[str, Any]) -> dict[str, str]:
    source_hash = sha256_hex(_source_payload(row))
    method_hash = sha256_hex(_method_payload(row))
    result_hash = sha256_hex(_result_payload(row))
    packet_core = {
        "packet_id": _packet_id(row["specimen_id"]),
        "specimen_id": row["specimen_id"],
        "job_id": _job_id(
            row["specimen_id"], row["method"], row["method_version"]
        ),
        "result_id": _result_id(row["specimen_id"], row["raw_source_uri"]),
        "method": row["method"],
        "instrument_id": row["instrument_id"],
        "fixture_id": row["fixture_id"],
        "source_sha256": source_hash,
        "method_sha256": method_hash,
        "result_sha256": result_hash,
        "value_sha256": sha256_hex({"value": row["result_value"]}),
        "unit_sha256": sha256_hex({"unit": row["result_unit"]}),
        "status": "STAGED",
    }
    return {
        "source_sha256": source_hash,
        "method_sha256": method_hash,
        "result_sha256": result_hash,
        "value_sha256": packet_core["value_sha256"],
        "unit_sha256": packet_core["unit_sha256"],
        "packet_sha256": sha256_hex(packet_core),
    }


def _stamp_goldens(row: dict[str, Any]) -> dict[str, Any]:
    stamped = deepcopy(row)
    stamped["golden_hashes"] = _derived_hashes(stamped)
    return stamped


def _base_program(index: int) -> dict[str, Any]:
    token = f"{index:03d}"
    material_class = _material_class_for_index(index)
    spec = METHOD_CATALOG[material_class]
    row: dict[str, Any] = {
        "row_id": f"MGA-ROW-{token}",
        "request_id": f"MGA-REQ-{token}",
        "specimen_id": f"MGA-SPEC-{token}",
        "coupon_id": f"MGA-COUPON-{token}",
        "material_class": material_class,
        "lab_id": LAB_ID,
        "method": spec["method"],
        "method_version": spec["version"],
        "fixture_id": spec["fixture_id"],
        "instrument_id": spec["instrument_id"],
        "environment_setpoint_c": spec["environment_setpoint_c"],
        "environment_setpoint_rh": spec["environment_setpoint_rh"],
        "conditioning_id": f"MGA-COND-{token}",
        "conditioning_required_hours": DEFAULT_REQUIRED_HOURS,
        "conditioning_elapsed_hours": DEFAULT_ELAPSED_HOURS,
        "out_of_chamber_minutes": DEFAULT_OUT_OF_CHAMBER_MINUTES,
        "max_out_of_chamber_minutes": DEFAULT_MAX_OUT_OF_CHAMBER_MINUTES,
        "utm_qc_pass": True,
        "load_cell_span_error_pct": 0.12,
        "chamber_actual_c": 23.1,
        "chamber_actual_rh": 50.2,
        "raw_source_uri": (
            f"synthetic://utm/{spec['instrument_id']}/run-{token}.json"
        ),
        "raw_source_revision": "RAW-2026.1",
        "result_value": round(40.0 + index * 0.25, 3),
        "result_unit": spec["unit"],
        "synthetic": True,
        "deidentified": True,
        "domain": DOMAIN,
        "expected_state": "READY",
        "expected_hold": None,
    }
    return _stamp_goldens(row)


def _duplicate_specimen_program(slot: int) -> dict[str, Any]:
    source_index = slot + 1
    row = _base_program(81 + slot)
    row["specimen_id"] = f"MGA-SPEC-{source_index:03d}"
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_DUPLICATE_SPECIMEN"
    return _stamp_goldens(row)


def _conditioning_window_program(index: int) -> dict[str, Any]:
    row = _base_program(index)
    row["conditioning_elapsed_hours"] = 12.0
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_CONDITIONING_WINDOW"
    return _stamp_goldens(row)


def _method_material_mismatch_program(index: int) -> dict[str, Any]:
    row = _base_program(index)
    other = METHOD_CATALOG[
        _material_class_for_index(index + 1)
    ]
    row["method"] = other["method"]
    row["method_version"] = other["version"]
    row["fixture_id"] = other["fixture_id"]
    row["result_unit"] = other["unit"]
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_METHOD_MATERIAL_MISMATCH"
    return _stamp_goldens(row)


def _utm_environment_qc_program(index: int) -> dict[str, Any]:
    row = _base_program(index)
    row["utm_qc_pass"] = False
    row["load_cell_span_error_pct"] = 1.75
    row["chamber_actual_c"] = 35.0
    row["chamber_actual_rh"] = 18.0
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_UTM_ENVIRONMENT_QC"
    return _stamp_goldens(row)


def build_acceptance_fixture() -> list[dict[str, Any]]:
    """Build the frozen 100-program 80 READY / 20 HOLD fixture."""
    rows = [_base_program(index) for index in range(1, 81)]
    rows.extend(_duplicate_specimen_program(slot) for slot in range(5))
    rows.extend(
        _conditioning_window_program(index) for index in range(86, 91)
    )
    rows.extend(
        _method_material_mismatch_program(index) for index in range(91, 96)
    )
    rows.extend(
        _utm_environment_qc_program(index) for index in range(96, 101)
    )
    if len(rows) != INPUT_COUNT:
        raise RuntimeError("fixture cardinality drift")
    return rows


def fixture_sha256(rows: list[dict[str, Any]] | None = None) -> str:
    return sha256_hex(
        rows if rows is not None else build_acceptance_fixture()
    )


class SyntheticReadOnlyProgramAdapter:
    """Read-only in-memory fixture source; no live or write capability."""

    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = deepcopy(rows)
        self.mode = "SYNTHETIC_READ_ONLY"
        self.live = False
        self.writes = 0

    def list_programs(self) -> list[dict[str, Any]]:
        return deepcopy(self._rows)

    def write(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("synthetic source adapter is read-only")


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "processed_rows": {},
        "identifier_index": {},
        "specimens": {},
        "jobs": {},
        "results": {},
        "packets": {},
        "holds": [],
        "events": [],
        "interface_live": False,
        "interfaces": "SYNTHETIC_READ_ONLY",
        "production_writes": 0,
        "automatic_releases": 0,
    }


def _event(
    journal: dict[str, Any], kind: str, payload: dict[str, Any]
) -> None:
    journal["events"].append(
        {
            "seq": len(journal["events"]) + 1,
            "kind": kind,
            **deepcopy(payload),
        }
    )


def normalize_program(row: dict[str, Any]) -> dict[str, Any]:
    source = _mapping(row, "row")
    golden = _mapping(source.get("golden_hashes"), "golden_hashes")
    return {
        "row_id": _text(source.get("row_id"), "row_id", allow_empty=False),
        "request_id": _text(source.get("request_id"), "request_id"),
        "specimen_id": _text(source.get("specimen_id"), "specimen_id"),
        "coupon_id": _text(source.get("coupon_id"), "coupon_id"),
        "material_class": _text(
            source.get("material_class"), "material_class"
        ).upper(),
        "lab_id": _text(source.get("lab_id"), "lab_id"),
        "method": _text(source.get("method"), "method"),
        "method_version": _text(
            source.get("method_version"), "method_version"
        ),
        "fixture_id": _text(source.get("fixture_id"), "fixture_id"),
        "instrument_id": _text(
            source.get("instrument_id"), "instrument_id"
        ),
        "environment_setpoint_c": _number(
            source.get("environment_setpoint_c"), "environment_setpoint_c"
        ),
        "environment_setpoint_rh": _number(
            source.get("environment_setpoint_rh"), "environment_setpoint_rh"
        ),
        "conditioning_id": _text(
            source.get("conditioning_id"), "conditioning_id"
        ),
        "conditioning_required_hours": _number(
            source.get("conditioning_required_hours"),
            "conditioning_required_hours",
        ),
        "conditioning_elapsed_hours": _number(
            source.get("conditioning_elapsed_hours"),
            "conditioning_elapsed_hours",
        ),
        "out_of_chamber_minutes": _number(
            source.get("out_of_chamber_minutes"), "out_of_chamber_minutes"
        ),
        "max_out_of_chamber_minutes": _number(
            source.get("max_out_of_chamber_minutes"),
            "max_out_of_chamber_minutes",
        ),
        "utm_qc_pass": _bool(source.get("utm_qc_pass"), "utm_qc_pass"),
        "load_cell_span_error_pct": _number(
            source.get("load_cell_span_error_pct"),
            "load_cell_span_error_pct",
        ),
        "chamber_actual_c": _number(
            source.get("chamber_actual_c"), "chamber_actual_c"
        ),
        "chamber_actual_rh": _number(
            source.get("chamber_actual_rh"), "chamber_actual_rh"
        ),
        "raw_source_uri": _text(
            source.get("raw_source_uri"), "raw_source_uri"
        ),
        "raw_source_revision": _text(
            source.get("raw_source_revision"), "raw_source_revision"
        ),
        "result_value": _number(
            source.get("result_value"), "result_value"
        ),
        "result_unit": _text(source.get("result_unit"), "result_unit"),
        "synthetic": _bool(source.get("synthetic"), "synthetic"),
        "deidentified": _bool(source.get("deidentified"), "deidentified"),
        "domain": _text(source.get("domain"), "domain").upper(),
        "golden_hashes": {
            key: _text(golden.get(key), f"golden_hashes.{key}")
            for key in (
                "source_sha256",
                "method_sha256",
                "result_sha256",
                "value_sha256",
                "unit_sha256",
                "packet_sha256",
            )
        },
    }


def classify_program(
    journal: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    if (
        not row["synthetic"]
        or not row["deidentified"]
        or row["domain"] != DOMAIN
    ):
        return {"ok": False, "code": "HOLD_TRUTH_BOUNDARY"}
    identifiers = [row[field] for field in UNIQUE_ID_FIELDS]
    if (
        any(not value for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
        or any(value in journal["identifier_index"] for value in identifiers)
    ):
        return {"ok": False, "code": "HOLD_DUPLICATE_SPECIMEN"}
    if (
        float(row["conditioning_elapsed_hours"])
        < float(row["conditioning_required_hours"])
        or float(row["out_of_chamber_minutes"])
        > float(row["max_out_of_chamber_minutes"])
    ):
        return {"ok": False, "code": "HOLD_CONDITIONING_WINDOW"}
    spec = METHOD_CATALOG.get(row["material_class"])
    if (
        spec is None
        or row["lab_id"] != LAB_ID
        or row["method"] != spec["method"]
        or row["method_version"] != spec["version"]
        or row["fixture_id"] != spec["fixture_id"]
        or row["result_unit"] != spec["unit"]
        or float(row["environment_setpoint_c"])
        != float(spec["environment_setpoint_c"])
        or float(row["environment_setpoint_rh"])
        != float(spec["environment_setpoint_rh"])
    ):
        return {"ok": False, "code": "HOLD_METHOD_MATERIAL_MISMATCH"}
    if (
        not row["utm_qc_pass"]
        or row["instrument_id"] != spec["instrument_id"]
        or float(row["load_cell_span_error_pct"]) > LOAD_CELL_SPAN_LIMIT_PCT
        or abs(
            float(row["chamber_actual_c"])
            - float(row["environment_setpoint_c"])
        )
        > CHAMBER_TEMP_TOLERANCE_C
        or abs(
            float(row["chamber_actual_rh"])
            - float(row["environment_setpoint_rh"])
        )
        > CHAMBER_RH_TOLERANCE_PCT
    ):
        return {"ok": False, "code": "HOLD_UTM_ENVIRONMENT_QC"}
    if row["golden_hashes"] != _derived_hashes(row):
        return {"ok": False, "code": "HOLD_GOLDEN_HASH_MISMATCH"}
    return {"ok": True, "code": None}


def _commit(
    journal: dict[str, Any], candidate: dict[str, Any]
) -> None:
    journal.clear()
    journal.update(candidate)


def ingest_program(
    journal: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    """Ingest one row atomically; rejection never partially mutates state."""
    try:
        norm = normalize_program(row)
    except (InputError, KeyError, TypeError, ValueError) as exc:
        return {
            "kind": "REJECT",
            "ok": False,
            "code": "REJECT_INVALID_INPUT",
            "row_id": (
                row.get("row_id", "").strip()
                if isinstance(row, dict)
                and isinstance(row.get("row_id"), str)
                else ""
            ),
            "detail": str(exc),
        }

    row_id = norm["row_id"]
    payload_sha256 = sha256_hex(norm)
    prior = journal["processed_rows"].get(row_id)
    if prior is not None:
        if prior["payload_sha256"] != payload_sha256:
            return {
                "kind": "REPLAY_CONFLICT",
                "ok": False,
                "code": "REPLAY_PAYLOAD_CONFLICT",
                "row_id": row_id,
            }
        return {
            "kind": "REPLAY_NOOP",
            "ok": True,
            "row_id": row_id,
            "prior_kind": prior["kind"],
        }

    candidate = deepcopy(journal)
    verdict = classify_program(candidate, norm)
    if not verdict["ok"]:
        hold = {
            "row_id": row_id,
            "request_id": norm["request_id"] or None,
            "specimen_id": norm["specimen_id"] or None,
            "code": verdict["code"],
            "state": "HOLD",
            "jobs_created": 0,
            "jobs_scheduled": 0,
            "results_created": 0,
            "packets_staged": 0,
            "packets_released": 0,
        }
        candidate["holds"].append(hold)
        candidate["processed_rows"][row_id] = {
            "kind": "HOLD",
            "code": verdict["code"],
            "payload_sha256": payload_sha256,
        }
        _event(candidate, "HOLD", hold)
        _commit(journal, candidate)
        return {"kind": "HOLD", "ok": False, **deepcopy(hold)}

    job_id = _job_id(
        norm["specimen_id"], norm["method"], norm["method_version"]
    )
    result_id = _result_id(norm["specimen_id"], norm["raw_source_uri"])
    packet_id = _packet_id(norm["specimen_id"])
    if (
        norm["specimen_id"] in candidate["specimens"]
        or job_id in candidate["jobs"]
        or result_id in candidate["results"]
        or packet_id in candidate["packets"]
    ):
        return {
            "kind": "REJECT",
            "ok": False,
            "code": "REJECT_DERIVED_IDENTIFIER_COLLISION",
            "row_id": row_id,
        }

    hashes = _derived_hashes(norm)
    specimen = {
        "specimen_id": norm["specimen_id"],
        "request_id": norm["request_id"],
        "coupon_id": norm["coupon_id"],
        "material_class": norm["material_class"],
        "conditioning_id": norm["conditioning_id"],
        "lab_id": norm["lab_id"],
        "source_sha256": hashes["source_sha256"],
        "state": "ACCESSIONED",
    }
    job = {
        "job_id": job_id,
        "specimen_id": norm["specimen_id"],
        "lab_id": norm["lab_id"],
        "method": norm["method"],
        "method_version": norm["method_version"],
        "fixture_id": norm["fixture_id"],
        "instrument_id": norm["instrument_id"],
        "environment_setpoint_c": norm["environment_setpoint_c"],
        "environment_setpoint_rh": norm["environment_setpoint_rh"],
        "method_sha256": hashes["method_sha256"],
        "scheduled": True,
        "state": "COMPLETE_PENDING_REVIEW",
    }
    result = {
        "result_id": result_id,
        "job_id": job_id,
        "specimen_id": norm["specimen_id"],
        "value": norm["result_value"],
        "unit": norm["result_unit"],
        "source_uri": norm["raw_source_uri"],
        "source_revision": norm["raw_source_revision"],
        "instrument_id": norm["instrument_id"],
        "fixture_id": norm["fixture_id"],
        "source_sha256": hashes["source_sha256"],
        "method_sha256": hashes["method_sha256"],
        "result_sha256": hashes["result_sha256"],
        "value_sha256": hashes["value_sha256"],
        "unit_sha256": hashes["unit_sha256"],
    }
    packet = {
        "packet_id": packet_id,
        "specimen_id": norm["specimen_id"],
        "job_id": job_id,
        "result_id": result_id,
        "method": norm["method"],
        "method_version": norm["method_version"],
        "instrument_id": norm["instrument_id"],
        "fixture_id": norm["fixture_id"],
        "source_sha256": hashes["source_sha256"],
        "method_sha256": hashes["method_sha256"],
        "result_sha256": hashes["result_sha256"],
        "value_sha256": hashes["value_sha256"],
        "unit_sha256": hashes["unit_sha256"],
        "packet_sha256": hashes["packet_sha256"],
        "status": "STAGED",
        "released": False,
        "released_by": None,
    }

    candidate["specimens"][norm["specimen_id"]] = specimen
    candidate["jobs"][job_id] = job
    candidate["results"][result_id] = result
    candidate["packets"][packet_id] = packet
    for field in UNIQUE_ID_FIELDS:
        candidate["identifier_index"][norm[field]] = {
            "row_id": row_id,
            "field": field,
        }
    candidate["processed_rows"][row_id] = {
        "kind": "READY",
        "payload_sha256": payload_sha256,
        "specimen_id": norm["specimen_id"],
        "job_id": job_id,
        "result_id": result_id,
        "packet_id": packet_id,
    }
    _event(
        candidate,
        "PACKET_STAGED",
        {
            "row_id": row_id,
            "specimen_id": norm["specimen_id"],
            "job_id": job_id,
            "result_id": result_id,
            "packet_id": packet_id,
        },
    )
    _commit(journal, candidate)
    return {
        "kind": "READY",
        "ok": True,
        "row_id": row_id,
        "specimen_id": norm["specimen_id"],
        "job_id": job_id,
        "result_id": result_id,
        "packet_id": packet_id,
    }


def release_packet(
    journal: dict[str, Any], packet_id: str, *, reviewer_id: str
) -> dict[str, Any]:
    """Release only through the trusted named-human reviewer directory."""
    if not isinstance(packet_id, str) or not isinstance(reviewer_id, str):
        return {"ok": False, "code": "RELEASE_INVALID_INPUT"}
    packet_id = packet_id.strip()
    reviewer_id = reviewer_id.strip()
    packet = journal["packets"].get(packet_id)
    if packet is None:
        return {"ok": False, "code": "UNKNOWN_PACKET"}
    if reviewer_id.upper() in AUTOMATION_IDENTITIES:
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
    reviewer = REVIEWER_DIRECTORY.get(reviewer_id)
    if (
        reviewer is None
        or reviewer.get("human") is not True
        or "RELEASE_QUALIFICATION_PACKET"
        not in reviewer.get("permissions", ())
        or not reviewer.get("display_name")
    ):
        return {"ok": False, "code": "UNAUTHORIZED_REVIEWER"}
    if packet["released"]:
        return {
            "ok": True,
            "duplicate": True,
            "status": "RELEASED",
            "released_by": packet["released_by"],
        }

    candidate = deepcopy(journal)
    target = candidate["packets"][packet_id]
    target["released"] = True
    target["released_by"] = {
        "reviewer_id": reviewer_id,
        "display_name": reviewer["display_name"],
    }
    target["status"] = "RELEASED"
    candidate["automatic_releases"] = journal["automatic_releases"]
    _event(
        candidate,
        "RELEASED",
        {
            "packet_id": packet_id,
            "reviewer_id": reviewer_id,
            "display_name": reviewer["display_name"],
        },
    )
    _commit(journal, candidate)
    return {
        "ok": True,
        "duplicate": False,
        "status": "RELEASED",
        "released_by": deepcopy(target["released_by"]),
    }


def replay_into(
    journal: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    before = {
        "specimens": len(journal["specimens"]),
        "jobs": len(journal["jobs"]),
        "results": len(journal["results"]),
        "packets": len(journal["packets"]),
        "holds": len(journal["holds"]),
    }
    effects = [ingest_program(journal, row) for row in deepcopy(rows)]
    return {
        "added_specimens": len(journal["specimens"]) - before["specimens"],
        "added_jobs": len(journal["jobs"]) - before["jobs"],
        "added_results": len(journal["results"]) - before["results"],
        "added_packets": len(journal["packets"]) - before["packets"],
        "added_holds": len(journal["holds"]) - before["holds"],
        "replay_noops": sum(
            item.get("kind") == "REPLAY_NOOP" for item in effects
        ),
        "replay_conflicts": sum(
            item.get("kind") == "REPLAY_CONFLICT" for item in effects
        ),
    }


def run_gate(
    rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    inbound = deepcopy(
        rows if rows is not None else build_acceptance_fixture()
    )
    source = SyntheticReadOnlyProgramAdapter(inbound)
    journal = empty_journal()
    effects = [
        ingest_program(journal, row) for row in source.list_programs()
    ]
    autonomous_release_effects = [
        release_packet(journal, packet_id, reviewer_id="SYSTEM")
        for packet_id in sorted(journal["packets"])[:3]
    ]
    replay = replay_into(journal, inbound)
    holds = sorted(
        deepcopy(journal["holds"]), key=lambda item: item["row_id"]
    )
    specimens = sorted(
        deepcopy(list(journal["specimens"].values())),
        key=lambda item: item["specimen_id"],
    )
    jobs = sorted(
        deepcopy(list(journal["jobs"].values())),
        key=lambda item: item["job_id"],
    )
    results = sorted(
        deepcopy(list(journal["results"].values())),
        key=lambda item: item["result_id"],
    )
    packets = sorted(
        deepcopy(list(journal["packets"].values())),
        key=lambda item: item["packet_id"],
    )
    hold_counts = {
        code: sum(item["code"] == code for item in holds)
        for code in HOLD_CODES
    }
    material_class_counts = {
        name: sum(item["material_class"] == name for item in specimens)
        for name in METHOD_CATALOG
    }
    hash_match_counts = {
        "value": sum(
            item["value_sha256"] == sha256_hex({"value": item["value"]})
            for item in results
        ),
        "unit": sum(
            item["unit_sha256"] == sha256_hex({"unit": item["unit"]})
            for item in results
        ),
        "packet": sum(
            len(item["packet_sha256"]) == 64 for item in packets
        ),
    }
    manifest = {
        "demand_id": DEMAND_ID,
        "specimen_ids": [item["specimen_id"] for item in specimens],
        "job_ids": [item["job_id"] for item in jobs],
        "result_ids": [item["result_id"] for item in results],
        "packets": [
            {
                "packet_id": item["packet_id"],
                "packet_sha256": item["packet_sha256"],
                "status": item["status"],
            }
            for item in packets
        ],
        "holds": [
            (item["row_id"], item["specimen_id"], item["code"])
            for item in holds
        ],
    }
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "input_rows": len(inbound),
        "ready": len(specimens),
        "holds": len(holds),
        "specimens": len(specimens),
        "jobs": len(jobs),
        "jobs_scheduled": sum(item["scheduled"] for item in jobs),
        "results": len(results),
        "packets_staged": sum(
            item["status"] == "STAGED" for item in packets
        ),
        "packets_released": sum(item["released"] for item in packets),
        "hold_counts": hold_counts,
        "material_class_counts": material_class_counts,
        "hash_match_counts": hash_match_counts,
        "fixture_sha256": fixture_sha256(inbound),
        "manifest_sha256": sha256_hex(manifest),
        "specimen_records": specimens,
        "job_records": jobs,
        "result_records": results,
        "packet_records": packets,
        "hold_records": holds,
        "effects": effects,
        "autonomous_release_effects": autonomous_release_effects,
        "replay": replay,
        "audit_sha256": sha256_hex(
            {
                "events": journal["events"],
                "manifest": manifest,
                "replay": replay,
                "truth_gate": TRUTH_GATE,
            }
        ),
        "interface_live": False,
        "interfaces": "SYNTHETIC_READ_ONLY",
        "source_writes": source.writes,
        "production_writes": 0,
        "automatic_releases": journal["automatic_releases"],
        "autonomous_release": False,
        "pre_sale_transport": "NONE",
        "cash_usd": 0,
        "official_binary": OFFICIAL_BINARY,
        "official_test": OFFICIAL_TEST,
    }


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    checks = {
        "input_rows": result.get("input_rows") == INPUT_COUNT,
        "ready": result.get("ready") == READY_COUNT,
        "holds": result.get("holds") == HOLD_COUNT,
        "specimens": result.get("specimens") == READY_COUNT,
        "jobs": result.get("jobs") == READY_COUNT,
        "jobs_scheduled": result.get("jobs_scheduled") == READY_COUNT,
        "results": result.get("results") == READY_COUNT,
        "packets_staged": result.get("packets_staged") == READY_COUNT,
        "packets_released": result.get("packets_released") == 0,
        "hold_counts": result.get("hold_counts") == HOLD_COUNTS,
        "material_class_counts": result.get("material_class_counts")
        == {
            "POLYMER": 20,
            "METAL": 20,
            "COMPOSITE": 20,
            "ELASTOMER": 20,
        },
        "hash_match_counts": result.get("hash_match_counts")
        == {
            "value": READY_COUNT,
            "unit": READY_COUNT,
            "packet": READY_COUNT,
        },
        "interfaces": result.get("interfaces") == "SYNTHETIC_READ_ONLY",
        "source_writes": result.get("source_writes") == 0,
        "production_writes": result.get("production_writes") == 0,
        "automatic_releases": result.get("automatic_releases") == 0,
        "autonomous_release": result.get("autonomous_release") is False,
        "pre_sale_transport": result.get("pre_sale_transport") == "NONE",
        "cash_usd": result.get("cash_usd") == 0,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    replay = result.get("replay") or {}
    for key in (
        "added_specimens",
        "added_jobs",
        "added_results",
        "added_packets",
        "added_holds",
        "replay_conflicts",
    ):
        if replay.get(key) != 0:
            failures.append(f"replay_{key}")
    if replay.get("replay_noops") != INPUT_COUNT:
        failures.append("replay_noops")
    if any(
        item.get("code") != "AUTONOMOUS_RELEASE_DENIED"
        for item in result.get("autonomous_release_effects") or []
    ):
        failures.append("autonomous_release_not_denied")
    if any(
        item.get("jobs_created")
        or item.get("jobs_scheduled")
        or item.get("results_created")
        or item.get("packets_staged")
        or item.get("packets_released")
        for item in result.get("hold_records") or []
    ):
        failures.append("hold_created_output")
    job_by_specimen = {
        item["specimen_id"]: item
        for item in result.get("job_records") or []
    }
    result_by_job = {
        item["job_id"]: item for item in result.get("result_records") or []
    }
    packets_by_specimen: dict[str, list[dict[str, Any]]] = {}
    for packet in result.get("packet_records") or []:
        packets_by_specimen.setdefault(packet["specimen_id"], []).append(
            packet
        )
    for specimen in result.get("specimen_records") or []:
        specimen_id = specimen["specimen_id"]
        job = job_by_specimen.get(specimen_id)
        packets = packets_by_specimen.get(specimen_id, [])
        if job is None or len(packets) != 1:
            failures.append("packet_specimen_lineage")
            break
        packet = packets[0]
        raw_result = result_by_job.get(job["job_id"])
        if raw_result is None:
            failures.append("result_job_lineage")
            break
        if (
            job["specimen_id"] != specimen["specimen_id"]
            or raw_result["job_id"] != job["job_id"]
            or packet["job_id"] != job["job_id"]
            or packet["result_id"] != raw_result["result_id"]
            or packet["method"] != job["method"]
            or packet["instrument_id"] != job["instrument_id"]
            or packet["fixture_id"] != job["fixture_id"]
            or raw_result["instrument_id"] != job["instrument_id"]
            or raw_result["fixture_id"] != job["fixture_id"]
        ):
            failures.append("lineage_link")
            break
        if (
            packet["source_sha256"] != raw_result["source_sha256"]
            or packet["method_sha256"] != raw_result["method_sha256"]
            or packet["result_sha256"] != raw_result["result_sha256"]
            or packet["value_sha256"] != raw_result["value_sha256"]
            or packet["unit_sha256"] != raw_result["unit_sha256"]
        ):
            failures.append("lineage_hash")
            break
    goldens = {
        "fixture_sha256": GOLDEN_FIXTURE_SHA256,
        "manifest_sha256": GOLDEN_MANIFEST_SHA256,
        "audit_sha256": GOLDEN_AUDIT_SHA256,
    }
    for field, expected in goldens.items():
        if expected != "pending" and result.get(field) != expected:
            failures.append(field)
    return failures


def cli_payload(result: dict[str, Any]) -> dict[str, Any]:
    failures = pass_contract(result)
    return {
        "ok": not failures,
        "failures": failures,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "input_rows": result["input_rows"],
        "ready": result["ready"],
        "holds": result["holds"],
        "hold_counts": result["hold_counts"],
        "specimens": result["specimens"],
        "jobs": result["jobs"],
        "jobs_scheduled": result["jobs_scheduled"],
        "results": result["results"],
        "packets_staged": result["packets_staged"],
        "packets_released": result["packets_released"],
        "material_class_counts": result["material_class_counts"],
        "hash_match_counts": result["hash_match_counts"],
        "replay": result["replay"],
        "fixture_sha256": result["fixture_sha256"],
        "manifest_sha256": result["manifest_sha256"],
        "audit_sha256": result["audit_sha256"],
        "interfaces": result["interfaces"],
        "pre_sale_transport": result["pre_sale_transport"],
        "cash_usd": result["cash_usd"],
        "official_test": OFFICIAL_TEST,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    result = run_gate()
    if "--print-goldens" in args:
        print(
            canonical_json(
                {
                    "fixture_sha256": result["fixture_sha256"],
                    "manifest_sha256": result["manifest_sha256"],
                    "audit_sha256": result["audit_sha256"],
                }
            )
        )
        return 0
    payload = cli_payload(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
