from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from .gate import HOLD_STATUS, READY_STATUS, canonical_json, compile_readiness, verify_readiness_package
except ImportError:
    from gate import HOLD_STATUS, READY_STATUS, canonical_json, compile_readiness, verify_readiness_package

AS_OF = "2026-09-13T10:00:00Z"
EXPECTED_HOLD_COUNTS = {
    "FORMULATION_REVISION_MISMATCH": 6,
    "MATERIAL_NOT_RELEASED": 6,
    "CALIBRATION_EXPIRED": 6,
    "ENVIRONMENT_NOT_READY": 6,
    "FILL_LINEAGE_MISMATCH": 6,
    "PACKAGING_BOM_MISMATCH": 6,
}


def _ts(hours: int) -> str:
    base = datetime(2026, 9, 13, 10, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(hours=hours)).isoformat(timespec="seconds").replace("+00:00", "Z")


def packet(index: int) -> dict[str, Any]:
    batch = f"BATCH-{index:03d}"
    lot = f"LOT-{index:03d}"
    policy = {
        "batchId": batch,
        "lotId": lot,
        "productCode": "SYNTH-PRODUCT-A",
        "approvedFormulationRevision": "FORM-7",
        "approvedLineRevision": "LINE-4",
        "expectedMaterialLots": {"MAT-A": f"MA-{index:03d}", "MAT-B": f"MB-{index:03d}"},
        "requiredEquipmentIds": ["FILLER-1", "INSPECTOR-1"],
        "approvedPackagingBomRevision": "BOM-9",
        "approvedLabelRevision": "LBL-5",
        "deviceAssemblyRequired": True,
        "environmentMaxAgeHours": 8,
        "fillInspectionMaxAgeHours": 24,
    }
    events = [
        {"eventId": f"E-{index:03d}-PLAN", "kind": "BATCH_PLAN", "entityId": batch, "observedAt": _ts(-4), "payload": {"batchId": batch, "lotId": lot, "productCode": "SYNTH-PRODUCT-A", "formulationRevision": "FORM-7", "lineId": "LINE-A", "lineRevision": "LINE-4", "plannedSlot": _ts(24)}},
        {"eventId": f"E-{index:03d}-MA", "kind": "MATERIAL_RELEASE", "entityId": "MAT-A", "observedAt": _ts(-12), "payload": {"lotId": f"MA-{index:03d}", "released": True, "evidenceRef": f"evidence://material/{index}/A"}},
        {"eventId": f"E-{index:03d}-MB", "kind": "MATERIAL_RELEASE", "entityId": "MAT-B", "observedAt": _ts(-12), "payload": {"lotId": f"MB-{index:03d}", "released": True, "evidenceRef": f"evidence://material/{index}/B"}},
        {"eventId": f"E-{index:03d}-FILLER", "kind": "EQUIPMENT_STATUS", "entityId": "FILLER-1", "observedAt": _ts(-2), "payload": {"status": "READY", "calibrationValidThrough": _ts(72), "evidenceRef": f"evidence://equipment/{index}/filler"}},
        {"eventId": f"E-{index:03d}-INSPECTOR", "kind": "EQUIPMENT_STATUS", "entityId": "INSPECTOR-1", "observedAt": _ts(-2), "payload": {"status": "READY", "calibrationValidThrough": _ts(72), "evidenceRef": f"evidence://equipment/{index}/inspector"}},
        {"eventId": f"E-{index:03d}-ENV", "kind": "ENVIRONMENT_STATUS", "entityId": "isolator-environment", "observedAt": _ts(-1), "payload": {"isolatorState": "READY", "environmentalMonitoringState": "ACCEPTABLE", "evidenceRef": f"evidence://environment/{index}"}},
        {"eventId": f"E-{index:03d}-FILL", "kind": "FILL_INSPECTION", "entityId": batch, "observedAt": _ts(-1), "payload": {"lineageBatchId": batch, "lineageLotId": lot, "fillWeightEvidenceRef": f"evidence://fill/{index}/weights", "inspectionEvidenceRef": f"evidence://inspection/{index}"}},
        {"eventId": f"E-{index:03d}-PACK", "kind": "PACKAGING_STATUS", "entityId": batch, "observedAt": _ts(-1), "payload": {"bomRevision": "BOM-9", "labelRevision": "LBL-5", "deviceAssemblyStatus": "READY", "evidenceRef": f"evidence://packaging/{index}"}},
        {"eventId": f"E-{index:03d}-DEV", "kind": "DEVIATION_STATUS", "entityId": f"DEV-{index:03d}", "observedAt": _ts(-1), "payload": {"batchId": batch, "status": "CLOSED", "evidenceRef": f"evidence://deviation/{index}"}},
    ]
    return {"policy": policy, "events": events}


def acceptance_packets() -> list[dict[str, Any]]:
    packets = [packet(index) for index in range(180)]
    for index in range(144, 150):
        packets[index]["events"][0]["payload"]["formulationRevision"] = "FORM-OLD"
    for index in range(150, 156):
        packets[index]["events"][1]["payload"]["released"] = False
    for index in range(156, 162):
        packets[index]["events"][3]["payload"]["calibrationValidThrough"] = _ts(-1)
    for index in range(162, 168):
        packets[index]["events"][5]["payload"]["environmentalMonitoringState"] = "HOLD"
    for index in range(168, 174):
        packets[index]["events"][6]["payload"]["lineageLotId"] = "LOT-WRONG"
    for index in range(174, 180):
        packets[index]["events"][7]["payload"]["bomRevision"] = "BOM-OLD"
    return packets


def run_acceptance() -> dict[str, Any]:
    ready = 0
    held = 0
    hold_counts: Counter[str] = Counter()
    package_digests: list[str] = []
    for raw in acceptance_packets():
        compiled = compile_readiness(raw, as_of=AS_OF)
        if not verify_readiness_package(compiled)["valid"]:
            raise RuntimeError("offline verifier returned invalid")
        if compiled["receipt"]["status"] == READY_STATUS:
            ready += 1
        elif compiled["receipt"]["status"] == HOLD_STATUS:
            held += 1
        else:
            raise RuntimeError("unexpected status")
        for hold in compiled["receipt"]["holds"]:
            hold_counts[hold["code"]] += 1

        retry = copy.deepcopy(raw)
        retry["events"].append(copy.deepcopy(raw["events"][0]))
        if canonical_json(compile_readiness(retry, as_of=AS_OF)) != canonical_json(compiled):
            raise RuntimeError("exact event retry changed package")
        reversed_input = {"policy": copy.deepcopy(raw["policy"]), "events": list(reversed(copy.deepcopy(raw["events"])))}
        if canonical_json(compile_readiness(reversed_input, as_of=AS_OF)) != canonical_json(compiled):
            raise RuntimeError("event ordering changed package")
        package_digests.append(compiled["receipt"]["payloadDigest"])

    result = {
        "schemaVersion": "tj.sterile-fill-finish-batch-readiness-acceptance/v1",
        "packets": 180,
        "ready": ready,
        "held": held,
        "holdCounts": dict(sorted(hold_counts.items())),
        "expectedHoldCounts": EXPECTED_HOLD_COUNTS,
        "allOfflineVerified": True,
        "retryByteStable": True,
        "orderInvariant": True,
        "receiptSetDigest": hashlib.sha256(canonical_json(package_digests).encode("utf-8")).hexdigest(),
    }
    if ready != 144 or held != 36:
        raise RuntimeError(f"acceptance count mismatch: ready={ready} held={held}")
    if result["holdCounts"] != EXPECTED_HOLD_COUNTS:
        raise RuntimeError(f"hold taxonomy mismatch: {result['holdCounts']}")
    return result


if __name__ == "__main__":
    print(json.dumps(run_acceptance(), indent=2, sort_keys=True))
