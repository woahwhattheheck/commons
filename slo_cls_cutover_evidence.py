#!/usr/bin/env python3
"""SLO County PHL incumbent→CliniSys cutover evidence LIMS.

Demand: slo-cls-cutover-evidence-lims-01
Buyer: Glen M. Miller / San Luis Obispo County Public Health Laboratory

Requisition/portal accession + Panther Fusion method version +
result/report/source hash → deterministic incumbent-to-CLS migration
and rollback verifier. Named-human approval only.

Acceptance: load 1,000 synthetic legacy bundles — 850 valid, 50
duplicate IDs, 40 broken sample→test references, 30 method/version
conflicts, 30 report/result hash mismatches. PASS only when exactly
850 are READY; 150 receive their predetermined HOLD; every valid
object maps once; zero orphans/duplicates; replay creates nothing;
rollback restores the exact baseline; no result/report releases
without named approval.

AquaTrace HOLD / BUILD-AND-VERIFY. Adapters stay simulated/read-only.
No public-health interpretation. PRE-SALE TRANSPORT: NONE.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

DEMAND_ID = "slo-cls-cutover-evidence-lims-01"
SCHEMA = "commons-slo-cls-cutover-evidence-lims/v1"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
BUYER = "Glen M. Miller / San Luis Obispo County Public Health Laboratory"
HUMAN_APPROVER = "APPROVER"
NAMED_HUMAN = "glen-m-miller"
VALID_COUNT = 850
HOLD_COUNT = 150
INPUT_COUNT = VALID_COUNT + HOLD_COUNT

HOLD_CODES = (
    "DUPLICATE_ID",
    "BROKEN_SAMPLE_TEST_REF",
    "METHOD_VERSION_CONFLICT",
    "REPORT_RESULT_HASH_MISMATCH",
)
HOLD_PLAN = {
    "DUPLICATE_ID": 50,
    "BROKEN_SAMPLE_TEST_REF": 40,
    "METHOD_VERSION_CONFLICT": 30,
    "REPORT_RESULT_HASH_MISMATCH": 30,
}

PANTHER_FUSION = {
    "PF-MEASLES": {"version": "PF-OA-2026.07", "kind": "MOLECULAR"},
    "PF-VZV": {"version": "PF-OA-2026.07", "kind": "MOLECULAR"},
    "PF-FLU": {"version": "PF-OA-2026.07", "kind": "MOLECULAR"},
    "PF-RSV": {"version": "PF-OA-2026.07", "kind": "MOLECULAR"},
}
METHODS = tuple(PANTHER_FUSION)
CONFLICT_PAIRS = (
    ("PF-MEASLES", "PF-OA-2025.01"),
    ("PF-VZV", "PF-OA-2024.11"),
    ("PF-FLU", "LEGACY-FLU-2019"),
    ("PF-RSV", "PF-OA-2023.03"),
    ("PF-MEASLES", "WRONG-REV"),
    ("PF-VZV", "INCUMBENT-ONLY"),
)

GOLDEN_COUNTS = {
    "input_rows": INPUT_COUNT,
    "ready": VALID_COUNT,
    "held": HOLD_COUNT,
    "mapped_once": VALID_COUNT,
    "orphans": 0,
    "duplicate_mappings": 0,
    "released_reports": 0,
    "staged_reports": VALID_COUNT,
    "replay_added_records": 0,
    "rollback_restored": 1,
    "production_writes": 0,
}

# Locked after the first deterministic PASS of this exact fixture.
GOLDEN_FIXTURE_SHA256 = "156ce11a5dd46c0b081eff9b9da3dba1bfdd5264b53db6bc6a9d1c76cd641ef4"
GOLDEN_AUDIT_SHA256 = "92c29637e02a6eda62707c87bf0e1a5be816f5f6a910cf577fd985fbf1f57dea"
GOLDEN_LINEAGE_SHA256 = "e3ab31e345104a78eb97d2301923aed660b712837517ca2666ca8b427de97d68"
GOLDEN_BASELINE_SHA256 = "4bdef9e897246f67333bd22f1c2035510db25754d3acf8de606780448af38a56"
HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE / "revenue" / "slo_cls_cutover"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def method_for(index: int) -> str:
    return METHODS[(index - 1) % len(METHODS)]


def valid_bundle_id(index: int) -> str:
    return "SLO-V%04d" % index


def valid_accession_id(index: int) -> str:
    return "REQ-V%04d" % index


def valid_sample_id(index: int) -> str:
    return "SMP-V%04d" % index


def valid_test_id(index: int) -> str:
    return "TST-V%04d" % index


def incumbent_id(index: int) -> str:
    return "INC-V%04d" % index


def cls_id_for(incumbent: str, accession_id: str, sample_id: str) -> str:
    digest = sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "CLS_MAP",
            "incumbent_id": incumbent,
            "accession_id": accession_id,
            "sample_id": sample_id,
        }
    )
    return "CLS-" + digest[:12]


def source_hash(accession_id: str, sample_id: str, test_id: str) -> str:
    return sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "SOURCE",
            "accession_id": accession_id,
            "sample_id": sample_id,
            "test_id": test_id,
        }
    )


def method_hash(method: str, method_version: str) -> str:
    return sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "METHOD",
            "method": method,
            "method_version": method_version,
        }
    )


def result_packet(index: int, method: str) -> dict[str, Any]:
    return {
        "instrument_id": "SIM-PANTHER-FUSION-01",
        "adapter": "SIMULATED",
        "method": method,
        "ct": round(18.0 + ((index - 1) % 40) * 0.15, 2),
        "detected": (index % 17) != 0,
        "qc_ok": True,
    }


def result_hash(packet: dict[str, Any]) -> str:
    body = {key: value for key, value in packet.items() if key not in {"adapter"}}
    return sha256_hex({"demand_id": DEMAND_ID, "kind": "RESULT", "raw": body})


def report_hash(accession_id: str, result_digest: str) -> str:
    return sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "kind": "REPORT",
            "accession_id": accession_id,
            "result_hash": result_digest,
        }
    )


def _base_row(
    row_id: str,
    bundle_id: str,
    *,
    accession_id: str,
    sample_id: str,
    test_id: str,
    method: str,
    method_version: str | None = None,
    incumbent: str | None = None,
    valid_index: int | None = None,
    expected_hold: str | None = None,
    result_digest: str | None = None,
    report_digest: str | None = None,
    source_digest: str | None = None,
) -> dict[str, Any]:
    index = valid_index or 1
    spec = PANTHER_FUSION.get(method)
    version = method_version if method_version is not None else (spec["version"] if spec else "UNKNOWN")
    packet = result_packet(index, method if spec else "PF-MEASLES")
    computed_result = result_hash(packet)
    result_digest = computed_result if result_digest is None else result_digest
    report_digest = report_hash(accession_id, computed_result) if report_digest is None else report_digest
    source_digest = source_hash(accession_id, sample_id, test_id) if source_digest is None else source_digest
    return {
        "row_id": row_id,
        "bundle_id": bundle_id,
        "accession_id": accession_id,
        "sample_id": sample_id,
        "test_id": test_id,
        "method": method,
        "method_version": version,
        "incumbent_id": incumbent or ("INC-%s" % bundle_id),
        "raw": packet,
        "result_hash": result_digest,
        "report_hash": report_digest,
        "source_hash": source_digest,
        "method_hash": method_hash(method, version) if spec and version == spec["version"] else "",
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
                "R%04d" % index,
                valid_bundle_id(index),
                accession_id=valid_accession_id(index),
                sample_id=valid_sample_id(index),
                test_id=valid_test_id(index),
                method=method,
                incumbent=incumbent_id(index),
                valid_index=index,
            )
        )
    for offset in range(50):
        target = (offset % VALID_COUNT) + 1
        rows.append(
            _base_row(
                "R%04d" % (851 + offset),
                "SLO-HDUP%02d" % (offset + 1),
                accession_id=valid_accession_id(target),
                sample_id=valid_sample_id(target),
                test_id="TST-HDUP%02d" % (offset + 1),
                method=method_for(target),
                incumbent="INC-HDUP%02d" % (offset + 1),
                expected_hold="DUPLICATE_ID",
            )
        )
    for offset in range(40):
        broken_sample = "" if offset % 2 == 0 else "SMP-ORPHAN%02d" % (offset + 1)
        broken_test = "" if offset % 2 == 1 else "TST-ORPHAN%02d" % (offset + 1)
        rows.append(
            _base_row(
                "R%04d" % (901 + offset),
                "SLO-HREF%02d" % (offset + 1),
                accession_id="REQ-HREF%02d" % (offset + 1),
                sample_id=broken_sample,
                test_id=broken_test,
                method="PF-MEASLES",
                incumbent="INC-HREF%02d" % (offset + 1),
                expected_hold="BROKEN_SAMPLE_TEST_REF",
            )
        )
    for offset in range(30):
        method, version = CONFLICT_PAIRS[offset % len(CONFLICT_PAIRS)]
        rows.append(
            _base_row(
                "R%04d" % (941 + offset),
                "SLO-HVER%02d" % (offset + 1),
                accession_id="REQ-HVER%02d" % (offset + 1),
                sample_id="SMP-HVER%02d" % (offset + 1),
                test_id="TST-HVER%02d" % (offset + 1),
                method=method,
                method_version=version,
                incumbent="INC-HVER%02d" % (offset + 1),
                expected_hold="METHOD_VERSION_CONFLICT",
            )
        )
    for offset in range(30):
        index = 1 + offset
        method = method_for(index)
        packet = result_packet(index, method)
        true_result = result_hash(packet)
        rows.append(
            _base_row(
                "R%04d" % (971 + offset),
                "SLO-HHASH%02d" % (offset + 1),
                accession_id="REQ-HHASH%02d" % (offset + 1),
                sample_id="SMP-HHASH%02d" % (offset + 1),
                test_id="TST-HHASH%02d" % (offset + 1),
                method=method,
                incumbent="INC-HHASH%02d" % (offset + 1),
                valid_index=index,
                expected_hold="REPORT_RESULT_HASH_MISMATCH",
                result_digest=true_result,
                report_digest="TAMPERED-" + true_result[:16],
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
        "input_rows": len(inbound),
        "valid_rows": sum(1 for row in inbound if row.get("expected_hold") is None),
        "hold_rows": sum(1 for row in inbound if row.get("expected_hold")),
        "hold_plan": dict(HOLD_PLAN),
        "row_ids": [row["row_id"] for row in inbound],
        "bundle_ids": [row["bundle_id"] for row in inbound],
        "expected_holds": [row.get("expected_hold") for row in inbound],
        "interfaces": "SIMULATED",
        "interface_live": False,
        "production_writes": False,
        "autonomous_release": False,
        "public_health_decision": False,
    }
    body["fixture_sha256"] = sha256_hex(body)
    return body


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "accessions": {},
        "holds": [],
        "events": [],
        "seen_ids": {},
        "mappings": {},
        "baseline": None,
        "migrated": False,
    }


def _event(journal: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    journal["events"].append({"seq": len(journal["events"]) + 1, "kind": kind, **deepcopy(payload)})


def journal_baseline_body(journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "accessions": deepcopy(journal["accessions"]),
        "holds": deepcopy(journal["holds"]),
        "seen_ids": deepcopy(journal["seen_ids"]),
        "mappings": deepcopy(journal["mappings"]),
        "migrated": journal["migrated"],
    }


def snapshot_baseline(journal: dict[str, Any]) -> str:
    body = journal_baseline_body(journal)
    digest = sha256_hex(body)
    journal["baseline"] = {"sha256": digest, "body": body}
    return digest


def classify_bundle(row: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    accession_id = _text(row.get("accession_id"))
    sample_id = _text(row.get("sample_id"))
    test_id = _text(row.get("test_id"))
    method = _text(row.get("method"))
    method_version = _text(row.get("method_version"))
    spec = PANTHER_FUSION.get(method)
    key = accession_id or None

    if key and key in journal["seen_ids"]:
        return {"ok": False, "code": "DUPLICATE_ID", "accession_id": accession_id, "bundle_id": _text(row.get("bundle_id"))}
    if not sample_id or not test_id:
        return {"ok": False, "code": "BROKEN_SAMPLE_TEST_REF", "accession_id": accession_id or None}
    if spec is None or spec["version"] != method_version:
        return {
            "ok": False,
            "code": "METHOD_VERSION_CONFLICT",
            "accession_id": accession_id or None,
            "method": method,
            "method_version": method_version,
        }
    packet = deepcopy(row.get("raw") or {})
    computed = result_hash(packet)
    declared_result = _text(row.get("result_hash"))
    declared_report = _text(row.get("report_hash"))
    expected_report = report_hash(accession_id, computed)
    if declared_result != computed or declared_report != expected_report:
        return {"ok": False, "code": "REPORT_RESULT_HASH_MISMATCH", "accession_id": accession_id}
    return {
        "ok": True,
        "accession_id": accession_id,
        "sample_id": sample_id,
        "test_id": test_id,
        "method": method,
        "method_version": method_version,
        "incumbent_id": _text(row.get("incumbent_id")),
        "bundle_id": _text(row.get("bundle_id")),
    }


def rendered_report(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "demand_id": DEMAND_ID,
        "accession_id": record["accession_id"],
        "sample_id": record["sample_id"],
        "method": record["method"],
        "method_version": record["method_version"],
        "result_hash": record["result_hash"],
        "report_hash": record["report_hash"],
        "source_hash": record["source_hash"],
        "cls_id": record.get("cls_id"),
        "state": "STAGED",
        "released": bool(record.get("released")),
        "interface_live": False,
        "public_health_decision": False,
    }


def report_status(record: dict[str, Any]) -> str:
    if record.get("released"):
        return "RELEASED"
    return "STAGED_PENDING_NAMED_APPROVAL"


def ingest_row(journal: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    row_id = _text(row.get("row_id"))
    existing = next(
        (item for item in journal["accessions"].values() if item["row_id"] == row_id),
        None,
    )
    if existing is not None:
        _event(journal, "REPLAY_NOOP", {"accession_id": existing["accession_id"], "bundle_id": existing["bundle_id"]})
        return {"kind": "REPLAY_NOOP", "accession_id": existing["accession_id"], "bundle_id": existing["bundle_id"]}

    existing_hold = next((item for item in journal["holds"] if item["row_id"] == row_id), None)
    if existing_hold is not None:
        _event(journal, "REPLAY_NOOP", {"bundle_id": existing_hold.get("bundle_id"), "code": existing_hold["code"]})
        return {"kind": "REPLAY_NOOP", "bundle_id": existing_hold.get("bundle_id"), "code": existing_hold["code"]}

    verdict = classify_bundle(row, journal)
    if not verdict["ok"]:
        hold = {
            "row_id": row_id,
            "bundle_id": _text(row.get("bundle_id")),
            "accession_id": verdict.get("accession_id"),
            "code": verdict["code"],
            "state": "HOLD",
            "mapped": False,
            "cls_id": None,
            "released": False,
        }
        journal["holds"].append(hold)
        _event(journal, "HOLD", hold)
        return {"kind": "HOLD", "duplicate": False, **hold}

    acc_id = verdict["accession_id"]
    packet = deepcopy(row.get("raw") or {})
    computed_result = result_hash(packet)
    record = {
        "accession_id": acc_id,
        "row_id": row_id,
        "bundle_id": verdict["bundle_id"],
        "sample_id": verdict["sample_id"],
        "test_id": verdict["test_id"],
        "method": verdict["method"],
        "method_version": verdict["method_version"],
        "incumbent_id": verdict["incumbent_id"],
        "cls_id": None,
        "raw": packet,
        "result_hash": computed_result,
        "report_hash": report_hash(acc_id, computed_result),
        "source_hash": source_hash(acc_id, verdict["sample_id"], verdict["test_id"]),
        "method_hash": method_hash(verdict["method"], verdict["method_version"]),
        "state": "READY",
        "released": False,
        "released_by": None,
        "report_status": "STAGED_PENDING_NAMED_APPROVAL",
        "interface_state": "SIMULATED",
        "interface_live": False,
    }
    record["report"] = rendered_report(record)
    journal["accessions"][acc_id] = record
    journal["seen_ids"][acc_id] = row_id
    _event(journal, "READY", {"accession_id": acc_id, "bundle_id": verdict["bundle_id"]})
    return {"kind": "READY", "accession_id": acc_id, "bundle_id": verdict["bundle_id"]}


def migrate(journal: dict[str, Any]) -> dict[str, Any]:
    if journal["baseline"] is None:
        snapshot_baseline(journal)
    mappings = {}
    for acc_id, record in journal["accessions"].items():
        mapped = cls_id_for(record["incumbent_id"], acc_id, record["sample_id"])
        record["cls_id"] = mapped
        record["report"] = rendered_report(record)
        mappings[record["incumbent_id"]] = mapped
        _event(journal, "MAPPED", {"incumbent_id": record["incumbent_id"], "cls_id": mapped})
    journal["mappings"] = mappings
    journal["migrated"] = True
    return {
        "mapped": len(mappings),
        "orphans": 0,
        "duplicate_mappings": 0 if len(set(mappings.values())) == len(mappings) else 1,
    }


def rollback(journal: dict[str, Any]) -> dict[str, Any]:
    baseline = journal.get("baseline")
    if not baseline:
        return {"ok": False, "code": "NO_BASELINE"}
    restored = deepcopy(baseline["body"])
    journal["accessions"] = restored["accessions"]
    journal["holds"] = restored["holds"]
    journal["seen_ids"] = restored["seen_ids"]
    journal["mappings"] = restored["mappings"]
    journal["migrated"] = restored["migrated"]
    digest = sha256_hex(journal_baseline_body(journal))
    _event(journal, "ROLLBACK", {"baseline_sha256": baseline["sha256"], "restored_sha256": digest})
    return {
        "ok": digest == baseline["sha256"],
        "baseline_sha256": baseline["sha256"],
        "restored_sha256": digest,
    }


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
    baseline_sha = snapshot_baseline(journal)
    migration = migrate(journal)
    autonomous = [
        release_report(journal, acc_id, actor_role="SYSTEM", actor="autonomous")
        for acc_id in journal["accessions"]
    ]
    ready = sorted(journal["accessions"].values(), key=lambda item: item["accession_id"])
    hold_codes = [item["code"] for item in journal["holds"]]
    mappings = dict(journal["mappings"])
    cls_ids = list(mappings.values())
    lineage = [
        {
            "accession_id": item["accession_id"],
            "incumbent_id": item["incumbent_id"],
            "cls_id": item["cls_id"],
            "source_hash": item["source_hash"],
            "method_hash": item["method_hash"],
            "result_hash": item["result_hash"],
            "report_hash": item["report_hash"],
        }
        for item in ready
    ]
    audit = {
        "demand_id": DEMAND_ID,
        "accession_ids": [item["accession_id"] for item in ready],
        "incumbent_ids": [item["incumbent_id"] for item in ready],
        "cls_ids": [item["cls_id"] for item in ready],
        "hold_codes": hold_codes,
        "hold_bundle_ids": [item["bundle_id"] for item in journal["holds"]],
        "lineage": lineage,
        "released": [item["accession_id"] for item in ready if item["released"]],
        "baseline_sha256": baseline_sha,
    }
    rollback_probe = empty_journal()
    for row in inbound:
        ingest_row(rollback_probe, row)
    snapshot_baseline(rollback_probe)
    migrate(rollback_probe)
    rolled = rollback(rollback_probe)
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
        "mapped_once": len(mappings),
        "orphans": 0 if len(mappings) == len(ready) else 1,
        "duplicate_mappings": 0 if len(set(cls_ids)) == len(cls_ids) else 1,
        "released_reports": sum(1 for item in ready if item["released"]),
        "staged_reports": sum(1 for item in ready if item["report_status"] == "STAGED_PENDING_NAMED_APPROVAL"),
        "replay_noops": sum(1 for item in effects if item.get("kind") == "REPLAY_NOOP"),
        "effects": effects,
        "autonomous_release_effects": autonomous,
        "accessions": ready,
        "holds": deepcopy(journal["holds"]),
        "mappings": mappings,
        "lineage": lineage,
        "lineage_sha256": sha256_hex(lineage),
        "audit": audit,
        "audit_sha256": sha256_hex(audit),
        "baseline_sha256": baseline_sha,
        "rollback_restored": 1 if rolled.get("ok") else 0,
        "rollback": rolled,
        "migration": migration,
        "interface_live": False,
        "interfaces": "SIMULATED",
        "autonomous_certification": False,
        "autonomous_release": False,
        "public_health_decision": False,
        "production_writes": 0,
        "pre_sale_transport": "NONE",
        "cash_usd": 0,
        "journal": journal,
    }
    body["manifest_sha256"] = sha256_hex(
        {key: value for key, value in body.items() if key not in {"manifest_sha256", "journal"}}
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
        "mapped_once": result.get("mapped_once"),
        "orphans": result.get("orphans"),
        "duplicate_mappings": result.get("duplicate_mappings"),
        "released_reports": result.get("released_reports"),
        "staged_reports": result.get("staged_reports"),
        "replay_added_records": result.get("replay_added_records", 0),
        "rollback_restored": result.get("rollback_restored"),
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
    accession_ids = [item["accession_id"] for item in result.get("accessions") or []]
    if len(set(accession_ids)) != VALID_COUNT:
        failures.append("accession_ids_not_unique")
    cls_ids = [item["cls_id"] for item in result.get("accessions") or []]
    if len(set(cls_ids)) != VALID_COUNT or any(not item for item in cls_ids):
        failures.append("cls_ids")
    incumbent_ids = [item["incumbent_id"] for item in result.get("accessions") or []]
    if len(set(incumbent_ids)) != VALID_COUNT:
        failures.append("incumbent_ids")
    for item in result.get("accessions") or []:
        if item.get("source_hash") != source_hash(item["accession_id"], item["sample_id"], item["test_id"]):
            failures.append("source_hash")
            break
        if item.get("method_hash") != method_hash(item["method"], item["method_version"]):
            failures.append("method_hash")
            break
        if item.get("result_hash") != result_hash(item["raw"]):
            failures.append("result_hash")
            break
        if item.get("report_hash") != report_hash(item["accession_id"], item["result_hash"]):
            failures.append("report_hash")
            break
        if item.get("released"):
            failures.append("released")
            break
        if item.get("interface_live"):
            failures.append("interface_live_accession")
            break
        if item.get("report", {}).get("state") != "STAGED":
            failures.append("report_not_staged")
            break
    if any(item.get("mapped") or item.get("cls_id") for item in result.get("holds") or []):
        failures.append("hold_mapped")
    if result.get("interface_live") is not False:
        failures.append("interface_live")
    if result.get("interfaces") != "SIMULATED":
        failures.append("interfaces")
    if result.get("autonomous_release") is not False:
        failures.append("autonomous_release")
    if result.get("public_health_decision") is not False:
        failures.append("public_health_decision")
    if not all(
        item.get("code") == "AUTONOMOUS_RELEASE_DENIED"
        for item in result.get("autonomous_release_effects") or []
    ):
        failures.append("autonomous_release_not_denied")
    if not result.get("rollback", {}).get("ok"):
        failures.append("rollback")
    if GOLDEN_AUDIT_SHA256 != "PENDING" and result.get("audit_sha256") != GOLDEN_AUDIT_SHA256:
        failures.append("audit_sha256")
    if GOLDEN_LINEAGE_SHA256 != "PENDING" and result.get("lineage_sha256") != GOLDEN_LINEAGE_SHA256:
        failures.append("lineage_sha256")
    if GOLDEN_BASELINE_SHA256 != "PENDING" and result.get("baseline_sha256") != GOLDEN_BASELINE_SHA256:
        failures.append("baseline_sha256")
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
        "baseline_sha256": first.get("baseline_sha256"),
        "manifest_sha256": first.get("manifest_sha256"),
        "ready": first.get("ready"),
        "held": first.get("held"),
        "hold_codes": sorted(set(first.get("hold_codes") or [])),
        "mapped_once": first.get("mapped_once"),
        "rollback_restored": first.get("rollback_restored"),
        "replay_added_records": replay.get("added_record_count"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
