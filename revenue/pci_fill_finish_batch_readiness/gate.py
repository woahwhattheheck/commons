from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

SCHEMA = "pci.fill-finish-batch-readiness/v1"
DECISION_SCHEMA = "pci.fill-finish-batch-readiness-decision/v1"

_REASON_ORDER = (
    "RECIPE_MISMATCH",
    "MATERIAL_UNRELEASED",
    "CALIBRATION_EXPIRED",
    "ENVIRONMENT_HOLD",
    "INSPECTION_LINEAGE_MISMATCH",
    "BOM_MISMATCH",
)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,95}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ReadinessError(ValueError):
    def __init__(self, code: str, detail: str | None = None):
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


def _fail(code: str, detail: str | None = None) -> None:
    raise ReadinessError(code, detail)


def _obj(value: Any, code: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(code)
    return value


def _exact_keys(value: dict[str, Any], keys: tuple[str, ...], code: str) -> None:
    if set(value) != set(keys):
        _fail(code)


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        _fail("INVALID_IDENTIFIER", field)
    return value


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        _fail("INVALID_DIGEST", field)
    return value


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        _fail("BOOLEAN_REQUIRED", field)
    return value


def _timestamp(value: Any, field: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not _TS_RE.fullmatch(value):
        _fail("NONCANONICAL_TIMESTAMP", field)
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        _fail("INVALID_TIMESTAMP", field)
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _fail("NONCANONICAL_TIMESTAMP", field)
    return value, dt


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReadinessError("NONCANONICAL_VALUE", str(exc)) from exc


def sha256(value: Any) -> str:
    payload = value if isinstance(value, (bytes, bytearray)) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_pair(raw: Any, field: str) -> dict[str, str]:
    obj = _obj(raw, f"{field.upper()}_OBJECT_REQUIRED")
    _exact_keys(obj, ("component_id", "version"), f"{field.upper()}_FIELDS")
    return {
        "component_id": _identifier(obj["component_id"], f"{field}.component_id"),
        "version": _identifier(obj["version"], f"{field}.version"),
    }


def normalize_packet(raw: Any) -> dict[str, Any]:
    packet = _obj(copy.deepcopy(raw), "PACKET_REQUIRED")
    _exact_keys(
        packet,
        (
            "schema_version",
            "packet_id",
            "batch_id",
            "planned_slot_at",
            "as_of",
            "recipe",
            "materials",
            "equipment",
            "environment",
            "fill_inspection",
            "bom",
        ),
        "PACKET_FIELDS",
    )
    if packet["schema_version"] != SCHEMA:
        _fail("SCHEMA_MISMATCH")
    packet_id = _identifier(packet["packet_id"], "packet_id")
    batch_id = _identifier(packet["batch_id"], "batch_id")
    planned_slot_at, slot_dt = _timestamp(packet["planned_slot_at"], "planned_slot_at")
    as_of, as_of_dt = _timestamp(packet["as_of"], "as_of")
    if as_of_dt > slot_dt:
        _fail("AS_OF_AFTER_PLANNED_SLOT")

    recipe = _obj(packet["recipe"], "RECIPE_REQUIRED")
    _exact_keys(
        recipe,
        ("recipe_id", "version", "approved", "approved_digest", "scheduled_recipe_id", "scheduled_version"),
        "RECIPE_FIELDS",
    )
    recipe_n = {
        "recipe_id": _identifier(recipe["recipe_id"], "recipe.recipe_id"),
        "version": _identifier(recipe["version"], "recipe.version"),
        "approved": _bool(recipe["approved"], "recipe.approved"),
        "approved_digest": _digest(recipe["approved_digest"], "recipe.approved_digest"),
        "scheduled_recipe_id": _identifier(recipe["scheduled_recipe_id"], "recipe.scheduled_recipe_id"),
        "scheduled_version": _identifier(recipe["scheduled_version"], "recipe.scheduled_version"),
    }

    materials = packet["materials"]
    if not isinstance(materials, list) or not materials:
        _fail("MATERIALS_REQUIRED")
    materials_n: list[dict[str, Any]] = []
    material_ids: set[str] = set()
    for i, raw_item in enumerate(materials):
        item = _obj(raw_item, "MATERIAL_OBJECT_REQUIRED")
        _exact_keys(item, ("lot_id", "component", "released", "release_digest"), "MATERIAL_FIELDS")
        lot_id = _identifier(item["lot_id"], f"materials[{i}].lot_id")
        if lot_id in material_ids:
            _fail("DUPLICATE_MATERIAL_LOT", lot_id)
        material_ids.add(lot_id)
        materials_n.append({
            "lot_id": lot_id,
            "component": _identifier(item["component"], f"materials[{i}].component"),
            "released": _bool(item["released"], f"materials[{i}].released"),
            "release_digest": _digest(item["release_digest"], f"materials[{i}].release_digest"),
        })
    materials_n.sort(key=lambda x: (x["component"], x["lot_id"]))

    equipment = packet["equipment"]
    if not isinstance(equipment, list) or not equipment:
        _fail("EQUIPMENT_REQUIRED")
    equipment_n: list[dict[str, Any]] = []
    equipment_ids: set[str] = set()
    for i, raw_item in enumerate(equipment):
        item = _obj(raw_item, "EQUIPMENT_OBJECT_REQUIRED")
        _exact_keys(item, ("equipment_id", "calibration_valid_until", "calibration_digest"), "EQUIPMENT_FIELDS")
        equipment_id = _identifier(item["equipment_id"], f"equipment[{i}].equipment_id")
        if equipment_id in equipment_ids:
            _fail("DUPLICATE_EQUIPMENT", equipment_id)
        equipment_ids.add(equipment_id)
        valid_until, valid_until_dt = _timestamp(item["calibration_valid_until"], f"equipment[{i}].calibration_valid_until")
        equipment_n.append({
            "equipment_id": equipment_id,
            "calibration_valid_until": valid_until,
            "calibration_valid_until_epoch": int(valid_until_dt.timestamp()),
            "calibration_digest": _digest(item["calibration_digest"], f"equipment[{i}].calibration_digest"),
        })
    equipment_n.sort(key=lambda x: x["equipment_id"])

    environment = _obj(packet["environment"], "ENVIRONMENT_REQUIRED")
    _exact_keys(environment, ("isolator_state", "em_state", "captured_at", "evidence_digest"), "ENVIRONMENT_FIELDS")
    captured_at, captured_dt = _timestamp(environment["captured_at"], "environment.captured_at")
    if captured_dt > as_of_dt:
        _fail("EVIDENCE_AFTER_AS_OF", "environment.captured_at")
    isolator_state = _identifier(environment["isolator_state"], "environment.isolator_state")
    em_state = _identifier(environment["em_state"], "environment.em_state")
    environment_n = {
        "isolator_state": isolator_state,
        "em_state": em_state,
        "captured_at": captured_at,
        "evidence_digest": _digest(environment["evidence_digest"], "environment.evidence_digest"),
    }

    inspection = _obj(packet["fill_inspection"], "FILL_INSPECTION_REQUIRED")
    _exact_keys(
        inspection,
        ("fill_weight_batch_id", "inspection_batch_id", "recipe_digest", "fill_weight_digest", "inspection_digest"),
        "FILL_INSPECTION_FIELDS",
    )
    inspection_n = {
        "fill_weight_batch_id": _identifier(inspection["fill_weight_batch_id"], "fill_inspection.fill_weight_batch_id"),
        "inspection_batch_id": _identifier(inspection["inspection_batch_id"], "fill_inspection.inspection_batch_id"),
        "recipe_digest": _digest(inspection["recipe_digest"], "fill_inspection.recipe_digest"),
        "fill_weight_digest": _digest(inspection["fill_weight_digest"], "fill_inspection.fill_weight_digest"),
        "inspection_digest": _digest(inspection["inspection_digest"], "fill_inspection.inspection_digest"),
    }

    bom = _obj(packet["bom"], "BOM_REQUIRED")
    _exact_keys(bom, ("required", "staged", "evidence_digest"), "BOM_FIELDS")
    required_raw, staged_raw = bom["required"], bom["staged"]
    if not isinstance(required_raw, list) or not required_raw or not isinstance(staged_raw, list) or not staged_raw:
        _fail("BOM_COMPONENTS_REQUIRED")
    required_n = [_normalize_pair(v, f"bom.required[{i}]") for i, v in enumerate(required_raw)]
    staged_n = [_normalize_pair(v, f"bom.staged[{i}]") for i, v in enumerate(staged_raw)]
    for label, values in (("required", required_n), ("staged", staged_n)):
        keys = [(v["component_id"], v["version"]) for v in values]
        if len(set(keys)) != len(keys):
            _fail("DUPLICATE_BOM_COMPONENT", label)
        values.sort(key=lambda x: (x["component_id"], x["version"]))
    bom_n = {
        "required": required_n,
        "staged": staged_n,
        "evidence_digest": _digest(bom["evidence_digest"], "bom.evidence_digest"),
    }

    # Drop derived epoch fields from the durable normalized source.
    normalized_equipment = [
        {k: v for k, v in item.items() if k != "calibration_valid_until_epoch"}
        for item in equipment_n
    ]
    return {
        "schema_version": SCHEMA,
        "packet_id": packet_id,
        "batch_id": batch_id,
        "planned_slot_at": planned_slot_at,
        "as_of": as_of,
        "recipe": recipe_n,
        "materials": materials_n,
        "equipment": normalized_equipment,
        "environment": environment_n,
        "fill_inspection": inspection_n,
        "bom": bom_n,
    }


def evaluate(raw_packet: Any) -> dict[str, Any]:
    packet = normalize_packet(raw_packet)
    slot_dt = _timestamp(packet["planned_slot_at"], "planned_slot_at")[1]
    reasons: list[str] = []

    recipe = packet["recipe"]
    if (
        not recipe["approved"]
        or recipe["scheduled_recipe_id"] != recipe["recipe_id"]
        or recipe["scheduled_version"] != recipe["version"]
    ):
        reasons.append("RECIPE_MISMATCH")

    if any(not item["released"] for item in packet["materials"]):
        reasons.append("MATERIAL_UNRELEASED")

    for item in packet["equipment"]:
        if _timestamp(item["calibration_valid_until"], "calibration_valid_until")[1] < slot_dt:
            reasons.append("CALIBRATION_EXPIRED")
            break

    environment = packet["environment"]
    if environment["isolator_state"] != "READY" or environment["em_state"] != "PASS":
        reasons.append("ENVIRONMENT_HOLD")

    inspection = packet["fill_inspection"]
    if (
        inspection["fill_weight_batch_id"] != packet["batch_id"]
        or inspection["inspection_batch_id"] != packet["batch_id"]
        or inspection["recipe_digest"] != recipe["approved_digest"]
    ):
        reasons.append("INSPECTION_LINEAGE_MISMATCH")

    required = [(x["component_id"], x["version"]) for x in packet["bom"]["required"]]
    staged = [(x["component_id"], x["version"]) for x in packet["bom"]["staged"]]
    if required != staged:
        reasons.append("BOM_MISMATCH")

    reasons = [reason for reason in _REASON_ORDER if reason in reasons]
    evidence_digests = sorted(
        [recipe["approved_digest"]]
        + [m["release_digest"] for m in packet["materials"]]
        + [e["calibration_digest"] for e in packet["equipment"]]
        + [environment["evidence_digest"], inspection["fill_weight_digest"], inspection["inspection_digest"], packet["bom"]["evidence_digest"]]
    )
    source_digest = sha256(packet)
    core = {
        "schema_version": DECISION_SCHEMA,
        "packet_id": packet["packet_id"],
        "batch_id": packet["batch_id"],
        "as_of": packet["as_of"],
        "planned_slot_at": packet["planned_slot_at"],
        "status": "READY" if not reasons else "HOLD",
        "hold_reasons": reasons,
        "source_digest": source_digest,
        "evidence_digests": evidence_digests,
        "authority": {
            "batch_release": False,
            "qa_qp_disposition": False,
            "recipe_authoring": False,
            "equipment_mutation": False,
            "environment_mutation": False,
            "label_device_release": False,
            "provider_mutation": False,
        },
    }
    return {**core, "receipt_digest": sha256(core)}


def verify_decision(raw_packet: Any, raw_decision: Any, *, verify_at: str, max_age_minutes: int = 24 * 60) -> dict[str, Any]:
    if type(max_age_minutes) is not int or isinstance(max_age_minutes, bool) or max_age_minutes < 1:
        _fail("INVALID_MAX_AGE")
    decision = _obj(copy.deepcopy(raw_decision), "DECISION_REQUIRED")
    expected = evaluate(raw_packet)
    if canonical_json(decision) != canonical_json(expected):
        _fail("DECISION_MISMATCH")
    verify_at_s, verify_dt = _timestamp(verify_at, "verify_at")
    as_of_dt = _timestamp(expected["as_of"], "decision.as_of")[1]
    if verify_dt < as_of_dt:
        _fail("VERIFY_BEFORE_AS_OF")
    age_minutes = int((verify_dt - as_of_dt).total_seconds() // 60)
    if age_minutes > max_age_minutes:
        _fail("DECISION_STALE")
    return {
        "valid": True,
        "fresh": True,
        "verify_at": verify_at_s,
        "age_minutes": age_minutes,
        "receipt_digest": expected["receipt_digest"],
        "status": expected["status"],
    }
