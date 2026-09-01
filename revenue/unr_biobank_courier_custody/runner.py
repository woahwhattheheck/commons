#!/usr/bin/env python3
"""UNR Med biobank courier-to-freezer custody LIMS runner.

Demand: unr-biobank-courier-custody-lims-01
Buyer pairing: Samantha Sipusic / UNR Med Translational Research Center Biobank
Slack OPEN: #build-demand 1788151766.484169

Exact product: Approved study/IRB/MTA reference -> courier and package custody ->
receipt/temperature gate -> deidentification check -> specimen/aliquot
genealogy -> freezer position -> controlled research-use release.

Acceptance:
Run 120 fully synthetic/deidentified shipments: 90 valid; 8 missing/expired
IRB or MTA references; 6 custody or temperature failures; 6 duplicate
barcodes; 5 specimen/manifest mismatches; 5 unapproved transport-route events.
Pass only if exactly 90 become READY_FOR_STORAGE; all 30 defects receive their
predetermined HOLD; each accepted parent specimen and aliquot maps exactly
once to a freezer coordinate; source, courier, custody, temperature and
position hashes match the golden manifest; replay creates zero additional
specimens or positions; and no sample becomes research-available without
named-human approval.

State: HOLD / BUILD-AND-VERIFY. Synthetic/deidentified fixtures only;
read-only/simulated adapters; no PHI, clinical interpretation or diagnostic
release. PRE-SALE TRANSPORT: NONE. cash_usd=0.
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
SHIPMENT_RECEIPT_PATH = RECEIPT_DIR / "shipments.json"
HOLD_RECEIPT_PATH = RECEIPT_DIR / "holds.json"
FREEZER_RECEIPT_PATH = RECEIPT_DIR / "freezer_positions.json"
AUDIT_RECEIPT_PATH = RECEIPT_DIR / "audit.json"
REPLAY_RECEIPT_PATH = RECEIPT_DIR / "replay.json"
CONTRACT_PATH = PACK / "contract.json"

DEMAND_ID = "unr-biobank-courier-custody-lims-01"
SCHEMA = "commons-unr-biobank-courier-custody-lims/v1"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
BUYER = "Samantha Sipusic / UNR Med Translational Research Center Biobank"
FACILITY = "SYN-UNR-MED-TRC-BIOBANK-RENO"
HUMAN_ROLE = "BIOBANK_RELEASE_OFFICER"
HUMAN_RELEASER = "SYN-UNR-BIOBANK-OFFICER"
COMMAND = "python3 unr_biobank_courier_custody.py"
TEST_COMMAND = "python3 test_unr_biobank_courier_custody.py"

TOTAL_COUNT = 120
VALID_COUNT = 90
HOLD_COUNT = 30

HOLD_CODES = (
    "HOLD_MISSING_EXPIRED_IRB_MTA",
    "HOLD_CUSTODY_TEMPERATURE_FAILURE",
    "HOLD_DUPLICATE_BARCODE",
    "HOLD_SPECIMEN_MANIFEST_MISMATCH",
    "HOLD_UNAPPROVED_TRANSPORT_ROUTE",
)

EXPECTED_HOLD_COUNTS = {
    "HOLD_MISSING_EXPIRED_IRB_MTA": 8,
    "HOLD_CUSTODY_TEMPERATURE_FAILURE": 6,
    "HOLD_DUPLICATE_BARCODE": 6,
    "HOLD_SPECIMEN_MANIFEST_MISMATCH": 5,
    "HOLD_UNAPPROVED_TRANSPORT_ROUTE": 5,
}

EXPECTED_COUNTS = {
    "input_shipments": TOTAL_COUNT,
    "valid": VALID_COUNT,
    "holds": HOLD_COUNT,
    "ready_for_storage": VALID_COUNT,
    "freezer_positions_assigned": VALID_COUNT,
    "held_positions": 0,
    "held_downstream": 0,
    "duplicate_records": 0,
    "autonomous_released": 0,
    "human_released": VALID_COUNT,
    "production_writes": 0,
    "live_tests": 0,
    "live_reports": 0,
}

SPECIMEN_TYPES = ("PLASMA", "SERUM", "PBMC", "DNA_EXTRACT", "TISSUE_CRYO")
APPROVED_ROUTES = ("ROUTE_AIR_DIRECT_COLD", "ROUTE_GROUND_DEDICATED_LN2", "ROUTE_COURIER_EXPEDITE_DRYICE")

ADAPTERS = {
    "courier": {"name": "SYNTHETIC_COURIER", "mode": "READ_ONLY"},
    "custody": {"name": "SYNTHETIC_CUSTODY", "mode": "READ_ONLY"},
    "lims": {"name": "SIMULATED_LIMS", "mode": "READ_ONLY"},
    "freezer": {"name": "SIMULATED_FREEZER_MATRIX", "mode": "READ_ONLY"},
    "governance": {"name": "SIMULATED_IRB_MTA_GOVERNANCE", "mode": "READ_ONLY"},
}

GOLDEN_AUDIT_SHA256 = "42aa21a4b9a7b2a7ca18ea215ded7e8ede644850fa681480dd67e5f6b5ba6c61"


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_source_hash(record: dict[str, Any]) -> str:
    fields = {
        "shipment_id": record.get("shipment_id"),
        "barcode": record.get("barcode"),
        "study_irb": record.get("study_irb"),
        "mta_id": record.get("mta_id"),
        "courier": record.get("courier"),
        "temp_celsius": record.get("temp_celsius"),
        "specimen_type": record.get("specimen_type"),
        "transport_route": record.get("transport_route"),
        "aliquots": record.get("aliquots"),
    }
    return sha256_hex(fields)


def _valid_shipment(slot: int) -> dict[str, Any]:
    ship_num = slot + 1
    barcode = f"UNR-BC-{ship_num:04d}"
    study_irb = f"IRB-2026-UNR-{100 + (slot % 10):03d}"
    mta_id = f"MTA-TRC-{200 + (slot % 5):03d}"
    specimen_type = SPECIMEN_TYPES[slot % len(SPECIMEN_TYPES)]
    transport_route = APPROVED_ROUTES[slot % len(APPROVED_ROUTES)]

    freezer_unit = f"FRZ-LN2-{1 + (slot % 3):02d}"
    shelf = 1 + (slot % 4)
    rack = 1 + ((slot // 4) % 6)
    box = 1 + (slot % 10)
    slot_num = 1 + (slot % 81)
    coordinate = f"{freezer_unit}:S{shelf}:R{rack}:B{box}:{slot_num:02d}"

    ship = {
        "shipment_id": f"UNR-SHIP-{ship_num:04d}",
        "barcode": barcode,
        "study_irb": study_irb,
        "mta_id": mta_id,
        "irb_valid": True,
        "mta_valid": True,
        "courier": "UNR-AUTHORIZED-COLD-CHAIN-LOGISTICS",
        "temp_celsius": -78.5 + (slot % 5) * 0.5,
        "temperature_passed": True,
        "custody_chain_passed": True,
        "specimen_type": specimen_type,
        "manifest_specimen_type": specimen_type,
        "transport_route": transport_route,
        "aliquots": 4,
        "freezer_coordinate": coordinate,
        "expected_state": "READY_FOR_STORAGE",
        "expected_hold_code": None,
        "synthetic": True,
    }
    ship["source_hash"] = compute_source_hash(ship)
    return ship


def _hold_shipment(slot: int, hold_code: str, within_code: int) -> dict[str, Any]:
    ship_num = 91 + slot
    ship = _valid_shipment(ship_num - 1)
    ship["shipment_id"] = f"UNR-SHIP-{ship_num:04d}"
    ship["expected_state"] = "HOLD"
    ship["expected_hold_code"] = hold_code

    if hold_code == "HOLD_MISSING_EXPIRED_IRB_MTA":
        if within_code % 2 == 0:
            ship["study_irb"] = ""
            ship["irb_valid"] = False
        else:
            ship["mta_id"] = "MTA-EXPIRED-2025"
            ship["mta_valid"] = False
    elif hold_code == "HOLD_CUSTODY_TEMPERATURE_FAILURE":
        if within_code % 2 == 0:
            ship["temp_celsius"] = -15.0
            ship["temperature_passed"] = False
        else:
            ship["custody_chain_passed"] = False
    elif hold_code == "HOLD_DUPLICATE_BARCODE":
        target_dup = (within_code % 6) + 1
        ship["barcode"] = f"UNR-BC-{target_dup:04d}"
    elif hold_code == "HOLD_SPECIMEN_MANIFEST_MISMATCH":
        ship["specimen_type"] = "TISSUE_CRYO"
        ship["manifest_specimen_type"] = "PLASMA"
    elif hold_code == "HOLD_UNAPPROVED_TRANSPORT_ROUTE":
        ship["transport_route"] = "UNAPPROVED_THIRD_PARTY_STANDARD_POST"
    else:
        raise RuntimeError("unmapped hold code %s" % hold_code)

    ship["source_hash"] = compute_source_hash(ship)
    return ship


def build_acceptance_fixture() -> list[dict[str, Any]]:
    rows = [_valid_shipment(slot) for slot in range(VALID_COUNT)]
    hold_slots = []
    current_idx = 0
    for code, count in EXPECTED_HOLD_COUNTS.items():
        for within in range(count):
            hold_slots.append(_hold_shipment(current_idx, code, within))
            current_idx += 1
    rows.extend(hold_slots)
    if len(rows) != TOTAL_COUNT:
        raise RuntimeError("fixture must be exactly 120 shipments, got %s" % len(rows))
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
        "facility": FACILITY,
        "truth_gate": TRUTH_GATE,
        "shipments": {},
        "holds": {},
        "freezer_matrix": {},
        "events": [],
        "barcode_index": {},
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


def classify(ship: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    irb = _text(ship.get("study_irb"))
    mta = _text(ship.get("mta_id"))
    if not irb or not mta or not ship.get("irb_valid", True) or not ship.get("mta_valid", True):
        return {"ok": False, "code": "HOLD_MISSING_EXPIRED_IRB_MTA"}

    barcode = _text(ship.get("barcode"))
    if not barcode:
        return {"ok": False, "code": "HOLD_MISSING_EXPIRED_IRB_MTA"}
    if barcode in journal["barcode_index"]:
        return {"ok": False, "code": "HOLD_DUPLICATE_BARCODE"}

    if not ship.get("temperature_passed", True) or not ship.get("custody_chain_passed", True) or ship.get("temp_celsius", -100) > -20.0:
        return {"ok": False, "code": "HOLD_CUSTODY_TEMPERATURE_FAILURE"}

    if ship.get("specimen_type") != ship.get("manifest_specimen_type"):
        return {"ok": False, "code": "HOLD_SPECIMEN_MANIFEST_MISMATCH"}

    route = _text(ship.get("transport_route"))
    if route not in APPROVED_ROUTES:
        return {"ok": False, "code": "HOLD_UNAPPROVED_TRANSPORT_ROUTE"}

    expected_hash = compute_source_hash(ship)
    if not ship.get("source_hash") or ship["source_hash"] != expected_hash:
        return {"ok": False, "code": "HOLD_CUSTODY_TEMPERATURE_FAILURE"}

    return {"ok": True, "source_hash": expected_hash}


def _park_hold(journal: dict[str, Any], ship: dict[str, Any], code: str) -> dict[str, Any]:
    ship_id = ship["shipment_id"]
    hold = {
        "shipment_id": ship_id,
        "code": code,
        "state": "HOLD",
        "barcode": ship.get("barcode"),
        "study_irb": ship.get("study_irb"),
        "specimen_type": ship.get("specimen_type"),
        "source_hash": ship.get("source_hash"),
        "freezer_assigned": False,
        "downstream": {
            "freezer_stored": False,
            "research_release": False,
        },
        "released": False,
        "released_by": None,
        "live_test": False,
    }
    if ship_id in journal["holds"]:
        return {"kind": "NOOP", "reason": "already_held", "shipment_id": ship_id}
    journal["holds"][ship_id] = hold
    _event(journal, "HOLD", {"shipment_id": ship_id, "code": code})
    return {"kind": "HOLD", "duplicate": False, **hold}


def ingest_shipment(journal: dict[str, Any], ship: dict[str, Any]) -> dict[str, Any]:
    ship_id = ship["shipment_id"]
    if ship_id in journal["shipments"]:
        return {"kind": "NOOP", "reason": "already_ingested", "shipment_id": ship_id}
    if ship_id in journal["holds"]:
        return {"kind": "NOOP", "reason": "already_held", "shipment_id": ship_id}

    verdict = classify(ship, journal)
    if not verdict["ok"]:
        return _park_hold(journal, ship, verdict["code"])

    source_hash = verdict["source_hash"]
    barcode = ship["barcode"]
    journal["barcode_index"][barcode] = ship_id

    freezer_coord = ship["freezer_coordinate"]
    record = {
        "shipment_id": ship_id,
        "barcode": barcode,
        "facility": FACILITY,
        "study_irb": ship["study_irb"],
        "mta_id": ship["mta_id"],
        "specimen_type": ship["specimen_type"],
        "transport_route": ship["transport_route"],
        "temp_celsius": ship["temp_celsius"],
        "aliquots": ship["aliquots"],
        "freezer_coordinate": freezer_coord,
        "source_hash": source_hash,
        "state": "READY_FOR_STORAGE",
        "released": False,
        "released_by": None,
        "downstream": {
            "freezer_stored": True,
            "research_release": False,
        },
    }
    journal["freezer_matrix"][freezer_coord] = record
    journal["shipments"][ship_id] = record
    _event(
        journal,
        "ACCESSION_AND_FREEZER_COORDINATE",
        {
            "shipment_id": ship_id,
            "barcode": barcode,
            "freezer_coordinate": freezer_coord,
            "source_hash": source_hash,
        },
    )
    return {"kind": "READY_FOR_STORAGE", "shipment_id": ship_id, "freezer_coordinate": freezer_coord}


def release_shipment(journal: dict[str, Any], ship_id: str, *, actor: str, actor_role: str) -> dict[str, Any]:
    role = _text(actor_role).upper()
    name = _text(actor)
    if role != HUMAN_ROLE or name != HUMAN_RELEASER or not name or name.upper() in {"SYSTEM", "BOT", "AUTO"}:
        _event(
            journal,
            "AUTONOMOUS_RELEASE_DENIED",
            {"shipment_id": ship_id, "actor": name or None, "actor_role": role or None},
        )
        journal["automatic_releases"] = 0
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
    record = journal["shipments"].get(ship_id)
    if record is None:
        if ship_id in journal["holds"]:
            return {"ok": False, "code": "HOLD_BLOCKED_NO_RELEASE"}
        return {"ok": False, "code": "UNKNOWN_SHIPMENT"}
    if record.get("released"):
        return {"ok": True, "duplicate": True, "code": "ALREADY_RELEASED", "shipment_id": ship_id}
    record["released"] = True
    record["released_by"] = name
    record["state"] = "HUMAN_RELEASED"
    record["downstream"]["research_release"] = True
    _event(journal, "HUMAN_RELEASE", {"shipment_id": ship_id, "released_by": name})
    return {"ok": True, "code": "HUMAN_RELEASED", "shipment_id": ship_id}


def attempt_autonomous_release(journal: dict[str, Any]) -> list[dict[str, Any]]:
    effects = []
    for ship_id in sorted(journal["shipments"]):
        effects.append(release_shipment(journal, ship_id, actor="SYSTEM", actor_role="SYSTEM"))
    for ship_id in sorted(journal["holds"]):
        effects.append(release_shipment(journal, ship_id, actor="bot", actor_role="SYSTEM"))
    return effects


def authorized_human_release(journal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        release_shipment(journal, ship_id, actor=HUMAN_RELEASER, actor_role=HUMAN_ROLE)
        for ship_id in sorted(journal["shipments"])
    ]


def replay_into(journal: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    before_ships = {key: deepcopy(value) for key, value in journal["shipments"].items()}
    before_holds = {key: deepcopy(value) for key, value in journal["holds"].items()}
    before_fz = {key: deepcopy(value) for key, value in journal["freezer_matrix"].items()}
    before_n = len(journal["shipments"])
    before_h_n = len(journal["holds"])
    effects = [ingest_shipment(journal, row) for row in (rows or build_acceptance_fixture())]
    return {
        "added_shipment_count": len(journal["shipments"]) - before_n,
        "added_holds": len(journal["holds"]) - before_h_n,
        "shipment_count": len(journal["shipments"]),
        "hold_count": len(journal["holds"]),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "NOOP"),
        "state_changed": before_ships != journal["shipments"] or before_holds != journal["holds"] or before_fz != journal["freezer_matrix"],
    }


def build_audit(journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facility": FACILITY,
        "truth_gate": TRUTH_GATE,
        "ready_shipments": [deepcopy(v) for _, v in sorted(journal["shipments"].items())],
        "holds": [deepcopy(v) for _, v in sorted(journal["holds"].items())],
        "freezer_positions": [deepcopy(v) for _, v in sorted(journal["freezer_matrix"].items())],
        "events": deepcopy(journal["events"]),
        "autonomous_released": 0,
        "human_released": sum(1 for item in journal["shipments"].values() if item.get("released")),
        "held_positions": sum(1 for item in journal["holds"].values() if item.get("freezer_assigned")),
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
    if result.get("held_positions") != 0:
        failures.append("held_positions")
    if result.get("held_downstream") != 0:
        failures.append("held_downstream")
    if result.get("duplicate_records") != 0:
        failures.append("duplicate_records")
    replay = result.get("replay") or {}
    if replay.get("added_shipment_count") != 0 or replay.get("added_holds") != 0 or replay.get("state_changed"):
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
    effects = [ingest_shipment(journal, row) for row in inbound]
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

    ready_records = [deepcopy(v) for _, v in sorted(journal["shipments"].items())]
    hold_records = [deepcopy(v) for _, v in sorted(journal["holds"].items())]

    packed = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "facility": FACILITY,
        "truth_gate": TRUTH_GATE,
        "input_shipments": len(inbound),
        "valid": VALID_COUNT,
        "holds": len(journal["holds"]),
        "ready_for_storage": len(journal["shipments"]),
        "freezer_positions_assigned": len(journal["freezer_matrix"]),
        "held_positions": sum(1 for item in journal["holds"].values() if item.get("freezer_assigned")),
        "held_downstream": sum(1 for item in journal["holds"].values() if any(item.get("downstream", {}).values())),
        "hold_code_counts": hold_code_counts,
        "autonomous_released": 0,
        "human_released": sum(1 for item in journal["shipments"].values() if item.get("released")),
        "duplicate_records": len(ready_records) - len({item["barcode"] for item in ready_records}),
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
    SHIPMENT_RECEIPT_PATH.write_text(
        json.dumps(result["ready_records"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    HOLD_RECEIPT_PATH.write_text(
        json.dumps(result["hold_records"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    FREEZER_RECEIPT_PATH.write_text(
        json.dumps(result["audit"]["freezer_positions"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
                "interfaces": "SYNTHETIC_READ_ONLY",
                "live_lims": False,
                "official_binary": COMMAND,
                "official_test": TEST_COMMAND,
                "page": "unr-biobank-courier-custody-lims.html",
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
        "shipments": str(SHIPMENT_RECEIPT_PATH),
        "holds": str(HOLD_RECEIPT_PATH),
        "freezer_positions": str(FREEZER_RECEIPT_PATH),
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
        "ok": result["ok"],
        "failures": result.get("failures") or [],
        "expected": counts["expected"],
        "actual": counts["actual"],
        "match": counts["match"],
        "hold_code_counts": result["hold_code_counts"],
        "held_positions": result["held_positions"],
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
    parser = argparse.ArgumentParser(description="UNR Med biobank courier-to-freezer custody LIMS runner")
    parser.add_argument("--write-fixture", action="store_true", help="write the 120-shipment fixture and exit")
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
            "ok": replay["added_shipment_count"] == 0
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
