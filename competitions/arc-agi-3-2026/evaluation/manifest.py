"""Strict manifest codec for paired SAGE experiments."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Mapping

from .core import ExperimentSpec, canonical_json


def load_manifest(path: str | Path) -> tuple[ExperimentSpec, ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"schema", "experiments"}:
        raise ValueError("manifest requires exactly schema + experiments")
    if raw["schema"] != "arc3-sage-experiment-manifest/v1":
        raise ValueError("unsupported experiment manifest schema")
    rows = raw["experiments"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("experiments must be a non-empty list")
    specs = tuple(ExperimentSpec(**row) for row in rows)
    if len({spec.hypothesis for spec in specs}) != len(specs):
        raise ValueError("duplicate hypothesis in manifest")
    return specs


def write_manifest(path: str | Path, specs: tuple[ExperimentSpec, ...]) -> None:
    if not specs:
        raise ValueError("cannot write empty manifest")
    obj: Mapping[str, object] = {
        "schema": "arc3-sage-experiment-manifest/v1",
        "experiments": [asdict(spec) for spec in specs],
    }
    Path(path).write_text(canonical_json(obj) + "\n", encoding="utf-8")
