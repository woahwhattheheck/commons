from __future__ import annotations

from typing import Any

from .codec import GateInputError, _dict, _hex64, _keys, _str

HOLD_SPEC = "SPEC_REVISION_MISMATCH"
HOLD_REGION = "REGION_USE_CLAIM_MISMATCH"
HOLD_LEGACY = "LEGACY_MAPPING_BREAK"
HOLD_STABILITY = "PILOT_STABILITY_INCOMPLETE"
HOLD_OWNER = "OWNER_VERSION_UNBOUND"


def parse_record(raw: Any) -> dict[str, Any]:
    obj = _dict(raw, "record")
    _keys(
        obj,
        {
            "schema",
            "record_id",
            "code",
            "ingredient_id",
            "spec_revision",
            "approved_spec_revision",
            "region",
            "approved_region",
            "use_level",
            "approved_use_level",
            "claim_ref",
            "approved_claim_ref",
            "allergen_label_hash",
            "legacy_code",
            "legacy_target_code",
            "stability_result",
            "stability_required",
            "commercial_owner",
            "science_owner",
            "owner_version",
            "bound_owner_version",
        },
        "record",
    )
    if obj["schema"] != "tate-lyle-cp-kelco-solution-pack/v1":
        raise GateInputError("unsupported record schema")
    return {
        "record_id": _str(obj["record_id"], "record.record_id"),
        "code": _str(obj["code"], "record.code"),
        "ingredient_id": _str(obj["ingredient_id"], "record.ingredient_id"),
        "spec_revision": _str(obj["spec_revision"], "record.spec_revision"),
        "approved_spec_revision": _str(obj["approved_spec_revision"], "record.approved_spec_revision"),
        "region": _str(obj["region"], "record.region"),
        "approved_region": _str(obj["approved_region"], "record.approved_region"),
        "use_level": _str(obj["use_level"], "record.use_level"),
        "approved_use_level": _str(obj["approved_use_level"], "record.approved_use_level"),
        "claim_ref": _str(obj["claim_ref"], "record.claim_ref"),
        "approved_claim_ref": _str(obj["approved_claim_ref"], "record.approved_claim_ref"),
        "allergen_label_hash": _hex64(obj["allergen_label_hash"], "record.allergen_label_hash"),
        "legacy_code": _str(obj["legacy_code"], "record.legacy_code"),
        "legacy_target_code": _str(obj["legacy_target_code"], "record.legacy_target_code"),
        "stability_result": _str(obj["stability_result"], "record.stability_result"),
        "stability_required": _str(obj["stability_required"], "record.stability_required"),
        "commercial_owner": _str(obj["commercial_owner"], "record.commercial_owner"),
        "science_owner": _str(obj["science_owner"], "record.science_owner"),
        "owner_version": _str(obj["owner_version"], "record.owner_version"),
        "bound_owner_version": _str(obj["bound_owner_version"], "record.bound_owner_version"),
    }


def classify(record: dict[str, Any]) -> tuple[str, list[str]]:
    holds: list[str] = []
    if record["spec_revision"] != record["approved_spec_revision"]:
        holds.append(HOLD_SPEC)
    if (
        record["region"] != record["approved_region"]
        or record["use_level"] != record["approved_use_level"]
        or record["claim_ref"] != record["approved_claim_ref"]
    ):
        holds.append(HOLD_REGION)
    if record["legacy_target_code"] != record["code"]:
        holds.append(HOLD_LEGACY)
    if record["stability_result"] != record["stability_required"]:
        holds.append(HOLD_STABILITY)
    if record["owner_version"] != record["bound_owner_version"]:
        holds.append(HOLD_OWNER)
    status = "HOLD" if holds else "PASS"
    return status, holds
