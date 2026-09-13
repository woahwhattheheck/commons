from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ._common import _fail, sha256_json

def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)


def _select_latest(events: list[dict[str, Any]], kind: str, entity_id: str) -> tuple[dict[str, Any] | None, bool]:
    candidates = [row for row in events if row["kind"] == kind and row["entityId"] == entity_id]
    if not candidates:
        return None, False
    max_time = max(_dt(row["observedAt"]) for row in candidates)
    latest = [row for row in candidates if _dt(row["observedAt"]) == max_time]
    if len({sha256_json(row["payload"]) for row in latest}) > 1:
        return None, True
    return sorted(latest, key=lambda row: row["eventId"])[0], False


def _hold(holds: list[dict[str, str]], code: str, subject: str) -> None:
    row = {"code": code, "subject": subject}
    if row not in holds:
        holds.append(row)


def _evaluate(payload: dict[str, Any], as_of: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    policy, events = payload["policy"], payload["events"]
    as_of_dt = _dt(as_of)
    for event in events:
        if _dt(event["observedAt"]) > as_of_dt:
            _fail("FUTURE_EVIDENCE", event["eventId"])
    holds: list[dict[str, str]] = []

    plan, ambiguous = _select_latest(events, "BATCH_PLAN", policy["batchId"])
    if ambiguous:
        _hold(holds, "AMBIGUOUS_LATEST_STATE", f"BATCH_PLAN:{policy['batchId']}")
    elif plan is None:
        _hold(holds, "BATCH_PLAN_MISSING", policy["batchId"])
    else:
        p = plan["payload"]
        if p["batchId"] != policy["batchId"] or p["lotId"] != policy["lotId"] or p["productCode"] != policy["productCode"]:
            _hold(holds, "BATCH_IDENTITY_MISMATCH", policy["batchId"])
        if p["formulationRevision"] != policy["approvedFormulationRevision"]:
            _hold(holds, "FORMULATION_REVISION_MISMATCH", policy["batchId"])
        if p["lineRevision"] != policy["approvedLineRevision"]:
            _hold(holds, "LINE_REVISION_MISMATCH", p["lineId"])
        if _dt(p["plannedSlot"]) <= as_of_dt:
            _hold(holds, "PLANNED_SLOT_NOT_FUTURE", policy["batchId"])

    for material_code, expected_lot in policy["expectedMaterialLots"].items():
        row, ambiguous = _select_latest(events, "MATERIAL_RELEASE", material_code)
        if ambiguous:
            _hold(holds, "AMBIGUOUS_LATEST_STATE", f"MATERIAL_RELEASE:{material_code}")
        elif row is None:
            _hold(holds, "MATERIAL_RELEASE_MISSING", material_code)
        else:
            if row["payload"]["lotId"] != expected_lot:
                _hold(holds, "MATERIAL_LOT_MISMATCH", material_code)
            if not row["payload"]["released"]:
                _hold(holds, "MATERIAL_NOT_RELEASED", material_code)

    for equipment_id in policy["requiredEquipmentIds"]:
        row, ambiguous = _select_latest(events, "EQUIPMENT_STATUS", equipment_id)
        if ambiguous:
            _hold(holds, "AMBIGUOUS_LATEST_STATE", f"EQUIPMENT_STATUS:{equipment_id}")
        elif row is None:
            _hold(holds, "EQUIPMENT_STATUS_MISSING", equipment_id)
        else:
            if row["payload"]["status"] != "READY":
                _hold(holds, "EQUIPMENT_NOT_READY", equipment_id)
            if _dt(row["payload"]["calibrationValidThrough"]) <= as_of_dt:
                _hold(holds, "CALIBRATION_EXPIRED", equipment_id)

    env, ambiguous = _select_latest(events, "ENVIRONMENT_STATUS", "isolator-environment")
    if ambiguous:
        _hold(holds, "AMBIGUOUS_LATEST_STATE", "ENVIRONMENT_STATUS:isolator-environment")
    elif env is None:
        _hold(holds, "ENVIRONMENT_STATUS_MISSING", "isolator-environment")
    else:
        if env["payload"]["isolatorState"] != "READY" or env["payload"]["environmentalMonitoringState"] != "ACCEPTABLE":
            _hold(holds, "ENVIRONMENT_NOT_READY", "isolator-environment")
        if (as_of_dt - _dt(env["observedAt"])).total_seconds() / 3600 > policy["environmentMaxAgeHours"]:
            _hold(holds, "ENVIRONMENT_EVIDENCE_STALE", "isolator-environment")

    fill, ambiguous = _select_latest(events, "FILL_INSPECTION", policy["batchId"])
    if ambiguous:
        _hold(holds, "AMBIGUOUS_LATEST_STATE", f"FILL_INSPECTION:{policy['batchId']}")
    elif fill is None:
        _hold(holds, "FILL_INSPECTION_MISSING", policy["batchId"])
    else:
        if fill["payload"]["lineageBatchId"] != policy["batchId"] or fill["payload"]["lineageLotId"] != policy["lotId"]:
            _hold(holds, "FILL_LINEAGE_MISMATCH", policy["batchId"])
        if (as_of_dt - _dt(fill["observedAt"])).total_seconds() / 3600 > policy["fillInspectionMaxAgeHours"]:
            _hold(holds, "FILL_INSPECTION_EVIDENCE_STALE", policy["batchId"])

    packaging, ambiguous = _select_latest(events, "PACKAGING_STATUS", policy["batchId"])
    if ambiguous:
        _hold(holds, "AMBIGUOUS_LATEST_STATE", f"PACKAGING_STATUS:{policy['batchId']}")
    elif packaging is None:
        _hold(holds, "PACKAGING_STATUS_MISSING", policy["batchId"])
    else:
        p = packaging["payload"]
        if p["bomRevision"] != policy["approvedPackagingBomRevision"]:
            _hold(holds, "PACKAGING_BOM_MISMATCH", policy["batchId"])
        if p["labelRevision"] != policy["approvedLabelRevision"]:
            _hold(holds, "LABEL_REVISION_MISMATCH", policy["batchId"])
        if policy["deviceAssemblyRequired"] and p["deviceAssemblyStatus"] != "READY":
            _hold(holds, "DEVICE_ASSEMBLY_NOT_READY", policy["batchId"])
        if not policy["deviceAssemblyRequired"] and p["deviceAssemblyStatus"] not in {"READY", "NOT_APPLICABLE"}:
            _hold(holds, "DEVICE_ASSEMBLY_STATUS_INVALID_FOR_POLICY", policy["batchId"])

    for deviation_id in sorted({row["entityId"] for row in events if row["kind"] == "DEVIATION_STATUS"}):
        row, ambiguous = _select_latest(events, "DEVIATION_STATUS", deviation_id)
        if ambiguous:
            _hold(holds, "AMBIGUOUS_LATEST_STATE", f"DEVIATION_STATUS:{deviation_id}")
        elif row is not None and row["payload"]["batchId"] == policy["batchId"] and row["payload"]["status"] == "OPEN":
            _hold(holds, "OPEN_DEVIATION", deviation_id)

    holds.sort(key=lambda row: (row["code"], row["subject"]))
    return holds, {
        "eventCount": len(events),
        "eventDigest": sha256_json(events),
        "policyDigest": sha256_json(policy),
    }


def _authority_envelope() -> dict[str, bool]:
    return {
        "batchReleaseAuthorized": False,
        "gmpDecisionAuthorized": False,
        "qpDecisionAuthorized": False,
        "qualityDecisionAuthorized": False,
        "scientificDecisionAuthorized": False,
        "manufacturingMutationAuthorized": False,
        "providerMutationAuthorized": False,
        "customerContactAuthorized": False,
        "paymentAuthorized": False,
        "deploymentAuthorized": False,
        "revenueRecognitionAuthorized": False,
    }


def _summary(receipt: dict[str, Any]) -> str:
    lines = [
        "# Sterile fill-finish batch-readiness receipt", "",
        f"- status: `{receipt['status']}`", f"- batch ref: `{receipt['batchRef']}`",
        f"- as of: `{receipt['asOf']}`", f"- normalized evidence events: `{receipt['eventCount']}`",
        f"- hold count: `{len(receipt['holds'])}`",
    ]
    for hold in receipt["holds"]:
        lines.append(f"  - `{hold['code']}` · `{hold['subject']}`")
    lines.extend(["", "This receipt is evidence for owner review only. It does not authorize GMP, QP, quality, scientific, batch-release, manufacturing, provider, payment, deployment, or revenue action.", ""])
    return "\n".join(lines)


