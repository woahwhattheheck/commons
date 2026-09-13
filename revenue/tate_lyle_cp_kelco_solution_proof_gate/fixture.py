from __future__ import annotations

import hashlib
from typing import Any

from .codec import BATCH_SCHEMA, RECORD_SCHEMA


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _base(i: int) -> dict[str, Any]:
    code = f"TLCK-{i:03d}"
    return {
        "schema": RECORD_SCHEMA,
        "record_id": f"REC-{i:03d}",
        "code": code,
        "ingredient_id": f"ING-{(i % 12) + 1:02d}",
        "spec_revision": "SPEC-7",
        "approved_spec_revision": "SPEC-7",
        "region": "NA",
        "approved_region": "NA",
        "use_level": "0.40",
        "approved_use_level": "0.40",
        "claim_ref": "CLAIM-A",
        "approved_claim_ref": "CLAIM-A",
        "allergen_label_hash": _hash(f"label-{i}"),
        "legacy_code": f"LEG-{i:03d}",
        "legacy_target_code": code,
        "stability_result": "STABLE",
        "stability_required": "STABLE",
        "commercial_owner": "COMM-OWNER-1",
        "science_owner": "SCI-OWNER-1",
        "owner_version": "OV-3",
        "bound_owner_version": "OV-3",
    }


def make_acceptance_batch() -> dict[str, Any]:
    """120 synthetic packs: 90 PASS, 30 HOLD, 75 seeded defects.

    Defect mix on HOLD records REC-091..REC-120:
    - 20 spec (091-110)
    - 15 region/use/claim (091-105)
    - 15 legacy mapping (106-120)
    - 15 stability (096-110)
    - 10 owner/version (111-120)
    """
    records = [_base(i) for i in range(1, 121)]
    for i in range(91, 111):
        records[i - 1]["spec_revision"] = "SPEC-6"
    for i in range(91, 106):
        records[i - 1]["region"] = "EU"
    for i in range(106, 121):
        records[i - 1]["legacy_target_code"] = "UNMAPPED"
    for i in range(96, 111):
        records[i - 1]["stability_result"] = "INCOMPLETE"
    for i in range(111, 121):
        records[i - 1]["owner_version"] = "OV-2"
    return {"schema": BATCH_SCHEMA, "records": records}
