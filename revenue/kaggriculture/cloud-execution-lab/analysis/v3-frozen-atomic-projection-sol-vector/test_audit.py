#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for the SOL-VECTOR FrozenSelected projection audit."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sol_vector_audit", HERE / "audit.py")
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def state_with(seeds):
    farm = audit._blank_farm()
    private = audit._blank_private()
    private["shed"]["WHEAT"] = 0
    private["inventories"] = [{}, {}]
    private["seeds"].update(seeds)
    return farm, private


def test_atomic_oversubscription_blocks_all():
    action = {
        "farmer": ["PLANT", "WHEAT"],
        "hands": [["PLANT", "WHEAT"]],
        "market": [],
    }
    farm, private = state_with({"WHEAT": 1})
    sequential_farm, sequential_private = copy.deepcopy(farm), copy.deepcopy(private)
    atomic_farm, atomic_private = copy.deepcopy(farm), copy.deepcopy(private)
    audit.apply_unit_stage(
        sequential_farm, sequential_private, action, step=1, atomic_plants=False
    )
    blocked = audit.apply_unit_stage(
        atomic_farm, atomic_private, action, step=1, atomic_plants=True
    )
    assert blocked == {"WHEAT"}
    assert sequential_private["seeds"]["WHEAT"] == 0
    assert atomic_private["seeds"]["WHEAT"] == 1
    assert sequential_farm["tiles"][4][4]["crop"] == "WHEAT"
    assert atomic_farm["tiles"][4][4] is None
    assert atomic_farm["tiles"][4][3] is None


def test_exact_supply_and_nonplant_parity():
    exact = {
        "farmer": ["PLANT", "WHEAT"],
        "hands": [["PLANT", "WHEAT"]],
        "market": [],
    }
    farm, private = state_with({"WHEAT": 2})
    left_farm, left_private = copy.deepcopy(farm), copy.deepcopy(private)
    right_farm, right_private = copy.deepcopy(farm), copy.deepcopy(private)
    audit.apply_unit_stage(left_farm, left_private, exact, step=1, atomic_plants=False)
    audit.apply_unit_stage(right_farm, right_private, exact, step=1, atomic_plants=True)
    assert left_farm == right_farm
    assert left_private == right_private

    move = {"farmer": ["NORTH"], "hands": [["WEST"]], "market": []}
    audit.apply_unit_stage(left_farm, left_private, move, step=2, atomic_plants=False)
    audit.apply_unit_stage(right_farm, right_private, move, step=2, atomic_plants=True)
    assert left_farm == right_farm
    assert left_private == right_private


def test_mixed_crop_only_blocks_oversubscribed_crop():
    action = {
        "farmer": ["PLANT", "WHEAT"],
        "hands": [["PLANT", "CARROT"]],
        "market": [],
    }
    farm, private = state_with({"WHEAT": 0, "CARROT": 1})
    blocked = audit.apply_unit_stage(farm, private, action, step=1, atomic_plants=True)
    assert blocked == {"WHEAT"}
    assert farm["tiles"][4][4] is None
    assert farm["tiles"][4][3]["crop"] == "CARROT"
    assert private["seeds"]["CARROT"] == 0


def test_current_helper_mirror_and_downstream_activation():
    witness = audit.downstream_witness()
    assert witness["changed"] is True
    assert witness["sequential_fill"] == 0
    assert witness["atomic_fill"] == 1
    assert witness["atomic"]["blocked_plant_events"][0]["step"] == 1


def test_route_census_is_complete_and_deterministic():
    first = audit.route_census()
    second = audit.route_census()
    assert first == second
    assert first["route_count"] == 4
    assert all(length >= 719 for length in first["route_lengths"].values())
    for row in first["repeated_same_crop_plant_rows"]:
        assert row["demand"] >= 2
        assert len(row["row_sha256"]) == 64


def test_report_is_strict_and_serializable():
    report = audit.build_report()
    assert report["synthetic_contract_pass"] is True
    assert report["score_claim"] is False
    assert report["canonical_mutation_authorized"] is False
    assert report["disposition"] in {"DORMANT", "ROUTE_RISK"}
    json.dumps(report, sort_keys=True, allow_nan=False)


TESTS = [
    test_atomic_oversubscription_blocks_all,
    test_exact_supply_and_nonplant_parity,
    test_mixed_crop_only_blocks_oversubscribed_crop,
    test_current_helper_mirror_and_downstream_activation,
    test_route_census_is_complete_and_deterministic,
    test_report_is_strict_and_serializable,
]


def main():
    for test in TESTS:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(TESTS)}/{len(TESTS)}")


if __name__ == "__main__":
    main()
