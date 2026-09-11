#!/usr/bin/env python3
"""Deterministic contract mutation campaign for the terminal selector."""

from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path
from typing import Any

import terminal_outcome_selector as selector

MUTATION_VALUES: tuple[Any, ...] = (
    None,
    True,
    False,
    1.5,
    "",
    "BAD VALUE",
    [],
    {},
    1 << 70,
    -(1 << 70),
)


def leaves(value: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    result: list[tuple[Any, ...]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            result.extend(leaves(child, path + (key,)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(leaves(child, path + (index,)))
    else:
        result.append(path)
    return result


def containers(value: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    result: list[tuple[Any, ...]] = []
    if isinstance(value, dict):
        result.append(path)
        for key, child in value.items():
            result.extend(containers(child, path + (key,)))
    elif isinstance(value, list):
        result.append(path)
        for index, child in enumerate(value):
            result.extend(containers(child, path + (index,)))
    return result


def get(root: Any, path: tuple[Any, ...]) -> Any:
    value = root
    for part in path:
        value = value[part]
    return value


def parent(root: Any, path: tuple[Any, ...]) -> tuple[Any, Any]:
    if not path:
        raise ValueError("root has no parent")
    return get(root, path[:-1]), path[-1]


def mutate(document: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    result = copy.deepcopy(document)
    mode = rng.randrange(10)
    if mode <= 2:
        path = rng.choice(leaves(result))
        owner, key = parent(result, path)
        owner[key] = copy.deepcopy(rng.choice(MUTATION_VALUES))
    elif mode == 3:
        paths = [path for path in containers(result) if path and isinstance(get(result, path), dict)]
        path = rng.choice(paths)
        target = get(result, path)
        target[f"extra_{rng.randrange(1000)}"] = rng.randrange(100)
    elif mode == 4:
        paths = [path for path in containers(result) if path and isinstance(get(result, path), dict) and get(result, path)]
        target = get(result, rng.choice(paths))
        del target[rng.choice(list(target))]
    elif mode == 5:
        rng.shuffle(result["plans"])
        rng.shuffle(result["required_scenarios"])
        for plan in result["plans"]:
            rng.shuffle(plan["rows"])
    elif mode == 6:
        plan = rng.choice(result["plans"])
        row = rng.choice(plan["rows"])
        row[rng.choice(("own_cash", "rival_cash"))] = rng.randint(-100_000, 100_000)
    elif mode == 7:
        plan = rng.choice(result["plans"])
        plan["rows"].append(copy.deepcopy(rng.choice(plan["rows"])))
    elif mode == 8:
        result["plans"].append(copy.deepcopy(rng.choice(result["plans"])))
    else:
        result["tail_policy"]["minimum_own_cash"] = rng.randint(-100_000, 100_000)
        result["tail_policy"]["maximum_outcome_improvement_sacrifice"] = rng.randint(0, 100_000)
    return result


def validate_report(report: dict[str, Any]) -> None:
    if not selector.verify_report_seal(report):
        raise AssertionError("accepted report has invalid seal")
    plan_map = {item["plan_id"]: item for item in report["plans"]}
    selected = report["selected_plan_id"]
    incumbent = report["incumbent_plan_id"]
    if selected != incumbent:
        item = plan_map[selected]
        if not item["eligible"]:
            raise AssertionError("selected candidate is ineligible")
        if item["outcome_regressions"]:
            raise AssertionError("selected candidate regresses outcome")
        if item["same_class_own_regressions"] or item["same_class_margin_regressions"]:
            raise AssertionError("selected candidate regresses same-class value")
        if item["own_cash_floor_violations"] or item["outcome_improvement_sacrifice_violations"]:
            raise AssertionError("selected candidate violates tail policy")
        fields = (
            "worst_outcome", "wins", "ties", "minimum_margin",
            "aggregate_margin", "minimum_own_cash", "aggregate_own_cash",
        )
        selected_rank = tuple(item["rank"][field] for field in fields)
        incumbent_rank = tuple(report["incumbent_rank"][field] for field in fields)
        if selected_rank <= incumbent_rank:
            raise AssertionError("selected candidate does not outrank incumbent")


def run(base: dict[str, Any], iterations: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    accepted = 0
    rejected = 0
    for _ in range(iterations):
        candidate = mutate(base, rng)
        try:
            report = selector.select_document(candidate)
        except selector.ContractError:
            rejected += 1
        else:
            accepted += 1
            validate_report(report)
    return {"iterations": iterations, "accepted": accepted, "rejected": rejected, "seed": seed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("WITNESS-INPUT.json"))
    parser.add_argument("--iterations", type=int, default=25000)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--output", type=Path, default=Path("FUZZ-RECEIPT.json"))
    args = parser.parse_args()
    base = selector.strict_loads(args.input.read_text(encoding="utf-8"))
    result = run(base, args.iterations, args.seed)
    args.output.write_bytes(selector.canonical_bytes(result))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
