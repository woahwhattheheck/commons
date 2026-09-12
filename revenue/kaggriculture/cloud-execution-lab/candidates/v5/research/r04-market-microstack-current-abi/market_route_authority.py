# SPDX-License-Identifier: Apache-2.0
"""Canonical route/queue provenance for recovered V3.1 R04 market stages.

The current V5 controller already has one shared provenance seam:
``current-route-witness/CurrentRouteWindow``. R04 market recovery consumes that
object instead of accepting caller-authored future actions.

The submitted R04 router also consulted a deferred worker-command queue. The
installed current Arlene controller has no such queue: its complete mutable
instance state is exactly ``R, cur, _fs, _fs_for``. This adapter makes that
absence an explicit, fail-closed authority claim. If the installed controller
ever grows any additional per-instance state, binding fails until a canonical
queue authority is defined rather than silently assuming an empty queue.

This adapter also independently re-verifies strict JSON bytes for the *entire*
installed route and every published window row. That keeps this consumer safe
across older/current-route-witness revisions whose own canonicalization may be
weaker than the market carrier requires.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

AUTHORITY_SCHEMA = "titan-v5-r04-market-route-authority-v1"
WINDOW_SCHEMA = "titan-v5-current-route-window-v1"
ROUTE_SOURCE = "installed_controller.R[cur]"
NO_QUEUE_MODEL = "installed-intact-arlene:no-separate-deferred-command-queue:v1"
EXPECTED_CONTROLLER_TYPE = "intact_arlene.Agent"
EXPECTED_CONTROLLER_STATE_KEYS = ("R", "_fs", "_fs_for", "cur")

CURRENT_ROUTE_AUTHORITY_COMMIT = "d61e0333efe5697b56a867ed84a23e909195d3f4"
CURRENT_ROUTE_AUTHORITY_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v5/research/"
    "current-route-witness/current_route_witness.py"
)
CURRENT_ROUTE_AUTHORITY_BLOB = "987e8a52e4f5ab48aa8390bb5655aac23e6c2f39"
CURRENT_CONTROLLER_AUTHORITY_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/reference/next-panel/vendor/arlene.py"
)
CURRENT_CONTROLLER_AUTHORITY_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"

HERE = Path(__file__).resolve().parent
WINDOW_MODULE_PATH = HERE.parent / "current-route-witness" / "current_route_witness.py"
_WINDOW_MODULE_NAME = "titan_v5_canonical_current_route_witness_for_r04"
_WINDOW_MODULE = None


def _canonical_json(value: Any) -> str | None:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        recovered = json.loads(rendered)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if recovered != value:
        return None
    return rendered


def _load_window_module():
    global _WINDOW_MODULE
    if _WINDOW_MODULE is not None:
        return _WINDOW_MODULE
    if not WINDOW_MODULE_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location(_WINDOW_MODULE_NAME, WINDOW_MODULE_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[_WINDOW_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(_WINDOW_MODULE_NAME, None)
        return None
    _WINDOW_MODULE = module
    return module


def _controller_state_keys(controller: Any) -> tuple[str, ...] | None:
    try:
        namespace = vars(controller)
    except TypeError:
        return None
    if not isinstance(namespace, dict):
        return None
    keys = tuple(sorted(namespace))
    if keys != EXPECTED_CONTROLLER_STATE_KEYS:
        return None
    return keys


def _action_worker_cardinality(action: Any) -> int | None:
    if not isinstance(action, dict) or "farmer" not in action:
        return None
    hands = action.get("hands")
    market = action.get("market")
    if not isinstance(hands, list) or not isinstance(market, list):
        return None
    commands = [action["farmer"], *hands]
    if not all(
        isinstance(command, list)
        and command
        and isinstance(command[0], str)
        for command in commands
    ):
        return None
    return len(commands)


def _window_receipt(window: Any) -> dict[str, Any] | None:
    try:
        receipt = window.receipt()
    except Exception:
        return None
    if not isinstance(receipt, dict):
        return None
    if receipt.get("schema") != WINDOW_SCHEMA:
        return None
    if receipt.get("route_source") != ROUTE_SOURCE:
        return None
    if receipt.get("controller_type") != EXPECTED_CONTROLLER_TYPE:
        return None
    if _canonical_json(receipt) is None:
        return None
    return receipt


def _strict_reverify_window(controller: Any, window: Any) -> bool:
    """Rebind strict whole-route bytes and every row against the live controller."""
    route_id = getattr(window, "route_id", None)
    routes = getattr(controller, "R", None)
    if not isinstance(route_id, str) or not isinstance(routes, dict):
        return False
    if getattr(controller, "cur", None) != route_id or route_id not in routes:
        return False
    route_ref = routes[route_id]
    if not isinstance(route_ref, (list, tuple)):
        return False

    strict_route_json = _canonical_json(list(route_ref))
    if strict_route_json is None:
        return False
    strict_route_sha = hashlib.sha256(strict_route_json.encode("ascii")).hexdigest()
    if getattr(window, "route_sha256", None) != strict_route_sha:
        return False

    # Rebind after serialization: no route switch, replacement, or in-place drift.
    if getattr(controller, "cur", None) != route_id:
        return False
    if getattr(controller, "R", None) is not routes or routes.get(route_id) is not route_ref:
        return False
    if _canonical_json(list(route_ref)) != strict_route_json:
        return False

    current_step = getattr(window, "current_step", None)
    lookahead = getattr(window, "lookahead", None)
    rows = getattr(window, "rows", None)
    if type(current_step) is not int or type(lookahead) is not int:
        return False
    if not isinstance(rows, tuple):
        return False
    expected_end = min(len(route_ref), current_step + 1 + lookahead)
    if len(rows) != max(0, expected_end - (current_step + 1)):
        return False

    for offset, row in enumerate(rows, start=1):
        expected_step = current_step + offset
        if getattr(row, "step", None) != expected_step:
            return False
        try:
            action = row.action()
        except Exception:
            return False
        strict_action_json = _canonical_json(action)
        if strict_action_json is None or strict_action_json != getattr(row, "action_json", None):
            return False
        digest = hashlib.sha256(strict_action_json.encode("ascii")).hexdigest()
        if digest != getattr(row, "action_sha256", None):
            return False
        if _action_worker_cardinality(action) != getattr(row, "worker_cardinality", None):
            return False
        if expected_step >= len(route_ref) or action != route_ref[expected_step]:
            return False
    return True


def _authority_material(window_receipt: dict[str, Any], state_keys: tuple[str, ...]):
    return {
        "schema": AUTHORITY_SCHEMA,
        "window": window_receipt,
        "queue_model": NO_QUEUE_MODEL,
        "controller_state_keys": list(state_keys),
    }


@dataclass(frozen=True)
class MarketRouteAuthority:
    """One immutable canonical route window plus explicit no-queue proof."""

    window: Any
    queue_model: str
    controller_state_keys: tuple[str, ...]
    authority_sha256: str

    def receipt(self) -> dict[str, Any]:
        window_receipt = _window_receipt(self.window)
        if window_receipt is None:
            raise ValueError("invalid canonical route-window receipt")
        material = _authority_material(window_receipt, self.controller_state_keys)
        return {**material, "authority_sha256": self.authority_sha256}

    def future_actions(self) -> dict[int, dict[str, Any]]:
        result = {}
        previous = int(self.window.current_step)
        for row in self.window.rows:
            step = row.step
            if type(step) is not int or step != previous + 1:
                raise ValueError("route-window rows are not contiguous")
            action = row.action()
            if _canonical_json(action) is None:
                raise ValueError("route-window row is not strict JSON")
            result[step] = action
            previous = step
        return result

    def queued_commands(self) -> tuple[Any, ...]:
        """Authenticated current-controller queue model: no separate queue."""
        return ()


def bind_market_route_authority(
    controller: Any,
    observation: Any,
    *,
    lookahead: int = 8,
) -> MarketRouteAuthority | None:
    """Bind installed controller -> canonical window -> strict market authority."""
    if f"{type(controller).__module__}.{type(controller).__qualname__}" != EXPECTED_CONTROLLER_TYPE:
        return None
    state_keys = _controller_state_keys(controller)
    if state_keys is None:
        return None
    module = _load_window_module()
    if module is None:
        return None
    binder = getattr(module, "bind_current_route_window", None)
    if not callable(binder):
        return None
    try:
        window = binder(controller, observation, lookahead=lookahead)
    except Exception:
        return None
    if window is None or _window_receipt(window) is None:
        return None
    if not _strict_reverify_window(controller, window):
        return None

    material = _authority_material(_window_receipt(window), state_keys)
    rendered = _canonical_json(material)
    if rendered is None:
        return None
    digest = hashlib.sha256(rendered.encode("ascii")).hexdigest()
    return MarketRouteAuthority(
        window=window,
        queue_model=NO_QUEUE_MODEL,
        controller_state_keys=state_keys,
        authority_sha256=digest,
    )


def validate_market_route_authority(
    authority: Any,
    observation: Any,
    *,
    required_end_step: int | None = None,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]] | None:
    """Validate one immutable market authority; return detached rows + receipt."""
    if type(authority) is not MarketRouteAuthority:
        return None
    if authority.queue_model != NO_QUEUE_MODEL:
        return None
    if authority.controller_state_keys != EXPECTED_CONTROLLER_STATE_KEYS:
        return None
    if not isinstance(observation, dict):
        return None
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or step < 0 or type(player) is not int or player not in (0, 1):
        return None

    receipt = _window_receipt(authority.window)
    if receipt is None:
        return None
    if receipt.get("current_step") != step or receipt.get("current_index") != step:
        return None

    farms = observation.get("farms")
    private = observation.get("private")
    if (
        not isinstance(farms, list)
        or len(farms) != 2
        or not isinstance(farms[player], dict)
        or not isinstance(farms[player].get("hands"), list)
        or not isinstance(private, dict)
        or not isinstance(private.get("inventories"), list)
    ):
        return None
    workers = 1 + len(farms[player]["hands"])
    if len(private["inventories"]) != workers:
        return None
    if receipt.get("current_worker_cardinality") != workers:
        return None

    material = _authority_material(receipt, authority.controller_state_keys)
    rendered = _canonical_json(material)
    if rendered is None:
        return None
    expected = hashlib.sha256(rendered.encode("ascii")).hexdigest()
    if authority.authority_sha256 != expected:
        return None

    try:
        actions = authority.future_actions()
    except (TypeError, ValueError, AttributeError, json.JSONDecodeError):
        return None
    if required_end_step is not None:
        if type(required_end_step) is not int or required_end_step < step:
            return None
        for due in range(step + 1, required_end_step + 1):
            if due not in actions:
                return None
    return actions, authority.receipt()
