from __future__ import annotations

from typing import Any

from .codec import (
    AUTHORITY,
    BATCH_SCHEMA,
    MANIFEST_SCHEMA,
    MAX_RECORDS,
    RECEIPT_SCHEMA,
    GateInputError,
    _HEX64,
    _canonical,
    _dict,
    _keys,
    digest,
)
from .rules import classify, parse_record

__all__ = ["AUTHORITY", "GateInputError", "digest", "evaluate", "verify"]


def evaluate(batch: Any) -> dict[str, Any]:
    obj = _dict(batch, "batch")
    _keys(obj, {"schema", "records"}, "batch")
    if obj["schema"] != BATCH_SCHEMA:
        raise GateInputError("unsupported batch schema")
    raw_records = obj["records"]
    if type(raw_records) is not list or not 1 <= len(raw_records) <= MAX_RECORDS:
        raise GateInputError("batch.records cardinality is out of bounds")

    by_id: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    source_writes = 0
    network_writes = 0

    for raw in raw_records:
        record = parse_record(raw)
        prior = by_id.get(record["record_id"])
        if prior is not None:
            if digest(prior) != digest(record):
                raise GateInputError("same record_id decoded to different payload")
            continue
        by_id[record["record_id"]] = record
        status, holds = classify(record)
        evidence = {
            "record_id": record["record_id"],
            "code": record["code"],
            "ingredient_id": record["ingredient_id"],
            "allergen_label_hash": record["allergen_label_hash"],
            "commercial_owner": record["commercial_owner"],
            "science_owner": record["science_owner"],
        }
        rows.append(
            {
                "record_id": record["record_id"],
                "code": record["code"],
                "status": status,
                "holds": holds,
                "evidence_sha256": digest(evidence),
            }
        )

    rows.sort(key=lambda row: (row["record_id"], row["code"]))
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    hold_count = sum(1 for row in rows if row["status"] == "HOLD")
    defect_count = sum(len(row["holds"]) for row in rows)
    manifest = {"schema": MANIFEST_SCHEMA, "authority": AUTHORITY, "rows": rows}
    manifest_sha = digest(manifest)
    core = {
        "schema": RECEIPT_SCHEMA,
        "authority": AUTHORITY,
        "decision": "HOLD" if hold_count else "PASS",
        "record_count": len(rows),
        "pass_count": pass_count,
        "hold_count": hold_count,
        "seeded_defect_count": defect_count,
        "batch_sha256": digest(batch),
        "manifest_sha256": manifest_sha,
        "source_writes": source_writes,
        "network_writes": network_writes,
        "external_authority": False,
        "formulation_approved": False,
        "claim_approved": False,
        "regulatory_decision": False,
        "product_release_authorized": False,
        "buyer_acceptance_inferred": False,
        "recognized_revenue_inferred": False,
    }
    receipt = dict(core)
    receipt["receipt_sha256"] = digest(core)
    report = _report(rows, receipt)
    return {"receipt": receipt, "manifest": manifest, "report": report}


def _report(rows: list[dict[str, Any]], receipt: dict[str, Any]) -> str:
    lines = [
        "# Tate & Lyle / CP Kelco solution-proof report",
        "",
        f"authority: {receipt['authority']}",
        f"records: {receipt['record_count']}",
        f"PASS: {receipt['pass_count']}",
        f"HOLD: {receipt['hold_count']}",
        f"defects: {receipt['seeded_defect_count']}",
        f"manifest: {receipt['manifest_sha256']}",
        f"receipt: {receipt['receipt_sha256']}",
        "",
        "PASS/HOLD is evidence completeness only. Owners decide.",
        "",
    ]
    for row in rows:
        holds = ",".join(row["holds"]) if row["holds"] else "-"
        lines.append(f"{row['status']} {row['record_id']} {row['code']} {holds}")
    return "\n".join(lines) + "\n"


def verify(result: Any, *, batch: Any) -> bool:
    try:
        obj = _dict(result, "result")
        _keys(obj, {"receipt", "manifest", "report"}, "result")
        receipt = _dict(obj["receipt"], "result.receipt")
        expected_fields = {
            "schema",
            "authority",
            "decision",
            "record_count",
            "pass_count",
            "hold_count",
            "seeded_defect_count",
            "batch_sha256",
            "manifest_sha256",
            "source_writes",
            "network_writes",
            "external_authority",
            "formulation_approved",
            "claim_approved",
            "regulatory_decision",
            "product_release_authorized",
            "buyer_acceptance_inferred",
            "recognized_revenue_inferred",
            "receipt_sha256",
        }
        _keys(receipt, expected_fields, "result.receipt")
        if receipt["schema"] != RECEIPT_SCHEMA or receipt["authority"] != AUTHORITY:
            return False
        for field in (
            "external_authority",
            "formulation_approved",
            "claim_approved",
            "regulatory_decision",
            "product_release_authorized",
            "buyer_acceptance_inferred",
            "recognized_revenue_inferred",
        ):
            if receipt[field] is not False:
                return False
        if receipt["source_writes"] != 0 or receipt["network_writes"] != 0:
            return False
        if receipt["batch_sha256"] != digest(batch):
            return False
        if receipt["manifest_sha256"] != digest(obj["manifest"]):
            return False
        core = dict(receipt)
        supplied = core.pop("receipt_sha256")
        if type(supplied) is not str or _HEX64.fullmatch(supplied) is None or supplied != digest(core):
            return False
        expected = evaluate(batch)
        return _canonical(expected) == _canonical(obj)
    except (GateInputError, KeyError, TypeError, ValueError):
        return False
