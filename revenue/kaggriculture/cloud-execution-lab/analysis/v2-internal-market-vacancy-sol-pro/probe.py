# SPDX-License-Identifier: Apache-2.0
"""Prove the internal-market-vacancy seam against the preserved interpreter."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import materialize

EXPECTED_ENGINE_SHA256 = (
    "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
)


class ProbeError(ValueError):
    """The source binding or official-engine witness is incomplete."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nonempty_rows(tape: list[Any]) -> list[dict[str, Any]]:
    return [
        {"index": index, "row": copy.deepcopy(row)}
        for index, row in enumerate(tape)
        if row
    ]


def internal_vacancies(tape: list[Any], limit: int) -> tuple[int, ...]:
    window = list(tape[: max(0, int(limit))])
    last_nonempty = max(
        (index for index, row in enumerate(window) if row), default=-1
    )
    return tuple(
        index for index, row in enumerate(window[:last_nonempty]) if not row
    )


def fill_last_internal_vacancy(
    tape: list[Any], order: list[Any], limit: int
) -> tuple[list[Any], int | None]:
    result = copy.deepcopy(tape)
    vacancies = internal_vacancies(result, limit)
    if len(result) < limit or not vacancies:
        return result, None
    slot = vacancies[-1]
    result[slot] = copy.deepcopy(order)
    return result, slot


def make_state(engine, own_orders: list[Any], rival_orders: list[Any]):
    board_size = 10
    farms = [engine._new_farm(board_size, 3000) for _ in range(2)]
    privates = [engine._new_private() for _ in range(2)]
    market = engine._new_market()
    town = engine._new_town()
    states = []
    for player, orders in enumerate((own_orders, rival_orders)):
        observation = SimpleNamespace(
            farms=farms,
            market=market,
            town=town,
            private=privates[player],
            player=player,
            step=0,
            day=0,
            hour=0,
        )
        states.append(
            SimpleNamespace(
                observation=observation,
                action={"farmer": ["PASS"], "hands": [], "market": orders},
            )
        )
    env = SimpleNamespace(
        configuration={
            "boardSize": board_size,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        }
    )
    return states, env, farms, privates, market


def execute(engine, orders: list[Any]) -> dict[str, Any]:
    states, env, farms, privates, market = make_state(engine, orders, [])
    privates[0]["shed"]["MILK"] = 2
    engine._process_market(states, env)
    return {
        "money": farms[0]["money"],
        "milk_in_shed": privates[0]["shed"].get("MILK", 0),
        "wheat_seeds": privates[0]["seeds"].get("WHEAT", 0),
        "carrot_seeds": privates[0]["seeds"].get("CARROT", 0),
        "milk_market_inventory": market["inventory"]["MILK"],
    }


def verify_materialization(receipt_path: Path, candidate: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeError(f"invalid materialization receipt: {exc}") from exc
    if receipt.get("schema") != (
        "titan.v2.internal-market-vacancy.materialization.v1"
    ):
        raise ProbeError("unexpected materialization schema")
    if receipt.get("candidate", {}).get("changed_files") != ["scheduler.py"]:
        raise ProbeError("materialization is not scheduler-only")
    scheduler = candidate / "scheduler.py"
    if materialize.sha256(scheduler.read_bytes()) != receipt["candidate"][
        "scheduler_sha256"
    ]:
        raise ProbeError("candidate scheduler hash does not match receipt")
    inventory = materialize.inventory(candidate)
    if materialize.closure_sha256(inventory) != receipt["candidate"][
        "closure_sha256"
    ]:
        raise ProbeError("candidate closure does not match receipt")
    text = scheduler.read_text(encoding="utf-8")
    for label, snippet in (
        ("helper", materialize.HELPER),
        ("feasibility", materialize.NEW_FEASIBILITY),
        ("output", materialize.NEW_OUTPUT),
    ):
        if text.count(snippet) != 1:
            raise ProbeError(f"candidate {label} multiplicity is not one")
    return receipt


def run(lab: Path, candidate: Path, materialization: Path) -> dict[str, Any]:
    lab = lab.resolve()
    engine_path = lab / "reference" / "engine" / "kaggriculture.py"
    scheduler_path = lab / "runtime" / "variants" / "v2" / "scheduler.py"
    if sha256(engine_path) != EXPECTED_ENGINE_SHA256:
        raise ProbeError("official engine SHA-256 mismatch")
    scheduler_bytes = scheduler_path.read_bytes()
    if materialize.git_blob_sha1(scheduler_bytes) != (
        materialize.EXPECTED_V2_SCHEDULER_BLOB
    ):
        raise ProbeError("frozen V2 scheduler Git blob mismatch")
    if hashlib.sha256(scheduler_bytes).hexdigest() != (
        materialize.EXPECTED_V2_SCHEDULER_SHA256
    ):
        raise ProbeError("frozen V2 scheduler SHA-256 mismatch")
    scheduler_text = scheduler_bytes.decode("utf-8")
    for label, snippet in (
        ("old feasibility", materialize.OLD_FEASIBILITY),
        ("old output", materialize.OLD_OUTPUT),
    ):
        if scheduler_text.count(snippet) != 1:
            raise ProbeError(f"frozen V2 {label} multiplicity is not one")

    engine_text = engine_path.read_text(encoding="utf-8")
    engine_contracts = [
        "queues.append(q[:max_orders])",
        "for i in range(max_len):",
        "ostate = _parse_order(q[i])",
    ]
    missing = [needle for needle in engine_contracts if needle not in engine_text]
    if missing:
        raise ProbeError(f"official engine queue contract drift: {missing!r}")

    receipt = verify_materialization(materialization, candidate)
    engine = load_module("_sol_pro_internal_vacancy_engine", engine_path)

    inherited = [
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_SEED", "WHEAT", 1],
        [],
        ["BUY_SEED", "CARROT", 1],
    ]
    sell = ["SELL", "MILK", 2]
    predecessor_tape = copy.deepcopy(inherited) + [copy.deepcopy(sell)]
    candidate_tape, slot = fill_last_internal_vacancy(inherited, sell, 10)
    if slot != 8:
        raise ProbeError(f"unexpected selected internal slot: {slot!r}")
    before_rows = nonempty_rows(inherited)
    after_rows = [
        row for row in nonempty_rows(candidate_tape) if row["index"] != slot
    ]
    if before_rows != after_rows:
        raise ProbeError("candidate moved or modified an inherited non-empty row")

    predecessor = execute(engine, predecessor_tape)
    repaired = execute(engine, candidate_tape)
    if predecessor["milk_in_shed"] != 2:
        raise ProbeError("predecessor unexpectedly executed beyond-cap SELL")
    if repaired["milk_in_shed"] != 0:
        raise ProbeError("internal-vacancy SELL did not execute exactly two units")
    if predecessor["wheat_seeds"] != 8 or repaired["wheat_seeds"] != 8:
        raise ProbeError("inherited WHEAT rows changed")
    if predecessor["carrot_seeds"] != 1 or repaired["carrot_seeds"] != 1:
        raise ProbeError("later inherited CARROT row changed")
    if repaired["money"] <= predecessor["money"]:
        raise ProbeError("witness did not recover spendable own cash")
    if repaired["milk_market_inventory"] <= predecessor["milk_market_inventory"]:
        raise ProbeError("witness did not commit the recovered market supply")

    trailing = inherited[:-2] + [
        ["BUY_SEED", "CARROT", 1],
        [],
    ]
    trailing_candidate, trailing_slot = fill_last_internal_vacancy(trailing, sell, 10)
    if trailing_slot is not None or trailing_candidate != trailing:
        raise ProbeError("internal-hole mechanism consumed a trailing vacancy")

    return {
        "schema": "titan.v2.internal-market-vacancy.mechanism.v1",
        "operation": "titan-v2-internal-market-vacancy-20260909-sol-pro-01",
        "verdict": "MECHANISM_CONFIRMED_ACTIVATION_UNMEASURED",
        "claim_boundary": {
            "official_engine_transition": True,
            "frozen_v2_source_seam": True,
            "candidate_materialization_bound": True,
            "historical_or_current_trace_activation": False,
            "official_game_strength": False,
            "canonical_admission": False,
        },
        "source": {
            "engine_sha256": EXPECTED_ENGINE_SHA256,
            "v2_scheduler_git_blob_sha1": (
                materialize.EXPECTED_V2_SCHEDULER_BLOB
            ),
            "v2_scheduler_sha256": (
                materialize.EXPECTED_V2_SCHEDULER_SHA256
            ),
            "candidate_scheduler_git_blob_sha1": receipt["candidate"][
                "scheduler_git_blob_sha1"
            ],
            "source_closure_sha256": receipt["source"]["closure_sha256"],
            "candidate_closure_sha256": receipt["candidate"]["closure_sha256"],
        },
        "witness": {
            "max_market_orders": 10,
            "internal_slot": slot,
            "predecessor_raw_rows": len(predecessor_tape),
            "candidate_raw_rows": len(candidate_tape),
            "inherited_nonempty_rows": before_rows,
            "predecessor": predecessor,
            "candidate": repaired,
            "own_cash_delta": repaired["money"] - predecessor["money"],
            "trailing_empty_control_untouched": True,
        },
        "next_gate": (
            "scan exact V2/current returned-action traces for a saturated "
            "first-N market window with an internal empty row and scheduler "
            "pending/selected SELL quantity; do not run games absent activation"
        ),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    witness = report["witness"]
    text = f"""# V2 internal market vacancy — mechanism receipt

**Verdict:** `{report['verdict']}`

The preserved official interpreter ignores a row appended beyond the first
{witness['max_market_orders']} raw market rows. In the exact witness, replacing
internal row {witness['internal_slot']} (an empty parser no-op) with the already
selected two-unit MILK sale executes the sale while every inherited non-empty
row remains at the same index.

- predecessor money: `{witness['predecessor']['money']}`
- candidate money: `{witness['candidate']['money']}`
- own-cash delta: `{witness['own_cash_delta']}`
- predecessor MILK remaining: `{witness['predecessor']['milk_in_shed']}`
- candidate MILK remaining: `{witness['candidate']['milk_in_shed']}`
- later CARROT seed row preserved: `{witness['candidate']['carrot_seeds']}`
- trailing-empty control untouched: `{witness['trailing_empty_control_untouched']}`

This proves an interpreter/source mechanism, not occurrence in a real trace and
not playing strength. No official games are admitted until an exact
returned-action trace census finds the topology.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--materialization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.lab, args.candidate, args.materialization)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.markdown)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
