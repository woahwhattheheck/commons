from __future__ import annotations

import copy
from collections import Counter

from .gate import SCHEMA, evaluate, sha256, verify_decision

D = lambda c: c * 64
AS_OF = "2026-09-13T12:00:00Z"
SLOT = "2026-09-14T12:00:00Z"
VERIFY_AT = "2026-09-13T13:00:00Z"


def base_packet(index: int) -> dict:
    batch = f"batch-{index:03d}"
    return {
        "schema_version": SCHEMA,
        "packet_id": f"packet-{index:03d}",
        "batch_id": batch,
        "planned_slot_at": SLOT,
        "as_of": AS_OF,
        "recipe": {
            "recipe_id": "recipe-alpha",
            "version": "v1",
            "approved": True,
            "approved_digest": D("a"),
            "scheduled_recipe_id": "recipe-alpha",
            "scheduled_version": "v1",
        },
        "materials": [
            {"lot_id": f"drug-{index:03d}", "component": "drug-product", "released": True, "release_digest": D("b")},
            {"lot_id": f"vial-{index:03d}", "component": "vial", "released": True, "release_digest": D("c")},
        ],
        "equipment": [
            {"equipment_id": "filler-01", "calibration_valid_until": "2026-10-01T00:00:00Z", "calibration_digest": D("d")},
            {"equipment_id": "balance-01", "calibration_valid_until": "2026-10-01T00:00:00Z", "calibration_digest": D("e")},
        ],
        "environment": {
            "isolator_state": "READY",
            "em_state": "PASS",
            "captured_at": "2026-09-13T11:55:00Z",
            "evidence_digest": D("f"),
        },
        "fill_inspection": {
            "fill_weight_batch_id": batch,
            "inspection_batch_id": batch,
            "recipe_digest": D("a"),
            "fill_weight_digest": D("1"),
            "inspection_digest": D("2"),
        },
        "bom": {
            "required": [
                {"component_id": "device", "version": "v3"},
                {"component_id": "label", "version": "v7"},
            ],
            "staged": [
                {"component_id": "device", "version": "v3"},
                {"component_id": "label", "version": "v7"},
            ],
            "evidence_digest": D("3"),
        },
    }


def packet_for(index: int) -> dict:
    packet = base_packet(index)
    if index < 144:
        return packet
    defect = (index - 144) // 6
    if defect == 0:
        packet["recipe"]["scheduled_version"] = "v2"
    elif defect == 1:
        packet["materials"][0]["released"] = False
    elif defect == 2:
        packet["equipment"][0]["calibration_valid_until"] = "2026-09-14T11:59:59Z"
    elif defect == 3:
        packet["environment"]["isolator_state"] = "HOLD"
    elif defect == 4:
        packet["fill_inspection"]["inspection_batch_id"] = f"other-{index:03d}"
    elif defect == 5:
        packet["bom"]["staged"][1]["version"] = "v8"
    else:
        raise AssertionError(index)
    return packet


def build_suite() -> list[dict]:
    return [packet_for(i) for i in range(180)]


def run_acceptance() -> dict:
    packets = build_suite()
    decisions = [evaluate(packet) for packet in packets]
    for packet, decision in zip(packets, decisions):
        verify_decision(packet, decision, verify_at=VERIFY_AT)
    status_counts = Counter(d["status"] for d in decisions)
    reason_counts = Counter(reason for d in decisions for reason in d["hold_reasons"])
    expected_reasons = {
        "RECIPE_MISMATCH": 6,
        "MATERIAL_UNRELEASED": 6,
        "CALIBRATION_EXPIRED": 6,
        "ENVIRONMENT_HOLD": 6,
        "INSPECTION_LINEAGE_MISMATCH": 6,
        "BOM_MISMATCH": 6,
    }
    assert status_counts == Counter({"READY": 144, "HOLD": 36})
    assert dict(reason_counts) == expected_reasons
    reverse = [evaluate(packet) for packet in reversed(copy.deepcopy(packets))]
    assert sorted(d["receipt_digest"] for d in reverse) == sorted(d["receipt_digest"] for d in decisions)
    return {
        "schema_version": "pci.fill-finish-batch-readiness-acceptance/v1",
        "packet_count": 180,
        "ready_count": 144,
        "hold_count": 36,
        "reason_counts": expected_reasons,
        "receipt_set_digest": sha256(sorted(d["receipt_digest"] for d in decisions)),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_acceptance(), sort_keys=True, indent=2))
