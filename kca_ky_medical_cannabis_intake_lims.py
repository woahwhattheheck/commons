#!/usr/bin/env python3
"""Synthetic KCA Kentucky Medical Cannabis Intake LIMS.

Demand: kca-ky-medical-cannabis-intake-lims-01
Buyer pairing: KCA Laboratories / Richard Sams (matched prospect: Jonathan Thompson)

This fail-closed intake reconciler verifies:
  registration/license <-> portal order <-> printed CoC <-> physical receipt
  <-> panel/matrix <-> internal/partner result provenance reconciliation,
staging a draft CoA only.

Official acceptance:
    python test_kca_ky_medical_cannabis_intake_lims.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

DEMAND_ID = "kca-ky-medical-cannabis-intake-lims-01"
SCHEMA = "commons-kca-ky-medical-cannabis-intake-lims/v1"
BUYER = "KCA Laboratories / Richard Sams"
MATCHED_PROSPECT = "Jonathan Thompson"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
OFFICIAL_BINARY = "python kca_ky_medical_cannabis_intake_lims.py"
OFFICIAL_TEST = "python test_kca_ky_medical_cannabis_intake_lims.py"

INPUT_COUNT = 100
READY_COUNT = 75
INVALID_OR_MISSING_LICENSE_COUNT = 10
COC_PHYSICAL_MISMATCH_COUNT = 5
DUPLICATE_ID_COUNT = 5
PARTNER_PROVENANCE_GAP_COUNT = 5
HOLD_COUNT = (
    INVALID_OR_MISSING_LICENSE_COUNT
    + COC_PHYSICAL_MISMATCH_COUNT
    + DUPLICATE_ID_COUNT
    + PARTNER_PROVENANCE_GAP_COUNT
)

HOLD_CODES = (
    "HOLD_INVALID_OR_MISSING_LICENSE",
    "HOLD_COC_PHYSICAL_MISMATCH",
    "HOLD_DUPLICATE_ID",
    "HOLD_PARTNER_PROVENANCE_GAP",
)
HOLD_COUNTS = {
    "HOLD_INVALID_OR_MISSING_LICENSE": INVALID_OR_MISSING_LICENSE_COUNT,
    "HOLD_COC_PHYSICAL_MISMATCH": COC_PHYSICAL_MISMATCH_COUNT,
    "HOLD_DUPLICATE_ID": DUPLICATE_ID_COUNT,
    "HOLD_PARTNER_PROVENANCE_GAP": PARTNER_PROVENANCE_GAP_COUNT,
}

# Kentucky medical cannabis testing panels and matrices
MATRIX_CATALOG: dict[str, dict[str, Any]] = {
    "FLOWER": {
        "matrix_code": "FLOWER",
        "description": "Dried Medical Cannabis Flower",
        "min_weight_g": 5.0,
        "default_panel": "FULL_COMPLIANCE",
    },
    "CONCENTRATE": {
        "matrix_code": "CONCENTRATE",
        "description": "Cannabis Extract / Concentrate",
        "min_weight_g": 2.0,
        "default_panel": "FULL_COMPLIANCE",
    },
    "EDIBLE": {
        "matrix_code": "EDIBLE",
        "description": "Infused Edible Matrix",
        "min_weight_g": 10.0,
        "default_panel": "POTENCY_HOMOGENEITY",
    },
}

PANEL_CATALOG: dict[str, dict[str, Any]] = {
    "FULL_COMPLIANCE": {
        "panel_code": "FULL_COMPLIANCE",
        "tests": [
            {
                "test_code": "POTENCY",
                "method": "KCA-HPLC-UV-CANNABINOIDS",
                "version": "2026.1",
                "unit": "% w/w",
                "lab_role": "INTERNAL",
                "lab_id": "KCA-MAIN-LAB",
            },
            {
                "test_code": "PESTICIDES",
                "method": "KCA-LCMSMS-PEST-MYCO",
                "version": "2026.1",
                "unit": "ug/g",
                "lab_role": "INTERNAL",
                "lab_id": "KCA-MAIN-LAB",
            },
            {
                "test_code": "HEAVY_METALS",
                "method": "KCA-ICPMS-METALS",
                "version": "2026.1",
                "unit": "ug/g",
                "lab_role": "PARTNER",
                "lab_id": "SYN-PARTNER-TRACE-LAB",
            },
        ],
    },
    "POTENCY_HOMOGENEITY": {
        "panel_code": "POTENCY_HOMOGENEITY",
        "tests": [
            {
                "test_code": "POTENCY",
                "method": "KCA-HPLC-UV-CANNABINOIDS",
                "version": "2026.1",
                "unit": "% w/w",
                "lab_role": "INTERNAL",
                "lab_id": "KCA-MAIN-LAB",
            },
            {
                "test_code": "HOMOGENEITY",
                "method": "KCA-HPLC-HOMOGENEITY-REL",
                "version": "2026.1",
                "unit": "% RSD",
                "lab_role": "PARTNER",
                "lab_id": "SYN-PARTNER-ANALYTICAL-LAB",
            },
        ],
    },
}

REVIEWER_DIRECTORY = {
    "SYN-HUMAN-KCA-REVIEWER-01": {
        "display_name": "Dr. Richard Sams (Synthetic Principal Reviewer)",
        "permissions": ("RELEASE_DRAFT_COA", "SIGN_COMPLIANCE_COA"),
        "human": True,
    },
    "SYN-HUMAN-KCA-REVIEWER-02": {
        "display_name": "Jonathan Thompson (Synthetic QA Officer)",
        "permissions": ("RELEASE_DRAFT_COA",),
        "human": True,
    },
}

AUTOMATION_IDENTITIES = frozenset(
    {"", "SYSTEM", "AUTO", "AUTOMATION", "BOT", "MACHINE", "METRC_SYNC"}
)

UNIQUE_ID_FIELDS = (
    "order_id",
    "portal_order_id",
    "coc_form_id",
    "physical_receipt_id",
    "sample_id",
    "package_tag",
    "manifest_id",
)


def _receipt_goldens() -> dict[str, str]:
    path = (
        Path(__file__).resolve().parent
        / "revenue"
        / "kca_ky_medical_cannabis_intake_lims"
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


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputError(f"{field} must be a list")
    return value


def _license_link(license_number: str) -> str:
    return f"synthetic://ky-omc-registry/license/{license_number}"


def _order_link(portal_order_id: str) -> str:
    return f"synthetic://kca-portal/order/{portal_order_id}"


def _coc_link(coc_form_id: str) -> str:
    return f"synthetic://coc-document/{coc_form_id}"


def _receipt_link(physical_receipt_id: str) -> str:
    return f"synthetic://sample-receiving/receipt/{physical_receipt_id}"


def _accession_id(sample_id: str) -> str:
    return "KCA-ACC-" + sha256_hex(
        {"demand_id": DEMAND_ID, "sample_id": sample_id}
    )[:14]


def _work_order_id(sample_id: str, panel_code: str) -> str:
    return "KCA-WO-" + sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "sample_id": sample_id,
            "panel_code": panel_code,
        }
    )[:14]


def _result_id(sample_id: str, test_code: str, lab_id: str) -> str:
    return "KCA-RES-" + sha256_hex(
        {
            "demand_id": DEMAND_ID,
            "sample_id": sample_id,
            "test_code": test_code,
            "lab_id": lab_id,
        }
    )[:14]


def _coa_id(sample_id: str) -> str:
    return "KCA-COA-DRAFT-" + sha256_hex(
        {"demand_id": DEMAND_ID, "sample_id": sample_id}
    )[:14]


def _provenance_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "lab_id": result["lab_id"],
        "lab_role": result["lab_role"],
        "method": result["method"],
        "method_version": result["method_version"],
        "source_uri": result["source_uri"],
        "source_raw_hash": result["source_raw_hash"],
        "test_code": result["test_code"],
    }


def _calculate_provenance_hash(result: dict[str, Any]) -> str:
    return sha256_hex(_provenance_payload(result))


def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": row["order_id"],
        "portal_order_id": row["portal_order_id"],
        "portal_order_link": row["portal_order_link"],
        "license_number": row["license_number"],
        "license_state": row["license_state"],
        "license_status": row["license_status"],
        "license_link": row["license_link"],
        "producer_name": row["producer_name"],
        "coc_form_id": row["coc_form_id"],
        "coc_order_id": row["coc_order_id"],
        "coc_link": row["coc_link"],
        "physical_receipt_id": row["physical_receipt_id"],
        "physical_coc_id": row["physical_coc_id"],
        "physical_receipt_link": row["physical_receipt_link"],
        "package_tag": row["package_tag"],
        "coc_package_tag": row["coc_package_tag"],
        "physical_package_tag": row["physical_package_tag"],
        "manifest_id": row["manifest_id"],
        "sample_id": row["sample_id"],
        "coc_sample_id": row["coc_sample_id"],
        "physical_sample_id": row["physical_sample_id"],
        "matrix": row["matrix"],
        "panel": row["panel"],
        "received_weight_g": row["received_weight_g"],
        "synthetic": row["synthetic"],
        "deidentified": row["deidentified"],
    }


def _results_payload(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "test_code": res["test_code"],
            "method": res["method"],
            "method_version": res["method_version"],
            "lab_role": res["lab_role"],
            "lab_id": res["lab_id"],
            "source_uri": res["source_uri"],
            "source_raw_hash": res["source_raw_hash"],
            "provenance_hash": res["provenance_hash"],
            "value": res["value"],
            "unit": res["unit"],
            "status": res["status"],
        }
        for res in row.get("results", [])
    ]


def _derived_hashes(row: dict[str, Any]) -> dict[str, Any]:
    source_hash = sha256_hex(_source_payload(row))
    results_hash = sha256_hex(_results_payload(row))
    
    coa_core = {
        "coa_id": _coa_id(row["sample_id"]),
        "accession_id": _accession_id(row["sample_id"]),
        "work_order_id": _work_order_id(row["sample_id"], row["panel"]),
        "order_id": row["order_id"],
        "sample_id": row["sample_id"],
        "package_tag": row["package_tag"],
        "license_number": row["license_number"],
        "matrix": row["matrix"],
        "panel": row["panel"],
        "source_sha256": source_hash,
        "results_sha256": results_hash,
        "stage": "DRAFT",
        "released": False,
    }
    
    return {
        "source_sha256": source_hash,
        "results_sha256": results_hash,
        "coa_sha256": sha256_hex(coa_core),
    }


def _stamp_goldens(row: dict[str, Any]) -> dict[str, Any]:
    stamped = deepcopy(row)
    stamped["golden_hashes"] = _derived_hashes(stamped)
    return stamped


def _generate_synthetic_results(
    sample_id: str, panel_code: str, token: str
) -> list[dict[str, Any]]:
    panel_def = PANEL_CATALOG[panel_code]
    results = []
    for test in panel_def["tests"]:
        source_uri = (
            f"synthetic://kca-instrument-run/{test['test_code'].lower()}-{token}.raw"
            if test["lab_role"] == "INTERNAL"
            else f"synthetic://partner-lab-transfer/{test['lab_id'].lower()}/{test['test_code'].lower()}-{token}.json"
        )
        source_raw_hash = sha256_hex(
            {
                "sample_id": sample_id,
                "test_code": test["test_code"],
                "source_uri": source_uri,
                "run_token": token,
            }
        )
        
        # Determine realistic synthetic values
        if test["test_code"] == "POTENCY":
            val: int | float = 22.45
        elif test["test_code"] == "PESTICIDES":
            val = 0.00
        elif test["test_code"] == "HEAVY_METALS":
            val = 0.02
        elif test["test_code"] == "HOMOGENEITY":
            val = 3.20
        else:
            val = 1.00

        res_dict = {
            "test_code": test["test_code"],
            "method": test["method"],
            "method_version": test["version"],
            "lab_role": test["lab_role"],
            "lab_id": test["lab_id"],
            "source_uri": source_uri,
            "source_raw_hash": source_raw_hash,
            "value": val,
            "unit": test["unit"],
            "status": "COMPLETED",
        }
        res_dict["provenance_hash"] = _calculate_provenance_hash(res_dict)
        results.append(res_dict)
    return results


def _base_order(index: int) -> dict[str, Any]:
    token = f"{index:03d}"
    matrix = "FLOWER" if index % 3 == 0 else ("CONCENTRATE" if index % 3 == 1 else "EDIBLE")
    panel = "FULL_COMPLIANCE" if matrix in ("FLOWER", "CONCENTRATE") else "POTENCY_HOMOGENEITY"
    weight = 10.0 if matrix == "EDIBLE" else (5.5 if matrix == "FLOWER" else 2.5)

    order_id = f"KCA-ORD-{token}"
    portal_order_id = f"PORTAL-ORD-{token}"
    license_num = f"KY-MED-LIC-{token}"
    coc_form_id = f"COC-FORM-{token}"
    physical_receipt_id = f"RECPT-PHYS-{token}"
    package_tag = f"1A400010000000000000{token}"
    sample_id = f"KCA-SMP-{token}"
    manifest_id = f"KY-MAN-{token}"

    results = _generate_synthetic_results(sample_id, panel, token)

    row: dict[str, Any] = {
        "row_id": f"KCA-ROW-{token}",
        "order_id": order_id,
        "portal_order_id": portal_order_id,
        "portal_order_link": _order_link(portal_order_id),
        "license_number": license_num,
        "license_state": "KY",
        "license_status": "ACTIVE_VALID",
        "license_link": _license_link(license_num),
        "producer_name": f"Synthetic KY Cultivator {token}",
        "coc_form_id": coc_form_id,
        "coc_order_id": portal_order_id,
        "coc_link": _coc_link(coc_form_id),
        "physical_receipt_id": physical_receipt_id,
        "physical_coc_id": coc_form_id,
        "physical_receipt_link": _receipt_link(physical_receipt_id),
        "package_tag": package_tag,
        "coc_package_tag": package_tag,
        "physical_package_tag": package_tag,
        "manifest_id": manifest_id,
        "sample_id": sample_id,
        "coc_sample_id": sample_id,
        "physical_sample_id": sample_id,
        "matrix": matrix,
        "panel": panel,
        "received_weight_g": weight,
        "results": results,
        "synthetic": True,
        "deidentified": True,
        "expected_state": "READY",
        "expected_hold": None,
    }
    return _stamp_goldens(row)


def _invalid_license_order(index: int) -> dict[str, Any]:
    row = _base_order(index)
    if index % 2 == 0:
        row["license_status"] = "REVOKED_OR_EXPIRED"
    else:
        row["license_number"] = ""
        row["license_link"] = ""
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_INVALID_OR_MISSING_LICENSE"
    return _stamp_goldens(row)


def _coc_physical_mismatch_order(index: int) -> dict[str, Any]:
    row = _base_order(index)
    token = f"{index:03d}"
    if index % 2 == 0:
        row["physical_sample_id"] = f"KCA-SMP-MISMATCH-{token}"
    else:
        row["physical_package_tag"] = f"1A400010000000000000-BAD-{token}"
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_COC_PHYSICAL_MISMATCH"
    return _stamp_goldens(row)


def _duplicate_id_order(slot: int) -> dict[str, Any]:
    # Reuse an existing base order's identifiers (slot 1 to 5)
    row = _base_order(slot + 1)
    row["row_id"] = f"KCA-ROW-{91 + slot:03d}"
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_DUPLICATE_ID"
    return _stamp_goldens(row)


def _partner_provenance_gap_order(index: int) -> dict[str, Any]:
    row = _base_order(index)
    # Tamper with partner result provenance (missing lab_id or broken hash)
    for res in row["results"]:
        if res["lab_role"] == "PARTNER":
            if index % 2 == 0:
                res["source_raw_hash"] = ""
                res["provenance_hash"] = ""
            else:
                res["provenance_hash"] = "tampered_fake_provenance_hash_00000000000000000000000000000000"
    row["expected_state"] = "HOLD"
    row["expected_hold"] = "HOLD_PARTNER_PROVENANCE_GAP"
    return _stamp_goldens(row)


def build_acceptance_fixture() -> list[dict[str, Any]]:
    """Build the frozen 100-order fixture: 75 READY / 25 HOLD."""
    # 75 valid KY-licensed orders (indices 1 to 75)
    rows = [_base_order(index) for index in range(1, 76)]
    # 10 invalid/missing license (indices 76 to 85)
    rows.extend(_invalid_license_order(index) for index in range(76, 86))
    # 5 CoC/physical-ID mismatches (indices 86 to 90)
    rows.extend(_coc_physical_mismatch_order(index) for index in range(86, 91))
    # 5 duplicate order/sample IDs (slots 0 to 4 -> rows 91 to 95)
    rows.extend(_duplicate_id_order(slot) for slot in range(5))
    # 5 partner-result provenance gaps (indices 96 to 100)
    rows.extend(_partner_provenance_gap_order(index) for index in range(96, 101))

    if len(rows) != INPUT_COUNT:
        raise RuntimeError(f"Fixture cardinality drift: expected {INPUT_COUNT}, got {len(rows)}")
    return rows


def fixture_sha256(rows: list[dict[str, Any]] | None = None) -> str:
    return sha256_hex(
        rows if rows is not None else build_acceptance_fixture()
    )


class SyntheticReadOnlyOrderAdapter:
    """Read-only in-memory fixture source; no live Metrc/state or write capability."""

    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = deepcopy(rows)
        self.mode = "SYNTHETIC_READ_ONLY"
        self.live = False
        self.writes = 0

    def list_orders(self) -> list[dict[str, Any]]:
        return deepcopy(self._rows)

    def write(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("synthetic order adapter is read-only; state and Metrc writes prohibited")


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "matched_prospect": MATCHED_PROSPECT,
        "processed_rows": {},
        "identifier_index": {},
        "accessions": {},
        "work_orders": {},
        "results": {},
        "draft_coas": {},
        "holds": [],
        "events": [],
        "interface_live": False,
        "interfaces": "SYNTHETIC_READ_ONLY",
        "production_writes": 0,
        "state_writes": 0,
        "metrc_writes": 0,
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


def normalize_order(row: dict[str, Any]) -> dict[str, Any]:
    source = _mapping(row, "row")
    golden = _mapping(source.get("golden_hashes"), "golden_hashes")
    raw_results = _list(source.get("results"), "results")

    norm_results = []
    for res_raw in raw_results:
        res = _mapping(res_raw, "result_item")
        norm_results.append(
            {
                "test_code": _text(res.get("test_code"), "test_code", allow_empty=False),
                "method": _text(res.get("method"), "method", allow_empty=False),
                "method_version": _text(res.get("method_version"), "method_version", allow_empty=False),
                "lab_role": _text(res.get("lab_role"), "lab_role", allow_empty=False).upper(),
                "lab_id": _text(res.get("lab_id"), "lab_id", allow_empty=False),
                "source_uri": _text(res.get("source_uri"), "source_uri", allow_empty=False),
                "source_raw_hash": _text(res.get("source_raw_hash"), "source_raw_hash"),
                "provenance_hash": _text(res.get("provenance_hash"), "provenance_hash"),
                "value": _number(res.get("value"), "value"),
                "unit": _text(res.get("unit"), "unit", allow_empty=False),
                "status": _text(res.get("status"), "status", allow_empty=False).upper(),
            }
        )

    norm = {
        "row_id": _text(source.get("row_id"), "row_id", allow_empty=False),
        "order_id": _text(source.get("order_id"), "order_id", allow_empty=False),
        "portal_order_id": _text(source.get("portal_order_id"), "portal_order_id"),
        "portal_order_link": _text(source.get("portal_order_link"), "portal_order_link"),
        "license_number": _text(source.get("license_number"), "license_number"),
        "license_state": _text(source.get("license_state"), "license_state").upper(),
        "license_status": _text(source.get("license_status"), "license_status").upper(),
        "license_link": _text(source.get("license_link"), "license_link"),
        "producer_name": _text(source.get("producer_name"), "producer_name"),
        "coc_form_id": _text(source.get("coc_form_id"), "coc_form_id"),
        "coc_order_id": _text(source.get("coc_order_id"), "coc_order_id"),
        "coc_link": _text(source.get("coc_link"), "coc_link"),
        "physical_receipt_id": _text(source.get("physical_receipt_id"), "physical_receipt_id"),
        "physical_coc_id": _text(source.get("physical_coc_id"), "physical_coc_id"),
        "physical_receipt_link": _text(source.get("physical_receipt_link"), "physical_receipt_link"),
        "package_tag": _text(source.get("package_tag"), "package_tag"),
        "coc_package_tag": _text(source.get("coc_package_tag"), "coc_package_tag"),
        "physical_package_tag": _text(source.get("physical_package_tag"), "physical_package_tag"),
        "manifest_id": _text(source.get("manifest_id"), "manifest_id"),
        "sample_id": _text(source.get("sample_id"), "sample_id"),
        "coc_sample_id": _text(source.get("coc_sample_id"), "coc_sample_id"),
        "physical_sample_id": _text(source.get("physical_sample_id"), "physical_sample_id"),
        "matrix": _text(source.get("matrix"), "matrix").upper(),
        "panel": _text(source.get("panel"), "panel").upper(),
        "received_weight_g": _number(source.get("received_weight_g"), "received_weight_g"),
        "results": norm_results,
        "synthetic": _bool(source.get("synthetic"), "synthetic"),
        "deidentified": _bool(source.get("deidentified"), "deidentified"),
        "golden_hashes": {
            key: _text(golden.get(key), f"golden_hashes.{key}")
            for key in ("source_sha256", "results_sha256", "coa_sha256")
        },
    }
    return norm


def classify_order(
    journal: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    # Fail closed on non-synthetic / non-deidentified
    if not row["synthetic"] or not row["deidentified"]:
        return {"ok": False, "code": "HOLD_TRUTH_BOUNDARY"}

    # 1. License Check: valid KY medical cannabis license
    if (
        not row["license_number"]
        or row["license_state"] != "KY"
        or row["license_status"] != "ACTIVE_VALID"
        or row["license_link"] != _license_link(row["license_number"])
    ):
        return {"ok": False, "code": "HOLD_INVALID_OR_MISSING_LICENSE"}

    # 2. Duplicate ID Check across processed journal
    identifiers = [row[field] for field in UNIQUE_ID_FIELDS]
    if (
        any(not value for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
        or any(value in journal["identifier_index"] for value in identifiers)
    ):
        return {"ok": False, "code": "HOLD_DUPLICATE_ID"}

    # 3. CoC <-> Physical Receipt & Manifest Mismatch Check
    if (
        row["coc_order_id"] != row["portal_order_id"]
        or row["physical_coc_id"] != row["coc_form_id"]
        or row["coc_package_tag"] != row["package_tag"]
        or row["physical_package_tag"] != row["package_tag"]
        or row["coc_sample_id"] != row["sample_id"]
        or row["physical_sample_id"] != row["sample_id"]
    ):
        return {"ok": False, "code": "HOLD_COC_PHYSICAL_MISMATCH"}

    # 4. Matrix & Panel Validation
    matrix_spec = MATRIX_CATALOG.get(row["matrix"])
    if not matrix_spec or row["received_weight_g"] < matrix_spec["min_weight_g"]:
        return {"ok": False, "code": "HOLD_MATRIX_SPEC_MISMATCH"}

    panel_spec = PANEL_CATALOG.get(row["panel"])
    if not panel_spec:
        return {"ok": False, "code": "HOLD_PANEL_UNSUPPORTED"}

    # 5. Partner & Internal Result Provenance Check
    for res in row["results"]:
        # Every partner result MUST carry valid lab/method/source hash matching provenance
        if not res["lab_id"] or not res["method"] or not res["source_raw_hash"]:
            return {"ok": False, "code": "HOLD_PARTNER_PROVENANCE_GAP"}
        
        expected_prov_hash = _calculate_provenance_hash(res)
        if res["provenance_hash"] != expected_prov_hash:
            return {"ok": False, "code": "HOLD_PARTNER_PROVENANCE_GAP"}

    # 6. Golden Hash Verification
    if row["golden_hashes"] != _derived_hashes(row):
        return {"ok": False, "code": "HOLD_GOLDEN_HASH_MISMATCH"}

    return {"ok": True, "code": None}


def _commit(journal: dict[str, Any], candidate: dict[str, Any]) -> None:
    journal.clear()
    journal.update(candidate)


def ingest_order(
    journal: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    """Ingest one order row atomically; rejection never partially mutates state."""
    try:
        norm = normalize_order(row)
    except (InputError, KeyError, TypeError, ValueError) as exc:
        return {
            "kind": "REJECT",
            "ok": False,
            "code": "REJECT_INVALID_INPUT",
            "row_id": (
                row.get("row_id", "").strip()
                if isinstance(row, dict) and isinstance(row.get("row_id"), str)
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
                "prior_state": prior["state"],
            }
        return {
            "kind": "REPLAY_NOOP",
            "ok": True,
            "code": "REPLAY_NOOP",
            "row_id": row_id,
            "state": prior["state"],
        }

    candidate = deepcopy(journal)
    decision = classify_order(candidate, norm)

    if not decision["ok"]:
        hold_record = {
            "row_id": row_id,
            "order_id": norm["order_id"],
            "sample_id": norm["sample_id"],
            "state": "HOLD",
            "code": decision["code"],
            "accessions_created": 0,
            "work_orders_created": 0,
            "results_created": 0,
            "draft_coas_staged": 0,
            "coas_released": 0,
        }
        candidate["holds"].append(hold_record)
        candidate["processed_rows"][row_id] = {
            "state": "HOLD",
            "code": decision["code"],
            "payload_sha256": payload_sha256,
        }
        _event(
            candidate,
            "ORDER_HELD",
            {
                "row_id": row_id,
                "code": decision["code"],
                "sample_id": norm["sample_id"],
            },
        )
        _commit(journal, candidate)
        return {
            "kind": "HOLD",
            "ok": False,
            "code": decision["code"],
            "row_id": row_id,
        }

    # Order is READY - Stage draft CoA & Accession records
    accession_id = _accession_id(norm["sample_id"])
    work_order_id = _work_order_id(norm["sample_id"], norm["panel"])
    coa_id = _coa_id(norm["sample_id"])

    # Register unique IDs to prevent future duplicate claims
    for field in UNIQUE_ID_FIELDS:
        candidate["identifier_index"][norm[field]] = row_id

    accession_record = {
        "accession_id": accession_id,
        "row_id": row_id,
        "order_id": norm["order_id"],
        "portal_order_id": norm["portal_order_id"],
        "license_number": norm["license_number"],
        "coc_form_id": norm["coc_form_id"],
        "physical_receipt_id": norm["physical_receipt_id"],
        "sample_id": norm["sample_id"],
        "package_tag": norm["package_tag"],
        "manifest_id": norm["manifest_id"],
        "matrix": norm["matrix"],
        "received_weight_g": norm["received_weight_g"],
        "source_sha256": norm["golden_hashes"]["source_sha256"],
        "status": "ACCESSIONED",
    }
    candidate["accessions"][accession_id] = accession_record

    work_order_record = {
        "work_order_id": work_order_id,
        "accession_id": accession_id,
        "sample_id": norm["sample_id"],
        "panel": norm["panel"],
        "status": "IN_PROGRESS",
    }
    candidate["work_orders"][work_order_id] = work_order_record

    result_ids = []
    for res in norm["results"]:
        res_id = _result_id(norm["sample_id"], res["test_code"], res["lab_id"])
        result_record = {
            "result_id": res_id,
            "work_order_id": work_order_id,
            "sample_id": norm["sample_id"],
            "test_code": res["test_code"],
            "method": res["method"],
            "method_version": res["method_version"],
            "lab_role": res["lab_role"],
            "lab_id": res["lab_id"],
            "source_uri": res["source_uri"],
            "source_raw_hash": res["source_raw_hash"],
            "provenance_hash": res["provenance_hash"],
            "value": res["value"],
            "unit": res["unit"],
            "status": res["status"],
        }
        candidate["results"][res_id] = result_record
        result_ids.append(result_ids) if False else result_ids.append(res_id)

    draft_coa_record = {
        "coa_id": coa_id,
        "accession_id": accession_id,
        "work_order_id": work_order_id,
        "sample_id": norm["sample_id"],
        "package_tag": norm["package_tag"],
        "license_number": norm["license_number"],
        "matrix": norm["matrix"],
        "panel": norm["panel"],
        "result_ids": result_ids,
        "source_sha256": norm["golden_hashes"]["source_sha256"],
        "results_sha256": norm["golden_hashes"]["results_sha256"],
        "coa_sha256": norm["golden_hashes"]["coa_sha256"],
        "stage": "DRAFT",
        "released": False,
        "released_by": None,
    }
    candidate["draft_coas"][coa_id] = draft_coa_record

    candidate["processed_rows"][row_id] = {
        "state": "READY",
        "code": None,
        "accession_id": accession_id,
        "work_order_id": work_order_id,
        "coa_id": coa_id,
        "payload_sha256": payload_sha256,
    }

    _event(
        candidate,
        "ORDER_ACCESSIONED_AND_DRAFT_STAGED",
        {
            "row_id": row_id,
            "sample_id": norm["sample_id"],
            "accession_id": accession_id,
            "coa_id": coa_id,
        },
    )
    _commit(journal, candidate)
    return {
        "kind": "READY",
        "ok": True,
        "code": None,
        "row_id": row_id,
        "accession_id": accession_id,
        "work_order_id": work_order_id,
        "coa_id": coa_id,
    }


def release_draft_coa(
    journal: dict[str, Any],
    coa_id: str,
    *,
    reviewer_id: str,
) -> dict[str, Any]:
    """Release a draft CoA only when authorized by a named human reviewer."""
    clean_reviewer = reviewer_id.strip() if isinstance(reviewer_id, str) else ""
    if clean_reviewer.upper() in AUTOMATION_IDENTITIES:
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}

    reviewer = REVIEWER_DIRECTORY.get(clean_reviewer)
    if reviewer is None or not reviewer.get("human"):
        return {"ok": False, "code": "UNAUTHORIZED_REVIEWER"}

    if "RELEASE_DRAFT_COA" not in reviewer.get("permissions", ()):
        return {"ok": False, "code": "INSUFFICIENT_PERMISSIONS"}

    coa = journal["draft_coas"].get(coa_id)
    if coa is None:
        return {"ok": False, "code": "COA_NOT_FOUND"}

    if coa["released"]:
        return {
            "ok": True,
            "code": "ALREADY_RELEASED",
            "coa_id": coa_id,
            "status": "RELEASED",
        }

    candidate = deepcopy(journal)
    target = candidate["draft_coas"][coa_id]
    target["released"] = True
    target["stage"] = "RELEASED"
    target["released_by"] = {
        "reviewer_id": clean_reviewer,
        "display_name": reviewer["display_name"],
    }
    _event(
        candidate,
        "DRAFT_COA_RELEASED",
        {
            "coa_id": coa_id,
            "reviewer_id": clean_reviewer,
            "display_name": reviewer["display_name"],
        },
    )
    _commit(journal, candidate)
    return {
        "ok": True,
        "code": "RELEASED",
        "coa_id": coa_id,
        "status": "RELEASED",
    }


def replay_into(
    journal: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, int]:
    """Replay rows into a journal and verify zero additions."""
    before_accessions = len(journal["accessions"])
    before_work_orders = len(journal["work_orders"])
    before_results = len(journal["results"])
    before_coas = len(journal["draft_coas"])
    before_holds = len(journal["holds"])

    noops = 0
    conflicts = 0
    for row in rows:
        outcome = ingest_order(journal, row)
        if outcome["kind"] == "REPLAY_NOOP":
            noops += 1
        elif outcome["kind"] == "REPLAY_CONFLICT":
            conflicts += 1

    return {
        "added_accessions": len(journal["accessions"]) - before_accessions,
        "added_work_orders": len(journal["work_orders"]) - before_work_orders,
        "added_results": len(journal["results"]) - before_results,
        "added_coas": len(journal["draft_coas"]) - before_coas,
        "added_holds": len(journal["holds"]) - before_holds,
        "replay_noops": noops,
        "replay_conflicts": conflicts,
    }


def run_gate(
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute the full 100-order reconciliation oracle."""
    dataset = rows if rows is not None else build_acceptance_fixture()
    adapter = SyntheticReadOnlyOrderAdapter(dataset)
    journal = empty_journal()

    for item in adapter.list_orders():
        ingest_order(journal, item)

    ready_count = sum(1 for p in journal["processed_rows"].values() if p["state"] == "READY")
    hold_count = sum(1 for p in journal["processed_rows"].values() if p["state"] == "HOLD")

    hold_counts_by_code: dict[str, int] = {code: 0 for code in HOLD_CODES}
    for h in journal["holds"]:
        code = h["code"]
        hold_counts_by_code[code] = hold_counts_by_code.get(code, 0) + 1

    return {
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "matched_prospect": MATCHED_PROSPECT,
        "schema": SCHEMA,
        "truth_gate": TRUTH_GATE,
        "input_rows": len(dataset),
        "ready": ready_count,
        "holds": hold_count,
        "accessions": len(journal["accessions"]),
        "work_orders": len(journal["work_orders"]),
        "results": len(journal["results"]),
        "draft_coas_staged": len(journal["draft_coas"]),
        "coas_released": sum(1 for c in journal["draft_coas"].values() if c["released"]),
        "hold_counts": hold_counts_by_code,
        "hold_records": journal["holds"],
        "accession_records": list(journal["accessions"].values()),
        "work_order_records": list(journal["work_orders"].values()),
        "result_records": list(journal["results"].values()),
        "coa_records": list(journal["draft_coas"].values()),
        "journal_sha256": state_sha256(journal),
    }


def pass_contract(result: dict[str, Any]) -> list[str]:
    """Validate that run_gate output conforms strictly to acceptance criteria."""
    failures: list[str] = []
    if result.get("input_rows") != INPUT_COUNT:
        failures.append(f"Expected input_rows {INPUT_COUNT}, got {result.get('input_rows')}")
    if result.get("ready") != READY_COUNT:
        failures.append(f"Expected ready {READY_COUNT}, got {result.get('ready')}")
    if result.get("holds") != HOLD_COUNT:
        failures.append(f"Expected holds {HOLD_COUNT}, got {result.get('holds')}")
    if result.get("accessions") != READY_COUNT:
        failures.append(f"Expected accessions {READY_COUNT}, got {result.get('accessions')}")
    if result.get("draft_coas_staged") != READY_COUNT:
        failures.append(f"Expected staged draft CoAs {READY_COUNT}, got {result.get('draft_coas_staged')}")
    if result.get("coas_released") != 0:
        failures.append(f"Expected automatic releases 0, got {result.get('coas_released')}")

    actual_hold_counts = result.get("hold_counts", {})
    if actual_hold_counts != HOLD_COUNTS:
        failures.append(f"Hold counts mismatch: expected {HOLD_COUNTS}, got {actual_hold_counts}")

    return failures


def audit_bundle() -> dict[str, Any]:
    rows = build_acceptance_fixture()
    result = run_gate(rows)
    return {
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "matched_prospect": MATCHED_PROSPECT,
        "fixture_sha256": fixture_sha256(rows),
        "manifest_sha256": sha256_hex(result),
        "acceptance": {
            "input_rows": INPUT_COUNT,
            "ready": READY_COUNT,
            "holds": HOLD_COUNT,
            "hold_counts": HOLD_COUNTS,
            "named_human_release_only": True,
            "replay_additions": 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--audit" in args:
        print(json.dumps(audit_bundle(), indent=2, sort_keys=True))
        return 0

    result = run_gate()
    failures = pass_contract(result)
    print(f"[{DEMAND_ID}] 100 synthetic orders -> {result['ready']} READY / {result['holds']} HOLD")
    for code, cnt in result["hold_counts"].items():
        print(f"  - {code}: {cnt}")
    if failures:
        print("CONTRACT VIOLATIONS:", file=sys.stderr)
        for f in failures:
            print(f"  * {f}", file=sys.stderr)
        return 1
    print("PASS: Contract strictly satisfied. Draft CoA staged only. 0 state/Metrc writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
