from __future__ import annotations

from typing import Any

from ._common import (
    _ALLOWED_EVENT_KINDS, _assert_public_safe, _evidence_ref, _exact_keys, _fail,
    _identifier, _list, _normalize_id_list, _normalize_string_map, _object,
    _safe_int, _text, _timestamp, canonical_json,
)

def _normalize_policy(raw: Any) -> dict[str, Any]:
    obj = _object(raw, "POLICY_OBJECT_REQUIRED")
    expected = {
        "batchId", "lotId", "productCode", "approvedFormulationRevision", "approvedLineRevision",
        "expectedMaterialLots", "requiredEquipmentIds", "approvedPackagingBomRevision",
        "approvedLabelRevision", "deviceAssemblyRequired", "environmentMaxAgeHours",
        "fillInspectionMaxAgeHours",
    }
    _exact_keys(obj, expected, "POLICY_SHAPE_MISMATCH")
    if not isinstance(obj["deviceAssemblyRequired"], bool):
        _fail("BOOLEAN_REQUIRED", "deviceAssemblyRequired")
    return {
        "batchId": _identifier(obj["batchId"], "policy.batchId"),
        "lotId": _identifier(obj["lotId"], "policy.lotId"),
        "productCode": _identifier(obj["productCode"], "policy.productCode"),
        "approvedFormulationRevision": _identifier(obj["approvedFormulationRevision"], "policy.approvedFormulationRevision"),
        "approvedLineRevision": _identifier(obj["approvedLineRevision"], "policy.approvedLineRevision"),
        "expectedMaterialLots": _normalize_string_map(obj["expectedMaterialLots"], "policy.expectedMaterialLots"),
        "requiredEquipmentIds": _normalize_id_list(obj["requiredEquipmentIds"], "policy.requiredEquipmentIds"),
        "approvedPackagingBomRevision": _identifier(obj["approvedPackagingBomRevision"], "policy.approvedPackagingBomRevision"),
        "approvedLabelRevision": _identifier(obj["approvedLabelRevision"], "policy.approvedLabelRevision"),
        "deviceAssemblyRequired": obj["deviceAssemblyRequired"],
        "environmentMaxAgeHours": _safe_int(obj["environmentMaxAgeHours"], "policy.environmentMaxAgeHours", 1, 168),
        "fillInspectionMaxAgeHours": _safe_int(obj["fillInspectionMaxAgeHours"], "policy.fillInspectionMaxAgeHours", 1, 720),
    }


def _normalize_event(raw: Any) -> dict[str, Any]:
    obj = _object(raw, "EVENT_OBJECT_REQUIRED")
    _exact_keys(obj, {"eventId", "kind", "entityId", "observedAt", "payload"}, "EVENT_SHAPE_MISMATCH")
    event_id = _identifier(obj["eventId"], "event.eventId")
    kind = _text(obj["kind"], "event.kind", 40)
    if kind not in _ALLOWED_EVENT_KINDS:
        _fail("UNKNOWN_EVENT_KIND", kind)
    entity_id = _identifier(obj["entityId"], "event.entityId")
    observed_at, _ = _timestamp(obj["observedAt"], "event.observedAt")
    payload = _object(obj["payload"], "EVENT_PAYLOAD_OBJECT_REQUIRED")
    _assert_public_safe(payload, f"event[{event_id}].payload")

    if kind == "BATCH_PLAN":
        _exact_keys(payload, {"batchId", "lotId", "productCode", "formulationRevision", "lineId", "lineRevision", "plannedSlot"}, "BATCH_PLAN_SHAPE_MISMATCH")
        normalized_payload = {
            "batchId": _identifier(payload["batchId"], "plan.batchId"),
            "lotId": _identifier(payload["lotId"], "plan.lotId"),
            "productCode": _identifier(payload["productCode"], "plan.productCode"),
            "formulationRevision": _identifier(payload["formulationRevision"], "plan.formulationRevision"),
            "lineId": _identifier(payload["lineId"], "plan.lineId"),
            "lineRevision": _identifier(payload["lineRevision"], "plan.lineRevision"),
            "plannedSlot": _timestamp(payload["plannedSlot"], "plan.plannedSlot")[0],
        }
    elif kind == "MATERIAL_RELEASE":
        _exact_keys(payload, {"lotId", "released", "evidenceRef"}, "MATERIAL_RELEASE_SHAPE_MISMATCH")
        if not isinstance(payload["released"], bool):
            _fail("BOOLEAN_REQUIRED", "material.released")
        normalized_payload = {
            "lotId": _identifier(payload["lotId"], "material.lotId"),
            "released": payload["released"],
            "evidenceRef": _evidence_ref(payload["evidenceRef"], "material.evidenceRef"),
        }
    elif kind == "EQUIPMENT_STATUS":
        _exact_keys(payload, {"status", "calibrationValidThrough", "evidenceRef"}, "EQUIPMENT_STATUS_SHAPE_MISMATCH")
        status = _text(payload["status"], "equipment.status", 20)
        if status not in {"READY", "HOLD", "OUT_OF_SERVICE"}:
            _fail("EQUIPMENT_STATUS_INVALID", status)
        normalized_payload = {
            "status": status,
            "calibrationValidThrough": _timestamp(payload["calibrationValidThrough"], "equipment.calibrationValidThrough")[0],
            "evidenceRef": _evidence_ref(payload["evidenceRef"], "equipment.evidenceRef"),
        }
    elif kind == "ENVIRONMENT_STATUS":
        _exact_keys(payload, {"isolatorState", "environmentalMonitoringState", "evidenceRef"}, "ENVIRONMENT_STATUS_SHAPE_MISMATCH")
        isolator = _text(payload["isolatorState"], "environment.isolatorState", 20)
        em = _text(payload["environmentalMonitoringState"], "environment.environmentalMonitoringState", 20)
        if isolator not in {"READY", "HOLD"} or em not in {"ACCEPTABLE", "HOLD"}:
            _fail("ENVIRONMENT_STATUS_INVALID")
        normalized_payload = {"isolatorState": isolator, "environmentalMonitoringState": em, "evidenceRef": _evidence_ref(payload["evidenceRef"], "environment.evidenceRef")}
    elif kind == "FILL_INSPECTION":
        _exact_keys(payload, {"lineageBatchId", "lineageLotId", "fillWeightEvidenceRef", "inspectionEvidenceRef"}, "FILL_INSPECTION_SHAPE_MISMATCH")
        normalized_payload = {
            "lineageBatchId": _identifier(payload["lineageBatchId"], "fill.lineageBatchId"),
            "lineageLotId": _identifier(payload["lineageLotId"], "fill.lineageLotId"),
            "fillWeightEvidenceRef": _evidence_ref(payload["fillWeightEvidenceRef"], "fill.fillWeightEvidenceRef"),
            "inspectionEvidenceRef": _evidence_ref(payload["inspectionEvidenceRef"], "fill.inspectionEvidenceRef"),
        }
    elif kind == "PACKAGING_STATUS":
        _exact_keys(payload, {"bomRevision", "labelRevision", "deviceAssemblyStatus", "evidenceRef"}, "PACKAGING_STATUS_SHAPE_MISMATCH")
        assembly = _text(payload["deviceAssemblyStatus"], "packaging.deviceAssemblyStatus", 20)
        if assembly not in {"READY", "HOLD", "NOT_APPLICABLE"}:
            _fail("DEVICE_ASSEMBLY_STATUS_INVALID", assembly)
        normalized_payload = {
            "bomRevision": _identifier(payload["bomRevision"], "packaging.bomRevision"),
            "labelRevision": _identifier(payload["labelRevision"], "packaging.labelRevision"),
            "deviceAssemblyStatus": assembly,
            "evidenceRef": _evidence_ref(payload["evidenceRef"], "packaging.evidenceRef"),
        }
    else:
        _exact_keys(payload, {"batchId", "status", "evidenceRef"}, "DEVIATION_STATUS_SHAPE_MISMATCH")
        status = _text(payload["status"], "deviation.status", 20)
        if status not in {"OPEN", "CLOSED"}:
            _fail("DEVIATION_STATUS_INVALID", status)
        normalized_payload = {
            "batchId": _identifier(payload["batchId"], "deviation.batchId"),
            "status": status,
            "evidenceRef": _evidence_ref(payload["evidenceRef"], "deviation.evidenceRef"),
        }
    return {"eventId": event_id, "kind": kind, "entityId": entity_id, "observedAt": observed_at, "payload": normalized_payload}


def _normalize_input(raw: Any) -> dict[str, Any]:
    root = _object(raw, "INPUT_OBJECT_REQUIRED")
    _exact_keys(root, {"policy", "events"}, "INPUT_SHAPE_MISMATCH")
    _assert_public_safe(root)
    policy = _normalize_policy(root["policy"])
    raw_events = _list(root["events"], "EVENTS_LIST_REQUIRED")
    events_by_id: dict[str, dict[str, Any]] = {}
    for raw_event in raw_events:
        event = _normalize_event(raw_event)
        prior = events_by_id.get(event["eventId"])
        if prior is not None and canonical_json(prior) != canonical_json(event):
            _fail("EVENT_ID_CONFLICT", event["eventId"])
        events_by_id[event["eventId"]] = event
    if not events_by_id:
        _fail("EVENTS_REQUIRED")
    return {"policy": policy, "events": sorted(events_by_id.values(), key=lambda row: row["eventId"])}


