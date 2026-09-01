#!/usr/bin/env python3
"""MVMTC aerospace fastener/additive-coupon evidence LIMS runner.

Demand: mvmtc-aero-fastener-evidence-lims-01
Buyer pairing: Craig A. Riviello / Miami Valley Materials Testing Center
Slack OPEN: #build-demand 1788152176.847959

Exact product: Quote/PO + sample/container accession -> applicable A2LA
scope/method revision -> mechanical/chemical/metallography job -> QC -> staged
evidence pack for fasteners and additive coupons.

Acceptance:
Run 100 synthetic lots: 75 valid; 8 missing PO/quote links; 5 duplicate
containers; 4 out-of-scope methods; 4 chemistry/material mismatches; 4 QC
failures. Pass only if exactly 75 are READY, 25 receive exact HOLD codes;
holds create no worksheet; every ready record preserves
scope/method/specimen/raw-value/unit/source hashes; replay creates zero
duplicates; human-only release.

Boundary/state: No controlled drawings, weapon, vehicle, propulsion or mission
data. HOLD / BUILD-AND-VERIFY; synthetic/read-only. PRE-SALE TRANSPORT: NONE.
cash_usd=0.
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
LOT_RECEIPT_PATH = RECEIPT_DIR / "lots.json"
HOLD_RECEIPT_PATH = RECEIPT_DIR / "holds.json"
WORKSHEET_RECEIPT_PATH = RECEIPT_DIR / "worksheets.json"
AUDIT_RECEIPT_PATH = RECEIPT_DIR / "audit.json"
REPLAY_RECEIPT_PATH = RECEIPT_DIR / "replay.json"
CONTRACT_PATH = PACK / "contract.json"

DEMAND_ID = "mvmtc-aero-fastener-evidence-lims-01"
SCHEMA = "commons-mvmtc-aero-fastener-evidence-lims/v1"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
BUYER = "Craig A. Riviello / Miami Valley Materials Testing Center"
FACILITY = "SYN-MVMTC-VANDALIA-OH"
A2LA_CERT = "A2LA-CERT-2394.01"
HUMAN_ROLE = "NAMED_RELEASE_OFFICER"
HUMAN_RELEASER = "SYN-MVMTC-RELEASE-OFFICER"
COMMAND = "python3 mvmtc_aero_fastener_evidence.py"
TEST_COMMAND = "python3 test_mvmtc_aero_fastener_evidence.py"

LOT_COUNT = 100
VALID_COUNT = 75
HOLD_COUNT = 25

HOLD_CODES = (
    "HOLD_MISSING_PO_QUOTE",
    "HOLD_DUPLICATE_CONTAINER",
    "HOLD_OUT_OF_SCOPE_METHOD",
    "HOLD_CHEMISTRY_MATERIAL_MISMATCH",
    "HOLD_QC_FAILURE",
)

EXPECTED_HOLD_COUNTS = {
    "HOLD_MISSING_PO_QUOTE": 8,
    "HOLD_DUPLICATE_CONTAINER": 5,
    "HOLD_OUT_OF_SCOPE_METHOD": 4,
    "HOLD_CHEMISTRY_MATERIAL_MISMATCH": 4,
    "HOLD_QC_FAILURE": 4,
}

EXPECTED_COUNTS = {
    "input_lots": LOT_COUNT,
    "valid": VALID_COUNT,
    "holds": HOLD_COUNT,
    "ready": VALID_COUNT,
    "worksheets_created": VALID_COUNT,
    "held_worksheets": 0,
    "held_downstream": 0,
    "duplicate_records": 0,
    "autonomous_released": 0,
    "human_released": VALID_COUNT,
    "production_writes": 0,
    "live_tests": 0,
    "live_reports": 0,
}

TEST_DISCIPLINES = ("MECHANICAL", "METALLOGRAPHY", "CHEMICAL")

METHODS: dict[str, dict[str, Any]] = {
    "ASTM_F606_TENSILE": {
        "discipline": "MECHANICAL",
        "title": "Standard Test Methods for Determining the Mechanical Properties of Externally and Internally Threaded Fasteners, Washers, Direct Tension Indicators, and Rivets",
        "revision": "ASTM F606/F606M-21",
        "unit": "ksi",
        "in_scope": True,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH"),
    },
    "ASTM_E8_COUPON_TENSILE": {
        "discipline": "MECHANICAL",
        "title": "Standard Test Methods for Tension Testing of Metallic Materials (Additive Coupons)",
        "revision": "ASTM E8/E8M-22",
        "unit": "ksi",
        "in_scope": True,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH"),
    },
    "ASTM_E18_ROCKWELL_HARDNESS": {
        "discipline": "MECHANICAL",
        "title": "Standard Test Methods for Rockwell Hardness of Metallic Materials",
        "revision": "ASTM E18-22",
        "unit": "HRC",
        "in_scope": True,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH"),
    },
    "ASTM_E384_MICROINDENTATION": {
        "discipline": "METALLOGRAPHY",
        "title": "Standard Test Method for Microindentation Hardness of Materials",
        "revision": "ASTM E384-22",
        "unit": "HV",
        "in_scope": True,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH"),
    },
    "ASTM_E3_METALLOGRAPHY": {
        "discipline": "METALLOGRAPHY",
        "title": "Standard Guide for Preparation of Metallographic Specimens",
        "revision": "ASTM E3-11(2017)",
        "unit": "MICROSTRUCTURE_PASS",
        "in_scope": True,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH"),
    },
    "ASTM_E1479_OES_ICP_CHEM": {
        "discipline": "CHEMICAL",
        "title": "Standard Practice for Describing and Specifying Inductively Coupled Plasma Atomic Emission Spectrometers",
        "revision": "ASTM E1479-16(2021)",
        "unit": "WEIGHT_PCT",
        "in_scope": True,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH"),
    },
}

OUT_OF_SCOPE_METHODS = {
    "UNAPPROVED_CUSTOM_SONIC": {
        "discipline": "NON_DESTRUCTIVE",
        "title": "Unapproved Custom Ultrasonic Pulse Check",
        "revision": "MVMTC-UNAPPROVED-2026",
        "unit": "dB",
        "in_scope": False,
        "applicable_materials": ("INCONEL_718", "TI_6AL_4V"),
    },
    "UNACCREDITED_PROPULSION_TORQUE": {
        "discipline": "SPECIALIZED",
        "title": "Unaccredited Hot Gas Propulsive Torque Test",
        "revision": "DOD-RESTRICTED-EXCLUDED",
        "unit": "ft-lbs",
        "in_scope": False,
        "applicable_materials": ("INCONEL_718",),
    },
}

MATERIALS = ("INCONEL_718", "TI_6AL_4V", "A286_STAINLESS", "17_4_PH")
CATEGORIES = ("FASTENER_BOLT", "FASTENER_NUT", "ADDITIVE_COUPON_LPBF", "ADDITIVE_COUPON_DED")

ADAPTERS = {
    "order_po": {"name": "SYNTHETIC_ORDER_PO", "mode": "READ_ONLY"},
    "accession": {"name": "SYNTHETIC_ACCESSION", "mode": "READ_ONLY"},
    "lims": {"name": "SIMULATED_LIMS", "mode": "READ_ONLY"},
    "testing": {"name": "SIMULATED_TESTING", "mode": "READ_ONLY"},
    "qc": {"name": "SIMULATED_QC", "mode": "READ_ONLY"},
    "evidence_pack": {"name": "SIMULATED_EVIDENCE_PACK", "mode": "READ_ONLY"},
}

GOLDEN_AUDIT_SHA256 = "722ecae70d14f81049346418a001e2d26de6ab26a6f13f99e40cee2233621c64"


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_source_hash(record: dict[str, Any]) -> str:
    fields = {
        "lot_id": record.get("lot_id"),
        "quote_number": record.get("quote_number"),
        "po_number": record.get("po_number"),
        "container_id": record.get("container_id"),
        "category": record.get("category"),
        "material": record.get("material"),
        "method_key": record.get("method_key"),
        "method_revision": record.get("method_revision"),
        "raw_value": record.get("raw_value"),
        "unit": record.get("unit"),
        "specimen_count": record.get("specimen_count"),
    }
    return sha256_hex(fields)


def _valid_lot(slot: int) -> dict[str, Any]:
    lot_num = slot + 1
    method_keys = list(METHODS.keys())
    method_key = method_keys[slot % len(method_keys)]
    method_info = METHODS[method_key]
    material = MATERIALS[slot % len(MATERIALS)]
    category = CATEGORIES[slot % len(CATEGORIES)]
    container_id = f"MVMTC-CONT-{lot_num:03d}"
    quote_number = f"Q-2026-MVMTC-{lot_num:04d}"
    po_number = f"PO-AERO-{lot_num:05d}"
    specimen_count = 3 + (slot % 4)

    raw_values = {
        "ASTM_F606_TENSILE": 185.4 + (slot % 10) * 1.2,
        "ASTM_E8_COUPON_TENSILE": 178.2 + (slot % 10) * 1.1,
        "ASTM_E18_ROCKWELL_HARDNESS": 44.5 + (slot % 5) * 0.5,
        "ASTM_E384_MICROINDENTATION": 455.0 + (slot % 15) * 2.0,
        "ASTM_E3_METALLOGRAPHY": "ACCEPTABLE_GRAIN_SIZE_ASTM_8",
        "ASTM_E1479_OES_ICP_CHEM": "NOMINAL_CHEMISTRY_PASS",
    }
    raw_value = raw_values[method_key]

    lot = {
        "lot_id": f"MVMTC-LOT-{lot_num:03d}",
        "quote_number": quote_number,
        "po_number": po_number,
        "container_id": container_id,
        "category": category,
        "material": material,
        "declared_material": material,
        "method_key": method_key,
        "method_revision": method_info["revision"],
        "discipline": method_info["discipline"],
        "unit": method_info["unit"],
        "specimen_count": specimen_count,
        "raw_value": raw_value,
        "qc_passed": True,
        "in_scope": True,
        "expected_state": "READY",
        "expected_hold_code": None,
        "synthetic": True,
    }
    lot["source_hash"] = compute_source_hash(lot)
    return lot


def _hold_lot(slot: int, hold_code: str, within_code: int) -> dict[str, Any]:
    lot_num = 76 + slot
    lot = _valid_lot(lot_num - 1)
    lot["lot_id"] = f"MVMTC-LOT-{lot_num:03d}"
    lot["expected_state"] = "HOLD"
    lot["expected_hold_code"] = hold_code

    if hold_code == "HOLD_MISSING_PO_QUOTE":
        if within_code % 2 == 0:
            lot["po_number"] = ""
        else:
            lot["quote_number"] = ""
    elif hold_code == "HOLD_DUPLICATE_CONTAINER":
        target_dup = (within_code % 5) + 1
        lot["container_id"] = f"MVMTC-CONT-{target_dup:03d}"
    elif hold_code == "HOLD_OUT_OF_SCOPE_METHOD":
        unapproved_keys = list(OUT_OF_SCOPE_METHODS.keys())
        chosen_key = unapproved_keys[within_code % len(unapproved_keys)]
        unapproved_info = OUT_OF_SCOPE_METHODS[chosen_key]
        lot["method_key"] = chosen_key
        lot["method_revision"] = unapproved_info["revision"]
        lot["discipline"] = unapproved_info["discipline"]
        lot["unit"] = unapproved_info["unit"]
        lot["in_scope"] = False
    elif hold_code == "HOLD_CHEMISTRY_MATERIAL_MISMATCH":
        lot["declared_material"] = "TI_6AL_4V"
        lot["material"] = "INCONEL_718"
        lot["raw_value"] = "CHEMISTRY_TITANIUM_CONTENT_OUT_OF_SPEC"
    elif hold_code == "HOLD_QC_FAILURE":
        lot["qc_passed"] = False
        lot["raw_value"] = 120.0
    else:
        raise RuntimeError("unmapped hold code %s" % hold_code)

    lot["source_hash"] = compute_source_hash(lot)
    return lot


def build_acceptance_fixture() -> list[dict[str, Any]]:
    rows = [_valid_lot(slot) for slot in range(VALID_COUNT)]
    hold_slots = []
    current_idx = 0
    for code, count in EXPECTED_HOLD_COUNTS.items():
        for within in range(count):
            hold_slots.append(_hold_lot(current_idx, code, within))
            current_idx += 1
    rows.extend(hold_slots)
    if len(rows) != LOT_COUNT:
        raise RuntimeError("fixture must be exactly 100 lots, got %s" % len(rows))
    return rows


def write_fixture(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    rows = build_acceptance_fixture()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows


def load_fixture(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    if path.is_file():
        rows = json.loads(path.read_text(encoding="utf-8"))
        if len(rows) == LOT_COUNT:
            return rows
    return build_acceptance_fixture()


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facility": FACILITY,
        "a2la_cert": A2LA_CERT,
        "truth_gate": TRUTH_GATE,
        "lots": {},
        "holds": {},
        "worksheets": {},
        "events": [],
        "container_index": {},
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


def classify(lot: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    po = _text(lot.get("po_number"))
    quote = _text(lot.get("quote_number"))
    if not po or not quote:
        return {"ok": False, "code": "HOLD_MISSING_PO_QUOTE"}

    container_id = _text(lot.get("container_id"))
    if not container_id:
        return {"ok": False, "code": "HOLD_MISSING_PO_QUOTE"}
    if container_id in journal["container_index"]:
        return {"ok": False, "code": "HOLD_DUPLICATE_CONTAINER"}

    method_key = _text(lot.get("method_key"))
    if method_key not in METHODS or not lot.get("in_scope", True):
        return {"ok": False, "code": "HOLD_OUT_OF_SCOPE_METHOD"}

    material = _text(lot.get("material"))
    declared = _text(lot.get("declared_material"))
    if material != declared or "OUT_OF_SPEC" in _text(lot.get("raw_value")):
        return {"ok": False, "code": "HOLD_CHEMISTRY_MATERIAL_MISMATCH"}

    if not lot.get("qc_passed", True):
        return {"ok": False, "code": "HOLD_QC_FAILURE"}

    expected_hash = compute_source_hash(lot)
    if not lot.get("source_hash") or lot["source_hash"] != expected_hash:
        return {"ok": False, "code": "HOLD_QC_FAILURE"}

    return {"ok": True, "source_hash": expected_hash}


def _park_hold(journal: dict[str, Any], lot: dict[str, Any], code: str) -> dict[str, Any]:
    lot_id = lot["lot_id"]
    hold = {
        "lot_id": lot_id,
        "code": code,
        "state": "HOLD",
        "container_id": lot.get("container_id"),
        "quote_number": lot.get("quote_number"),
        "po_number": lot.get("po_number"),
        "method_key": lot.get("method_key"),
        "source_hash": lot.get("source_hash"),
        "worksheet_created": False,
        "downstream": {
            "testing_started": False,
            "metallography_staged": False,
            "evidence_pack_staged": False,
            "report_released": False,
        },
        "released": False,
        "released_by": None,
        "live_test": False,
    }
    if lot_id in journal["holds"]:
        return {"kind": "NOOP", "reason": "already_held", "lot_id": lot_id}
    journal["holds"][lot_id] = hold
    _event(journal, "HOLD", {"lot_id": lot_id, "code": code})
    return {"kind": "HOLD", "duplicate": False, **hold}


def ingest_lot(journal: dict[str, Any], lot: dict[str, Any]) -> dict[str, Any]:
    lot_id = lot["lot_id"]
    if lot_id in journal["lots"]:
        return {"kind": "NOOP", "reason": "already_ingested", "lot_id": lot_id}
    if lot_id in journal["holds"]:
        return {"kind": "NOOP", "reason": "already_held", "lot_id": lot_id}

    verdict = classify(lot, journal)
    if not verdict["ok"]:
        return _park_hold(journal, lot, verdict["code"])

    source_hash = verdict["source_hash"]
    container_id = lot["container_id"]
    journal["container_index"][container_id] = lot_id

    worksheet_id = f"WS-MVMTC-{lot_id.replace('MVMTC-LOT-', '')}"
    worksheet = {
        "worksheet_id": worksheet_id,
        "lot_id": lot_id,
        "facility": FACILITY,
        "a2la_cert": A2LA_CERT,
        "container_id": container_id,
        "quote_number": lot["quote_number"],
        "po_number": lot["po_number"],
        "category": lot["category"],
        "material": lot["material"],
        "method_key": lot["method_key"],
        "method_revision": lot["method_revision"],
        "discipline": lot["discipline"],
        "unit": lot["unit"],
        "specimen_count": lot["specimen_count"],
        "raw_value": lot["raw_value"],
        "source_hash": source_hash,
        "state": "READY",
        "released": False,
        "released_by": None,
        "downstream": {
            "testing_started": True,
            "metallography_staged": True,
            "evidence_pack_staged": True,
            "report_released": False,
        },
    }
    journal["worksheets"][worksheet_id] = worksheet
    journal["lots"][lot_id] = worksheet
    _event(
        journal,
        "ACCESSION_AND_WORKSHEET",
        {
            "lot_id": lot_id,
            "worksheet_id": worksheet_id,
            "source_hash": source_hash,
        },
    )
    return {"kind": "READY", "lot_id": lot_id, "worksheet_id": worksheet_id}


def release_lot(journal: dict[str, Any], lot_id: str, *, actor: str, actor_role: str) -> dict[str, Any]:
    role = _text(actor_role).upper()
    name = _text(actor)
    if role != HUMAN_ROLE or name != HUMAN_RELEASER or not name or name.upper() in {"SYSTEM", "BOT", "AUTO"}:
        _event(
            journal,
            "AUTONOMOUS_RELEASE_DENIED",
            {"lot_id": lot_id, "actor": name or None, "actor_role": role or None},
        )
        journal["automatic_releases"] = 0
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
    record = journal["lots"].get(lot_id)
    if record is None:
        if lot_id in journal["holds"]:
            return {"ok": False, "code": "HOLD_BLOCKED_NO_RELEASE"}
        return {"ok": False, "code": "UNKNOWN_LOT"}
    if record.get("released"):
        return {"ok": True, "duplicate": True, "code": "ALREADY_RELEASED", "lot_id": lot_id}
    record["released"] = True
    record["released_by"] = name
    record["state"] = "HUMAN_RELEASED"
    record["downstream"]["report_released"] = True
    _event(journal, "HUMAN_RELEASE", {"lot_id": lot_id, "released_by": name})
    return {"ok": True, "code": "HUMAN_RELEASED", "lot_id": lot_id}


def attempt_autonomous_release(journal: dict[str, Any]) -> list[dict[str, Any]]:
    effects = []
    for lot_id in sorted(journal["lots"]):
        effects.append(release_lot(journal, lot_id, actor="SYSTEM", actor_role="SYSTEM"))
    for lot_id in sorted(journal["holds"]):
        effects.append(release_lot(journal, lot_id, actor="bot", actor_role="SYSTEM"))
    return effects


def authorized_human_release(journal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        release_lot(journal, lot_id, actor=HUMAN_RELEASER, actor_role=HUMAN_ROLE)
        for lot_id in sorted(journal["lots"])
    ]


def replay_into(journal: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    before_lots = {key: deepcopy(value) for key, value in journal["lots"].items()}
    before_holds = {key: deepcopy(value) for key, value in journal["holds"].items()}
    before_ws = {key: deepcopy(value) for key, value in journal["worksheets"].items()}
    before_lot_n = len(journal["lots"])
    before_hold_n = len(journal["holds"])
    effects = [ingest_lot(journal, row) for row in (rows or build_acceptance_fixture())]
    return {
        "added_lot_count": len(journal["lots"]) - before_lot_n,
        "added_holds": len(journal["holds"]) - before_hold_n,
        "lot_count": len(journal["lots"]),
        "hold_count": len(journal["holds"]),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "NOOP"),
        "state_changed": before_lots != journal["lots"] or before_holds != journal["holds"] or before_ws != journal["worksheets"],
    }


def build_audit(journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facility": FACILITY,
        "a2la_cert": A2LA_CERT,
        "truth_gate": TRUTH_GATE,
        "ready_lots": [deepcopy(v) for _, v in sorted(journal["lots"].items())],
        "holds": [deepcopy(v) for _, v in sorted(journal["holds"].items())],
        "worksheets": [deepcopy(v) for _, v in sorted(journal["worksheets"].items())],
        "events": deepcopy(journal["events"]),
        "autonomous_released": 0,
        "human_released": sum(1 for item in journal["lots"].values() if item.get("released")),
        "held_worksheets": sum(1 for item in journal["holds"].values() if item.get("worksheet_created")),
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
    if result.get("held_worksheets") != 0:
        failures.append("held_worksheets")
    if result.get("held_downstream") != 0:
        failures.append("held_downstream")
    if result.get("duplicate_records") != 0:
        failures.append("duplicate_records")
    replay = result.get("replay") or {}
    if replay.get("added_lot_count") != 0 or replay.get("added_holds") != 0 or replay.get("state_changed"):
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
    effects = [ingest_lot(journal, row) for row in inbound]
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

    ready_records = [deepcopy(v) for _, v in sorted(journal["lots"].items())]
    hold_records = [deepcopy(v) for _, v in sorted(journal["holds"].items())]

    packed = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facility": FACILITY,
        "a2la_cert": A2LA_CERT,
        "truth_gate": TRUTH_GATE,
        "input_lots": len(inbound),
        "valid": VALID_COUNT,
        "holds": len(journal["holds"]),
        "ready": len(journal["lots"]),
        "worksheets_created": len(journal["worksheets"]),
        "held_worksheets": sum(1 for item in journal["holds"].values() if item.get("worksheet_created")),
        "held_downstream": sum(1 for item in journal["holds"].values() if any(item.get("downstream", {}).values())),
        "hold_code_counts": hold_code_counts,
        "autonomous_released": 0,
        "human_released": sum(1 for item in journal["lots"].values() if item.get("released")),
        "duplicate_records": len(ready_records) - len({item["lot_id"] for item in ready_records}),
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
    STATE_PATH.write_text(json.dumps(journal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_body = cli_payload(result)
    RUN_RECEIPT_PATH.write_text(json.dumps(run_body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    LOT_RECEIPT_PATH.write_text(
        json.dumps(result["ready_records"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    HOLD_RECEIPT_PATH.write_text(
        json.dumps(result["hold_records"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    WORKSHEET_RECEIPT_PATH.write_text(
        json.dumps(result["audit"]["worksheets"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
                "facility": FACILITY,
                "a2la_cert": A2LA_CERT,
                "interfaces": "SYNTHETIC_READ_ONLY",
                "live_lims": False,
                "official_binary": COMMAND,
                "official_test": TEST_COMMAND,
                "page": "mvmtc-aero-fastener-evidence-lims.html",
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
        "lots": str(LOT_RECEIPT_PATH),
        "holds": str(HOLD_RECEIPT_PATH),
        "worksheets": str(WORKSHEET_RECEIPT_PATH),
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
        "facility": FACILITY,
        "a2la_cert": A2LA_CERT,
        "ok": result["ok"],
        "failures": result.get("failures") or [],
        "expected": counts["expected"],
        "actual": counts["actual"],
        "match": counts["match"],
        "hold_code_counts": result["hold_code_counts"],
        "held_worksheets": result["held_worksheets"],
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
    parser = argparse.ArgumentParser(description="MVMTC aerospace fastener evidence LIMS gate runner")
    parser.add_argument("--write-fixture", action="store_true", help="write the 100-lot fixture and exit")
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
            "ok": replay["added_lot_count"] == 0
            and replay["added_holds"] == 0
            and not replay["state_changed"],
            "replay": replay,
            "journal_sha256": sha256_hex(journal),
        }
        STATE_PATH.write_text(json.dumps(journal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
