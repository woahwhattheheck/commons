#!/usr/bin/env python3
"""Luvak–SSA materials accession/report cutover LIMS.

Demand: luvak-ssa-lab-analytics-cutover-lims-01
Buyer: Dean Gaskill / Luvak Laboratories

Accepted quote → submission form → physical package → optional CoC
reconciliation; material/method revision freeze; interstitial-gas/metals
result hashes; staged report across the SSA cutover. Named-human
approval only.

Acceptance: run 100 synthetic shipments — 80 valid, 8 missing
accepted-quote links, 4 duplicate sample IDs, 4 form/package mismatches,
4 method-revision mismatches. PASS only when exactly 80 are READY;
20 receive exact HOLD codes; holds create no test/report stage; each
ready record preserves quote/form/CoC/method/result/report hashes;
replay produces zero duplicates; named-human release only.

AquaTrace HOLD / BUILD-AND-VERIFY. Adapters stay simulated/read-only.
Materials-quality evidence only. PRE-SALE TRANSPORT: NONE.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

DEMAND_ID = "luvak-ssa-lab-analytics-cutover-lims-01"
SCHEMA = "commons-luvak-ssa-lab-analytics-cutover-lims/v1"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
BUYER = "Dean Gaskill / Luvak Laboratories"
HUMAN_APPROVER = "APPROVER"
NAMED_HUMAN = "dean-gaskill"
VALID_COUNT = 80
HOLD_COUNT = 20
INPUT_COUNT = VALID_COUNT + HOLD_COUNT

HOLD_CODES = (
    "MISSING_ACCEPTED_QUOTE",
    "DUPLICATE_SAMPLE_ID",
    "FORM_PACKAGE_MISMATCH",
    "METHOD_REVISION_MISMATCH",
)
HOLD_PLAN = {
    "MISSING_ACCEPTED_QUOTE": 8,
    "DUPLICATE_SAMPLE_ID": 4,
    "FORM_PACKAGE_MISMATCH": 4,
    "METHOD_REVISION_MISMATCH": 4,
}

METHODS = {
    "INTERSTITIAL_O": {"version": "IGA-O-2024-SYN", "unit": "ppm", "kind": "GAS"},
    "INTERSTITIAL_N": {"version": "IGA-N-2024-SYN", "unit": "ppm", "kind": "GAS"},
    "INTERSTITIAL_H": {"version": "IGA-H-2024-SYN", "unit": "ppm", "kind": "GAS"},
    "METALS_ICP": {"version": "ICP-MS-2024-SYN", "unit": "wt%", "kind": "METALS"},
}
METHOD_NAMES = tuple(METHODS)
MISMATCH_REVISIONS = (
    ("INTERSTITIAL_O", "IGA-O-2018-LEGACY"),
    ("INTERSTITIAL_N", "IGA-N-WRONG"),
    ("INTERSTITIAL_H", "SSA-DRAFT"),
    ("METALS_ICP", "ICP-2011"),
)

GOLDEN_COUNTS = {
    "input_rows": INPUT_COUNT,
    "ready": VALID_COUNT,
    "held": HOLD_COUNT,
    "held_test_stages": 0,
    "held_report_stages": 0,
    "released_reports": 0,
    "staged_reports": VALID_COUNT,
    "replay_added_records": 0,
    "production_writes": 0,
}

GOLDEN_FIXTURE_SHA256 = "b1160d4d7b27f6f254c263b5d8e4d13204903444a97a98205612c059c456dda2"
GOLDEN_AUDIT_SHA256 = "c69f62396eab88a5c31a994caf4bcb9c51dc6c86a5473e458eff1fad2744c46f"
GOLDEN_LINEAGE_SHA256 = "7b608c694273df9eea371a0f945250653f49dc40ff2f9075c3c2f4c178c03df5"
GOLDEN_REPORT_DIGEST = "7db20de0c437719284a9d380c2e2c5b49c00b0bce091decf75bd442cc5db542b"
HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE / "revenue" / "luvak_ssa_lab_analytics"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def method_for(index: int) -> str:
    return METHOD_NAMES[(index - 1) % len(METHOD_NAMES)]


def valid_sample_id(index: int) -> str:
    return "LVK-SMP-%03d" % index


def valid_quote_id(index: int) -> str:
    return "LVK-Q-%03d" % index


def accession_id(sample_id: str, quote_id: str) -> str:
    digest = sha256_hex({"demand_id": DEMAND_ID, "sample_id": sample_id, "quote_id": quote_id})
    return "LVK-" + digest[:12]


def quote_hash(quote_id: str) -> str:
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "QUOTE", "quote_id": quote_id, "accepted": True})


def form_hash(form_id: str, sample_id: str) -> str:
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "FORM", "form_id": form_id, "sample_id": sample_id})


def coc_hash(coc_id: str, sample_id: str) -> str:
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "COC", "coc_id": coc_id, "sample_id": sample_id})


def method_hash(method: str, method_version: str) -> str:
    return sha256_hex(
        {"demand_id": DEMAND_ID, "kind": "METHOD", "method": method, "method_version": method_version}
    )


def result_packet(index: int, method: str) -> dict[str, Any]:
    spec = METHODS[method]
    return {
        "instrument_id": "SIM-%s-01" % method,
        "adapter": "SIMULATED",
        "value": round(12.0 + ((index - 1) % 25) * 0.08, 3),
        "unit": spec["unit"],
        "kind": spec["kind"],
        "qc_ok": True,
    }


def result_hash(packet: dict[str, Any]) -> str:
    body = {key: value for key, value in packet.items() if key not in {"adapter"}}
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "RESULT", "raw": body})


def report_hash(sample_id: str, result_digest: str) -> str:
    return sha256_hex(
        {"demand_id": DEMAND_ID, "kind": "REPORT", "sample_id": sample_id, "result_hash": result_digest}
    )


def _base_row(
    row_id: str,
    sample_id: str,
    *,
    quote_id: str,
    form_id: str,
    package_id: str,
    form_package_id: str | None = None,
    coc_id: str | None = None,
    method: str,
    method_version: str | None = None,
    valid_index: int | None = None,
    expected_hold: str | None = None,
) -> dict[str, Any]:
    index = valid_index or 1
    spec = METHODS.get(method)
    version = method_version if method_version is not None else (spec["version"] if spec else "UNKNOWN")
    packet = result_packet(index, method if spec else "INTERSTITIAL_O")
    form_pkg = form_package_id if form_package_id is not None else package_id
    coc = coc_id if coc_id is not None else "COC-%s" % sample_id
    return {
        "row_id": row_id,
        "sample_id": sample_id,
        "quote_id": quote_id,
        "quote_accepted": bool(quote_id),
        "form_id": form_id,
        "package_id": package_id,
        "form_package_id": form_pkg,
        "coc_id": coc,
        "method": method,
        "method_version": version,
        "cutover_site": "SSA",
        "raw": packet,
        "quote_hash": quote_hash(quote_id) if quote_id else "",
        "form_hash": form_hash(form_id, sample_id) if form_id and sample_id else "",
        "coc_hash": coc_hash(coc, sample_id) if coc and sample_id else "",
        "method_hash": method_hash(method, version) if spec and spec["version"] == version else "",
        "result_hash": result_hash(packet),
        "expected_hold": expected_hold,
        "interface_state": "SIMULATED",
        "interface_live": False,
    }


def build_acceptance_fixture() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(1, VALID_COUNT + 1):
        method = method_for(index)
        rows.append(
            _base_row(
                "R%03d" % index,
                valid_sample_id(index),
                quote_id=valid_quote_id(index),
                form_id="FORM-%03d" % index,
                package_id="PKG-%03d" % index,
                method=method,
                valid_index=index,
            )
        )
    for offset in range(8):
        rows.append(
            _base_row(
                "R%03d" % (81 + offset),
                "LVK-SMP-HQ%02d" % (offset + 1),
                quote_id="",
                form_id="FORM-HQ%02d" % (offset + 1),
                package_id="PKG-HQ%02d" % (offset + 1),
                method="INTERSTITIAL_O",
                expected_hold="MISSING_ACCEPTED_QUOTE",
            )
        )
    for offset in range(4):
        target = offset + 1
        rows.append(
            _base_row(
                "R%03d" % (89 + offset),
                valid_sample_id(target),
                quote_id="LVK-Q-HDUP%02d" % (offset + 1),
                form_id="FORM-HDUP%02d" % (offset + 1),
                package_id="PKG-HDUP%02d" % (offset + 1),
                method=method_for(target),
                expected_hold="DUPLICATE_SAMPLE_ID",
            )
        )
    for offset in range(4):
        rows.append(
            _base_row(
                "R%03d" % (93 + offset),
                "LVK-SMP-HFP%02d" % (offset + 1),
                quote_id="LVK-Q-HFP%02d" % (offset + 1),
                form_id="FORM-HFP%02d" % (offset + 1),
                package_id="PKG-HFP%02d" % (offset + 1),
                form_package_id="PKG-OTHER%02d" % (offset + 1),
                method="METALS_ICP",
                expected_hold="FORM_PACKAGE_MISMATCH",
            )
        )
    for offset, (method, version) in enumerate(MISMATCH_REVISIONS):
        rows.append(
            _base_row(
                "R%03d" % (97 + offset),
                "LVK-SMP-HREV%02d" % (offset + 1),
                quote_id="LVK-Q-HREV%02d" % (offset + 1),
                form_id="FORM-HREV%02d" % (offset + 1),
                package_id="PKG-HREV%02d" % (offset + 1),
                method=method,
                method_version=version,
                expected_hold="METHOD_REVISION_MISMATCH",
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
        "methods": list(METHOD_NAMES),
        "input_rows": len(inbound),
        "valid_rows": sum(1 for row in inbound if row.get("expected_hold") is None),
        "hold_rows": sum(1 for row in inbound if row.get("expected_hold")),
        "hold_plan": dict(HOLD_PLAN),
        "row_ids": [row["row_id"] for row in inbound],
        "sample_ids": [row["sample_id"] for row in inbound],
        "expected_holds": [row.get("expected_hold") for row in inbound],
        "interfaces": "SIMULATED",
        "interface_live": False,
        "production_writes": False,
        "autonomous_release": False,
        "materials_qualification_decision": False,
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
        "seen_samples": {},
    }


def _event(journal: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    journal["events"].append({"seq": len(journal["events"]) + 1, "kind": kind, **deepcopy(payload)})


def classify_row(row: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    sample_id = _text(row.get("sample_id"))
    quote_id = _text(row.get("quote_id"))
    form_id = _text(row.get("form_id"))
    package_id = _text(row.get("package_id"))
    form_package_id = _text(row.get("form_package_id"))
    method = _text(row.get("method"))
    method_version = _text(row.get("method_version"))
    spec = METHODS.get(method)

    if not quote_id:
        return {"ok": False, "code": "MISSING_ACCEPTED_QUOTE", "sample_id": sample_id or None}
    if sample_id and sample_id in journal["seen_samples"]:
        return {"ok": False, "code": "DUPLICATE_SAMPLE_ID", "sample_id": sample_id}
    if not form_id or not package_id or form_package_id != package_id:
        return {"ok": False, "code": "FORM_PACKAGE_MISMATCH", "sample_id": sample_id or None}
    if spec is None or spec["version"] != method_version:
        return {
            "ok": False,
            "code": "METHOD_REVISION_MISMATCH",
            "sample_id": sample_id or None,
            "method": method,
            "method_version": method_version,
        }
    return {
        "ok": True,
        "sample_id": sample_id,
        "quote_id": quote_id,
        "form_id": form_id,
        "package_id": package_id,
        "coc_id": _text(row.get("coc_id")),
        "method": method,
        "method_version": method_version,
        "accession_id": accession_id(sample_id, quote_id),
    }


def rendered_report(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "demand_id": DEMAND_ID,
        "accession_id": record["accession_id"],
        "sample_id": record["sample_id"],
        "quote_id": record["quote_id"],
        "method": record["method"],
        "method_version": record["method_version"],
        "cutover_site": "SSA",
        "quote_hash": record["quote_hash"],
        "form_hash": record["form_hash"],
        "coc_hash": record["coc_hash"],
        "method_hash": record["method_hash"],
        "result_hash": record["result_hash"],
        "report_hash": record["report_hash"],
        "state": "STAGED",
        "released": bool(record.get("released")),
        "interface_live": False,
        "materials_qualification_decision": False,
    }


def report_status(record: dict[str, Any]) -> str:
    if record.get("released"):
        return "RELEASED"
    return "STAGED_PENDING_NAMED_APPROVAL"


def ingest_row(journal: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    row_id = _text(row.get("row_id"))
    existing = next((item for item in journal["accessions"].values() if item["row_id"] == row_id), None)
    if existing is not None:
        _event(journal, "REPLAY_NOOP", {"accession_id": existing["accession_id"], "sample_id": existing["sample_id"]})
        return {"kind": "REPLAY_NOOP", "accession_id": existing["accession_id"], "sample_id": existing["sample_id"]}
    existing_hold = next((item for item in journal["holds"] if item["row_id"] == row_id), None)
    if existing_hold is not None:
        _event(journal, "REPLAY_NOOP", {"sample_id": existing_hold.get("sample_id"), "code": existing_hold["code"]})
        return {"kind": "REPLAY_NOOP", "sample_id": existing_hold.get("sample_id"), "code": existing_hold["code"]}

    verdict = classify_row(row, journal)
    if not verdict["ok"]:
        hold = {
            "row_id": row_id,
            "sample_id": verdict.get("sample_id"),
            "code": verdict["code"],
            "state": "HOLD",
            "test_stage": None,
            "report_stage": None,
            "released": False,
        }
        journal["holds"].append(hold)
        _event(journal, "HOLD", hold)
        return {"kind": "HOLD", "duplicate": False, **hold}

    acc_id = verdict["accession_id"]
    packet = deepcopy(row.get("raw") or {})
    result_digest = result_hash(packet)
    record = {
        "accession_id": acc_id,
        "row_id": row_id,
        "sample_id": verdict["sample_id"],
        "quote_id": verdict["quote_id"],
        "form_id": verdict["form_id"],
        "package_id": verdict["package_id"],
        "coc_id": verdict["coc_id"],
        "method": verdict["method"],
        "method_version": verdict["method_version"],
        "cutover_site": "SSA",
        "raw": packet,
        "quote_hash": quote_hash(verdict["quote_id"]),
        "form_hash": form_hash(verdict["form_id"], verdict["sample_id"]),
        "coc_hash": coc_hash(verdict["coc_id"], verdict["sample_id"]),
        "method_hash": method_hash(verdict["method"], verdict["method_version"]),
        "result_hash": result_digest,
        "report_hash": report_hash(verdict["sample_id"], result_digest),
        "state": "READY",
        "test_stage": "SSA_ANALYTICS",
        "report_stage": "STAGED",
        "released": False,
        "released_by": None,
        "report_status": "STAGED_PENDING_NAMED_APPROVAL",
        "interface_state": "SIMULATED",
        "interface_live": False,
    }
    record["report"] = rendered_report(record)
    journal["accessions"][acc_id] = record
    journal["seen_samples"][verdict["sample_id"]] = row_id
    _event(journal, "READY", {"accession_id": acc_id, "sample_id": verdict["sample_id"]})
    return {"kind": "READY", "accession_id": acc_id, "sample_id": verdict["sample_id"]}


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
    ready = sorted(journal["accessions"].values(), key=lambda item: item["sample_id"])
    hold_codes = [item["code"] for item in journal["holds"]]
    reports = [item["report"] for item in ready]
    lineage = [
        {
            "sample_id": item["sample_id"],
            "quote_hash": item["quote_hash"],
            "form_hash": item["form_hash"],
            "coc_hash": item["coc_hash"],
            "method_hash": item["method_hash"],
            "result_hash": item["result_hash"],
            "report_hash": item["report_hash"],
        }
        for item in ready
    ]
    audit = {
        "demand_id": DEMAND_ID,
        "sample_ids": [item["sample_id"] for item in ready],
        "accession_ids": [item["accession_id"] for item in ready],
        "hold_codes": hold_codes,
        "hold_sample_ids": [item["sample_id"] for item in journal["holds"]],
        "lineage": lineage,
        "released": [item["sample_id"] for item in ready if item["released"]],
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
        "held_test_stages": sum(1 for item in journal["holds"] if item.get("test_stage")),
        "held_report_stages": sum(1 for item in journal["holds"] if item.get("report_stage")),
        "released_reports": sum(1 for item in ready if item["released"]),
        "staged_reports": sum(1 for item in ready if item["report_status"] == "STAGED_PENDING_NAMED_APPROVAL"),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "REPLAY_NOOP"),
        "effects": effects,
        "autonomous_release_effects": autonomous,
        "accessions": ready,
        "holds": deepcopy(journal["holds"]),
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
        "materials_qualification_decision": False,
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
        "held_test_stages": result.get("held_test_stages"),
        "held_report_stages": result.get("held_report_stages"),
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
        if item.get("quote_hash") != quote_hash(item["quote_id"]):
            failures.append("quote_hash")
            break
        if item.get("form_hash") != form_hash(item["form_id"], item["sample_id"]):
            failures.append("form_hash")
            break
        if item.get("coc_hash") != coc_hash(item["coc_id"], item["sample_id"]):
            failures.append("coc_hash")
            break
        if item.get("method_hash") != method_hash(item["method"], item["method_version"]):
            failures.append("method_hash")
            break
        if item.get("result_hash") != result_hash(item["raw"]):
            failures.append("result_hash")
            break
        if item.get("report_hash") != report_hash(item["sample_id"], item["result_hash"]):
            failures.append("report_hash")
            break
        if item.get("report", {}).get("state") != "STAGED":
            failures.append("report_not_staged")
            break
        if item.get("released"):
            failures.append("released")
            break
        if item.get("cutover_site") != "SSA":
            failures.append("cutover_site")
            break
    if any(item.get("test_stage") or item.get("report_stage") or item.get("released") for item in result.get("holds") or []):
        failures.append("hold_staged")
    if result.get("interface_live") is not False:
        failures.append("interface_live")
    if result.get("interfaces") != "SIMULATED":
        failures.append("interfaces")
    if result.get("autonomous_release") is not False:
        failures.append("autonomous_release")
    if result.get("materials_qualification_decision") is not False:
        failures.append("materials_qualification_decision")
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
