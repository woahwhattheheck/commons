from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .model import DOMAIN_MODEL, DOMAINS, STAGE_MODEL, STAGES

SCHEMA = "loadlight-intake/v1"
REPORT_SCHEMA = "loadlight-report/v1"
STAGE_WEIGHTS = {
    "anticipate": 1.30,
    "plan": 1.40,
    "decide": 1.20,
    "monitor": 1.50,
    "execute": 1.00,
}
COGNITIVE_STAGES = {"anticipate", "plan", "decide", "monitor"}


class IntakeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, label: str, *, maximum: int = 500) -> str:
    if type(value) is not str or not value.strip():
        raise IntakeError(f"{label} must be a non-empty string")
    out = value.strip()
    if len(out) > maximum:
        raise IntakeError(f"{label} exceeds {maximum} characters")
    return out


def _number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise IntakeError(f"{label} must be numeric")
    out = float(value)
    if not 0 < out <= 24 * 60:
        raise IntakeError(f"{label} must be in (0, 1440]")
    return out


def _time(value: Any, label: str) -> str | None:
    if value in (None, ""):
        return None
    text = _text(value, label, maximum=64)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise IntakeError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IntakeError(f"{label} must include timezone")
    return parsed.isoformat()


def _parse_intake(raw: Any) -> tuple[list[str], list[dict[str, Any]]]:
    if type(raw) is not dict:
        raise IntakeError("intake must be an object")
    allowed = {"schema", "household_id", "actors", "items"}
    extra = sorted(set(raw) - allowed)
    if extra:
        raise IntakeError(f"unknown intake fields: {', '.join(extra)}")
    if raw.get("schema") != SCHEMA:
        raise IntakeError(f"schema must be {SCHEMA}")
    _text(raw.get("household_id"), "household_id")
    actors_raw = raw.get("actors")
    if type(actors_raw) is not list or len(actors_raw) < 2 or len(actors_raw) > 8:
        raise IntakeError("actors must be a list of 2..8 names")
    actors = [_text(a, "actor", maximum=80) for a in actors_raw]
    if len(set(actors)) != len(actors):
        raise IntakeError("actors must be unique")
    items_raw = raw.get("items")
    if type(items_raw) is not list or not items_raw or len(items_raw) > 5000:
        raise IntakeError("items must be a non-empty list of at most 5000")
    ids: set[str] = set()
    items: list[dict[str, Any]] = []
    for index, item_raw in enumerate(items_raw):
        if type(item_raw) is not dict:
            raise IntakeError(f"items[{index}] must be an object")
        allowed_item = {"id", "task", "text", "actor", "effort_minutes", "stage", "domain", "due_at"}
        extra_item = sorted(set(item_raw) - allowed_item)
        if extra_item:
            raise IntakeError(f"items[{index}] unknown fields: {', '.join(extra_item)}")
        item_id = _text(item_raw.get("id"), f"items[{index}].id", maximum=120)
        if item_id in ids:
            raise IntakeError(f"duplicate item id: {item_id}")
        ids.add(item_id)
        actor = _text(item_raw.get("actor"), f"items[{index}].actor", maximum=80)
        if actor not in actors:
            raise IntakeError(f"items[{index}].actor is not in actors")
        text = _text(item_raw.get("text"), f"items[{index}].text")
        task = _text(item_raw.get("task"), f"items[{index}].task", maximum=160)
        effort = _number(item_raw.get("effort_minutes"), f"items[{index}].effort_minutes")
        stage_source = "human"
        stage = item_raw.get("stage")
        if stage in (None, ""):
            pred = STAGE_MODEL.predict(text)
            stage = pred.label
            stage_conf = round(pred.confidence, 6)
            stage_source = "local_nb"
        else:
            stage = _text(stage, f"items[{index}].stage", maximum=30).lower()
            if stage not in STAGES:
                raise IntakeError(f"items[{index}].stage unsupported")
            stage_conf = 1.0
        domain_source = "human"
        domain = item_raw.get("domain")
        if domain in (None, ""):
            pred = DOMAIN_MODEL.predict(text)
            domain = pred.label
            domain_conf = round(pred.confidence, 6)
            domain_source = "local_nb"
        else:
            domain = _text(domain, f"items[{index}].domain", maximum=30).lower()
            if domain not in DOMAINS:
                raise IntakeError(f"items[{index}].domain unsupported")
            domain_conf = 1.0
        items.append({
            "id": item_id,
            "task": task,
            "actor": actor,
            "effort_minutes": effort,
            "stage": stage,
            "stage_source": stage_source,
            "stage_confidence": stage_conf,
            "domain": domain,
            "domain_source": domain_source,
            "domain_confidence": domain_conf,
            "due_at": _time(item_raw.get("due_at"), f"items[{index}].due_at"),
            "source_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return actors, items


def analyze(raw: Any) -> dict[str, Any]:
    actors, items = _parse_intake(raw)
    by_actor = {
        actor: {
            "weighted_units": 0.0,
            "cognitive_units": 0.0,
            "execution_units": 0.0,
            "item_count": 0,
            "stage_units": {stage: 0.0 for stage in STAGES},
        }
        for actor in actors
    }
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized: list[dict[str, Any]] = []
    for item in items:
        units = item["effort_minutes"] * STAGE_WEIGHTS[item["stage"]]
        units = round(units, 3)
        row = dict(item)
        row["weighted_units"] = units
        normalized.append(row)
        bucket = by_actor[item["actor"]]
        bucket["weighted_units"] += units
        bucket["item_count"] += 1
        bucket["stage_units"][item["stage"]] += units
        if item["stage"] in COGNITIVE_STAGES:
            bucket["cognitive_units"] += units
        else:
            bucket["execution_units"] += units
        by_task[item["task"]].append(row)

    total_cognitive = sum(v["cognitive_units"] for v in by_actor.values())
    total_units = sum(v["weighted_units"] for v in by_actor.values())
    for actor in actors:
        bucket = by_actor[actor]
        for key in ("weighted_units", "cognitive_units", "execution_units"):
            bucket[key] = round(bucket[key], 3)
        bucket["stage_units"] = {k: round(v, 3) for k, v in bucket["stage_units"].items()}
        bucket["cognitive_share"] = round(bucket["cognitive_units"] / total_cognitive, 6) if total_cognitive else 0.0
        bucket["total_share"] = round(bucket["weighted_units"] / total_units, 6) if total_units else 0.0

    least_loaded = sorted(actors, key=lambda a: (by_actor[a]["cognitive_units"], a))
    handoffs: list[dict[str, Any]] = []
    for task, task_items in sorted(by_task.items()):
        cognitive = [row for row in task_items if row["stage"] in COGNITIVE_STAGES]
        if len(cognitive) < 2:
            continue
        units_by_actor: dict[str, float] = defaultdict(float)
        stages_by_actor: dict[str, set[str]] = defaultdict(set)
        for row in cognitive:
            units_by_actor[row["actor"]] += row["weighted_units"]
            stages_by_actor[row["actor"]].add(row["stage"])
        total = sum(units_by_actor.values())
        primary = max(units_by_actor, key=lambda a: (units_by_actor[a], a))
        share = units_by_actor[primary] / total if total else 0.0
        if share < 0.70 or len(stages_by_actor[primary]) < 2:
            continue
        recipient = next((a for a in least_loaded if a != primary), None)
        if recipient is None:
            continue
        transferable = sorted(stages_by_actor[primary], key=lambda s: (STAGE_WEIGHTS[s], s), reverse=True)
        handoffs.append({
            "task": task,
            "from_actor": primary,
            "to_actor": recipient,
            "current_cognitive_share": round(share, 6),
            "candidate_stage": transferable[0],
            "reason": "multiple cognitive stages are concentrated with one actor; offer an explicit handoff",
            "authority": "suggestion_only",
        })

    report = {
        "schema": REPORT_SCHEMA,
        "household_id_sha256": hashlib.sha256(_text(raw.get("household_id"), "household_id").encode("utf-8")).hexdigest(),
        "actors": actors,
        "actor_metrics": by_actor,
        "handoff_candidates": handoffs,
        "classified_items": normalized,
        "privacy": {
            "raw_text_emitted": False,
            "source_text_represented_by_sha256": True,
            "medical_or_mental_health_inference": False,
            "safety_decisioning": False,
        },
        "interpretation": {
            "is_moral_fairness_score": False,
            "purpose": "make cognitive coordination work visible and easier to hand off",
            "human_review_required": True,
        },
    }
    report["report_sha256"] = _digest(report)
    return report
