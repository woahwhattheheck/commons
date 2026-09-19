"""UIOWA-079 record contract; no provider calls or execution of recorded content."""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any


class InvalidRecord(ValueError):
    """A supplied record cannot be interpreted without changing its meaning."""


def obj(**properties: Any) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def arr(items: dict) -> dict:
    return {"type": "array", "items": items}


def nullable(schema: dict) -> dict:
    return {**schema, "type": [schema["type"], "null"]}


TEXT = {"type": "string", "minLength": 1, "pattern": r"[\s\S]*\S[\s\S]*"}
ID = {**TEXT, "maxLength": 160}
WHEN = {"type": "string", "format": "date-time"}
NUMBER = nullable({"type": "number", "minimum": 0})
ARTIFACT = obj(id=ID, kind={"type": "string", "enum": ["prompt", "configuration", "knowledge",
    "dataset", "rubric", "protocol", "output", "investigation"]}, version=TEXT, locator=TEXT,
    captured_at=WHEN, sha256=nullable({"type": "string", "pattern": "^[0-9a-f]{64}$"}),
    content=nullable({"type": "string"}))
VERSION = obj(id=ID, workflow_id=ID, effective_at=WHEN, parent_id=nullable(ID),
    lifecycle={"type": "string", "enum": ["experiment", "in_service", "retired"]},
    support_owner=nullable(TEXT), change_reason=TEXT,
    model=obj(family=TEXT, revision=nullable(TEXT)), prompt_id=ID, config_id=ID, source_ids=arr(ID))
CASE = obj(id=ID, output_id=nullable(ID), passed={"type": ["boolean", "null"]},
    repair_seconds=NUMBER, latency_ms=NUMBER)
RUN = obj(id=ID, version_id=ID, observed_at=WHEN,
    kind={"type": "string", "enum": ["evaluation", "runtime"]}, dataset_id=ID, rubric_id=ID,
    protocol_id=ID, cohort=TEXT, evaluator_revision=TEXT, cases=arr(CASE), notes=TEXT)
COMPARISON = obj(id=ID, baseline_run_id=ID, candidate_run_id=ID)
INCIDENT = obj(id=ID, run_id=ID, case_id=ID, opened_at=WHEN, resolved_at=nullable(WHEN),
    owner=nullable(TEXT), symptom=TEXT, investigation_ids=arr(ID), resolution=nullable(TEXT),
    corrective_version_id=nullable(ID), followup_comparison_id=nullable(ID))
SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "UIOWA-079 AI lifecycle evidence record v1",
    **obj(schema_version={"type": "integer", "const": 1},
          data_status={"type": "string", "enum": ["synthetic", "supplied"]}, as_of=WHEN,
          artifacts=arr(ARTIFACT), versions=arr(VERSION), runs=arr(RUN),
          comparisons=arr(COMPARISON), incidents=arr(INCIDENT))}


def timestamp(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value):
        raise InvalidRecord(f"timezone-aware timestamp required: {value!r}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise InvalidRecord(f"invalid timestamp: {value!r}") from exc


def check(value: Any, schema: dict = SCHEMA, path: str = "$") -> None:
    """Validate this contract's vocabulary, not arbitrary JSON Schema documents.

    All constraints used by SCHEMA are implemented here. Semantic references,
    digest integrity, and chronological consistency are checked in lifecycle.py.
    """
    types = schema["type"]
    types = [types] if isinstance(types, str) else types
    matches = {"null": value is None, "boolean": type(value) is bool,
               "integer": type(value) is int, "number": type(value) in (int, float),
               "string": isinstance(value, str), "array": isinstance(value, list),
               "object": isinstance(value, dict)}
    if not any(matches[t] for t in types):
        raise InvalidRecord(f"{path}: expected {'/'.join(types)}")
    if value is None:
        return
    if "const" in schema and value != schema["const"]:
        raise InvalidRecord(f"{path}: unsupported value {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise InvalidRecord(f"{path}: unsupported value {value!r}")
    if isinstance(value, dict):
        props = schema["properties"]
        missing, extra = set(schema["required"]) - value.keys(), value.keys() - props.keys()
        if missing or extra:
            raise InvalidRecord(f"{path}: missing={sorted(missing)}, unknown={sorted(extra)}")
        for key, sub in props.items():
            check(value[key], sub, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check(item, schema["items"], f"{path}[{index}]")
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", math.inf):
            raise InvalidRecord(f"{path}: invalid string length")
        if "minLength" in schema and not value.strip():
            raise InvalidRecord(f"{path}: blank value")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise InvalidRecord(f"{path}: string does not match required pattern")
        if schema.get("format") == "date-time":
            timestamp(value)
    elif type(value) in (int, float):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite or value < schema.get("minimum", -math.inf):
            raise InvalidRecord(f"{path}: expected finite nonnegative number")
