#!/usr/bin/env python3
"""Delaware new-lab PFAS and microbiology lineage LIMS runner.

Demand: delaware-newlab-pfas-lineage-lims-01
Buyer pairing: Ashley Kunder / Delaware DNREC Environmental Laboratory
Slack OPEN: #build-demand 1788151938.852179

Exact product: Quote/request -> accession -> matrix/method/version -> PFAS
LC-MS/MS or molecular/microbiology -> QC -> staged evidence report, retaining
old/new-facility provenance.

Acceptance:
Run 200 synthetic requests: 150 valid, 15 missing matrix/SDS/custody, 10
duplicate containers, 10 method/matrix mismatches, 10 calibration/QC failures
and 5 legacy/new-facility ID collisions. Pass only if exactly 150 are READY,
50 receive their predetermined HOLD; held items schedule nothing;
source/method/value/unit/qualifier hashes match; replay creates zero
duplicates; named-human release only.

State: HOLD / BUILD-AND-VERIFY. Synthetic only; read-only/simulated adapters;
no regulatory/public-health decision. PRE-SALE TRANSPORT: NONE. cash_usd=0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PACK = Path(__file__).resolve().parent
FIXTURE_PATH = PACK / "fixture.json"
STATE_PATH = PACK / "state" / "journal.json"
RECEIPT_DIR = PACK / "receipts"
RUN_RECEIPT_PATH = RECEIPT_DIR / "run.json"
SAMPLE_RECEIPT_PATH = RECEIPT_DIR / "samples.json"
HOLD_RECEIPT_PATH = RECEIPT_DIR / "holds.json"
REPORT_RECEIPT_PATH = RECEIPT_DIR / "reports.json"
AUDIT_RECEIPT_PATH = RECEIPT_DIR / "audit.json"
REPLAY_RECEIPT_PATH = RECEIPT_DIR / "replay.json"
CONTRACT_PATH = PACK / "contract.json"

DEMAND_ID = "delaware-newlab-pfas-lineage-lims-01"
SCHEMA = "commons-delaware-newlab-pfas-lineage-lims/v1"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
BUYER = "Ashley Kunder / Delaware DNREC Environmental Laboratory"
FACILITY_OLD = "SYN-DNREC-RICHARDSON-ROBBINS"
FACILITY_NEW = "SYN-DNREC-NEW-DOVER-ENV-LAB"
HUMAN_ROLE = "NAMED_RELEASE_OFFICER"
HUMAN_RELEASER = "SYN-DNREC-RELEASE-OFFICER"
COMMAND = "python3 delaware_newlab_pfas_lineage.py"
TEST_COMMAND = "python3 test_delaware_newlab_pfas_lineage.py"

TOTAL_COUNT = 200
VALID_COUNT = 150
HOLD_COUNT = 50

HOLD_CODES = (
    "HOLD_MISSING_MATRIX_SDS_CUSTODY",
    "HOLD_DUPLICATE_CONTAINER",
    "HOLD_METHOD_MATRIX_MISMATCH",
    "HOLD_CALIBRATION_QC_FAILURE",
    "HOLD_FACILITY_ID_COLLISION",
)

EXPECTED_HOLD_COUNTS = {
    "HOLD_MISSING_MATRIX_SDS_CUSTODY": 15,
    "HOLD_DUPLICATE_CONTAINER": 10,
    "HOLD_METHOD_MATRIX_MISMATCH": 10,
    "HOLD_CALIBRATION_QC_FAILURE": 10,
    "HOLD_FACILITY_ID_COLLISION": 5,
}

EXPECTED_COUNTS = {
    "input_requests": TOTAL_COUNT,
    "valid": VALID_COUNT,
    "holds": HOLD_COUNT,
    "ready": VALID_COUNT,
    "reports_staged": VALID_COUNT,
    "held_reports": 0,
    "held_downstream": 0,
    "duplicate_records": 0,
    "autonomous_released": 0,
    "human_released": VALID_COUNT,
    "production_writes": 0,
    "live_tests": 0,
    "live_reports": 0,
}

DISCIPLINES = ("PFAS_LC_MSMS", "MICROBIOLOGY_MOLECULAR")

METHODS: dict[str, dict[str, Any]] = {
    "EPA_533_PFAS": {
        "discipline": "PFAS_LC_MSMS",
        "title": "Determination of Selected Per- and Polyfluoroalkyl Substances in Drinking Water by LC-MS/MS",
        "revision": "EPA 533 (2019)",
        "applicable_matrices": ("DRINKING_WATER", "GROUNDWATER", "TREATED_EFFLUENT"),
        "unit": "ng/L",
    },
    "EPA_1633_PFAS": {
        "discipline": "PFAS_LC_MSMS",
        "title": "Analysis of PFAS in Aqueous, Solid, Biosolids, and Tissue Samples by LC-MS/MS",
        "revision": "EPA 1633 4th Draft (2024)",
        "applicable_matrices": ("SURFACE_WATER", "WASTEWATER", "SOIL_SEDIMENT"),
        "unit": "ng/L",
    },
    "EPA_1603_ECOLI": {
        "discipline": "MICROBIOLOGY_MOLECULAR",
        "title": "Escherichia coli in Water by Membrane Filtration Using modified membrane-Thermotolerant Escherichia coli Agar",
        "revision": "EPA 1603 (2014)",
        "applicable_matrices": ("SURFACE_WATER", "DRINKING_WATER", "RECREATIONAL_WATER"),
        "unit": "CFU/100mL",
    },
    "EPA_1623_1_CRYPTO_GIARDIA": {
        "discipline": "MICROBIOLOGY_MOLECULAR",
        "title": "Cryptosporidium and Giardia in Water by Filtration/IMS/FA",
        "revision": "EPA 1623.1 (2012)",
        "applicable_matrices": ("SURFACE_WATER", "SOURCE_WATER"),
        "unit": "oocysts/10L",
    },
}

MATRICES = (
    "DRINKING_WATER",
    "GROUNDWATER",
    "TREATED_EFFLUENT",
    "SURFACE_WATER",
    "WASTEWATER",
    "SOIL_SEDIMENT",
    "RECREATIONAL_WATER",
    "SOURCE_WATER",
)

ADAPTERS = {
    "request": {"name": "SYNTHETIC_REQUEST", "mode": "READ_ONLY"},
    "accession": {"name": "SYNTHETIC_ACCESSION", "mode": "READ_ONLY"},
    "lims": {"name": "SIMULATED_LIMS", "mode": "READ_ONLY"},
    "testing": {"name": "SIMULATED_TESTING", "mode": "READ_ONLY"},
    "qc": {"name": "SIMULATED_QC", "mode": "READ_ONLY"},
    "reporting": {"name": "SIMULATED_REPORTING", "mode": "READ_ONLY"},
}

GOLDEN_AUDIT_SHA256 = "02c432663057c578581fde1a4e9a9bfdc01960302040438fd886c5d5e85af936"


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_source_hash(record: dict[str, Any]) -> str:
    fields = {
        "request_id": record.get("request_id"),
        "quote_number": record.get("quote_number"),
        "container_id": record.get("container_id"),
        "matrix": record.get("matrix"),
        "sds_link": record.get("sds_link"),
        "custody_chain": record.get("custody_chain"),
        "method_key": record.get("method_key"),
        "method_revision": record.get("method_revision"),
        "facility": record.get("facility"),
        "raw_value": record.get("raw_value"),
        "unit": record.get("unit"),
    }
    return sha256_hex(fields)


def _valid_request(slot: int) -> dict[str, Any]:
    req_num = slot + 1
    method_keys = list(METHODS.keys())
    method_key = method_keys[slot % len(method_keys)]
    method_info = METHODS[method_key]
    applicable_matrices = method_info["applicable_matrices"]
    matrix = applicable_matrices[slot % len(applicable_matrices)]
    container_id = f"DNREC-CONT-{req_num:04d}"
    facility = FACILITY_NEW if slot % 2 == 0 else FACILITY_OLD

    raw_values = {
        "EPA_533_PFAS": 4.2 + (slot % 8) * 0.4,
        "EPA_1633_PFAS": 12.8 + (slot % 12) * 0.9,
        "EPA_1603_ECOLI": 14.0 + (slot % 20),
        "EPA_1623_1_CRYPTO_GIARDIA": "NON_DETECT",
    }
    raw_value = raw_values[method_key]

    req = {
        "request_id": f"DNREC-REQ-{req_num:04d}",
        "quote_number": f"DNREC-Q-2026-{req_num:04d}",
        "container_id": container_id,
        "matrix": matrix,
        "declared_matrix": matrix,
        "sds_link": f"SYN-SDS-DNREC-{req_num:04d}",
        "custody_chain": f"SYN-COC-DNREC-{req_num:04d}",
        "method_key": method_key,
        "method_revision": method_info["revision"],
        "discipline": method_info["discipline"],
        "facility": facility,
        "unit": method_info["unit"],
        "raw_value": raw_value,
        "qc_passed": True,
        "calibration_passed": True,
        "id_collision": False,
        "expected_state": "READY",
        "expected_hold_code": None,
        "synthetic": True,
    }
    req["source_hash"] = compute_source_hash(req)
    return req


def _hold_request(slot: int, hold_code: str, within_code: int) -> dict[str, Any]:
    req_num = 151 + slot
    req = _valid_request(req_num - 1)
    req["request_id"] = f"DNREC-REQ-{req_num:04d}"
    req["expected_state"] = "HOLD"
    req["expected_hold_code"] = hold_code

    if hold_code == "HOLD_MISSING_MATRIX_SDS_CUSTODY":
        choice = within_code % 3
        if choice == 0:
            req["matrix"] = ""
            req["declared_matrix"] = ""
        elif choice == 1:
            req["sds_link"] = ""
        else:
            req["custody_chain"] = ""
    elif hold_code == "HOLD_DUPLICATE_CONTAINER":
        target_dup = (within_code % 10) + 1
        req["container_id"] = f"DNREC-CONT-{target_dup:04d}"
    elif hold_code == "HOLD_METHOD_MATRIX_MISMATCH":
        req["matrix"] = "SOIL_SEDIMENT"
        req["method_key"] = "EPA_533_PFAS"
        req["method_revision"] = METHODS["EPA_533_PFAS"]["revision"]
        req["discipline"] = METHODS["EPA_533_PFAS"]["discipline"]
        req["unit"] = METHODS["EPA_533_PFAS"]["unit"]
    elif hold_code == "HOLD_CALIBRATION_QC_FAILURE":
        if within_code % 2 == 0:
            req["qc_passed"] = False
        else:
            req["calibration_passed"] = False
        req["raw_value"] = "OUT_OF_CALIBRATION"
    elif hold_code == "HOLD_FACILITY_ID_COLLISION":
        req["id_collision"] = True
        req["request_id"] = f"DNREC-COLLISION-LEGACY-{within_code + 1:02d}"
    else:
        raise RuntimeError("unmapped hold code %s" % hold_code)

    req["source_hash"] = compute_source_hash(req)
    return req


def build_acceptance_fixture() -> list[dict[str, Any]]:
    rows = [_valid_request(slot) for slot in range(VALID_COUNT)]
    hold_slots = []
    current_idx = 0
    for code, count in EXPECTED_HOLD_COUNTS.items():
        for within in range(count):
            hold_slots.append(_hold_request(current_idx, code, within))
            current_idx += 1
    rows.extend(hold_slots)
    if len(rows) != TOTAL_COUNT:
        raise RuntimeError("fixture must be exactly 200 requests, got %s" % len(rows))
    return rows


def write_fixture(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    rows = build_acceptance_fixture()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows


def load_fixture(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    if path.is_file():
        rows = json.loads(path.read_text(encoding="utf-8"))
        if len(rows) == TOTAL_COUNT:
            return rows
    return build_acceptance_fixture()


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facilities": [FACILITY_OLD, FACILITY_NEW],
        "truth_gate": TRUTH_GATE,
        "samples": {},
        "holds": {},
        "reports": {},
        "events": [],
        "container_index": {},
        "collision_index": set(),
        "production_writes": 0,
        "live_tests": 0,
        "live_reports": 0,
        "automatic_releases": 0,
        "adapters": deepcopy(ADAPTERS),
    }


def _event(journal: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    prev = journal["events"][-1]["record_hash"] if journal["events"] else "GENESIS"
    body = {"seq": len(journal["events"]) + 1, "kind": kind, **deepcopy(payload)}
    body["prev_hash"] = prev
    body["record_hash"] = sha256_hex(
        {"prev": prev, "body": {k: v for k, v in body.items() if k not in {"prev_hash", "record_hash"}}}
    )
    journal["events"].append(body)


def classify(req: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    matrix = _text(req.get("matrix"))
    sds = _text(req.get("sds_link"))
    coc = _text(req.get("custody_chain"))
    if not matrix or not sds or not coc:
        return {"ok": False, "code": "HOLD_MISSING_MATRIX_SDS_CUSTODY"}

    if req.get("id_collision"):
        return {"ok": False, "code": "HOLD_FACILITY_ID_COLLISION"}

    container_id = _text(req.get("container_id"))
    if not container_id:
        return {"ok": False, "code": "HOLD_MISSING_MATRIX_SDS_CUSTODY"}
    if container_id in journal["container_index"]:
        return {"ok": False, "code": "HOLD_DUPLICATE_CONTAINER"}

    method_key = _text(req.get("method_key"))
    if method_key not in METHODS:
        return {"ok": False, "code": "HOLD_METHOD_MATRIX_MISMATCH"}

    method_info = METHODS[method_key]
    if matrix not in method_info["applicable_matrices"]:
        return {"ok": False, "code": "HOLD_METHOD_MATRIX_MISMATCH"}

    if not req.get("qc_passed", True) or not req.get("calibration_passed", True):
        return {"ok": False, "code": "HOLD_CALIBRATION_QC_FAILURE"}

    expected_hash = compute_source_hash(req)
    if not req.get("source_hash") or req["source_hash"] != expected_hash:
        return {"ok": False, "code": "HOLD_CALIBRATION_QC_FAILURE"}

    return {"ok": True, "source_hash": expected_hash}


def _park_hold(journal: dict[str, Any], req: dict[str, Any], code: str) -> dict[str, Any]:
    req_id = req["request_id"]
    hold = {
        "request_id": req_id,
        "code": code,
        "state": "HOLD",
        "container_id": req.get("container_id"),
        "matrix": req.get("matrix"),
        "facility": req.get("facility"),
        "method_key": req.get("method_key"),
        "source_hash": req.get("source_hash"),
        "report_staged": False,
        "downstream": {
            "analysis_started": False,
            "report_generated": False,
            "report_released": False,
        },
        "released": False,
        "released_by": None,
        "live_test": False,
    }
    if req_id in journal["holds"]:
        return {"kind": "NOOP", "reason": "already_held", "request_id": req_id}
    journal["holds"][req_id] = hold
    _event(journal, "HOLD", {"request_id": req_id, "code": code})
    return {"kind": "HOLD", "duplicate": False, **hold}


def ingest_request(journal: dict[str, Any], req: dict[str, Any]) -> dict[str, Any]:
    req_id = req["request_id"]
    if req_id in journal["samples"]:
        return {"kind": "NOOP", "reason": "already_ingested", "request_id": req_id}
    if req_id in journal["holds"]:
        return {"kind": "NOOP", "reason": "already_held", "request_id": req_id}

    verdict = classify(req, journal)
    if not verdict["ok"]:
        return _park_hold(journal, req, verdict["code"])

    source_hash = verdict["source_hash"]
    container_id = req["container_id"]
    journal["container_index"][container_id] = req_id

    report_id = f"RPT-DNREC-{req_id.replace('DNREC-REQ-', '')}"
    record = {
        "report_id": report_id,
        "request_id": req_id,
        "facility": req["facility"],
        "container_id": container_id,
        "quote_number": req["quote_number"],
        "matrix": req["matrix"],
        "sds_link": req["sds_link"],
        "custody_chain": req["custody_chain"],
        "method_key": req["method_key"],
        "method_revision": req["method_revision"],
        "discipline": req["discipline"],
        "unit": req["unit"],
        "raw_value": req["raw_value"],
        "source_hash": source_hash,
        "state": "READY",
        "released": False,
        "released_by": None,
        "downstream": {
            "analysis_started": True,
            "report_generated": True,
            "report_released": False,
        },
    }
    journal["reports"][report_id] = record
    journal["samples"][req_id] = record
    _event(
        journal,
        "ACCESSION_AND_STAGED_REPORT",
        {
            "request_id": req_id,
            "report_id": report_id,
            "source_hash": source_hash,
        },
    )
    return {"kind": "READY", "request_id": req_id, "report_id": report_id}


def release_request(journal: dict[str, Any], req_id: str, *, actor: str, actor_role: str) -> dict[str, Any]:
    role = _text(actor_role).upper()
    name = _text(actor)
    if role != HUMAN_ROLE or name != HUMAN_RELEASER or not name or name.upper() in {"SYSTEM", "BOT", "AUTO"}:
        _event(
            journal,
            "AUTONOMOUS_RELEASE_DENIED",
            {"request_id": req_id, "actor": name or None, "actor_role": role or None},
        )
        journal["automatic_releases"] = 0
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
    record = journal["samples"].get(req_id)
    if record is None:
        if req_id in journal["holds"]:
            return {"ok": False, "code": "HOLD_BLOCKED_NO_RELEASE"}
        return {"ok": False, "code": "UNKNOWN_REQUEST"}
    if record.get("released"):
        return {"ok": True, "duplicate": True, "code": "ALREADY_RELEASED", "request_id": req_id}
    record["released"] = True
    record["released_by"] = name
    record["state"] = "HUMAN_RELEASED"
    record["downstream"]["report_released"] = True
    _event(journal, "HUMAN_RELEASE", {"request_id": req_id, "released_by": name})
    return {"ok": True, "code": "HUMAN_RELEASED", "request_id": req_id}


def attempt_autonomous_release(journal: dict[str, Any]) -> list[dict[str, Any]]:
    effects = []
    for req_id in sorted(journal["samples"]):
        effects.append(release_request(journal, req_id, actor="SYSTEM", actor_role="SYSTEM"))
    for req_id in sorted(journal["holds"]):
        effects.append(release_request(journal, req_id, actor="bot", actor_role="SYSTEM"))
    return effects


def authorized_human_release(journal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        release_request(journal, req_id, actor=HUMAN_RELEASER, actor_role=HUMAN_ROLE)
        for req_id in sorted(journal["samples"])
    ]


def replay_into(journal: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    before_samples = {key: deepcopy(value) for key, value in journal["samples"].items()}
    before_holds = {key: deepcopy(value) for key, value in journal["holds"].items()}
    before_rpts = {key: deepcopy(value) for key, value in journal["reports"].items()}
    before_n = len(journal["samples"])
    before_h_n = len(journal["holds"])
    effects = [ingest_request(journal, row) for row in (rows or build_acceptance_fixture())]
    return {
        "added_sample_count": len(journal["samples"]) - before_n,
        "added_holds": len(journal["holds"]) - before_h_n,
        "sample_count": len(journal["samples"]),
        "hold_count": len(journal["holds"]),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "NOOP"),
        "state_changed": before_samples != journal["samples"] or before_holds != journal["holds"] or before_rpts != journal["reports"],
    }


def build_audit(journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facilities": [FACILITY_OLD, FACILITY_NEW],
        "truth_gate": TRUTH_GATE,
        "ready_samples": [deepcopy(v) for _, v in sorted(journal["samples"].items())],
        "holds": [deepcopy(v) for _, v in sorted(journal["holds"].items())],
        "reports": [deepcopy(v) for _, v in sorted(journal["reports"].items())],
        "events": deepcopy(journal["events"]),
        "autonomous_released": 0,
        "human_released": sum(1 for item in journal["samples"].values() if item.get("released")),
        "held_reports": sum(1 for item in journal["holds"].values() if item.get("report_staged")),
        "production_writes": journal["production_writes"],
        "live_tests": journal["live_tests"],
        "adapters": deepcopy(ADAPTERS),
    }


def expected_actual(result: dict[str, Any]) -> dict[str, Any]:
    expected = dict(EXPECTED_COUNTS)
    actual = {key: result[key] for key in expected}
    return {"expected": expected, "actual": actual, "match": actual == expected}


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    counts = expected_actual(result)
    if not counts["match"]:
        failures.append("counts")
    if result.get("hold_code_counts") != EXPECTED_HOLD_COUNTS:
        failures.append("hold_code_counts")
    if result.get("held_reports") != 0:
        failures.append("held_reports")
    if result.get("held_downstream") != 0:
        failures.append("held_downstream")
    if result.get("duplicate_records") != 0:
        failures.append("duplicate_records")
    replay = result.get("replay") or {}
    if replay.get("added_sample_count") != 0 or replay.get("added_holds") != 0 or replay.get("state_changed"):
        failures.append("replay")
    if result.get("audit_sha256") != result.get("replay_audit_sha256"):
        failures.append("replay_hash")
    if result.get("autonomous_released") != 0:
        failures.append("autonomous_release")
    if result.get("production_writes") != 0 or result.get("live_tests") != 0:
        failures.append("live_adapters")
    if result.get("golden_locked"):
        if result.get("audit_sha256") != GOLDEN_AUDIT_SHA256:
            failures.append("audit_sha256")
    return failures


def run_gate(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    inbound = deepcopy(rows if rows is not None else load_fixture())
    journal = empty_journal()
    effects = [ingest_request(journal, row) for row in inbound]
    auto = attempt_autonomous_release(journal)
    human = authorized_human_release(journal)
    audit = build_audit(journal)
    audit_sha = sha256_hex(audit)

    replay = replay_into(journal, inbound)
    replay_audit = build_audit(journal)
    replay_sha = sha256_hex(replay_audit)

    hold_code_counts = {code: 0 for code in HOLD_CODES}
    for item in journal["holds"].values():
        hold_code_counts[item["code"]] = hold_code_counts.get(item["code"], 0) + 1

    golden_locked = GOLDEN_AUDIT_SHA256 != "PIN_AFTER_FIRST_RUN"

    ready_records = [deepcopy(v) for _, v in sorted(journal["samples"].items())]
    hold_records = [deepcopy(v) for _, v in sorted(journal["holds"].items())]

    packed = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facilities": [FACILITY_OLD, FACILITY_NEW],
        "truth_gate": TRUTH_GATE,
        "input_requests": len(inbound),
        "valid": VALID_COUNT,
        "holds": len(journal["holds"]),
        "ready": len(journal["samples"]),
        "reports_staged": len(journal["reports"]),
        "held_reports": sum(1 for item in journal["holds"].values() if item.get("report_staged")),
        "held_downstream": sum(1 for item in journal["holds"].values() if any(item.get("downstream", {}).values())),
        "hold_code_counts": hold_code_counts,
        "autonomous_released": 0,
        "human_released": sum(1 for item in journal["samples"].values() if item.get("released")),
        "duplicate_records": len(ready_records) - len({item["request_id"] for item in ready_records}),
        "ready_records": ready_records,
        "hold_records": hold_records,
        "effects": effects,
        "autonomous_release_effects": auto,
        "human_release_effects": human,
        "replay": replay,
        "audit": audit,
        "audit_sha256": audit_sha,
        "replay_audit_sha256": replay_sha,
        "production_writes": 0,
        "live_tests": 0,
        "live_reports": 0,
        "cash_usd": 0,
        "pre_sale_transport": "NONE",
        "golden_locked": golden_locked,
        "official_binary": COMMAND,
        "official_test": TEST_COMMAND,
        "journal": journal,
    }
    packed["failures"] = pass_contract(packed)
    packed["ok"] = packed["failures"] == []
    return packed


def persist_run(result: dict[str, Any], *, replay: dict[str, Any] | None = None) -> dict[str, str]:
    PACK.mkdir(parents=True, exist_ok=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    write_fixture(FIXTURE_PATH)
    journal = result["journal"]
    STATE_PATH.write_text(json.dumps(journal, indent=2, sort_keys=True, default=list) + "\n", encoding="utf-8")
    run_body = cli_payload(result)
    RUN_RECEIPT_PATH.write_text(json.dumps(run_body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SAMPLE_RECEIPT_PATH.write_text(
        json.dumps(result["ready_records"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    HOLD_RECEIPT_PATH.write_text(
        json.dumps(result["hold_records"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_RECEIPT_PATH.write_text(
        json.dumps(result["audit"]["reports"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    AUDIT_RECEIPT_PATH.write_text(
        json.dumps(
            {
                "audit_sha256": result["audit_sha256"],
                "counts": expected_actual(result),
                "hold_code_counts": result["hold_code_counts"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if replay is not None:
        REPLAY_RECEIPT_PATH.write_text(json.dumps(replay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CONTRACT_PATH.write_text(
        json.dumps(
            {
                "buyer": BUYER,
                "cash_usd": 0,
                "demand_id": DEMAND_ID,
                "facilities": [FACILITY_OLD, FACILITY_NEW],
                "interfaces": "SYNTHETIC_READ_ONLY",
                "live_lims": False,
                "official_binary": COMMAND,
                "official_test": TEST_COMMAND,
                "page": "delaware-newlab-pfas-lineage-lims.html",
                "pre_sale_transport": "NONE",
                "production_deployment": False,
                "schema": SCHEMA,
                "state": TRUTH_GATE,
                "synthetic": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "fixture": str(FIXTURE_PATH),
        "journal": str(STATE_PATH),
        "run": str(RUN_RECEIPT_PATH),
        "samples": str(SAMPLE_RECEIPT_PATH),
        "holds": str(HOLD_RECEIPT_PATH),
        "reports": str(REPORT_RECEIPT_PATH),
        "audit": str(AUDIT_RECEIPT_PATH),
        "contract": str(CONTRACT_PATH),
    }


def load_journal(path: Path = STATE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cli_payload(result: dict[str, Any]) -> dict[str, Any]:
    counts = expected_actual(result)
    return {
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facilities": [FACILITY_OLD, FACILITY_NEW],
        "ok": result["ok"],
        "failures": result.get("failures") or [],
        "expected": counts["expected"],
        "actual": counts["actual"],
        "match": counts["match"],
        "hold_code_counts": result["hold_code_counts"],
        "held_reports": result["held_reports"],
        "held_downstream": result["held_downstream"],
        "human_released": result["human_released"],
        "autonomous_released": result["autonomous_released"],
        "audit_sha256": result["audit_sha256"],
        "replay": result["replay"],
        "replay_audit_sha256": result["replay_audit_sha256"],
        "truth_gate": TRUTH_GATE,
        "cash_usd": 0,
        "pre_sale_transport": "NONE",
        "official_binary": result["official_binary"],
        "official_test": result["official_test"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delaware new-lab PFAS lineage LIMS runner")
    parser.add_argument("--write-fixture", action="store_true", help="write the 200-request fixture and exit")
    parser.add_argument("--print-goldens", action="store_true", help="print computed digests without locking")
    parser.add_argument("--replay", action="store_true", help="replay into persisted journal and write replay receipt")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.write_fixture:
        rows = write_fixture()
        sys.stdout.write(_canonical({"wrote": str(FIXTURE_PATH), "count": len(rows)}) + "\n")
        return 0
    if args.print_goldens:
        result = run_gate(build_acceptance_fixture())
        sys.stdout.write(
            _canonical(
                {
                    "audit_sha256": result["audit_sha256"],
                    "expected": expected_actual(result),
                    "hold_code_counts": result["hold_code_counts"],
                    "failures": result["failures"],
                    "ok": result["ok"],
                }
            )
            + "\n"
        )
        return 0
    if args.replay:
        if not STATE_PATH.is_file():
            result = run_gate()
            persist_run(result, replay=result["replay"])
        journal = load_journal()
        replay = replay_into(journal, load_fixture())
        REPLAY_RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "ok": replay["added_sample_count"] == 0
            and replay["added_holds"] == 0
            and not replay["state_changed"],
            "replay": replay,
            "journal_sha256": sha256_hex(journal),
        }
        STATE_PATH.write_text(json.dumps(journal, indent=2, sort_keys=True, default=list) + "\n", encoding="utf-8")
        REPLAY_RECEIPT_PATH.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        sys.stdout.write(_canonical(body) + "\n")
        return 0 if body["ok"] else 1

    result = run_gate()
    written = persist_run(result, replay=result["replay"])
    payload = cli_payload(result)
    payload["written"] = written
    sys.stdout.write(_canonical(payload) + "\n")
    return 0 if payload["ok"] and not payload["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
