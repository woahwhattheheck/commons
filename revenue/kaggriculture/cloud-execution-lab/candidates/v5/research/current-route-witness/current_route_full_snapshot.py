# SPDX-License-Identifier: Apache-2.0
"""Superset committed-route capture for consumers that need the full native tape.

The underlying trust primitive is the canonical current-route witness `_capture_route`.
This helper performs one capture and can derive ordinary `CurrentRouteWindow` objects
from those same detached bytes without reopening the controller route.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from current_route_witness import (
    MAX_LOOKAHEAD,
    ROUTE_SOURCE,
    SCHEMA,
    CurrentRouteWindow,
    RouteActionWitness,
    _action_worker_cardinality,
    _canonical_json,
    _capture_route,
    _plain_nonnegative_int,
    _route_id,
    _worker_count,
)

FULL_SCHEMA = "titan-v5-current-full-route-snapshot-v1"


@dataclass(frozen=True)
class CurrentFullRouteSnapshot:
    schema: str
    route_source: str
    controller_type: str
    route_id: str
    current_step: int
    current_index: int
    current_worker_cardinality: int
    route_length: int
    route_sha256: str
    route_json: str

    def route_actions(self) -> tuple[dict[str, Any], ...]:
        value = json.loads(self.route_json)
        if not isinstance(value, list) or any(not isinstance(action, dict) for action in value):
            raise ValueError("full route snapshot is malformed")
        return tuple(value)

    def receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "route_source": self.route_source,
            "controller_type": self.controller_type,
            "route_id": self.route_id,
            "current_step": self.current_step,
            "current_index": self.current_index,
            "current_worker_cardinality": self.current_worker_cardinality,
            "route_length": self.route_length,
            "route_sha256": self.route_sha256,
        }

    def window(self, lookahead: int) -> CurrentRouteWindow | None:
        if type(lookahead) is not int or not 1 <= lookahead <= MAX_LOOKAHEAD:
            return None
        route = self.route_actions()
        end = min(len(route), self.current_step + 1 + lookahead)
        if end <= self.current_step + 1:
            return None
        rows = []
        for authored_step in range(self.current_step + 1, end):
            authored = route[authored_step]
            cardinality = _action_worker_cardinality(authored)
            action_json = _canonical_json(authored)
            if cardinality is None or action_json is None:
                return None
            rows.append(RouteActionWitness(
                step=authored_step,
                worker_cardinality=cardinality,
                action_json=action_json,
                action_sha256=hashlib.sha256(action_json.encode("ascii")).hexdigest(),
            ))
        material = json.dumps({
            "schema": SCHEMA,
            "route_source": ROUTE_SOURCE,
            "route_sha256": self.route_sha256,
            "route_id": self.route_id,
            "current_step": self.current_step,
            "rows": [row.receipt() for row in rows],
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        window_sha256 = hashlib.sha256(material.encode("ascii")).hexdigest()
        return CurrentRouteWindow(
            schema=SCHEMA,
            route_source=ROUTE_SOURCE,
            controller_type=self.controller_type,
            route_id=self.route_id,
            current_step=self.current_step,
            current_index=self.current_index,
            current_worker_cardinality=self.current_worker_cardinality,
            route_length=self.route_length,
            route_sha256=self.route_sha256,
            lookahead=lookahead,
            rows=tuple(rows),
            window_sha256=window_sha256,
        )


def bind_current_full_route(controller: Any, observation: Any, *, completed_route_id: Any = None) -> CurrentFullRouteSnapshot | None:
    if _route_id(completed_route_id) is None or not isinstance(observation, dict):
        return None
    step = observation.get("step")
    if not _plain_nonnegative_int(step):
        return None
    count = _worker_count(observation)
    if count is None:
        return None
    captured = _capture_route(controller, completed_route_id)
    if captured is None:
        return None
    route_id, controller_type, route, route_sha256 = captured
    if step >= len(route):
        return None
    route_json = _canonical_json(route)
    if route_json is None or hashlib.sha256(route_json.encode("ascii")).hexdigest() != route_sha256:
        return None
    return CurrentFullRouteSnapshot(
        schema=FULL_SCHEMA,
        route_source=ROUTE_SOURCE,
        controller_type=controller_type,
        route_id=route_id,
        current_step=step,
        current_index=step,
        current_worker_cardinality=count,
        route_length=len(route),
        route_sha256=route_sha256,
        route_json=route_json,
    )
