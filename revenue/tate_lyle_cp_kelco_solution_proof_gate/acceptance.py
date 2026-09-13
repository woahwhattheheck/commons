from __future__ import annotations

import copy
import json

try:
    from .gate import compile_artifacts, normalize_packet, policy_commitment, snapshot_commitment, verify_artifacts
except ImportError:
    from gate import compile_artifacts, normalize_packet, policy_commitment, snapshot_commitment, verify_artifacts


def h(i: int) -> str:
    return f"{i:064x}"[-64:]


def fixture() -> dict:
    ingredients = []
    rules = []
    mappings = []
    owners = [
        {"owner_ref": "OWNER-COMMERCIAL-A", "role": "commercial", "owner_version": "owners-v3"},
        {"owner_ref": "OWNER-SCIENCE-A", "role": "science", "owner_version": "owners-v3"},
    ]
    packs = []
    for i in range(120):
        ingredient = f"ING-{i:04d}"
        legacy = f"LEG-{i:04d}"
        spec = f"SPEC-{i % 9}-R3"
        region = ["NA", "EU", "APAC"][i % 3]
        use_ref = f"USE-{i % 7}"
        claim_ref = f"CLAIM-{i % 5}"
        ingredients.append({"ingredient_id": ingredient, "spec_revision": spec})
        rules.append({
            "ingredient_id": ingredient,
            "region": region,
            "use_ref": use_ref,
            "max_use_level_mgkg": 1000 + i,
            "claim_ref": claim_ref,
        })
        mappings.append({"legacy_id": legacy, "ingredient_id": ingredient, "mapping_version": "map-v4"})
        packs.append({
            "record_id": f"PACK-{i:04d}",
            "ingredient_id": ingredient,
            "spec_revision": spec,
            "region": region,
            "use_ref": use_ref,
            "use_level_mgkg": 900 + i,
            "claim_ref": claim_ref,
            "allergen_evidence_sha256": h(10000 + i),
            "label_evidence_sha256": h(20000 + i),
            "pilot_stability": {
                "result_id": f"STAB-{i:04d}",
                "status": "PASS",
                "protocol_version": "stab-v2",
                "evidence_sha256": h(30000 + i),
            },
            "legacy_substitute": {
                "legacy_id": legacy,
                "mapping_version": "map-v4",
                "evidence_sha256": h(40000 + i),
            },
            "commercial_owner_ref": "OWNER-COMMERCIAL-A",
            "science_owner_ref": "OWNER-SCIENCE-A",
            "owner_version": "owners-v3",
            "source_sha256": h(50000 + i),
        })
    packet = {
        "schema_version": "1",
        "snapshot": {
            "snapshot_id": "synthetic-solution-packs-20260913",
            "captured_at": "2026-09-13T14:00:00Z",
            "source_system_ref": "synthetic-frozen-pack-v1",
        },
        "policy": {
            "policy_id": "cross-portfolio-formulation-evidence-v1",
            "policy_version": "1.0.0",
            "max_snapshot_age_seconds": 7200,
            "approved_ingredients": ingredients,
            "allowed_region_use_claims": rules,
            "legacy_mappings": mappings,
            "stability_protocol_version": "stab-v2",
            "owner_registry_version": "owners-v3",
            "owners": owners,
        },
        "solution_packs": packs,
    }
    # Canonical demand: 75 defects over exactly 30 held packs.
    # 0-19: 20 spec defects.
    for i in range(0, 20):
        packet["solution_packs"][i]["spec_revision"] = "WRONG-SPEC"
    # 0-14: 15 region/use/claim defects.
    for i in range(0, 15):
        packet["solution_packs"][i]["claim_ref"] = "WRONG-CLAIM"
    # 0-14: 15 legacy mapping defects.
    for i in range(0, 15):
        packet["solution_packs"][i]["legacy_substitute"]["mapping_version"] = "wrong-map"
    # 15-29: 15 stability defects.
    for i in range(15, 30):
        packet["solution_packs"][i]["pilot_stability"]["status"] = "HOLD"
    # 20-29: 10 owner/version defects.
    for i in range(20, 30):
        packet["solution_packs"][i]["owner_version"] = "owners-v2"
    return packet


def run() -> dict:
    packet = fixture()
    normalized = normalize_packet(packet)
    snapshot_sha = snapshot_commitment(normalized)
    policy_sha = policy_commitment(normalized)
    when = "2026-09-13T14:30:00Z"
    a = compile_artifacts(packet, expected_snapshot_sha256=snapshot_sha, expected_policy_sha256=policy_sha, evaluation_time=when)
    b = compile_artifacts(copy.deepcopy(packet), expected_snapshot_sha256=snapshot_sha, expected_policy_sha256=policy_sha, evaluation_time=when)
    assert a == b
    assert verify_artifacts(packet, a, expected_snapshot_sha256=snapshot_sha, expected_policy_sha256=policy_sha, evaluation_time=when)
    result = json.loads(a["result.json"])
    expected_counts = {
        "SPEC_REVISION_MISMATCH": 20,
        "REGION_USE_CLAIM_MISMATCH": 15,
        "LEGACY_MAPPING_MISMATCH": 15,
        "STABILITY_MISMATCH": 15,
        "OWNER_VERSION_MISMATCH": 10,
    }
    assert result["summary"]["record_count"] == 120
    assert result["summary"]["pass_count"] == 90
    assert result["summary"]["hold_count"] == 30
    assert result["summary"]["seeded_defect_code_count"] == 75
    assert result["summary"]["defect_code_counts"] == expected_counts
    assert sum(len([c for c in row["codes"] if c in expected_counts]) for row in result["rows"]) == 75
    assert result["authority"]["source_writes"] == 0
    assert result["authority"]["network_writes"] == 0
    receipt = json.loads(a["receipt.json"])
    return {
        "acceptance": "PASS",
        "records": 120,
        "pass": 90,
        "hold": 30,
        "seeded_defects": 75,
        "defect_code_counts": expected_counts,
        "byte_identical_two_runs": True,
        "offline_verify": True,
        "manifest_sha256": receipt["manifest_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "snapshot_sha256": snapshot_sha,
        "policy_sha256": policy_sha,
        "source_writes": 0,
        "network_writes": 0,
        "external_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
