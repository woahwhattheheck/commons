#!/usr/bin/env python3
"""Observational producer for TITAN V3.1 D3 externality evidence.

The reviewed D3 gate validates score and product-price externality evidence but does
not manufacture it.  This module supplies that missing producer seam without changing
gameplay: it calls the pinned official evaluator's ``play()`` function while replacing
``engine.interpreter`` with a temporary wrapper that calls the original interpreter
first and then reads only public post-step state.

Capture failures never change an otherwise-valid game result.  They only make the
capture incomplete, which downstream assembly expresses as
``externality_complete=false`` so D3 HOLDs rather than PASSing on partial evidence.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


OFFICIAL_EVALUATOR_BLOB = "1fb6b655bb4ca1e1684be165a8ef513e2e6c2325"
OFFICIAL_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
PUBLIC_SUPPLY_DONOR_BLOB = "d9d2add77033a56fd2784e0132fd2abb2f700371"
SOURCE_NAME = "official_replay_public_state"

_CROP_PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
_ANIMAL_PRODUCTS = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
_ANIMAL_STRUCTURES = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
_PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)
_BOARD_SIZE = 10


class ProducerError(ValueError):
    """Raised for malformed producer inputs, never for public-state capture failure."""


def _strict_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _public_rival_supply(farms: Any, candidate_seat: int) -> dict[str, int] | None:
    """Strict public standing-supply parser derived from reviewed D1 theorem.

    ``None`` means malformed/ambiguous public evidence. ``{}`` is a valid board with
    no visible standing supply.  Only public farm tiles are inspected; private shed,
    inventories and submitted orders are never read.
    """
    if type(candidate_seat) is not int or candidate_seat not in (0, 1):
        return None
    if type(farms) is not list or len(farms) != 2:
        return None
    rival = farms[1 - candidate_seat]
    if type(rival) is not dict:
        return None
    tiles = rival.get("tiles")
    if type(tiles) is not list or len(tiles) != _BOARD_SIZE:
        return None

    result: dict[str, int] = {}
    for row in tiles:
        if type(row) is not list or len(row) != _BOARD_SIZE:
            return None
        for tile in row:
            if tile is None or tile == "LOCKED":
                continue
            if type(tile) is not dict:
                return None

            kind = tile.get("kind")
            if kind == "PLANT":
                crop = tile.get("crop")
                units = _strict_nonnegative_int(tile.get("yield_units"))
                if type(crop) is not str or crop not in _CROP_PRODUCTS or units is None:
                    return None
                if units:
                    result[crop] = result.get(crop, 0) + units
                continue

            animal = tile.get("animal")
            if animal is not None:
                if type(animal) is not str or animal not in _ANIMAL_PRODUCTS:
                    return None
                if kind != _ANIMAL_STRUCTURES[animal]:
                    return None
                units = _strict_nonnegative_int(tile.get("yield_units"))
                if units is None:
                    return None
                if units:
                    product = _ANIMAL_PRODUCTS[animal]
                    result[product] = result.get(product, 0) + units
                continue

            if kind not in ("WEED", "COOP", "PASTURE"):
                return None
            if tile.get("crop") is not None:
                return None
    return result


def _snapshot_public(state: Any, candidate_seat: int) -> dict[str, Any] | None:
    """Return one strict post-step public snapshot, or ``None`` if ambiguous."""
    if type(state) is not list or len(state) != 2:
        return None
    try:
        observations = [state[0].observation, state[1].observation]
    except (AttributeError, IndexError, TypeError):
        return None

    steps: list[int] = []
    for obs in observations:
        try:
            step = obs.get("step") if isinstance(obs, Mapping) else obs.step
        except (AttributeError, TypeError):
            return None
        if type(step) is not int or step < 0:
            return None
        steps.append(step)
    if steps[0] != steps[1]:
        return None

    obs = observations[candidate_seat]
    try:
        farms = obs.get("farms") if isinstance(obs, Mapping) else obs.farms
        market = obs.get("market") if isinstance(obs, Mapping) else obs.market
    except (AttributeError, TypeError):
        return None
    if type(market) is not dict:
        return None
    prices = market.get("prices")
    if type(prices) is not dict:
        return None

    exact_prices: dict[str, int] = {}
    for product in _PRODUCTS:
        value = prices.get(product)
        if type(value) is not int or value < 0:
            return None
        exact_prices[product] = value

    supply = _public_rival_supply(farms, candidate_seat)
    if supply is None:
        return None
    return {"step": steps[0], "prices": exact_prices, "rival_supply": supply}


def _valid_trace_sha(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _valid_scores(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == 2
        and all(
            not isinstance(score, bool)
            and isinstance(score, (int, float))
            and math.isfinite(float(score))
            for score in value
        )
    )


def capture_official_play(
    evaluator: Any,
    engine: Any,
    specs: Sequence[str],
    cache: Any,
    loader: Any,
    seed: int,
    candidate_seat: int,
    **play_kwargs: Any,
) -> dict[str, Any]:
    """Call the exact evaluator play path and capture public post-step observations.

    The engine interpreter is restored in ``finally``.  Any failure in the observational
    read path is recorded and ignored so it cannot alter the official evaluator result.
    Exceptions raised by the original interpreter/evaluator are *not* swallowed.
    """
    if type(candidate_seat) is not int or candidate_seat not in (0, 1):
        raise ProducerError("candidate_seat must be exact int 0 or 1")
    if type(seed) is not int or isinstance(seed, bool):
        raise ProducerError("seed must be an exact integer")
    if not hasattr(evaluator, "play") or not callable(evaluator.play):
        raise ProducerError("evaluator.play must be callable")
    original = getattr(engine, "interpreter", None)
    if not callable(original):
        raise ProducerError("engine.interpreter must be callable")

    snapshots: list[dict[str, Any]] = []
    capture_errors: list[str] = []

    def observing_interpreter(state: Any, env: Any) -> Any:
        outcome = original(state, env)
        try:
            snap = _snapshot_public(state, candidate_seat)
            # Initialization has no step yet and is deliberately ignored.  Once a
            # nonnegative step is present, malformed public state is a capture failure.
            has_step = False
            if type(state) is list and len(state) == 2:
                for item in state:
                    try:
                        obs = item.observation
                        raw = obs.get("step") if isinstance(obs, Mapping) else obs.step
                        if raw is not None:
                            has_step = True
                            break
                    except (AttributeError, TypeError):
                        pass
            if snap is not None:
                snapshots.append(snap)
            elif has_step:
                capture_errors.append("malformed public post-step state")
        except Exception as exc:  # observational failures must never alter gameplay
            capture_errors.append(f"capture {type(exc).__name__}: {exc}"[:300])
        return outcome

    engine.interpreter = observing_interpreter
    try:
        result = evaluator.play(
            engine,
            specs,
            cache,
            loader,
            seed,
            candidate_seat,
            **play_kwargs,
        )
    finally:
        engine.interpreter = original

    if type(result) is not dict:
        raise ProducerError("evaluator.play result must be an object")

    complete = result.get("status") == "complete" and _valid_scores(result.get("scores"))
    if not complete:
        raise ProducerError("official evaluator play did not complete with two finite scores")

    result_steps = result.get("steps")
    trace_ok = _valid_trace_sha(result.get("trace_sha256"))
    if type(result_steps) is not int or result_steps < 0:
        trace_ok = False
    expected_steps = list(range(result_steps)) if type(result_steps) is int and result_steps >= 0 else []
    captured_steps = [snap["step"] for snap in snapshots]
    step_domain_ok = captured_steps == expected_steps

    return {
        "result": result,
        "snapshots": snapshots,
        "capture_complete": bool(not capture_errors and trace_ok and step_domain_ok),
        "capture_errors": capture_errors,
        "capture_receipt": {
            "steps_reported": result_steps,
            "steps_captured": len(snapshots),
            "step_domain_ok": step_domain_ok,
            "trace_sha256_present": trace_ok,
        },
    }


def _cell_key(opponent: Any, seed: Any, candidate_seat: Any) -> tuple[str, str, int]:
    if type(opponent) is not str or not opponent.strip():
        raise ProducerError("opponent must be a non-empty string")
    if type(seed) is not int or isinstance(seed, bool):
        raise ProducerError("seed must be an exact integer")
    if type(candidate_seat) is not int or candidate_seat not in (0, 1):
        raise ProducerError("candidate_seat must be exact int 0 or 1")
    return opponent.strip(), str(seed), candidate_seat


def compare_cell(
    opponent: str,
    seed: int,
    candidate_seat: int,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare two captured official plays and prepare one D3 cell receipt."""
    opponent_norm, seed_norm, seat = _cell_key(opponent, seed, candidate_seat)
    if not isinstance(baseline, Mapping) or not isinstance(candidate, Mapping):
        raise ProducerError("baseline and candidate captures must be objects")
    b_result, c_result = baseline.get("result"), candidate.get("result")
    if type(b_result) is not dict or type(c_result) is not dict:
        raise ProducerError("captures must contain evaluator result objects")
    if not _valid_scores(b_result.get("scores")) or not _valid_scores(c_result.get("scores")):
        raise ProducerError("captures must contain two finite player-ordered scores")

    cell = {
        "opponent": opponent_norm,
        "seed": seed_norm,
        "candidate_seat": seat,
        "baseline_scores": list(b_result["scores"]),
        "candidate_scores": list(c_result["scores"]),
    }

    complete = bool(baseline.get("capture_complete") is True and candidate.get("capture_complete") is True)
    b_snaps = baseline.get("snapshots")
    c_snaps = candidate.get("snapshots")
    if type(b_snaps) is not list or type(c_snaps) is not list:
        complete = False
        b_snaps, c_snaps = [], []

    if complete:
        b_steps = [snap.get("step") if isinstance(snap, Mapping) else None for snap in b_snaps]
        c_steps = [snap.get("step") if isinstance(snap, Mapping) else None for snap in c_snaps]
        if b_steps != c_steps:
            complete = False

    events: list[dict[str, Any]] = []
    if complete:
        for b_snap, c_snap in zip(b_snaps, c_snaps):
            if not isinstance(b_snap, Mapping) or not isinstance(c_snap, Mapping):
                complete = False
                break
            step = b_snap.get("step")
            b_prices, c_prices = b_snap.get("prices"), c_snap.get("prices")
            b_supply, c_supply = b_snap.get("rival_supply"), c_snap.get("rival_supply")
            if (
                type(step) is not int
                or type(b_prices) is not dict
                or type(c_prices) is not dict
                or type(b_supply) is not dict
                or type(c_supply) is not dict
            ):
                complete = False
                break
            for product in _PRODUCTS:
                bp, cp = b_prices.get(product), c_prices.get(product)
                bu, cu = b_supply.get(product, 0), c_supply.get(product, 0)
                if (
                    type(bp) is not int
                    or type(cp) is not int
                    or type(bu) is not int
                    or type(cu) is not int
                    or bu < 0
                    or cu < 0
                ):
                    complete = False
                    break
                if cp != bp:
                    events.append(
                        {
                            "event_id": f"{opponent_norm}|{seed_norm}|seat{seat}|step{step}|{product}",
                            "opponent": opponent_norm,
                            "seed": seed_norm,
                            "candidate_seat": seat,
                            "product": product,
                            "source": SOURCE_NAME,
                            "price_delta": cp - bp,
                            "rival_long_units": max(bu, cu),
                        }
                    )
            if not complete:
                break

    if not complete:
        events = []

    return {
        "cell": cell,
        "externality_complete": complete,
        "events": events,
        "coverage": (
            {
                "opponent": opponent_norm,
                "seed": seed_norm,
                "candidate_seat": seat,
                "source": SOURCE_NAME,
                "events_observed": len(events),
            }
            if complete
            else None
        ),
        "producer_receipt": {
            "baseline_trace_sha256": b_result.get("trace_sha256"),
            "candidate_trace_sha256": c_result.get("trace_sha256"),
            "baseline_steps": b_result.get("steps"),
            "candidate_steps": c_result.get("steps"),
            "baseline_capture_complete": baseline.get("capture_complete") is True,
            "candidate_capture_complete": candidate.get("capture_complete") is True,
        },
    }


def assemble_d3_document(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Flatten one or more unique cell receipts into the reviewed D3 schema."""
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or not receipts:
        raise ProducerError("receipts must be a non-empty sequence")
    cells: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    all_complete = True
    producer_receipts: list[dict[str, Any]] = []

    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, Mapping):
            raise ProducerError(f"receipts[{index}] must be an object")
        cell = receipt.get("cell")
        if type(cell) is not dict:
            raise ProducerError(f"receipts[{index}].cell must be an object")
        key = (str(cell.get("opponent")), str(cell.get("seed")), cell.get("candidate_seat"))
        if key in seen:
            raise ProducerError(f"duplicate D3 cell: {key}")
        seen.add(key)
        cells.append(dict(cell))
        producer_receipts.append(dict(receipt.get("producer_receipt") or {}))

        if receipt.get("externality_complete") is not True:
            all_complete = False
            continue
        cov = receipt.get("coverage")
        evs = receipt.get("events")
        if type(cov) is not dict or type(evs) is not list:
            raise ProducerError(f"receipts[{index}] complete receipt is malformed")
        coverage.append(dict(cov))
        events.extend(dict(event) for event in evs)

    document: dict[str, Any] = {
        "cells": cells,
        "externality_complete": all_complete,
        "externality_events": events,
        "producer_receipts": producer_receipts,
    }
    if all_complete:
        document["externality_coverage"] = coverage
    return document
