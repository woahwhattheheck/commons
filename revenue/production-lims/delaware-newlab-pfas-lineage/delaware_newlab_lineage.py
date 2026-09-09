"""Synthetic, read-only Delaware new-lab PFAS/microbiology lineage LIMS.

This module is a deterministic shadow over frozen synthetic requests. It has no
production adapter, no regulatory/public-health decision path, and no automatic
report release.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEMAND_ID = "delaware-newlab-pfas-lineage-lims-01"
MANIFEST_PREFIX = "DELAWARE-NEWLAB-SYNTHETIC-MANIFEST-V1\n"
HOLD_CODES = (
    "MISSING_MATRIX_SDS_CUSTODY",
    "DUPLICATE_CONTAINER",
    "METHOD_MATRIX_MISMATCH",
    "CALIBRATION_QC_FAIL",
    "LEGACY_NEW_FACILITY_ID_COLLISION",
)
METHOD_SPECS = (
    ("PFAS", "WATER", "EPA-1633", "R1", "ng/L"),
    ("MICROBIOLOGY", "WATER", "SM-9223B", "R2", "MPN/100mL"),
    ("MOLECULAR", "WATER", "PCR-ENTERO", "R1", "copies/mL"),
)


class IntegrityError(ValueError):
    """Frozen fixture or manifest content violated the integrity contract."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record_hash(record: dict[str, Any]) -> str:
    return _sha256_text(_canonical(record))


def _manifest_envelope(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "demand_id": manifest["demand_id"],
        "fixture_version": manifest["fixture_version"],
        "dataset_sha256": manifest["dataset_sha256"],
        "expanded_records_sha256": manifest["expanded_records_sha256"],
        "record_count": manifest["record_count"],
        "expected_ready": manifest["expected_ready"],
        "expected_hold": manifest["expected_hold"],
        "expected_hold_codes": manifest["expected_hold_codes"],
        "allowed_methods": manifest["allowed_methods"],
    }


def verify_manifest_signature(manifest: dict[str, Any]) -> None:
    if manifest.get("signature_alg") != "sha256-content-envelope-v1":
        raise IntegrityError("unsupported manifest signature algorithm")
    expected = _sha256_text(MANIFEST_PREFIX + _canonical(_manifest_envelope(manifest)))
    if manifest.get("signature") != expected:
        raise IntegrityError("manifest content-envelope signature mismatch")
