#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Static census for E13's future-sale/post-sale-acquisition exposure.

This intentionally proves only that the frozen Arlene route bank contains the
requested-order shape that can reach the source defect.  It does not claim that
the future SELL fills, that FrozenSelected changes a returned action, or that a
score changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

OPERATION = "TITAN-V3-E13-FUTURE-SALE-SOLVENCY-CLOSURE-20260910-01"
ARLENE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/next-panel/vendor/arlene.py"
)
EXPECTED_ARLENE_GIT_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
DEFAULT_HORIZON = 8
DEFAULT_MAX_ORDERS = 10
FIXED_ACQUISITIONS = frozenset(("HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL"))
OPERATING_PRODUCTS = frozenset(("WHEAT", "FERTILIZER"))


class CensusError(RuntimeError):
    """Raised when the frozen route source or a route shape is not auditable."""


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_repo_root(start: Path | None = None) -> Path:
    origin = (start or Path(__file__).resolve()).resolve()
    candidates: Iterable[Path] = (origin, *origin.parents)
    for candidate in candidates:
        if candidate.is_file():
            candidate = candidate.parent
        if (candidate / ARLENE_REL).is_file():
            return candidate
    raise CensusError(f"could not locate repository root containing {ARLENE_REL}")


def _positive_quantity(row: Any) -> int | None:
    if not isinstance(row, list) or len(row) < 3:
        return None
    try:
        quantity = int(row[2])
    except (TypeError, ValueError, OverflowError):
        return None
    return quantity if quantity > 0 else None


def _active_market(action: Any, max_orders: int) -> list[Any]:
    if not isinstance(action, Mapping):
        return []
    market = action.get("market", [])
    if not isinstance(market, list):
        return []
    return market[: max(1, int(max_orders))]


def _positive_sell(row: Any, targets: frozenset[str] | None = None) -> bool:
    if not isinstance(row, list) or len(row) < 3 or row[0] != "SELL":
        return False
    if targets is not None and row[1] not in targets:
        return False
    return _positive_quantity(row) is not None


def _fixed_acquisition(row: Any) -> bool:
    if not isinstance(row, list) or not row or row[0] not in FIXED_ACQUISITIONS:
        return False
    if row[0] in ("HIRE", "BUY_LAND"):
        return True
    return _positive_quantity(row) is not None


def route_digest(route: Any) -> str:
    data = json.dumps(
        route, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256(data)


def scan_routes(
    routes: Mapping[str, list[Any]],
    products: Iterable[str],
    *,
    max_orders: int = DEFAULT_MAX_ORDERS,
    horizon: int = DEFAULT_HORIZON,
) -> dict[str, Any]:
    if not isinstance(routes, Mapping) or not routes:
        raise CensusError("routes must be a nonempty mapping")
    max_orders = max(1, int(max_orders))
    horizon = max(0, int(horizon))
    targets = frozenset(str(item) for item in products) - OPERATING_PRODUCTS

    named_exposures: list[dict[str, Any]] = []
    route_identities: dict[str, str] = {}
    for route_name in sorted(routes):
        route = routes[route_name]
        if not isinstance(route, list):
            raise CensusError(f"route {route_name!r} is not a list")
        digest = route_digest(route)
        route_identities[str(route_name)] = digest
        for now, action in enumerate(route):
            current_sales = [
                {
                    "index": index,
                    "item": row[1],
                    "quantity": _positive_quantity(row),
                }
                for index, row in enumerate(_active_market(action, max_orders))
                if _positive_sell(row, targets)
            ]
            if not current_sales:
                continue

            end = min(len(route) - 1, now + horizon)
            funding_turn: int | None = None
            funding_rows: list[dict[str, Any]] = []
            for turn in range(now + 1, end + 1):
                sales = [
                    {
                        "index": index,
                        "item": row[1],
                        "quantity": _positive_quantity(row),
                    }
                    for index, row in enumerate(
                        _active_market(route[turn], max_orders)
                    )
                    if _positive_sell(row)
                ]
                if sales:
                    funding_turn = turn
                    funding_rows = sales
                    break
            if funding_turn is None:
                continue

            later_acquisitions: list[dict[str, Any]] = []
            for turn in range(funding_turn + 1, end + 1):
                for index, row in enumerate(_active_market(route[turn], max_orders)):
                    if _fixed_acquisition(row):
                        later_acquisitions.append(
                            {
                                "turn": turn,
                                "index": index,
                                "operation": row[0],
                                "item": row[1] if len(row) > 1 else "",
                                "quantity": (
                                    _positive_quantity(row)
                                    if row[0] not in ("HIRE", "BUY_LAND")
                                    else 1
                                ),
                            }
                        )
            if not later_acquisitions:
                continue

            named_exposures.append(
                {
                    "route": str(route_name),
                    "route_sha256": digest,
                    "current_turn": now,
                    "horizon_end": end,
                    "current_target_sales": current_sales,
                    "first_future_requested_sale_turn": funding_turn,
                    "first_future_requested_sales": funding_rows,
                    "strictly_later_fixed_acquisitions": later_acquisitions,
                }
            )

    unique_keys = {
        (
            exposure["route_sha256"],
            exposure["current_turn"],
            exposure["first_future_requested_sale_turn"],
            tuple(
                (
                    row["turn"],
                    row["index"],
                    row["operation"],
                    row["item"],
                    row["quantity"],
                )
                for row in exposure["strictly_later_fixed_acquisitions"]
            ),
        )
        for exposure in named_exposures
    }
    operation_counts: dict[str, int] = {}
    for exposure in named_exposures:
        for row in exposure["strictly_later_fixed_acquisitions"]:
            operation_counts[row["operation"]] = (
                operation_counts.get(row["operation"], 0) + 1
            )

    return {
        "schema": "titan.v3.e13-future-sale-solvency.route-census.v1",
        "operation": OPERATION,
        "structural_only": True,
        "requested_future_sale_fill_proven": False,
        "returned_action_activation_proven": False,
        "score_causality_claim": False,
        "parameters": {
            "horizon": horizon,
            "max_market_orders_per_turn": max_orders,
            "target_products": sorted(targets),
            "post_sale_requirement": "acquisition_turn_strictly_greater_than_sale_turn",
        },
        "route_count": len(routes),
        "unique_route_body_count": len(set(route_identities.values())),
        "named_exposure_count": len(named_exposures),
        "unique_route_step_exposure_count": len(unique_keys),
        "later_acquisition_operation_counts": dict(sorted(operation_counts.items())),
        "route_sha256": route_identities,
        "examples": named_exposures[:24],
        "examples_truncated": len(named_exposures) > 24,
    }


def load_frozen_routes(source_path: Path) -> tuple[Mapping[str, list[Any]], list[str], bytes]:
    source = source_path.read_bytes()
    actual_blob = git_blob_sha(source)
    if actual_blob != EXPECTED_ARLENE_GIT_BLOB:
        raise CensusError(
            f"Arlene Git blob mismatch: expected {EXPECTED_ARLENE_GIT_BLOB}, "
            f"got {actual_blob}"
        )
    name = "titan_v3_e13_future_sale_solvency_frozen_arlene"
    spec = importlib.util.spec_from_file_location(name, source_path)
    if spec is None or spec.loader is None:
        raise CensusError(f"could not load module specification for {source_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    route_map = module.routes()
    products = list(module.PRODUCTS)
    return route_map, products, source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--max-orders", type=int, default=DEFAULT_MAX_ORDERS)
    args = parser.parse_args()

    root = args.root.resolve() if args.root else find_repo_root()
    source_path = root / ARLENE_REL
    routes, products, source = load_frozen_routes(source_path)
    report = scan_routes(
        routes,
        products,
        max_orders=args.max_orders,
        horizon=args.horizon,
    )
    report["source"] = {
        "path": ARLENE_REL.as_posix(),
        "git_blob_sha1": git_blob_sha(source),
        "sha256": sha256(source),
        "bytes": len(source),
    }
    output = args.output.resolve()
    if output == source_path.resolve():
        raise CensusError("refusing to overwrite frozen Arlene source")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(output)
    if output.read_bytes() != payload:
        raise CensusError("route census failed deterministic readback")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
