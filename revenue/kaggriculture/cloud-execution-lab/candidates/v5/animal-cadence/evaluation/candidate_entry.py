# SPDX-License-Identifier: Apache-2.0
"""Evaluation-only current-V5 entrypoint with the animal-cadence candidate.

This module is copied beside an *unchanged* canonical current archive.  It calls
that archive's main.py first, then—only after a fully completed runtime action—
asks the source-pinned certificate authority for one admissible day-close
certificate and applies the published pure transform.  Any malformed context,
source/profile drift, deadline fallback, authority decline, or local exception
returns the canonical action unchanged.

Per-game engagement counters are written next to this file for the matched
runner.  They are evidence only and are never policy input.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
METRICS = HERE / "animal-cadence-eval-metrics.json"
_STATE = None


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _modules():
    global _STATE
    if _STATE is None:
        baseline = _load("_cadence_eval_baseline", HERE / "main.py")
        source = HERE / "candidates" / "v5" / "animal-cadence"
        builder = _load("_cadence_eval_builder", source / "certificate_builder.py")
        candidate = _load("_cadence_eval_candidate", source / "alternate_feed.py")
        _STATE = (baseline, builder, candidate)
    return _STATE


def _fresh_metrics(step):
    return {
        "schema": "titan-v5/animal-cadence/matched-eval-agent-metrics/v1",
        "last_step": step,
        "calls": 0,
        "completed_calls": 0,
        "authority_engagements": 0,
        "candidate_engagements": 0,
        "feed_actions_suppressed": 0,
        "unique_tile_wheat_saved": 0,
        "authority_declines": {},
        "candidate_declines": {},
        "errors": {},
        "engagement_steps": [],
    }


def _read_metrics(step):
    if step == 0 or not METRICS.is_file():
        return _fresh_metrics(step)
    try:
        value = json.loads(METRICS.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return _fresh_metrics(step)
    if not isinstance(value, dict) or value.get("schema") != "titan-v5/animal-cadence/matched-eval-agent-metrics/v1":
        return _fresh_metrics(step)
    return value


def _write_metrics(value):
    temp = METRICS.with_suffix(".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(METRICS)


def _bump(mapping, key):
    key = str(key or "unknown")
    mapping[key] = int(mapping.get(key, 0)) + 1


def _feature_profile(instance, builder):
    features = getattr(instance, "features", None)
    profile = {}
    for name in builder._REQUIRED_FEATURES:
        if name == "town_procurement":
            profile[name] = bool(getattr(instance, "town_procurement_enabled", False))
        else:
            profile[name] = getattr(features, name, None)
    return profile


def agent(observation, configuration=None):
    baseline, builder, candidate = _modules()
    step = observation.get("step") if isinstance(observation, dict) else getattr(observation, "step", None)
    step = step if type(step) is int and step >= 0 else -1
    metrics = _read_metrics(step)
    metrics["calls"] += 1
    metrics["last_step"] = step

    # Canonical action always exists before candidate work begins.
    selected = baseline.agent(observation, configuration)
    instance = getattr(baseline, "_INSTANCE", None)
    diagnostics = getattr(instance, "diagnostics", {}) if instance is not None else {}
    completed = isinstance(diagnostics, dict) and diagnostics.get("status") == "completed"
    if not completed:
        _bump(metrics["authority_declines"], "runtime_action_not_completed")
        _write_metrics(metrics)
        return selected
    metrics["completed_calls"] += 1

    try:
        controller = getattr(instance, "controller", None)
        profile = _feature_profile(instance, builder)
        route_identity, certificate, authority = builder.build_next_feed_certificate(
            observation, selected, configuration or {}, controller, profile, completed=True)
        reason = authority.get("reason") if isinstance(authority, dict) else "malformed_authority_report"
        if not isinstance(authority, dict) or not authority.get("certified"):
            _bump(metrics["authority_declines"], reason)
            _write_metrics(metrics)
            return selected
        metrics["authority_engagements"] += 1
        transformed, report = candidate.apply_alternate_feed(
            observation,
            selected,
            next_feed_certificate=certificate,
            route_identity=route_identity,
            turns_per_day=(configuration or {}).get("turnsPerDay", 24),
        )
        if not isinstance(report, dict) or not report.get("changed"):
            _bump(metrics["candidate_declines"], report.get("reason") if isinstance(report, dict) else "malformed_candidate_report")
            _write_metrics(metrics)
            return selected
        metrics["candidate_engagements"] += 1
        metrics["feed_actions_suppressed"] += int(report.get("feed_actions_suppressed", 0))
        metrics["unique_tile_wheat_saved"] += int(report.get("wheat_saved", 0))
        metrics["engagement_steps"].append({
            "step": step,
            "position": authority.get("candidate_position"),
            "route_id": route_identity.get("route_id") if isinstance(route_identity, dict) else None,
            "tail_sha256": route_identity.get("tail_sha256") if isinstance(route_identity, dict) else None,
            "feed_actions_suppressed": int(report.get("feed_actions_suppressed", 0)),
            "wheat_saved": int(report.get("wheat_saved", 0)),
        })
        _write_metrics(metrics)
        return transformed
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, AttributeError, OSError, RuntimeError) as error:
        _bump(metrics["errors"], f"{type(error).__name__}:{error}")
        _write_metrics(metrics)
        return selected
