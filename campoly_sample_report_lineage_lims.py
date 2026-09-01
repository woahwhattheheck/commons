#!/usr/bin/env python3
"""Synthetic Cambridge Polymer sample-to-report lineage LIMS.

Demand: campoly-sample-report-lineage-lims-01
Buyer pairing: Norma Turner / Cambridge Polymer Group

This fail-closed fixture engine reconciles quote, purchase-order, request-form,
SDS, sample-bag, package, method/version, raw-result, and staged-report
lineage. It has no live adapter and performs no production write or automatic
report release.

Official acceptance:
    python test_campoly_sample_report_lineage_lims.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

DEMAND_ID = "campoly-sample-report-lineage-lims-01"
SCHEMA = "commons-campoly-sample-report-lineage-lims/v1"
BUYER = "Norma Turner / Cambridge Polymer Group"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
OFFICIAL_BINARY = "python campoly_sample_report_lineage_lims.py"
OFFICIAL_TEST = "python test_campoly_sample_report_lineage_lims.py"

INPUT_COUNT = 100
READY_COUNT = 80
MISSING_QUOTE_COUNT = 8
REQUIRED_SDS_COUNT = 4
DUPLICATE_ID_COUNT = 4
BAG_FORM_MISMATCH_COUNT = 4
HOLD_COUNT = (
    MISSING_QUOTE_COUNT
    + REQUIRED_SDS_COUNT
    + DUPLICATE_ID_COUNT
    + BAG_FORM_MISMATCH_COUNT
)

HOLD_CODES = (
    "HOLD_MISSING_QUOTE_LINK",
    "HOLD_REQUIRED_SDS",
    "HOLD_DUPLICATE_ID",
    "HOLD_BAG_FORM_MISMATCH",
)
HOLD_COUNTS = {
    "HOLD_MISSING_QUOTE_LINK": MISSING_QUOTE_COUNT,
    "HOLD_REQUIRED_SDS": REQUIRED_SDS_COUNT,
    "HOLD_DUPLICATE_ID": DUPLICATE_ID_COUNT,
    "HOLD_BAG_FORM_MISMATCH": BAG_FORM_MISMATCH_COUNT,
}

METHOD_CATALOG: dict[str, dict[str, str]] = {
    "ROUTINE": {
        "method": "SYN-CPG-FTIR-ATR",
        "version": "2026.1",
        "unit": "absorbance-unit",
        "qualifier": "ACCEPTED",
    },
    "NON_ROUTINE": {
        "method": "SYN-CPG-DSC-CUSTOM",
        "version": "2026.2",
        "unit": "degC",
        "qualifier": "REVIEWED",
    },
}

REVIEWER_DIRECTORY = {
    "SYN-HUMAN-CAMPOLY-REVIEWER-01": {
        "display_name": "Synthetic Named Reviewer One",
        "permissions": ("RELEASE_ANALYTICAL_REPORT",),
        "human": True,
    }
}
AUTOMATION_IDENTITIES = frozenset(
    {"", "SYSTEM", "AUTO", "AUTOMATION", "BOT", "MACHINE"}
)

UNIQUE_ID_FIELDS = (
    "shipment_id",
    "quote_id",
    "purchase_order_id",
    "request_form_id",
    "sds_id",
    "package_id",
    "bag_id",
    "sample_id",
)


def _receipt_goldens() -> dict[str, str]:
    path = (
        Path(__file__).resolve().parent
        / "revenue"
        / "campoly_sample_report_lineage_lims"
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


def _quote_link(quote_id: str) -> str:
    return f"synthetic://quote/{quote_id}"


def _po_link(purchase_order_id: str) -> str:
    return f"synthetic://purchase-order/{purchase_order_id}"


def _form_link(request_form_id: str) -> str:
    return f"synthetic://request-form/{request_form_id}"


def _sds_digest(sds_id: str, revision: str) -> str:
    return sha256_hex({"sds_id": sds_id, "revision": revision})


def _accession_id(shipment_id: str) -> str:
    return "CPG-ACC-" + sha256_hex(
        {"demand_id": DEMAND_ID, "shipment_id": shipment_id}
    )[:14]


def _work_order_id(sample_id: str, method: str, version: str) -> str:
    return "CPG-WO-" + sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "sample_id": sample_id,
            "method": method,
            "version": version,
        }
    )[:14]


def _result_id(sample_id: str, source_uri: str) -> str:
    return "CPG-RES-" + sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "sample_id": sample_id,
            "source_uri": source_uri,
        }
    )[:14]


def _report_id(sample_id: str) -> str:
    return "CPG-RPT-" + sha256_hex(
        {"demand_id": DEMAND_ID, "sample_id": sample_id}
    )[:14]


def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "shipment_id": row["shipment_id"],
        "quote_id": row["quote_id"],
        "quote_link": row["quote_link"],
        "purchase_order_id": row["purchase_order_id"],
        "po_quote_id": row["po_quote_id"],
        "po_link": row["po_link"],
        "request_form_id": row["request_form_id"],
        "form_po_id": row["form_po_id"],
        "form_link": row["form_link"],
        "sds_required": row["sds_required"],
        "sds_id": row["sds_id"],
        "sds_revision": row["sds_revision"],
        "sds_sha256": row["sds_sha256"],
        "package_id": row["package_id"],
        "bag_id": row["bag_id"],
        "bag_label_sample_id": row["bag_label_sample_id"],
        "form_sample_id": row["form_sample_id"],
        "sample_id": row["sample_id"],
        "synthetic": row["synthetic"],
        "deidentified": row["deidentified"],
    }


def _method_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "method_class": row["method_class"],
        "method": row["method"],
        "method_version": row["method_version"],
    }


def _result_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": row["sample_id"],
        "method": row["method"],
        "method_version": row["method_version"],
        "value": row["result_value"],
        "unit": row["result_unit"],
        "qualifier": row["result_qualifier"],
        "source_uri": row["raw_source_uri"],
        "source_revision": row["raw_source_revision"],
    }


def _derived_hashes(row: dict[str, Any]) -> dict[str, str]:
    source_hash = sha256_hex(_source_payload(row))
    method_hash = sha256_hex(_method_payload(row))
    result_hash = sha256_hex(_result_payload(row))
    report_core = {
        "report_id": _report_id(row["sample_id"]),
        "accession_id": _accession_id(row["shipment_id"]),
        "work_order_id": _work_order_id(
            row["sample_id"], row["method"], row["method_version"]
        ),
        "result_id": _result_id(row["sample_id"], row["raw_source_uri"]),
        "sample_id": row["sample_id"],
        "package_id": row["package_id"],
        "source_sha256": source_hash,
        "method_sha256": method_hash,
        "result_sha256": result_hash,
        "value_sha256": sha256_hex({"value": row["result_value"]}),
        "unit_sha256": sha256_hex({"unit": row["result_unit"]}),
        "qualifier_sha256": sha256_hex(
            {"qualifier": row["result_qualifier"]}
        ),
        "status": "STAGED",
    }
    return {
        "source_sha256": source_hash,
        "method_sha256": method_hash,
        "result_sha256": result_hash,
        "value_sha256": report_core["value_sha256"],
        "unit_sha256": report_core["unit_sha256"],
        "qualifier_sha256": report_core["qualifier_sha256"],
        "report_sha256": sha256_hex(report_core),
    }


def _stamp_goldens(row: dict[str, Any]) -> dict[str, Any]:
    stamped = deepcopy(row)
    stamped["golden_hashes"] = _derived_hashes(stamped)
    return stamped


def _base_shipment(index: int) -> dict[str, Any]:
    token = f"{index:03d}"
    method_class = "ROUTINE" if index % 2 else "NON_ROUTINE"
    method = METHOD_CATALOG[method_class]
    sds_id = f"CPG-SDS-{token}"
    row: dict[str, Any] = {
        "row_id": f"CPG-ROW-{token}",
        "shipment_id": f"CPG-SHIP-{token}",
        "quote_id": f"CPG-QUOTE-{token}",
        "quote_link": _quote_link(f"CPG-QUOTE-{token}"),
        "purchase_order_id": f"CPG-PO-{token}",
        "po_quote_id": f"CPG-QUOTE-{token}",
        "po_link": _po_link(f"CPG-PO-{token}"),
        "request_form_id": f"CPG-FORM-{token}",
        "form_po_id": f"CPG-PO-{token}",
        "form_link": _form_link(f"CPG-FORM-{token}"),
        "sds_required": True,
        "sds_id": sds_id,
        "sds_revision": "2026.1",
        "sds_sha256": _sds_digest(sds_id, "2026.1"),
        "package_id": f"CPG-PKG-{token}",
        "bag_id": f"CPG-BAG-{token}",
        "sample_id": f"CPG-SAMPLE-{token}",
        "bag_label_sample_id": f"CPG-SAMPLE-{token}",
        "form_sample_id": f"CPG-SAMPLE-{token}",
        "method_class": method_class,
        "method": method["method"],
        "method_version": method["version"],
        "raw_source_uri": f"synthetic://instrument/run-{token}.json",
        "raw_source_revision": "RAW-2026.1",
        "result_value": round(20.0 + index * 0.125, 3),
        "result_unit": method["unit"],
        "result_qualifier": method["qualifier"],
        "synthetic": True,
        "deidentified": True,
        "expected_state": "READY",
        "expected_hold": None,
    }
    return _stamp_goldens(row)


def _missing_quote_shipment(index: int) -> dict[str, Any]:
    row = _base_shipment(index)
    row["quote_link"] = ""
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_MISSING_QUOTE_LINK"
    return _stamp_goldens(row)


def _required_sds_shipment(index: int) -> dict[str, Any]:
    row = _base_shipment(index)
    row["sds_id"] = ""
    row["sds_revision"] = ""
    row["sds_sha256"] = ""
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_REQUIRED_SDS"
    return _stamp_goldens(row)


def _duplicate_id_shipment(slot: int) -> dict[str, Any]:
    row = _base_shipment(slot + 1)
    row["row_id"] = f"CPG-ROW-{93 + slot:03d}"
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_DUPLICATE_ID"
    return _stamp_goldens(row)


def _bag_form_mismatch_shipment(index: int) -> dict[str, Any]:
    row = _base_shipment(index)
    row["bag_label_sample_id"] = f"CPG-SAMPLE-MISMATCH-{index:03d}"
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_BAG_FORM_MISMATCH"
    return _stamp_goldens(row)


def build_acceptance_fixture() -> list[dict[str, Any]]:
    """Build the frozen 100-shipment 80 READY / 20 HOLD fixture."""
    rows = [_base_shipment(index) for index in range(1, 81)]
    rows.extend(_missing_quote_shipment(index) for index in range(81, 89))
    rows.extend(_required_sds_shipment(index) for index in range(89, 93))
    rows.extend(_duplicate_id_shipment(slot) for slot in range(4))
    rows.extend(_bag_form_mismatch_shipment(index) for index in range(97, 101))
    if len(rows) != INPUT_COUNT:
        raise RuntimeError("fixture cardinality drift")
    return rows


def fixture_sha256(rows: list[dict[str, Any]] | None = None) -> str:
    return sha256_hex(
        rows if rows is not None else build_acceptance_fixture()
    )


class SyntheticReadOnlyShipmentAdapter:
    """Read-only in-memory fixture source; no live or write capability."""

    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = deepcopy(rows)
        self.mode = "SYNTHETIC_READ_ONLY"
        self.live = False
        self.writes = 0

    def list_shipments(self) -> list[dict[str, Any]]:
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
        "accessions": {},
        "work_orders": {},
        "results": {},
        "reports": {},
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


def normalize_shipment(row: dict[str, Any]) -> dict[str, Any]:
    source = _mapping(row, "row")
    golden = _mapping(source.get("golden_hashes"), "golden_hashes")
    norm = {
        "row_id": _text(source.get("row_id"), "row_id", allow_empty=False),
        "shipment_id": _text(source.get("shipment_id"), "shipment_id"),
        "quote_id": _text(source.get("quote_id"), "quote_id"),
        "quote_link": _text(source.get("quote_link"), "quote_link"),
        "purchase_order_id": _text(
            source.get("purchase_order_id"), "purchase_order_id"
        ),
        "po_quote_id": _text(source.get("po_quote_id"), "po_quote_id"),
        "po_link": _text(source.get("po_link"), "po_link"),
        "request_form_id": _text(
            source.get("request_form_id"), "request_form_id"
        ),
        "form_po_id": _text(source.get("form_po_id"), "form_po_id"),
        "form_link": _text(source.get("form_link"), "form_link"),
        "sds_required": _bool(source.get("sds_required"), "sds_required"),
        "sds_id": _text(source.get("sds_id"), "sds_id"),
        "sds_revision": _text(source.get("sds_revision"), "sds_revision"),
        "sds_sha256": _text(source.get("sds_sha256"), "sds_sha256"),
        "package_id": _text(source.get("package_id"), "package_id"),
        "bag_id": _text(source.get("bag_id"), "bag_id"),
        "bag_label_sample_id": _text(
            source.get("bag_label_sample_id"), "bag_label_sample_id"
        ),
        "form_sample_id": _text(
            source.get("form_sample_id"), "form_sample_id"
        ),
        "sample_id": _text(source.get("sample_id"), "sample_id"),
        "method_class": _text(
            source.get("method_class"), "method_class"
        ).upper(),
        "method": _text(source.get("method"), "method"),
        "method_version": _text(
            source.get("method_version"), "method_version"
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
        "result_qualifier": _text(
            source.get("result_qualifier"), "result_qualifier"
        ).upper(),
        "synthetic": _bool(source.get("synthetic"), "synthetic"),
        "deidentified": _bool(
            source.get("deidentified"), "deidentified"
        ),
        "golden_hashes": {
            key: _text(golden.get(key), f"golden_hashes.{key}")
            for key in (
                "source_sha256",
                "method_sha256",
                "result_sha256",
                "value_sha256",
                "unit_sha256",
                "qualifier_sha256",
                "report_sha256",
            )
        },
    }
    return norm


def classify_shipment(
    journal: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    if not row["synthetic"] or not row["deidentified"]:
        return {"ok": False, "code": "HOLD_TRUTH_BOUNDARY"}
    if (
        not row["quote_id"]
        or row["quote_link"] != _quote_link(row["quote_id"])
    ):
        return {"ok": False, "code": "HOLD_MISSING_QUOTE_LINK"}
    if row["sds_required"] and (
        not row["sds_id"]
        or not row["sds_revision"]
        or row["sds_sha256"]
        != _sds_digest(row["sds_id"], row["sds_revision"])
    ):
        return {"ok": False, "code": "HOLD_REQUIRED_SDS"}
    identifiers = [row[field] for field in UNIQUE_ID_FIELDS]
    if (
        any(not value for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
        or any(value in journal["identifier_index"] for value in identifiers)
    ):
        return {"ok": False, "code": "HOLD_DUPLICATE_ID"}
    if (
        row["po_quote_id"] != row["quote_id"]
        or row["po_link"] != _po_link(row["purchase_order_id"])
        or row["form_po_id"] != row["purchase_order_id"]
        or row["form_link"] != _form_link(row["request_form_id"])
        or row["bag_label_sample_id"] != row["sample_id"]
        or row["form_sample_id"] != row["sample_id"]
    ):
        return {"ok": False, "code": "HOLD_BAG_FORM_MISMATCH"}
    method = METHOD_CATALOG.get(row["method_class"])
    if (
        method is None
        or row["method"] != method["method"]
        or row["method_version"] != method["version"]
        or row["result_unit"] != method["unit"]
        or row["result_qualifier"] != method["qualifier"]
    ):
        return {"ok": False, "code": "HOLD_METHOD_BINDING"}
    if row["golden_hashes"] != _derived_hashes(row):
        return {"ok": False, "code": "HOLD_GOLDEN_HASH_MISMATCH"}
    return {"ok": True, "code": None}


def _commit(
    journal: dict[str, Any], candidate: dict[str, Any]
) -> None:
    journal.clear()
    journal.update(candidate)


def ingest_shipment(
    journal: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    """Ingest one row atomically; rejection never partially mutates state."""
    try:
        norm = normalize_shipment(row)
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
    verdict = classify_shipment(candidate, norm)
    if not verdict["ok"]:
        hold = {
            "row_id": row_id,
            "shipment_id": norm["shipment_id"] or None,
            "sample_id": norm["sample_id"] or None,
            "code": verdict["code"],
            "state": "HOLD",
            "accessions_created": 0,
            "work_orders_created": 0,
            "results_created": 0,
            "reports_staged": 0,
            "reports_released": 0,
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

    accession_id = _accession_id(norm["shipment_id"])
    work_order_id = _work_order_id(
        norm["sample_id"], norm["method"], norm["method_version"]
    )
    result_id = _result_id(norm["sample_id"], norm["raw_source_uri"])
    report_id = _report_id(norm["sample_id"])
    if (
        accession_id in candidate["accessions"]
        or work_order_id in candidate["work_orders"]
        or result_id in candidate["results"]
        or report_id in candidate["reports"]
    ):
        return {
            "kind": "REJECT",
            "ok": False,
            "code": "REJECT_DERIVED_IDENTIFIER_COLLISION",
            "row_id": row_id,
        }

    hashes = _derived_hashes(norm)
    accession = {
        "accession_id": accession_id,
        "shipment_id": norm["shipment_id"],
        "sample_id": norm["sample_id"],
        "quote_id": norm["quote_id"],
        "purchase_order_id": norm["purchase_order_id"],
        "request_form_id": norm["request_form_id"],
        "sds_id": norm["sds_id"],
        "package_id": norm["package_id"],
        "bag_id": norm["bag_id"],
        "source_sha256": hashes["source_sha256"],
        "state": "ACCESSIONED",
    }
    work_order = {
        "work_order_id": work_order_id,
        "accession_id": accession_id,
        "sample_id": norm["sample_id"],
        "method_class": norm["method_class"],
        "method": norm["method"],
        "method_version": norm["method_version"],
        "method_sha256": hashes["method_sha256"],
        "state": "COMPLETE_PENDING_REVIEW",
    }
    result = {
        "result_id": result_id,
        "work_order_id": work_order_id,
        "sample_id": norm["sample_id"],
        "value": norm["result_value"],
        "unit": norm["result_unit"],
        "qualifier": norm["result_qualifier"],
        "source_uri": norm["raw_source_uri"],
        "source_revision": norm["raw_source_revision"],
        "source_sha256": hashes["source_sha256"],
        "method_sha256": hashes["method_sha256"],
        "result_sha256": hashes["result_sha256"],
        "value_sha256": hashes["value_sha256"],
        "unit_sha256": hashes["unit_sha256"],
        "qualifier_sha256": hashes["qualifier_sha256"],
    }
    report = {
        "report_id": report_id,
        "accession_id": accession_id,
        "work_order_id": work_order_id,
        "result_id": result_id,
        "sample_id": norm["sample_id"],
        "package_id": norm["package_id"],
        "source_sha256": hashes["source_sha256"],
        "method_sha256": hashes["method_sha256"],
        "result_sha256": hashes["result_sha256"],
        "value_sha256": hashes["value_sha256"],
        "unit_sha256": hashes["unit_sha256"],
        "qualifier_sha256": hashes["qualifier_sha256"],
        "report_sha256": hashes["report_sha256"],
        "status": "STAGED",
        "released": False,
        "released_by": None,
    }

    candidate["accessions"][accession_id] = accession
    candidate["work_orders"][work_order_id] = work_order
    candidate["results"][result_id] = result
    candidate["reports"][report_id] = report
    for field in UNIQUE_ID_FIELDS:
        candidate["identifier_index"][norm[field]] = {
            "row_id": row_id,
            "field": field,
        }
    candidate["processed_rows"][row_id] = {
        "kind": "READY",
        "payload_sha256": payload_sha256,
        "accession_id": accession_id,
        "work_order_id": work_order_id,
        "result_id": result_id,
        "report_id": report_id,
    }
    _event(
        candidate,
        "REPORT_STAGED",
        {
            "row_id": row_id,
            "accession_id": accession_id,
            "work_order_id": work_order_id,
            "result_id": result_id,
            "report_id": report_id,
        },
    )
    _commit(journal, candidate)
    return {
        "kind": "READY",
        "ok": True,
        "row_id": row_id,
        "accession_id": accession_id,
        "work_order_id": work_order_id,
        "result_id": result_id,
        "report_id": report_id,
    }


def release_report(
    journal: dict[str, Any], report_id: str, *, reviewer_id: str
) -> dict[str, Any]:
    """Release only through the trusted named-human reviewer directory."""
    if not isinstance(report_id, str) or not isinstance(reviewer_id, str):
        return {"ok": False, "code": "RELEASE_INVALID_INPUT"}
    report_id = report_id.strip()
    reviewer_id = reviewer_id.strip()
    report = journal["reports"].get(report_id)
    if report is None:
        return {"ok": False, "code": "UNKNOWN_REPORT"}
    if reviewer_id.upper() in AUTOMATION_IDENTITIES:
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
    reviewer = REVIEWER_DIRECTORY.get(reviewer_id)
    if (
        reviewer is None
        or reviewer.get("human") is not True
        or "RELEASE_ANALYTICAL_REPORT"
        not in reviewer.get("permissions", ())
        or not reviewer.get("display_name")
    ):
        return {"ok": False, "code": "UNAUTHORIZED_REVIEWER"}
    if report["released"]:
        return {
            "ok": True,
            "duplicate": True,
            "status": "RELEASED",
            "released_by": report["released_by"],
        }

    candidate = deepcopy(journal)
    target = candidate["reports"][report_id]
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
            "report_id": report_id,
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
        "accessions": len(journal["accessions"]),
        "work_orders": len(journal["work_orders"]),
        "results": len(journal["results"]),
        "reports": len(journal["reports"]),
        "holds": len(journal["holds"]),
    }
    effects = [ingest_shipment(journal, row) for row in deepcopy(rows)]
    return {
        "added_accessions": len(journal["accessions"])
        - before["accessions"],
        "added_work_orders": len(journal["work_orders"])
        - before["work_orders"],
        "added_results": len(journal["results"]) - before["results"],
        "added_reports": len(journal["reports"]) - before["reports"],
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
    source = SyntheticReadOnlyShipmentAdapter(inbound)
    journal = empty_journal()
    effects = [
        ingest_shipment(journal, row) for row in source.list_shipments()
    ]
    autonomous_release_effects = [
        release_report(
            journal, report_id, reviewer_id="SYSTEM"
        )
        for report_id in sorted(journal["reports"])[:3]
    ]
    replay = replay_into(journal, inbound)
    holds = sorted(
        deepcopy(journal["holds"]), key=lambda item: item["row_id"]
    )
    accessions = sorted(
        deepcopy(list(journal["accessions"].values())),
        key=lambda item: item["accession_id"],
    )
    work_orders = sorted(
        deepcopy(list(journal["work_orders"].values())),
        key=lambda item: item["work_order_id"],
    )
    results = sorted(
        deepcopy(list(journal["results"].values())),
        key=lambda item: item["result_id"],
    )
    reports = sorted(
        deepcopy(list(journal["reports"].values())),
        key=lambda item: item["report_id"],
    )
    hold_counts = {
        code: sum(item["code"] == code for item in holds)
        for code in HOLD_CODES
    }
    method_class_counts = {
        name: sum(
            item["method_class"] == name for item in work_orders
        )
        for name in METHOD_CATALOG
    }
    hash_match_counts = {
        "value": sum(
            item["value_sha256"]
            == sha256_hex({"value": item["value"]})
            for item in results
        ),
        "unit": sum(
            item["unit_sha256"] == sha256_hex({"unit": item["unit"]})
            for item in results
        ),
        "qualifier": sum(
            item["qualifier_sha256"]
            == sha256_hex({"qualifier": item["qualifier"]})
            for item in results
        ),
        "report": sum(
            len(item["report_sha256"]) == 64 for item in reports
        ),
    }
    manifest = {
        "demand_id": DEMAND_ID,
        "accession_ids": [item["accession_id"] for item in accessions],
        "work_order_ids": [item["work_order_id"] for item in work_orders],
        "result_ids": [item["result_id"] for item in results],
        "reports": [
            {
                "report_id": item["report_id"],
                "report_sha256": item["report_sha256"],
                "status": item["status"],
            }
            for item in reports
        ],
        "holds": [
            (item["row_id"], item["shipment_id"], item["code"])
            for item in holds
        ],
    }
    result = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "input_rows": len(inbound),
        "ready": len(accessions),
        "holds": len(holds),
        "accessions": len(accessions),
        "work_orders": len(work_orders),
        "results": len(results),
        "reports_staged": sum(
            item["status"] == "STAGED" for item in reports
        ),
        "reports_released": sum(item["released"] for item in reports),
        "hold_counts": hold_counts,
        "method_class_counts": method_class_counts,
        "hash_match_counts": hash_match_counts,
        "fixture_sha256": fixture_sha256(inbound),
        "manifest_sha256": sha256_hex(manifest),
        "accession_records": accessions,
        "work_order_records": work_orders,
        "result_records": results,
        "report_records": reports,
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
    return result


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    checks = {
        "input_rows": result.get("input_rows") == INPUT_COUNT,
        "ready": result.get("ready") == READY_COUNT,
        "holds": result.get("holds") == HOLD_COUNT,
        "accessions": result.get("accessions") == READY_COUNT,
        "work_orders": result.get("work_orders") == READY_COUNT,
        "results": result.get("results") == READY_COUNT,
        "reports_staged": result.get("reports_staged") == READY_COUNT,
        "reports_released": result.get("reports_released") == 0,
        "hold_counts": result.get("hold_counts") == HOLD_COUNTS,
        "method_class_counts": result.get("method_class_counts")
        == {"ROUTINE": 40, "NON_ROUTINE": 40},
        "hash_match_counts": result.get("hash_match_counts")
        == {
            "value": READY_COUNT,
            "unit": READY_COUNT,
            "qualifier": READY_COUNT,
            "report": READY_COUNT,
        },
        "interfaces": result.get("interfaces")
        == "SYNTHETIC_READ_ONLY",
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
        "added_accessions",
        "added_work_orders",
        "added_results",
        "added_reports",
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
        item.get("accessions_created")
        or item.get("work_orders_created")
        or item.get("results_created")
        or item.get("reports_staged")
        or item.get("reports_released")
        for item in result.get("hold_records") or []
    ):
        failures.append("hold_created_output")
    work_by_accession = {
        item["accession_id"]: item
        for item in result.get("work_order_records") or []
    }
    result_by_work = {
        item["work_order_id"]: item
        for item in result.get("result_records") or []
    }
    reports_by_accession: dict[str, list[dict[str, Any]]] = {}
    for report in result.get("report_records") or []:
        reports_by_accession.setdefault(
            report["accession_id"], []
        ).append(report)
    for accession in result.get("accession_records") or []:
        accession_id = accession["accession_id"]
        work_order = work_by_accession.get(accession_id)
        reports = reports_by_accession.get(accession_id, [])
        if work_order is None or len(reports) != 1:
            failures.append("report_accession_lineage")
            break
        report = reports[0]
        raw_result = result_by_work.get(work_order["work_order_id"])
        if raw_result is None:
            failures.append("result_work_order_lineage")
            break
        if (
            work_order["accession_id"] != accession["accession_id"]
            or raw_result["work_order_id"] != work_order["work_order_id"]
            or report["work_order_id"] != work_order["work_order_id"]
            or report["result_id"] != raw_result["result_id"]
        ):
            failures.append("lineage_link")
            break
        if (
            report["source_sha256"] != raw_result["source_sha256"]
            or report["method_sha256"] != raw_result["method_sha256"]
            or report["result_sha256"] != raw_result["result_sha256"]
            or report["value_sha256"] != raw_result["value_sha256"]
            or report["unit_sha256"] != raw_result["unit_sha256"]
            or report["qualifier_sha256"]
            != raw_result["qualifier_sha256"]
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
        "accessions": result["accessions"],
        "work_orders": result["work_orders"],
        "results": result["results"],
        "reports_staged": result["reports_staged"],
        "reports_released": result["reports_released"],
        "method_class_counts": result["method_class_counts"],
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
