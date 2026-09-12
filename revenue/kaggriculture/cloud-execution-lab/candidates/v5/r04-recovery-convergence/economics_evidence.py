# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib
from typing import Any, Mapping

from common import (
    GateError, HEX64, canonical, hex_value, loads_raw, number, plain_int, text, v5c,
)

REPORT_SCHEMA = "titan-v5-paired-economics/v4"
RECEIPT_SCHEMA = "titan-v5-paired-economics-receipt/v4"
AUTHORIZED_OPPONENT_IDS = ("apex_v7", "arlene_v14")
REFERENCE_POLICIES_GIT_BLOB = "6bce02dad705ccc57656ff2e2139db215f9fcc57"
MIN_SEEDS = 4
REPORT_KEYS = frozenset({
    "schema", "control_id", "candidate_id", "engine_id", "opponent_pack_id",
    "control_archive_sha256", "candidate_archive_sha256", "cells",
})
CELL_KEYS = frozenset({
    "opponent_id", "seed", "seat", "control_own", "control_rival",
    "candidate_own", "candidate_rival",
})


def replay_report(report: Any, composition_id: str) -> dict[str, Any]:
    if type(report) is not dict or set(report) != REPORT_KEYS:
        raise GateError("composition economics report has wrong closed shape")
    if report["schema"] != REPORT_SCHEMA:
        raise GateError("composition economics report schema mismatch")
    control_id = v5c(report["control_id"], "economics control_id")
    candidate_id = v5c(report["candidate_id"], "economics candidate_id")
    if candidate_id != composition_id:
        raise GateError("economics candidate_id is not the authenticated composition identity")
    if control_id == candidate_id:
        raise GateError("economics control_id and candidate_id must differ")
    engine_id = text(report["engine_id"], "economics engine_id")
    opponent_pack = report["opponent_pack_id"]
    if opponent_pack is not None:
        opponent_pack = text(opponent_pack, "economics opponent_pack_id")
    control_archive = hex_value(
        report["control_archive_sha256"], "economics control_archive_sha256", HEX64
    )
    candidate_archive = hex_value(
        report["candidate_archive_sha256"], "economics candidate_archive_sha256", HEX64
    )
    if control_archive == candidate_archive:
        raise GateError("economics control and candidate archive hashes must differ")

    cells = report["cells"]
    if type(cells) is not list:
        raise GateError("economics cells must be a list")
    keys, seeds, seats = [], {}, {}
    deltas, controls, candidates = {}, {}, {}
    all_deltas, all_controls, all_candidates = [], [], []
    for index, cell in enumerate(cells):
        field = f"economics cells[{index}]"
        if type(cell) is not dict or set(cell) != CELL_KEYS:
            raise GateError(f"{field} has wrong raw-score shape")
        opponent = text(cell["opponent_id"], f"{field}.opponent_id")
        seed = plain_int(cell["seed"], f"{field}.seed")
        seat = plain_int(cell["seat"], f"{field}.seat")
        if seat not in (0, 1):
            raise GateError(f"{field}.seat must be 0 or 1")
        keys.append((opponent, seed, seat))
        seeds.setdefault(opponent, set()).add(seed)
        seats.setdefault((opponent, seed), set()).add(seat)

        control_margin = (
            plain_int(cell["control_own"], f"{field}.control_own")
            - plain_int(cell["control_rival"], f"{field}.control_rival")
        )
        candidate_margin = (
            plain_int(cell["candidate_own"], f"{field}.candidate_own")
            - plain_int(cell["candidate_rival"], f"{field}.candidate_rival")
        )
        delta = candidate_margin - control_margin
        deltas.setdefault(opponent, []).append(delta)
        controls.setdefault(opponent, []).append(control_margin)
        candidates.setdefault(opponent, []).append(candidate_margin)
        all_deltas.append(delta)
        all_controls.append(control_margin)
        all_candidates.append(candidate_margin)

    if keys != sorted(keys):
        raise GateError("economics cells must be canonically sorted by opponent/seed/seat")
    if len(keys) != len(set(keys)):
        raise GateError("economics opponent/seed/seat cells must be unique")
    authorized = list(AUTHORIZED_OPPONENT_IDS)
    if sorted(seeds) != authorized:
        raise GateError("economics opponent roster is not exact authorized Apex+Arlene roster")
    seed_set = seeds[authorized[0]]
    if len(seed_set) < MIN_SEEDS:
        raise GateError("economics panel has insufficient seeds per opponent")
    if any(seeds[opponent] != seed_set for opponent in authorized[1:]):
        raise GateError("economics opponents must cover identical seed sets")
    if any(
        seats.get((opponent, seed)) != {0, 1}
        for opponent in authorized for seed in seed_set
    ):
        raise GateError("economics panel must contain both seats for every opponent/seed")
    if len(cells) != len(authorized) * len(seed_set) * 2:
        raise GateError("economics panel is not a balanced authorized topology")

    per_opponent = {}
    for opponent in authorized:
        delta = sum(deltas[opponent])
        if delta < 0:
            raise GateError(f"economics opponent margin regresses: {opponent}")
        per_opponent[opponent] = {
            "cell_count": len(deltas[opponent]),
            "control_margin_sum": sum(controls[opponent]),
            "candidate_margin_sum": sum(candidates[opponent]),
            "sum_margin_delta": delta,
        }
    sum_delta = sum(all_deltas)
    if sum_delta < 0:
        raise GateError("economics global margin regresses")
    return {
        "control_id": control_id,
        "candidate_id": candidate_id,
        "engine_id": engine_id,
        "opponent_pack_id": opponent_pack,
        "control_archive_sha256": control_archive,
        "candidate_archive_sha256": candidate_archive,
        "opponent_count": len(authorized),
        "opponent_ids": authorized,
        "authorized_opponent_ids": authorized,
        "opponent_registry_git_blob": REFERENCE_POLICIES_GIT_BLOB,
        "cell_count": len(cells),
        "seed_count": len(seed_set),
        "sum_margin_delta": sum_delta,
        "mean_margin_delta": sum_delta / len(cells),
        "positive_cells": sum(delta > 0 for delta in all_deltas),
        "negative_cells": sum(delta < 0 for delta in all_deltas),
        "tied_cells": sum(delta == 0 for delta in all_deltas),
        "control_margin_sum": sum(all_controls),
        "candidate_margin_sum": sum(all_candidates),
        "per_opponent": per_opponent,
        "panel_sha256": hashlib.sha256(canonical(cells)).hexdigest(),
    }


def validate_receipt(receipt: Any, expected: Mapping[str, Any]) -> None:
    if type(receipt) is not dict:
        raise GateError("economics firewall receipt must be an object")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise GateError("economics firewall receipt schema mismatch")
    if receipt.get("classification") != "PASS" or receipt.get("promotion_ready") is not True:
        raise GateError("economics firewall receipt is not a promotion-ready PASS")
    fields = (
        "control_id", "candidate_id", "engine_id", "opponent_pack_id",
        "control_archive_sha256", "candidate_archive_sha256", "opponent_count",
        "opponent_ids", "authorized_opponent_ids", "opponent_registry_git_blob",
        "cell_count", "seed_count", "sum_margin_delta", "positive_cells",
        "negative_cells", "tied_cells", "control_margin_sum",
        "candidate_margin_sum", "per_opponent", "panel_sha256",
    )
    for field in fields:
        if receipt.get(field) != expected[field]:
            raise GateError(
                f"economics firewall receipt {field} disagrees with raw report replay"
            )
    if number(receipt.get("mean_margin_delta"), "economics receipt mean_margin_delta") != expected[
        "mean_margin_delta"
    ]:
        raise GateError(
            "economics firewall receipt mean_margin_delta disagrees with raw report replay"
        )


def validate_composition_economics(
    value: Any,
    component_source_sha256: str,
    composition_id: str,
):
    if type(value) is not dict:
        raise GateError("composition_economics must be an object")
    status = value.get("status")
    if status == "PENDING":
        if set(value) != {"status"}:
            raise GateError("PENDING composition_economics may contain only status")
        return None, ["economics_not_pass:combined_composition"]
    if status != "PASS_PAIRED_ECONOMICS":
        raise GateError(
            "composition_economics.status must be PENDING or PASS_PAIRED_ECONOMICS"
        )
    if set(value) != {
        "status", "component_source_sha256", "report_raw", "report_sha256",
        "receipt_raw", "receipt_sha256",
    }:
        raise GateError("PASS composition_economics has wrong closed shape")
    if hex_value(
        value["component_source_sha256"],
        "composition_economics.component_source_sha256",
        HEX64,
    ) != component_source_sha256:
        raise GateError("composition economics binds a different source fingerprint")

    report, _, report_sha = loads_raw(value["report_raw"], "composition_economics.report_raw")
    if report_sha != hex_value(
        value["report_sha256"], "composition_economics.report_sha256", HEX64
    ):
        raise GateError("composition economics report byte hash mismatch")
    expected = replay_report(report, composition_id)

    receipt, _, receipt_sha = loads_raw(
        value["receipt_raw"], "composition_economics.receipt_raw"
    )
    if receipt_sha != hex_value(
        value["receipt_sha256"], "composition_economics.receipt_sha256", HEX64
    ):
        raise GateError("composition economics receipt byte hash mismatch")
    validate_receipt(receipt, expected)
    return {**expected, "report_sha256": report_sha, "receipt_sha256": receipt_sha}, []
