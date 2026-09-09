# SPDX-License-Identifier: Apache-2.0
"""Copy-on-write early-land overlay for the current TITAN route bank.

The only policy change is to append one ``BUY_LAND`` order at steps 74 and 98
when the selected route row has room and does not already contain that order.
The source route bank and every untouched route/row/order object remain intact,
so controls created in the same interpreter cannot inherit candidate mutations.

Current TITAN wraps the producer with SpatialTempo during lazy initialization.
That wrapper captures the route mapping in a closure and rebuilds from it before
each producer call. Installation therefore rebinds that captured route source
to the isolated candidate mapping; assigning ``controller.R`` alone would be
silently erased on the first real action.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any, Mapping, MutableMapping, Sequence

LAND_STEPS: tuple[int, int] = (74, 98)
DEFAULT_MAX_ORDERS = 10
REVISION = "current-land-74-98-cow-v1"


@dataclass(frozen=True)
class PatchReport:
    revision: str
    route_keys: int
    distinct_routes: int
    changed_routes: int
    insertions: int
    inserted_by_step: dict[str, int]
    skipped_duplicate: int
    skipped_full: int
    skipped_short_route: int
    source_fingerprint: str
    candidate_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def route_fingerprint(routes: Mapping[Any, Sequence[Mapping[str, Any]]]) -> str:
    """Fingerprint route values without depending on insertion order of keys."""
    ordered = [(str(key), routes[key]) for key in sorted(routes, key=lambda x: str(x))]
    return hashlib.sha256(_canonical(ordered)).hexdigest()


def _contains_land(market: Sequence[Any]) -> bool:
    return any(
        isinstance(order, (list, tuple)) and bool(order) and order[0] == "BUY_LAND"
        for order in market
    )


def patch_routes(
    routes: Mapping[Any, Sequence[Mapping[str, Any]]],
    *,
    max_orders: int = DEFAULT_MAX_ORDERS,
    land_steps: Sequence[int] = LAND_STEPS,
) -> tuple[dict[Any, Sequence[Mapping[str, Any]]], PatchReport]:
    """Return a copy-on-write route bank and an exact mutation receipt.

    The input mapping and nested objects are never mutated. Aliased route lists
    remain aliased in the returned mapping. A route is copied only when at least
    one insertion is admitted; only changed rows and their market lists are
    copied inside that route.
    """
    if not isinstance(routes, Mapping):
        raise TypeError("routes must be a mapping")
    if isinstance(max_orders, bool) or not isinstance(max_orders, int) or max_orders <= 0:
        raise ValueError("max_orders must be a positive integer")

    steps: tuple[int, ...] = tuple(int(step) for step in land_steps)
    if not steps or any(step < 0 for step in steps) or len(set(steps)) != len(steps):
        raise ValueError("land_steps must contain unique non-negative integers")

    source_fingerprint = route_fingerprint(routes)
    patched: dict[Any, Sequence[Mapping[str, Any]]] = dict(routes)
    route_cache: dict[int, Sequence[Mapping[str, Any]]] = {}
    counters: Counter[str] = Counter()
    distinct_routes: set[int] = set()

    for key, original_route in routes.items():
        if not isinstance(original_route, Sequence) or isinstance(original_route, (str, bytes)):
            raise TypeError(f"route {key!r} must be a sequence")
        route_id = id(original_route)
        distinct_routes.add(route_id)
        if route_id in route_cache:
            patched[key] = route_cache[route_id]
            continue

        candidate_route: list[Mapping[str, Any]] | None = None
        for step in steps:
            if step >= len(original_route):
                counters["skipped_short_route"] += 1
                continue
            source_row = original_route[step]
            if not isinstance(source_row, Mapping):
                raise TypeError(f"route {key!r} step {step} must be a mapping")
            market = source_row.get("market") or []
            if not isinstance(market, Sequence) or isinstance(market, (str, bytes)):
                raise TypeError(f"route {key!r} step {step} market must be a sequence")
            if _contains_land(market):
                counters["skipped_duplicate"] += 1
                continue
            if len(market) >= max_orders:
                counters["skipped_full"] += 1
                continue

            if candidate_route is None:
                candidate_route = list(original_route)
            row = dict(source_row)
            row["market"] = list(market) + [["BUY_LAND"]]
            candidate_route[step] = row
            counters["insertions"] += 1
            counters[f"step:{step}"] += 1

        result_route: Sequence[Mapping[str, Any]] = (
            original_route if candidate_route is None else candidate_route
        )
        if candidate_route is not None:
            counters["changed_routes"] += 1
        route_cache[route_id] = result_route
        patched[key] = result_route

    report = PatchReport(
        revision=REVISION,
        route_keys=len(routes),
        distinct_routes=len(distinct_routes),
        changed_routes=counters["changed_routes"],
        insertions=counters["insertions"],
        inserted_by_step={str(step): counters[f"step:{step}"] for step in steps},
        skipped_duplicate=counters["skipped_duplicate"],
        skipped_full=counters["skipped_full"],
        skipped_short_route=counters["skipped_short_route"],
        source_fingerprint=source_fingerprint,
        candidate_fingerprint=route_fingerprint(patched),
    )
    return patched, report


def _rebind_spatial_route_source(
    agent: Any,
    controller: Any,
    source_routes: Mapping[Any, Sequence[Mapping[str, Any]]],
    candidate_routes: Mapping[Any, Sequence[Mapping[str, Any]]],
) -> bool:
    """Rebind SpatialTempo's captured pristine bank without mutating the source.

    SpatialTempo.install stores ``pristine = controller.R`` in the closure of
    ``controller.act`` and rebuilds ``controller.R`` from that object on every
    call. Exact-current TITAN always installs that wrapper for frozen mode.
    Refuse an unrecognized binding rather than ship an inert policy.
    """
    spatial = getattr(agent, "spatial", None)
    if spatial is None:
        return False

    wrapped = getattr(controller, "act", None)
    code = getattr(wrapped, "__code__", None)
    closure = getattr(wrapped, "__closure__", None)
    if code is None or not closure:
        raise RuntimeError("SpatialTempo producer wrapper closure required")

    cells = dict(zip(code.co_freevars, closure))
    pristine_cell = cells.get("pristine")
    controller_cell = cells.get("controller")
    spatial_cell = cells.get("self")
    if pristine_cell is None:
        raise RuntimeError("SpatialTempo pristine route binding unavailable")
    if pristine_cell.cell_contents is not source_routes:
        raise RuntimeError("SpatialTempo pristine route binding does not match controller.R")
    if controller_cell is not None and controller_cell.cell_contents is not controller:
        raise RuntimeError("SpatialTempo controller binding does not match initialized controller")
    if spatial_cell is not None and spatial_cell.cell_contents is not spatial:
        raise RuntimeError("SpatialTempo owner binding does not match initialized spatial state")

    crop_routes = getattr(spatial, "_crop_routes", source_routes)
    if crop_routes is not source_routes:
        raise RuntimeError("SpatialTempo crop route binding does not match controller.R")

    pristine_cell.cell_contents = candidate_routes
    spatial._crop_routes = candidate_routes
    return True


def install(agent: Any, *, max_orders: int = DEFAULT_MAX_ORDERS) -> PatchReport:
    """Install once per initialized controller, including deadline reinitialization.

    TITAN intentionally replaces ``agent.controller`` after an episode deadline.
    Idempotence therefore belongs to the controller object, not to the long-lived
    agent wrapper. Keeping that distinction prevents the overlay from silently
    disappearing in later episodes while still avoiding duplicate insertions.
    """
    controller = getattr(agent, "controller", None)
    routes = getattr(controller, "R", None)
    if controller is None or routes is None:
        raise RuntimeError("initialized TITAN controller with route bank required")

    existing = getattr(agent, "_land_7498_report", None)
    installed_controller = getattr(agent, "_land_7498_controller", None)
    if isinstance(existing, PatchReport) and installed_controller is controller:
        return existing

    patched, report = patch_routes(routes, max_orders=max_orders)
    spatial_rebound = _rebind_spatial_route_source(agent, controller, routes, patched)
    controller.R = patched
    agent._land_7498_controller = controller
    agent._land_7498_report = report
    agent._land_7498_spatial_rebound = spatial_rebound
    diagnostics = getattr(agent, "diagnostics", None)
    if isinstance(diagnostics, MutableMapping):
        payload = report.to_dict()
        payload["spatial_pristine_rebound"] = spatial_rebound
        diagnostics["land_74_98"] = payload
    return report


def wrap(agent: Any, *, max_orders: int = DEFAULT_MAX_ORDERS) -> Any:
    """Patch immediately after TITAN's lazy initialization, before production."""
    if getattr(agent, "_land_7498_wrapped", False):
        return agent
    original_initialize = agent._initialize

    def initialize() -> None:
        original_initialize()
        install(agent, max_orders=max_orders)

    agent._initialize = initialize
    agent._land_7498_wrapped = True
    return agent
