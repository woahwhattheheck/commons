# SPDX-License-Identifier: Apache-2.0
"""Exact-prestate guarded runtime for replay-derived TITAN route candidates.

This module copies the reviewed certificate projection from Commons draft
#12067 and couples it to the continuously-shadowed incumbent contract from
#11992/#12095.  A route row is emitted only after its source certificate equals
the live certificate.  Any malformed row, seat drift, missing step, or
certificate mismatch permanently hands the game back to the already-advanced
incumbent.

The market certificate binds the acting player's own/private and public market
prestate.  It intentionally does *not* claim knowledge of the rival's hidden
simultaneous market queue or exact market outcome.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

CERTIFICATE_DONOR_HEAD = "cbfff2bec813e2c2609ce9c5819b74669e98c566"
CERTIFICATE_DONOR_BLOB = "89a3325eb541ae0e8a81e1e0a426292820f10d98"
CERT_SCHEMA = "titan-v3-s13-action-prestate-certificate/v1"
MODES = frozenset({"post24_full", "post24_market", "post24_units"})
CERTIFICATE_MODE = {
    "post24_full": "full",
    "post24_market": "market",
    "post24_units": "units",
}


class CertificateError(RuntimeError):
    """Malformed state/action data cannot participate in route substitution."""


def strict_json(data: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise CertificateError(f"{label}: duplicate JSON key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise CertificateError(f"{label}: non-finite JSON constant {value}")

    try:
        return json.loads(data.decode(), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CertificateError(f"{label}: invalid UTF-8 JSON: {exc}") from exc


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise CertificateError(f"value is not canonical JSON: {exc}") from exc


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def obj(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(f"{label}: expected object")
    return value


def arr(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CertificateError(f"{label}: expected array")
    return value


def exact_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CertificateError(f"{label}: expected integer >= {minimum}")
    return value


def config_projection(configuration: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    defaults = {
        "boardSize": 10,
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
    }
    for key, default in defaults.items():
        out[key] = exact_int(
            configuration.get(key, default),
            f"configuration.{key}",
            0 if key == "farmHandCostMult" else 1,
        )
    params = configuration.get("marketParams")
    if params is not None and not isinstance(params, Mapping):
        raise CertificateError("configuration.marketParams: expected object or null")
    out["marketParams"] = params
    return out


def exact_action(value: Any) -> dict[str, Any]:
    action = obj(value, "action")
    if set(action) != {"farmer", "hands", "market"}:
        raise CertificateError(f"action keys drift: {sorted(action)}")
    farmer, hands, market = action["farmer"], action["hands"], action["market"]
    if not isinstance(farmer, list) or not farmer or not isinstance(farmer[0], str):
        raise CertificateError("action.farmer is malformed")
    if not isinstance(hands, list) or any(
        not isinstance(row, list) or not row or not isinstance(row[0], str)
        for row in hands
    ):
        raise CertificateError("action.hands is malformed")
    if not isinstance(market, list) or any(
        row != []
        and (not isinstance(row, list) or not row or not isinstance(row[0], str))
        for row in market
    ):
        raise CertificateError("action.market is malformed")
    return strict_json(canonical(action), "action")


def prestate_certificate(
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    seat: int,
    mode: str,
) -> dict[str, Any]:
    """Exact copy of #12067's reviewed own/prestate certificate projection."""
    if mode not in {"units", "market", "full"}:
        raise CertificateError(f"unsupported mode {mode!r}")
    farms = arr(observation.get("farms"), "observation.farms")
    if not 0 <= seat < len(farms):
        raise CertificateError("seat is outside observation.farms")
    if (
        type(observation.get("player", seat)) is not int
        or observation.get("player", seat) != seat
    ):
        raise CertificateError(
            f"observation.player {observation.get('player')!r} does not bind seat {seat}"
        )
    farm = obj(farms[seat], "player farm")
    private = obj(observation.get("private"), "observation.private")
    cfg = config_projection(obj(configuration, "configuration"))
    action = exact_action(action)
    domains: dict[str, str] = {}
    if mode in {"units", "full"}:
        domains["units"] = sha(
            {
                "day": exact_int(observation.get("day"), "observation.day"),
                "farm": farm,
                "private": private,
                "configuration": {
                    key: cfg[key]
                    for key in ("boardSize", "turnsPerDay", "shedCapacity")
                },
                "action": {
                    "farmer": action["farmer"],
                    "hands": action["hands"],
                },
            }
        )
    if mode in {"market", "full"}:
        domains["market"] = sha(
            {
                "farm": {
                    key: farm.get(key)
                    for key in (
                        "money",
                        "hands",
                        "hires_today",
                        "unlocked_quadrants",
                        "tiles",
                        "farmer",
                    )
                },
                "private": private,
                "market": obj(observation.get("market"), "observation.market"),
                "configuration": {
                    key: cfg[key]
                    for key in (
                        "boardSize",
                        "shedCapacity",
                        "maxMarketOrdersPerTurn",
                        "farmHandCostMult",
                        "marketParams",
                    )
                },
                "action": action["market"],
            }
        )
    return {
        "schema": CERT_SCHEMA,
        "mode": mode,
        "seat": seat,
        "action_sha256": sha(action),
        "domains": domains,
    }


def certificate_matches(
    expected: Mapping[str, Any],
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    seat: int,
) -> bool:
    mode = obj(expected, "expected certificate").get("mode")
    if not isinstance(mode, str):
        raise CertificateError("expected certificate has no mode")
    return canonical(expected) == canonical(
        prestate_certificate(observation, configuration, action, seat=seat, mode=mode)
    )


def _step(obs: Mapping[str, Any]) -> int:
    value = obs.get("step", 0)
    if type(value) is not int or value < 0:
        raise ValueError("observation step must be a nonnegative integer")
    return value


def _player(obs: Mapping[str, Any]) -> int:
    player = obs.get("player")
    if type(player) is not int or player < 0:
        raise ValueError("observation player must be a nonnegative integer")
    return player


def _farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    player = _player(obs)
    farms = obs.get("farms")
    if not isinstance(farms, Sequence) or isinstance(farms, (str, bytes)):
        raise ValueError("observation has no canonical farms view")
    if player >= len(farms) or not isinstance(farms[player], Mapping):
        raise ValueError("observation player farm is unavailable")
    return farms[player]


def _market_limit(configuration: Mapping[str, Any] | None) -> int:
    raw = (configuration or {}).get("maxMarketOrdersPerTurn", 10)
    if type(raw) is bool:
        return 1
    try:
        return max(1, int(raw))
    except (TypeError, ValueError, OverflowError):
        return 10


def _unit_action(value: Any) -> list[Any] | None:
    if not isinstance(value, list) or not value or not isinstance(value[0], str):
        return None
    return copy.deepcopy(value)


def _market_action(value: Any) -> list[list[Any]] | None:
    if not isinstance(value, list):
        return None
    result: list[list[Any]] = []
    for row in value:
        if row == []:
            result.append([])
        elif isinstance(row, list) and row and isinstance(row[0], str):
            result.append(copy.deepcopy(row))
        else:
            return None
    return result


def _baseline_shape(base: Any) -> dict[str, Any]:
    if not isinstance(base, Mapping):
        raise ValueError("baseline action must be a mapping")
    farmer = _unit_action(base.get("farmer"))
    hands = base.get("hands")
    market = _market_action(base.get("market"))
    if farmer is None or not isinstance(hands, list) or market is None:
        raise ValueError("baseline action has malformed farmer/hands/market fields")
    normalized_hands: list[list[Any]] = []
    for row in hands:
        action = _unit_action(row)
        if action is None:
            raise ValueError("baseline hand action is malformed")
        normalized_hands.append(action)
    return {"farmer": farmer, "hands": normalized_hands, "market": market}


class CertifiedLeaderRoutePolicy:
    """Shadow an incumbent and emit only exact-certificate-matching route rows."""

    def __init__(
        self,
        baseline_agent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Any],
        tape: Mapping[int | str, Mapping[str, Any]],
        *,
        mode: str,
        source_seat: int,
        start_step: int = 24,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"unsupported route mode: {mode}")
        if type(source_seat) is not int or source_seat < 0:
            raise ValueError("source_seat must be a nonnegative integer")
        if type(start_step) is not int or start_step < 24:
            raise ValueError("leader route may not own the opening day")
        self._baseline_agent = baseline_agent
        self._tape: dict[int, Mapping[str, Any]] = {}
        for raw_step, entry in tape.items():
            if isinstance(raw_step, bool):
                raise ValueError("tape contains a boolean step")
            try:
                step = int(raw_step)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("tape contains an invalid step") from exc
            if str(step) != str(raw_step) or step < 0 or not isinstance(entry, Mapping):
                raise ValueError("tape contains a noncanonical step or entry")
            if step in self._tape:
                raise ValueError("tape contains a duplicate step")
            self._tape[step] = entry
        self.mode = mode
        self.certificate_mode = CERTIFICATE_MODE[mode]
        self.source_seat = source_seat
        self.start_step = start_step
        self.active = True
        self.handoff_step: int | None = None
        self.handoff_reason: str | None = None
        self.activation_steps: list[int] = []
        self.certificate_checks = 0
        self.certificate_matches = 0

    def _reset(self) -> None:
        self.active = True
        self.handoff_step = None
        self.handoff_reason = None
        self.activation_steps = []
        self.certificate_checks = 0
        self.certificate_matches = 0

    def _handoff(self, step: int, reason: str) -> None:
        self.active = False
        if self.handoff_step is None:
            self.handoff_step = step
            self.handoff_reason = reason

    def _candidate(
        self,
        obs: Mapping[str, Any],
        configuration: Mapping[str, Any],
        base: dict[str, Any],
        entry: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        raw = entry.get("action")
        expected = entry.get("certificate")
        if not isinstance(raw, Mapping) or not isinstance(expected, Mapping):
            return None
        action = exact_action(raw)
        if expected.get("mode") != self.certificate_mode:
            return None
        if expected.get("seat") != self.source_seat:
            return None

        self.certificate_checks += 1
        if not certificate_matches(
            expected,
            obs,
            configuration,
            action,
            seat=self.source_seat,
        ):
            return None
        self.certificate_matches += 1

        out = copy.deepcopy(base)
        live_hands = _farm(obs).get("hands")
        if not isinstance(live_hands, list):
            return None
        if self.mode in {"post24_full", "post24_units"}:
            farmer = _unit_action(action.get("farmer"))
            hands = action.get("hands")
            if farmer is None or not isinstance(hands, list) or len(hands) != len(live_hands):
                return None
            normalized_hands: list[list[Any]] = []
            for row in hands:
                normalized = _unit_action(row)
                if normalized is None:
                    return None
                normalized_hands.append(normalized)
            out["farmer"] = farmer
            out["hands"] = normalized_hands
        if self.mode in {"post24_full", "post24_market"}:
            market = _market_action(action.get("market"))
            if market is None:
                return None
            out["market"] = market[: _market_limit(configuration)]
        return out

    def agent(
        self,
        obs: Mapping[str, Any],
        configuration: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        step = _step(obs)
        if step == 0:
            self._reset()

        # Incumbent advancement is unconditional and precedes every route check.
        # Give the incumbent private copies: a controller that mutates its inputs
        # must not alter either the caller-visible observation or the prestate that
        # is certified immediately afterward. Its internal route state still
        # advances exactly once on every observation.
        baseline_obs = copy.deepcopy(obs)
        baseline_configuration = copy.deepcopy(configuration)
        base = _baseline_shape(
            self._baseline_agent(baseline_obs, baseline_configuration)
        )
        if not self.active or step < self.start_step:
            return base
        try:
            player = _player(obs)
        except ValueError:
            self._handoff(step, "malformed_player")
            return base
        if player != self.source_seat:
            self._handoff(step, "source_seat_mismatch")
            return base
        entry = self._tape.get(step)
        if entry is None:
            self._handoff(step, "missing_route_row")
            return base
        if configuration is None:
            cfg: Mapping[str, Any] = {}
        elif isinstance(configuration, Mapping):
            cfg = configuration
        else:
            self._handoff(step, "malformed_configuration")
            return base
        try:
            candidate = self._candidate(obs, cfg, base, entry)
        except (CertificateError, KeyError, TypeError, ValueError, OverflowError):
            candidate = None
        if candidate is None:
            self._handoff(step, "certificate_or_action_mismatch")
            return base
        if candidate != base:
            self.activation_steps.append(step)
        return candidate

    def diagnostics(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "certificate_mode": self.certificate_mode,
            "source_seat": self.source_seat,
            "start_step": self.start_step,
            "active": self.active,
            "handoff_step": self.handoff_step,
            "handoff_reason": self.handoff_reason,
            "certificate_checks": self.certificate_checks,
            "certificate_matches": self.certificate_matches,
            "activation_count": len(self.activation_steps),
            "activation_steps": list(self.activation_steps),
            "certificate_donor_head": CERTIFICATE_DONOR_HEAD,
            "certificate_donor_blob": CERTIFICATE_DONOR_BLOB,
            "market_outcome_claim": False,
        }
