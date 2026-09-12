# SPDX-License-Identifier: Apache-2.0
"""Conservative current-route MELON realization certificate for TITAN V4.

This is a proof producer for ``liquidation_bound.py``. It authenticates the
current frozen Arlene source and credits only literal, positive ``SELL MELON``
quantities that are authored at or after a caller-proved ``not_before_step`` and
inside Arlene's executable market-order prefix. Dynamic dead-stock liquidation,
terminal settlement, town consumption, and inferred future stock are deliberately
not credited here; those require additional custody proofs.

The returned integer is therefore a lower bound on explicit authored SELL outlet
capacity, not a forecast and not an activation decision. Missing, malformed, or
drifted evidence returns ``None``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any, Mapping, Sequence

EXPECTED_ARLENE_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
EXPECTED_TURNS = 720
EXPECTED_MAX_ORDERS = 10
MELON = "MELON"

HERE = Path(__file__).resolve()

def _cloud_lab_root() -> Path:
    for parent in HERE.parents:
        if parent.name == "cloud-execution-lab":
            return parent
    # Unit tests may import this file from a shallow temporary directory. The
    # checkout-only exact-source test is skipped there.
    return HERE.parent

CLOUD_LAB = _cloud_lab_root()
ARLENE_PATH = CLOUD_LAB / "reference" / "next-panel" / "vendor" / "arlene.py"


class RouteRealizationError(ValueError):
    """Current-route evidence is insufficient for a realization certificate."""


def _plain_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise RouteRealizationError(f"{name}_must_be_plain_int_ge_{minimum}")
    return value


def git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def git_blob_sha(path: Path) -> str:
    return git_blob_sha_bytes(path.read_bytes())


def _load_module_from_bytes(data: bytes, path: Path):
    module = types.ModuleType("_melon_realize_current_arlene")
    module.__file__ = str(path)
    try:
        code = compile(data, str(path), "exec")
        exec(code, module.__dict__)
    except Exception as error:
        raise RouteRealizationError("cannot_execute_captured_arlene_source") from error
    return module


def load_authenticated_current_routes(
    path: Path = ARLENE_PATH,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Load exact current Arlene routes or fail on any source/shape drift."""
    if not isinstance(path, Path):
        path = Path(path)
    try:
        source_bytes = path.read_bytes()
    except OSError as error:
        raise RouteRealizationError("arlene_source_unavailable") from error
    blob = git_blob_sha_bytes(source_bytes)
    if blob != EXPECTED_ARLENE_BLOB:
        raise RouteRealizationError(
            f"arlene_blob_drift:{blob}"
        )

    # Execute the exact bytes we authenticated. Never reopen the authority path
    # after verification; a mutable checkout must not redirect the proof source.
    module = _load_module_from_bytes(source_bytes, path)
    if getattr(module, "TURNS", None) != EXPECTED_TURNS:
        raise RouteRealizationError("arlene_turn_count_drift")
    if getattr(module, "MAX_ORDERS", None) != EXPECTED_MAX_ORDERS:
        raise RouteRealizationError("arlene_market_cap_drift")
    decoder = getattr(module, "routes", None)
    if not callable(decoder):
        raise RouteRealizationError("arlene_routes_decoder_missing")
    raw = decoder()
    if not isinstance(raw, Mapping) or not raw:
        raise RouteRealizationError("arlene_routes_must_be_nonempty_mapping")

    routes: dict[str, list[dict[str, Any]]] = {}
    for route_id, route in raw.items():
        if not isinstance(route_id, str) or not route_id:
            raise RouteRealizationError("arlene_route_id_malformed")
        if not isinstance(route, list) or len(route) != EXPECTED_TURNS:
            raise RouteRealizationError(f"arlene_route_length_drift:{route_id}")
        if any(not isinstance(action, dict) for action in route):
            raise RouteRealizationError(f"arlene_route_action_malformed:{route_id}")
        routes[route_id] = route

    declared = {
        getattr(module, name)
        for name in ("MAIN", "YARN", "YARN_CARROT", "MILK_GLUT")
        if isinstance(getattr(module, name, None), str)
    }
    if not declared.issubset(routes):
        raise RouteRealizationError("arlene_declared_route_missing")

    raw_decisions = getattr(module, "DECISIONS", None)
    if not isinstance(raw_decisions, tuple):
        raise RouteRealizationError("arlene_decisions_missing")
    decision_turns: list[int] = []
    for index, decision in enumerate(raw_decisions):
        if not isinstance(decision, tuple) or len(decision) != 4:
            raise RouteRealizationError(f"arlene_decision_malformed:{index}")
        turn, _feature, _threshold, target = decision
        if type(turn) is not int or not (0 <= turn < EXPECTED_TURNS):
            raise RouteRealizationError(f"arlene_decision_turn_malformed:{index}")
        if not isinstance(target, str) or target not in routes:
            raise RouteRealizationError(f"arlene_decision_target_malformed:{index}")
        decision_turns.append(turn)
    if decision_turns != sorted(set(decision_turns)):
        raise RouteRealizationError("arlene_decision_turns_not_strict")

    return routes, {
        "arlene_git_blob": blob,
        "turns": EXPECTED_TURNS,
        "max_orders": EXPECTED_MAX_ORDERS,
        "route_ids": sorted(routes),
        "declared_route_ids": sorted(declared),
        "decision_turns": decision_turns,
    }


def explicit_melon_sell_capacity(
    route: Sequence[Mapping[str, Any]],
    *,
    current_step: Any,
    not_before_step: Any,
    max_orders: Any = EXPECTED_MAX_ORDERS,
    stop_before_step: Any | None = None,
) -> int | None:
    """Count conservative authored MELON SELL capacity after the proven start.

    ``not_before_step`` is intentionally caller-owned. It must already prove the
    earliest callback at which the new MELON production under consideration can
    be present in shed custody. This helper does not infer growth, harvest, DROP,
    or movement timing.
    """
    try:
        current = _plain_int(current_step, "current_step")
        not_before = _plain_int(not_before_step, "not_before_step")
        cap = _plain_int(max_orders, "max_orders", minimum=1)
        stop = None if stop_before_step is None else _plain_int(
            stop_before_step, "stop_before_step"
        )
        if not isinstance(route, Sequence) or isinstance(route, (str, bytes)):
            raise RouteRealizationError("route_must_be_sequence")
        if current > len(route):
            raise RouteRealizationError("current_step_beyond_route")
        start = max(current, not_before)
        end = len(route) if stop is None else min(len(route), stop)
        if start >= end:
            return 0

        total = 0
        for step in range(start, end):
            action = route[step]
            if not isinstance(action, Mapping):
                raise RouteRealizationError(f"route_action_malformed:{step}")
            market = action.get("market") or []
            if not isinstance(market, list):
                raise RouteRealizationError(f"market_malformed:{step}")
            # Engine-inert rows beyond the route's market cap are not evidence.
            for row_index, row in enumerate(market[:cap]):
                if not row:
                    continue
                if not isinstance(row, list):
                    raise RouteRealizationError(
                        f"market_row_malformed:{step}:{row_index}"
                    )
                if row[0] != "SELL":
                    continue
                if len(row) < 3:
                    raise RouteRealizationError(
                        f"sell_row_malformed:{step}:{row_index}"
                    )
                if row[1] != MELON:
                    continue
                quantity = row[2]
                if type(quantity) is not int:
                    raise RouteRealizationError(
                        f"melon_sell_quantity_malformed:{step}:{row_index}"
                    )
                if quantity <= 0:
                    # Dead SELL rows are not outlet capacity.
                    continue
                total += quantity
        return total
    except (RouteRealizationError, KeyError, IndexError, TypeError, OverflowError):
        return None


def current_route_melon_realization_certificate(
    *,
    route_id: Any,
    current_step: Any,
    not_before_step: Any,
    path: Path = ARLENE_PATH,
) -> dict[str, Any] | None:
    """Build a source-bound proof packet consumable by ``liquidation_bound``."""
    if not isinstance(route_id, str) or not route_id:
        return None
    try:
        routes, source = load_authenticated_current_routes(path)
    except (RouteRealizationError, OSError, ImportError, ValueError, TypeError):
        return None
    route = routes.get(route_id)
    if route is None:
        return None
    try:
        current_plain = _plain_int(current_step, "current_step")
        not_before_plain = _plain_int(not_before_step, "not_before_step")
    except RouteRealizationError:
        return None
    next_decision = next(
        (turn for turn in source["decision_turns"] if turn > current_plain),
        source["turns"],
    )
    units = explicit_melon_sell_capacity(
        route,
        current_step=current_plain,
        not_before_step=not_before_plain,
        max_orders=source["max_orders"],
        stop_before_step=next_decision,
    )
    if units is None:
        return None
    start = max(current_plain, not_before_plain)
    return {
        "schema": "titan-v4-melon-route-realization/v1",
        "route_id": route_id,
        "current_step": current_plain,
        "not_before_step": not_before_plain,
        "credited_from_step": start,
        "credited_before_step_exclusive": next_decision,
        "future_decision_turns": [
            turn for turn in source["decision_turns"] if turn > current_plain
        ],
        "certified_remaining_realization_units": units,
        "certificate_kind": "explicit_future_executable_sell_melon_only",
        "arlene_git_blob": source["arlene_git_blob"],
        "max_orders": source["max_orders"],
        "credits_terminal_settlement": False,
        "credits_dynamic_dead_stock_sales": False,
        "credits_town_consumption": False,
        "decision_authority": False,
    }
