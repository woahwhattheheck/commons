#!/usr/bin/env python3
"""CS Analytical expansion cross-line evidence LIMS.

Demand: csanalytical-expansion-crossline-evidence-lims-01
Buyer: Brandon Zurawlow / CS Analytical

Client study + sample/lot + product/package component → CCIT vs
raw-material/gas/micro route → method/version → instrument/run →
QC/audit → staged report, with explicit cross-line misroute blocking.
Named-human approval only.

Acceptance: run 120 synthetic submissions — 90 valid, 8 duplicate IDs,
7 wrong line/method routes, 5 missing study/package metadata, 5
instrument/QC failures, 5 source-hash mismatches. PASS only when
exactly 90 are READY; 30 receive their predetermined HOLD; intake
holds schedule nothing; no held record stages or releases a report;
method/instrument/value/unit/audit/source hashes match; replay adds
zero records; human-only release.

AquaTrace HOLD / BUILD-AND-VERIFY. Adapters stay simulated/read-only.
No compliance decision. PRE-SALE TRANSPORT: NONE.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

DEMAND_ID = "csanalytical-expansion-crossline-evidence-lims-01"
SCHEMA = "commons-csanalytical-expansion-crossline-evidence-lims/v1"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
BUYER = "Brandon Zurawlow / CS Analytical"
HUMAN_APPROVER = "APPROVER"
NAMED_HUMAN = "brandon-zurawlow"
VALID_COUNT = 90
HOLD_COUNT = 30
INPUT_COUNT = VALID_COUNT + HOLD_COUNT

HOLD_CODES = (
    "DUPLICATE_ID",
    "WRONG_LINE_METHOD",
    "MISSING_STUDY_PACKAGE",
    "INSTRUMENT_QC_FAILURE",
    "SOURCE_HASH_MISMATCH",
)
HOLD_PLAN = {
    "DUPLICATE_ID": 8,
    "WRONG_LINE_METHOD": 7,
    "MISSING_STUDY_PACKAGE": 5,
    "INSTRUMENT_QC_FAILURE": 5,
    "SOURCE_HASH_MISMATCH": 5,
}

LINES = {
    "CCIT": {
        "methods": {
            "VACUUM-DECAY": {"version": "VD-2024-SYN", "instrument": "SIM-VD-01", "unit": "mbar/s"},
            "HVLD": {"version": "HVLD-2023-SYN", "instrument": "SIM-HVLD-01", "unit": "uA"},
        },
        "worklist": "CCIT_LINE",
        "qc_window": (0.8, 1.2),
    },
    "RAW_MATERIAL": {
        "methods": {
            "USP-661": {"version": "USP-661-2023-SYN", "instrument": "SIM-FTIR-01", "unit": "%match"},
            "FTIR": {"version": "FTIR-ATR-2024-SYN", "instrument": "SIM-FTIR-02", "unit": "%match"},
        },
        "worklist": "RAW_MATERIAL_LINE",
        "qc_window": (98.0, 100.0),
    },
    "GAS": {
        "methods": {
            "HS-GC": {"version": "HSGC-2022-SYN", "instrument": "SIM-HSGC-01", "unit": "ppm"},
            "O2-HEADSPACE": {"version": "O2HS-2024-SYN", "instrument": "SIM-O2-01", "unit": "%O2"},
        },
        "worklist": "GAS_LINE",
        "qc_window": (19.5, 21.5),
    },
    "MICRO": {
        "methods": {
            "USP-71": {"version": "USP-71-2024-SYN", "instrument": "SIM-STER-01", "unit": "cfu"},
            "BIOBURDEN": {"version": "ISO-11737-1-SYN", "instrument": "SIM-BB-01", "unit": "cfu"},
        },
        "worklist": "MICRO_LINE",
        "qc_window": (0.0, 0.0),
    },
}
LINE_NAMES = tuple(LINES)
MISROUTE_PAIRS = (
    ("CCIT", "USP-71"),
    ("CCIT", "HS-GC"),
    ("RAW_MATERIAL", "VACUUM-DECAY"),
    ("GAS", "HVLD"),
    ("GAS", "BIOBURDEN"),
    ("MICRO", "FTIR"),
    ("MICRO", "O2-HEADSPACE"),
)

GOLDEN_COUNTS = {
    "input_rows": INPUT_COUNT,
    "ready": VALID_COUNT,
    "held": HOLD_COUNT,
    "scheduled_holds": 0,
    "held_reports_staged": 0,
    "released_reports": 0,
    "staged_reports": VALID_COUNT,
    "replay_added_records": 0,
    "production_writes": 0,
}

GOLDEN_FIXTURE_SHA256 = "a15e0d4fdf758b1c6b3aaf953c207050bed39f95282d5fd40bee97376939d6a8"
GOLDEN_AUDIT_SHA256 = "edb76b5450c40ff2c52027176485c120e99ca5b1bb51ebb76d237dd836c00632"
GOLDEN_LINEAGE_SHA256 = "539ec0898544c686cb7bb47c1851326d2cb0d870ef905b86c221b23dcc2b67e6"
GOLDEN_REPORT_DIGEST = "32d53085590c4db83117700ac2bd0efae1245b1942bf6757db2d680723850e6b"
HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE / "revenue" / "csanalytical_expansion_crossline"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "y"}


def line_for(index: int) -> str:
    return LINE_NAMES[(index - 1) % len(LINE_NAMES)]


def method_for(line: str, index: int) -> str:
    names = tuple(LINES[line]["methods"])
    return names[(index - 1) % len(names)]


def valid_study_id(index: int) -> str:
    return "CSA-STU-%03d" % index


def valid_sample_id(index: int) -> str:
    return "CSA-SMP-%03d" % index


def valid_lot_id(index: int) -> str:
    return "CSA-LOT-%03d" % index


def accession_id(study_id: str, sample_id: str, lot_id: str) -> str:
    digest = sha256_hex(
        {"demand_id": DEMAND_ID, "study_id": study_id, "sample_id": sample_id, "lot_id": lot_id}
    )
    return "CSA-" + digest[:12]


def source_hash(study_id: str, sample_id: str, lot_id: str, package_id: str) -> str:
    return sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "SOURCE",
            "study_id": study_id,
            "sample_id": sample_id,
            "lot_id": lot_id,
            "package_id": package_id,
        }
    )


def method_hash(line: str, method: str, method_version: str) -> str:
    return sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "METHOD",
            "line": line,
            "method": method,
            "method_version": method_version,
        }
    )


def instrument_hash(instrument: str, run_id: str) -> str:
    return sha256_hex(
        {"demand_id": DEMAND_ID, "kind": "INSTRUMENT", "instrument": instrument, "run_id": run_id}
    )


def unit_hash(line: str, method: str) -> str:
    spec = LINES[line]["methods"][method]
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "UNIT", "unit": spec["unit"]})


def value_packet(index: int, line: str, method: str, *, qc_ok: bool) -> dict[str, Any]:
    line_spec = LINES.get(line) or LINES["CCIT"]
    spec = line_spec["methods"].get(method)
    if spec is None:
        fallback_line = next(
            (name for name, body in LINES.items() if method in body["methods"]),
            "CCIT",
        )
        spec = LINES[fallback_line]["methods"].get(method) or LINES["CCIT"]["methods"]["VACUUM-DECAY"]
        line_spec = LINES[fallback_line]
    low, high = line_spec["qc_window"]
    qc_value = (low + high) / 2.0 if qc_ok else high + 4.0
    return {
        "instrument_id": spec["instrument"],
        "adapter": "SIMULATED",
        "value": round(10.0 + ((index - 1) % 20) * 0.25, 2),
        "unit": spec["unit"],
        "qc_value": round(qc_value, 3),
        "qc_ok": qc_ok,
        "run_id": "RUN-%s-%03d" % (line, index),
    }


def value_hash(packet: dict[str, Any]) -> str:
    body = {key: value for key, value in packet.items() if key not in {"adapter", "qc_ok"}}
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "VALUE", "raw": body})


def audit_hash(study_id: str, line: str, method: str, value_digest: str) -> str:
    return sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "AUDIT",
            "study_id": study_id,
            "line": line,
            "method": method,
            "value_hash": value_digest,
        }
    )


def qc_ok_for_packet(line: str, packet: dict[str, Any]) -> bool:
    low, high = LINES[line]["qc_window"]
    try:
        value = float(packet.get("qc_value"))
    except (TypeError, ValueError):
        return False
    return low <= value <= high and _flag(packet.get("qc_ok"))


def _base_row(
    row_id: str,
    study_id: str,
    *,
    sample_id: str,
    lot_id: str,
    package_id: str,
    line: str,
    method: str,
    valid_index: int | None = None,
    expected_hold: str | None = None,
    declared_source: str | None = None,
    qc_ok: bool = True,
) -> dict[str, Any]:
    index = valid_index or 1
    spec = LINES.get(line, {}).get("methods", {}).get(method)
    method_version = spec["version"] if spec else "UNKNOWN"
    packet = value_packet(index, line if line in LINES else "CCIT", method if spec else "VACUUM-DECAY", qc_ok=qc_ok)
    computed_source = source_hash(study_id, sample_id, lot_id, package_id) if study_id and sample_id and lot_id and package_id else ""
    return {
        "row_id": row_id,
        "study_id": study_id,
        "sample_id": sample_id,
        "lot_id": lot_id,
        "package_id": package_id,
        "component": "vial-closure" if line == "CCIT" else line.lower(),
        "line": line,
        "method": method,
        "method_version": method_version,
        "raw": packet,
        "source_hash": computed_source if declared_source is None else declared_source,
        "method_hash": method_hash(line, method, method_version) if spec else "",
        "instrument_hash": instrument_hash(packet["instrument_id"], packet["run_id"]) if spec else "",
        "value_hash": value_hash(packet),
        "unit_hash": unit_hash(line, method) if spec else "",
        "expected_hold": expected_hold,
        "interface_state": "SIMULATED",
        "interface_live": False,
    }


def build_acceptance_fixture() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(1, VALID_COUNT + 1):
        line = line_for(index)
        rows.append(
            _base_row(
                "R%03d" % index,
                valid_study_id(index),
                sample_id=valid_sample_id(index),
                lot_id=valid_lot_id(index),
                package_id="PKG-%03d" % index,
                line=line,
                method=method_for(line, index),
                valid_index=index,
            )
        )
    for offset in range(8):
        target = offset + 1
        rows.append(
            _base_row(
                "R%03d" % (91 + offset),
                valid_study_id(target),
                sample_id=valid_sample_id(target),
                lot_id=valid_lot_id(target),
                package_id="PKG-HDUP%02d" % (offset + 1),
                line=line_for(target),
                method=method_for(line_for(target), target),
                expected_hold="DUPLICATE_ID",
            )
        )
    for offset, (line, method) in enumerate(MISROUTE_PAIRS):
        rows.append(
            _base_row(
                "R%03d" % (99 + offset),
                "CSA-STU-HMIS%02d" % (offset + 1),
                sample_id="CSA-SMP-HMIS%02d" % (offset + 1),
                lot_id="CSA-LOT-HMIS%02d" % (offset + 1),
                package_id="PKG-HMIS%02d" % (offset + 1),
                line=line,
                method=method,
                expected_hold="WRONG_LINE_METHOD",
            )
        )
    missing_fields = ("study_id", "package_id", "study_id", "package_id", "lot_id")
    for offset, field in enumerate(missing_fields):
        kwargs = {
            "sample_id": "CSA-SMP-HMETA%02d" % (offset + 1),
            "lot_id": "CSA-LOT-HMETA%02d" % (offset + 1),
            "package_id": "PKG-HMETA%02d" % (offset + 1),
        }
        study_id = "CSA-STU-HMETA%02d" % (offset + 1)
        if field == "study_id":
            study_id = ""
        if field == "package_id":
            kwargs["package_id"] = ""
        if field == "lot_id":
            kwargs["lot_id"] = ""
        rows.append(
            _base_row(
                "R%03d" % (106 + offset),
                study_id,
                line="CCIT",
                method="VACUUM-DECAY",
                expected_hold="MISSING_STUDY_PACKAGE",
                **kwargs,
            )
        )
    for offset in range(5):
        index = 91 + offset
        line = line_for(index)
        rows.append(
            _base_row(
                "R%03d" % (111 + offset),
                "CSA-STU-HQC%02d" % (offset + 1),
                sample_id="CSA-SMP-HQC%02d" % (offset + 1),
                lot_id="CSA-LOT-HQC%02d" % (offset + 1),
                package_id="PKG-HQC%02d" % (offset + 1),
                line=line,
                method=method_for(line, index),
                valid_index=index,
                expected_hold="INSTRUMENT_QC_FAILURE",
                qc_ok=False,
            )
        )
    for offset in range(5):
        index = 1 + offset
        line = line_for(index)
        rows.append(
            _base_row(
                "R%03d" % (116 + offset),
                "CSA-STU-HSRC%02d" % (offset + 1),
                sample_id="CSA-SMP-HSRC%02d" % (offset + 1),
                lot_id="CSA-LOT-HSRC%02d" % (offset + 1),
                package_id="PKG-HSRC%02d" % (offset + 1),
                line=line,
                method=method_for(line, index),
                valid_index=index,
                expected_hold="SOURCE_HASH_MISMATCH",
                declared_source="TAMPERED-SOURCE-%02d" % (offset + 1),
            )
        )
    if len(rows) != INPUT_COUNT:
        raise RuntimeError("acceptance fixture must be exactly %s rows, got %s" % (INPUT_COUNT, len(rows)))
    return rows


def fixture_manifest(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    inbound = deepcopy(rows if rows is not None else build_acceptance_fixture())
    body = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "lines": list(LINE_NAMES),
        "input_rows": len(inbound),
        "valid_rows": sum(1 for row in inbound if row.get("expected_hold") is None),
        "hold_rows": sum(1 for row in inbound if row.get("expected_hold")),
        "hold_plan": dict(HOLD_PLAN),
        "row_ids": [row["row_id"] for row in inbound],
        "study_ids": [row["study_id"] for row in inbound],
        "expected_holds": [row.get("expected_hold") for row in inbound],
        "interfaces": "SIMULATED",
        "interface_live": False,
        "production_writes": False,
        "autonomous_release": False,
        "compliance_decision": False,
    }
    body["fixture_sha256"] = sha256_hex({key: value for key, value in body.items() if key != "fixture_sha256"})
    return body


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "accessions": {},
        "holds": [],
        "events": [],
        "seen_ids": {},
        "scheduled": {},
    }


def _event(journal: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    journal["events"].append({"seq": len(journal["events"]) + 1, "kind": kind, **deepcopy(payload)})


def identity_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            _text(row.get("study_id")),
            _text(row.get("sample_id")),
            _text(row.get("lot_id")),
        ]
    )


def classify_row(row: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    study_id = _text(row.get("study_id"))
    sample_id = _text(row.get("sample_id"))
    lot_id = _text(row.get("lot_id"))
    package_id = _text(row.get("package_id"))
    line = _text(row.get("line"))
    method = _text(row.get("method"))
    key = identity_key(row)
    spec = LINES.get(line, {}).get("methods", {}).get(method)

    if key in journal["seen_ids"] and study_id and sample_id and lot_id:
        return {"ok": False, "code": "DUPLICATE_ID", "study_id": study_id or None}
    if spec is None:
        return {"ok": False, "code": "WRONG_LINE_METHOD", "study_id": study_id or None, "line": line, "method": method}
    if not study_id or not package_id or not lot_id or not sample_id:
        return {"ok": False, "code": "MISSING_STUDY_PACKAGE", "study_id": study_id or None}
    packet = deepcopy(row.get("raw") or {})
    if not qc_ok_for_packet(line, packet):
        return {"ok": False, "code": "INSTRUMENT_QC_FAILURE", "study_id": study_id}
    expected_source = source_hash(study_id, sample_id, lot_id, package_id)
    if _text(row.get("source_hash")) != expected_source:
        return {"ok": False, "code": "SOURCE_HASH_MISMATCH", "study_id": study_id}
    return {
        "ok": True,
        "study_id": study_id,
        "sample_id": sample_id,
        "lot_id": lot_id,
        "package_id": package_id,
        "line": line,
        "method": method,
        "method_version": spec["version"],
        "instrument": spec["instrument"],
        "route": LINES[line]["worklist"],
        "accession_id": accession_id(study_id, sample_id, lot_id),
        "identity_key": key,
    }


def rendered_report(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "demand_id": DEMAND_ID,
        "accession_id": record["accession_id"],
        "study_id": record["study_id"],
        "sample_id": record["sample_id"],
        "line": record["line"],
        "method": record["method"],
        "method_version": record["method_version"],
        "source_hash": record["source_hash"],
        "method_hash": record["method_hash"],
        "instrument_hash": record["instrument_hash"],
        "value_hash": record["value_hash"],
        "unit_hash": record["unit_hash"],
        "audit_hash": record["audit_hash"],
        "state": "STAGED",
        "released": bool(record.get("released")),
        "interface_live": False,
        "compliance_decision": False,
    }


def report_status(record: dict[str, Any]) -> str:
    if record.get("released"):
        return "RELEASED"
    return "STAGED_PENDING_NAMED_APPROVAL"


def ingest_row(journal: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    row_id = _text(row.get("row_id"))
    existing = next((item for item in journal["accessions"].values() if item["row_id"] == row_id), None)
    if existing is not None:
        _event(journal, "REPLAY_NOOP", {"accession_id": existing["accession_id"], "study_id": existing["study_id"]})
        return {"kind": "REPLAY_NOOP", "accession_id": existing["accession_id"], "study_id": existing["study_id"]}
    existing_hold = next((item for item in journal["holds"] if item["row_id"] == row_id), None)
    if existing_hold is not None:
        _event(journal, "REPLAY_NOOP", {"study_id": existing_hold.get("study_id"), "code": existing_hold["code"]})
        return {"kind": "REPLAY_NOOP", "study_id": existing_hold.get("study_id"), "code": existing_hold["code"]}

    verdict = classify_row(row, journal)
    if not verdict["ok"]:
        hold = {
            "row_id": row_id,
            "study_id": verdict.get("study_id"),
            "code": verdict["code"],
            "line": _text(row.get("line")) or None,
            "method": _text(row.get("method")) or None,
            "state": "HOLD",
            "scheduled": False,
            "worklist": None,
            "report": None,
            "released": False,
        }
        journal["holds"].append(hold)
        _event(journal, "HOLD", hold)
        return {"kind": "HOLD", "duplicate": False, **hold}

    acc_id = verdict["accession_id"]
    packet = deepcopy(row.get("raw") or {})
    value_digest = value_hash(packet)
    record = {
        "accession_id": acc_id,
        "row_id": row_id,
        "study_id": verdict["study_id"],
        "sample_id": verdict["sample_id"],
        "lot_id": verdict["lot_id"],
        "package_id": verdict["package_id"],
        "line": verdict["line"],
        "method": verdict["method"],
        "method_version": verdict["method_version"],
        "instrument": verdict["instrument"],
        "route": verdict["route"],
        "raw": packet,
        "source_hash": source_hash(verdict["study_id"], verdict["sample_id"], verdict["lot_id"], verdict["package_id"]),
        "method_hash": method_hash(verdict["line"], verdict["method"], verdict["method_version"]),
        "instrument_hash": instrument_hash(packet["instrument_id"], packet["run_id"]),
        "value_hash": value_digest,
        "unit_hash": unit_hash(verdict["line"], verdict["method"]),
        "audit_hash": audit_hash(verdict["study_id"], verdict["line"], verdict["method"], value_digest),
        "state": "READY",
        "scheduled": True,
        "released": False,
        "released_by": None,
        "report_status": "STAGED_PENDING_NAMED_APPROVAL",
        "interface_state": "SIMULATED",
        "interface_live": False,
    }
    record["report"] = rendered_report(record)
    record["report_hash"] = sha256_hex(record["report"])
    journal["accessions"][acc_id] = record
    journal["seen_ids"][verdict["identity_key"]] = row_id
    journal["scheduled"][acc_id] = verdict["route"]
    _event(journal, "READY", {"accession_id": acc_id, "study_id": verdict["study_id"], "route": verdict["route"]})
    return {"kind": "READY", "accession_id": acc_id, "route": verdict["route"]}


def release_report(
    journal: dict[str, Any],
    accession_id_value: str,
    *,
    actor_role: str,
    actor: str,
) -> dict[str, Any]:
    record = journal["accessions"].get(accession_id_value)
    if record is None:
        return {"ok": False, "code": "UNKNOWN_ACCESSION"}
    role = _text(actor_role).upper()
    if role != HUMAN_APPROVER:
        _event(
            journal,
            "RELEASE_DENIED",
            {
                "accession_id": accession_id_value,
                "code": "AUTONOMOUS_RELEASE_DENIED",
                "actor_role": role or None,
            },
        )
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED", "report_status": report_status(record)}
    if _text(actor) != NAMED_HUMAN:
        _event(
            journal,
            "RELEASE_DENIED",
            {
                "accession_id": accession_id_value,
                "code": "NAMED_HUMAN_REQUIRED",
                "actor": _text(actor) or None,
            },
        )
        return {"ok": False, "code": "NAMED_HUMAN_REQUIRED", "report_status": report_status(record)}
    if record["released"]:
        return {"ok": True, "duplicate": True, "report_status": "RELEASED"}
    record["released"] = True
    record["released_by"] = NAMED_HUMAN
    record["report_status"] = "RELEASED"
    record["report"] = rendered_report(record)
    record["report_hash"] = sha256_hex(record["report"])
    _event(journal, "RELEASED", {"accession_id": accession_id_value, "released_by": NAMED_HUMAN})
    return {"ok": True, "duplicate": False, "report_status": "RELEASED"}


def run_gate(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    inbound = deepcopy(rows if rows is not None else build_acceptance_fixture())
    journal = empty_journal()
    effects = [ingest_row(journal, row) for row in inbound]
    autonomous = [
        release_report(journal, acc_id, actor_role="SYSTEM", actor="autonomous")
        for acc_id in journal["accessions"]
    ]
    ready = sorted(journal["accessions"].values(), key=lambda item: item["study_id"])
    hold_codes = [item["code"] for item in journal["holds"]]
    reports = [item["report"] for item in ready]
    lineage = [
        {
            "study_id": item["study_id"],
            "source_hash": item["source_hash"],
            "method_hash": item["method_hash"],
            "instrument_hash": item["instrument_hash"],
            "value_hash": item["value_hash"],
            "unit_hash": item["unit_hash"],
            "audit_hash": item["audit_hash"],
            "report_hash": item["report_hash"],
        }
        for item in ready
    ]
    audit = {
        "demand_id": DEMAND_ID,
        "study_ids": [item["study_id"] for item in ready],
        "accession_ids": [item["accession_id"] for item in ready],
        "hold_codes": hold_codes,
        "hold_study_ids": [item["study_id"] for item in journal["holds"]],
        "routes": {item["study_id"]: item["route"] for item in ready},
        "lineage": lineage,
        "released": [item["study_id"] for item in ready if item["released"]],
    }
    body = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "input_rows": len(inbound),
        "ready": len(ready),
        "held": len(journal["holds"]),
        "hold_codes": hold_codes,
        "hold_code_set": sorted(set(hold_codes)),
        "scheduled_holds": sum(1 for item in journal["holds"] if item.get("scheduled")),
        "held_reports_staged": sum(1 for item in journal["holds"] if item.get("report")),
        "released_reports": sum(1 for item in ready if item["released"]),
        "staged_reports": sum(1 for item in ready if item["report_status"] == "STAGED_PENDING_NAMED_APPROVAL"),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "REPLAY_NOOP"),
        "effects": effects,
        "autonomous_release_effects": autonomous,
        "accessions": ready,
        "holds": deepcopy(journal["holds"]),
        "routes": {item["study_id"]: item["route"] for item in ready},
        "accession_ids": [item["accession_id"] for item in ready],
        "reports": reports,
        "report_digest": sha256_hex(reports),
        "lineage": lineage,
        "lineage_sha256": sha256_hex(lineage),
        "audit": audit,
        "audit_sha256": sha256_hex(audit),
        "interface_live": False,
        "interfaces": "SIMULATED",
        "autonomous_certification": False,
        "autonomous_release": False,
        "compliance_decision": False,
        "production_writes": 0,
        "pre_sale_transport": "NONE",
        "cash_usd": 0,
    }
    body["manifest_sha256"] = sha256_hex(
        {key: value for key, value in body.items() if key != "manifest_sha256"}
    )
    return body


def replay_into(journal: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    inbound = deepcopy(rows if rows is not None else build_acceptance_fixture())
    before = set(journal["accessions"])
    before_holds = {sha256_hex(item) for item in journal["holds"]}
    effects = [ingest_row(journal, row) for row in inbound]
    added = set(journal["accessions"]) - before
    added_holds = [item for item in journal["holds"] if sha256_hex(item) not in before_holds]
    return {
        "added_accessions": sorted(added),
        "added_accession_count": len(added),
        "added_holds": len(added_holds),
        "added_record_count": len(added) + len(added_holds),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "REPLAY_NOOP"),
        "accession_count": len(journal["accessions"]),
        "hold_count": len(journal["holds"]),
    }


def expected_actual(result: dict[str, Any]) -> dict[str, Any]:
    actual = {
        "input_rows": result.get("input_rows"),
        "ready": result.get("ready"),
        "held": result.get("held"),
        "scheduled_holds": result.get("scheduled_holds"),
        "held_reports_staged": result.get("held_reports_staged"),
        "released_reports": result.get("released_reports"),
        "staged_reports": result.get("staged_reports"),
        "replay_added_records": result.get("replay_added_records", 0),
        "production_writes": result.get("production_writes"),
    }
    return {"expected": dict(GOLDEN_COUNTS), "actual": actual, "match": actual == GOLDEN_COUNTS}


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures = []
    counts = expected_actual(result)
    if not counts["match"]:
        failures.append("counts")
    if result.get("hold_code_set") != sorted(HOLD_CODES):
        failures.append("hold_code_set")
    if Counter(result.get("hold_codes") or []) != Counter(HOLD_PLAN):
        failures.append("hold_code_counts")
    if len(set(result.get("accession_ids") or [])) != VALID_COUNT:
        failures.append("accession_ids_not_unique")
    for item in result.get("accessions") or []:
        expected_source = source_hash(item["study_id"], item["sample_id"], item["lot_id"], item["package_id"])
        if item.get("source_hash") != expected_source:
            failures.append("source_hash")
            break
        if item.get("method_hash") != method_hash(item["line"], item["method"], item["method_version"]):
            failures.append("method_hash")
            break
        if item.get("instrument_hash") != instrument_hash(item["raw"]["instrument_id"], item["raw"]["run_id"]):
            failures.append("instrument_hash")
            break
        if item.get("value_hash") != value_hash(item["raw"]):
            failures.append("value_hash")
            break
        if item.get("unit_hash") != unit_hash(item["line"], item["method"]):
            failures.append("unit_hash")
            break
        if item.get("audit_hash") != audit_hash(item["study_id"], item["line"], item["method"], item["value_hash"]):
            failures.append("audit_hash")
            break
        if item.get("report", {}).get("state") != "STAGED":
            failures.append("report_not_staged")
            break
        if item.get("released"):
            failures.append("released")
            break
        if item.get("route") != LINES[item["line"]]["worklist"]:
            failures.append("route")
            break
    if any(item.get("scheduled") or item.get("report") or item.get("released") for item in result.get("holds") or []):
        failures.append("hold_scheduled_or_released")
    if result.get("interface_live") is not False:
        failures.append("interface_live")
    if result.get("interfaces") != "SIMULATED":
        failures.append("interfaces")
    if result.get("autonomous_release") is not False:
        failures.append("autonomous_release")
    if result.get("compliance_decision") is not False:
        failures.append("compliance_decision")
    if not all(
        item.get("code") == "AUTONOMOUS_RELEASE_DENIED"
        for item in result.get("autonomous_release_effects") or []
    ):
        failures.append("autonomous_release_not_denied")
    if GOLDEN_AUDIT_SHA256 != "PENDING" and result.get("audit_sha256") != GOLDEN_AUDIT_SHA256:
        failures.append("audit_sha256")
    if GOLDEN_LINEAGE_SHA256 != "PENDING" and result.get("lineage_sha256") != GOLDEN_LINEAGE_SHA256:
        failures.append("lineage_sha256")
    if GOLDEN_REPORT_DIGEST != "PENDING" and result.get("report_digest") != GOLDEN_REPORT_DIGEST:
        failures.append("report_digest")
    return failures


def main() -> int:
    first = run_gate()
    second = run_gate()
    journal = empty_journal()
    for row in build_acceptance_fixture():
        ingest_row(journal, row)
    replay = replay_into(journal)
    first["replay_added_records"] = replay["added_record_count"]
    failures = pass_contract(first)
    if first.get("audit_sha256") != second.get("audit_sha256"):
        failures.append("replay_mismatch")
    if replay.get("added_record_count") != 0:
        failures.append("replay_added_records")
    counts = expected_actual(first)
    report = {
        "ok": not failures,
        "failures": failures,
        "expected": counts["expected"],
        "actual": counts["actual"],
        "fixture_sha256": fixture_manifest()["fixture_sha256"],
        "audit_sha256": first.get("audit_sha256"),
        "lineage_sha256": first.get("lineage_sha256"),
        "report_digest": first.get("report_digest"),
        "manifest_sha256": first.get("manifest_sha256"),
        "ready": first.get("ready"),
        "held": first.get("held"),
        "hold_codes": sorted(set(first.get("hold_codes") or [])),
        "staged_reports": first.get("staged_reports"),
        "replay_added_records": replay.get("added_record_count"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
