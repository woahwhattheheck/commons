# SPDX-License-Identifier: Apache-2.0
"""Receipt-bound public adapter for the V233/V234 donor theorem.

``v233_v234_current`` is retained as theorem mechanics. This public surface accepts
only the canonical full-route snapshot derived from the landed receipt-bound v3
route authority, validates it against the current observation, then presents a
private compatibility view to the unchanged donor implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
from typing import Any

from current_route_full_snapshot import CurrentFullRouteSnapshot, FULL_SCHEMA
from current_route_witness import ROUTE_SOURCE
import v233_v234_current as donor

SAFE_SCHEMA = "titan-v5-v233-v234-receipt-bound-safe-v1"


def _strict_route_json(raw: Any) -> tuple[str, list[dict[str, Any]]] | None:
    if type(raw) is not str:
        return None
    try:
        route = json.loads(raw)
        rerendered = json.dumps(
            route,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if rerendered != raw or not isinstance(route, list) or any(not isinstance(row, dict) for row in route):
        return None
    return rerendered, route


@dataclass(frozen=True)
class _LegacyDonorSnapshot:
    """Compatibility object passed only after canonical v3 snapshot validation."""

    schema: str
    route_source: str
    route_id: str
    current_step: int
    route_sha256: str
    route_length: int
    route_json: str


def _validated_legacy_view(snapshot: Any, observation: Any) -> _LegacyDonorSnapshot | None:
    if type(snapshot) is not CurrentFullRouteSnapshot or not isinstance(observation, dict):
        return None
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or step < 0 or type(player) is not int or player not in (0, 1):
        return None
    if (
        snapshot.schema != FULL_SCHEMA
        or snapshot.route_source != ROUTE_SOURCE
        or snapshot.route_step != step
        or snapshot.last_step != step
        or snapshot.player != player
        or snapshot.current_step != step
        or snapshot.current_index != step
        or type(snapshot.route_id) is not str
        or not snapshot.route_id
        or type(snapshot.route_length) is not int
        or snapshot.route_length <= step
        or type(snapshot.route_sha256) is not str
    ):
        return None
    strict = _strict_route_json(snapshot.route_json)
    if strict is None:
        return None
    route_json, route = strict
    if len(route) != snapshot.route_length:
        return None
    if hashlib.sha256(route_json.encode("ascii")).hexdigest() != snapshot.route_sha256:
        return None

    # Re-derive one canonical bounded receipt from the same detached bytes. This
    # binds the full-route companion back to the exact v3 receipt fields and
    # worker envelope used by ordinary downstream consumers.
    window = snapshot.window(1)
    if window is None:
        return None
    receipt = window.receipt()
    if (
        receipt.get("route_source") != ROUTE_SOURCE
        or receipt.get("route_id") != snapshot.route_id
        or receipt.get("route_step") != step
        or receipt.get("last_step") != step
        or receipt.get("player") != player
        or receipt.get("current_step") != step
        or receipt.get("current_index") != step
        or receipt.get("route_sha256") != snapshot.route_sha256
        or receipt.get("route_length") != snapshot.route_length
    ):
        return None

    return _LegacyDonorSnapshot(
        schema=donor.FULL_ROUTE_SCHEMA,
        route_source=donor.ROUTE_SOURCE,
        route_id=snapshot.route_id,
        current_step=step,
        route_sha256=snapshot.route_sha256,
        route_length=snapshot.route_length,
        route_json=route_json,
    )


class V233V234SixSheepCurrentSafeABI:
    """Public V5 surface: canonical receipt snapshot in, unchanged donor theorem out."""

    schema = SAFE_SCHEMA

    def __init__(self, *, enabled: bool = False):
        self._donor = donor.V233V234SixSheepCurrentABI(enabled=enabled)

    @property
    def enabled(self) -> bool:
        return self._donor.enabled

    def telemetry(self, seat: int = 0):
        return self._donor.telemetry(seat)

    def transform(self, observation: Any, selected_action: Any, *, route_snapshot: Any = None):
        legacy = _validated_legacy_view(route_snapshot, observation)
        if legacy is None:
            return copy.deepcopy(selected_action)
        return self._donor.transform(
            observation,
            selected_action,
            route_snapshot=legacy,
        )
