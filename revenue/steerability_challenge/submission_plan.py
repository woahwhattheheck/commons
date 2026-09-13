"""Preflight plan validator for Steerability Challenge submissions.

The competition Starter Kit remains authoritative.  This module deliberately
validates only the public contract that is knowable before registration:
one shared pipeline structure across three competition models, with model
differences isolated to trained artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

COMPETITION_MODELS: tuple[str, ...] = (
    "google/gemma-4-31B-it",
    "ibm-granite/granite-4.2-30b",
    "Qwen/Qwen3.8-27B",
)
ACCESS_TRACK = {
    "prompt": "black-box",
    "api_output": "black-box",
    "logits": "white-box",
    "activations": "white-box",
    "weights": "open",
}
TRACK_ORDER = {"black-box": 0, "white-box": 1, "open": 2}
TOP_KEYS = frozenset(
    {
        "schema_version",
        "guide_version",
        "toolkit_commit",
        "recipe",
        "models",
        "custom_controls",
        "notes",
    }
)
MODEL_KEYS = frozenset({"spipe_path", "artifacts"})
ARTIFACT_KEYS = frozenset({"path", "sha256", "source", "license"})


class PlanError(ValueError):
    """Raised when a pre-registration plan violates the public challenge contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _artifact_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str) and value.startswith("$artifact:"):
        name = value.split(":", 1)[1].strip()
        if not name:
            raise PlanError("artifact placeholder name cannot be empty")
        refs.add(name)
    elif isinstance(value, Mapping):
        for item in value.values():
            refs.update(_artifact_refs(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            refs.update(_artifact_refs(item))
    return refs


def _validate_sha256(value: Any, *, field: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PlanError(f"{field} must be a 64-character lowercase SHA-256")
    return text


def _validate_recipe(recipe: Any) -> tuple[list[dict[str, Any]], set[str], str]:
    if not isinstance(recipe, list) or not recipe:
        raise PlanError("recipe must be a non-empty list")
    seen_ids: set[str] = set()
    artifact_refs: set[str] = set()
    highest_track = "black-box"
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(recipe):
        if not isinstance(raw, dict):
            raise PlanError(f"recipe[{index}] must be an object")
        allowed = {"id", "method", "access", "params"}
        extra = set(raw) - allowed
        if extra:
            raise PlanError(f"recipe[{index}] has unsupported keys: {sorted(extra)}")
        step_id = str(raw.get("id", "")).strip()
        method = str(raw.get("method", "")).strip()
        access = str(raw.get("access", "")).strip()
        params = raw.get("params", {})
        if not step_id or step_id in seen_ids:
            raise PlanError(f"recipe[{index}].id must be unique and non-empty")
        if not method:
            raise PlanError(f"recipe[{index}].method is required")
        if access not in ACCESS_TRACK:
            raise PlanError(f"recipe[{index}].access must be one of {sorted(ACCESS_TRACK)}")
        if not isinstance(params, dict):
            raise PlanError(f"recipe[{index}].params must be an object")
        seen_ids.add(step_id)
        artifact_refs.update(_artifact_refs(params))
        step_track = ACCESS_TRACK[access]
        if TRACK_ORDER[step_track] > TRACK_ORDER[highest_track]:
            highest_track = step_track
        normalized.append(
            {"id": step_id, "method": method, "access": access, "params": params}
        )
    return normalized, artifact_refs, highest_track


def validate_plan(
    raw: Mapping[str, Any],
    *,
    require_files: bool = False,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PlanError("plan must be a JSON object")
    extra = set(raw) - TOP_KEYS
    if extra:
        raise PlanError(f"unsupported top-level keys: {sorted(extra)}")
    if raw.get("schema_version") != 1:
        raise PlanError("schema_version must be 1")
    guide_version = str(raw.get("guide_version", "")).strip()
    if not guide_version:
        raise PlanError("guide_version is required")
    toolkit_commit = str(raw.get("toolkit_commit", "")).strip().lower()
    if len(toolkit_commit) != 40 or any(ch not in "0123456789abcdef" for ch in toolkit_commit):
        raise PlanError("toolkit_commit must be a full 40-character git SHA")

    recipe, artifact_refs, derived_track = _validate_recipe(raw.get("recipe"))
    models = raw.get("models")
    if not isinstance(models, dict):
        raise PlanError("models must be an object")
    if set(models) != set(COMPETITION_MODELS):
        missing = sorted(set(COMPETITION_MODELS) - set(models))
        extra_models = sorted(set(models) - set(COMPETITION_MODELS))
        raise PlanError(f"model set mismatch missing={missing} extra={extra_models}")

    root = Path(base_dir) if base_dir is not None else Path.cwd()
    model_rows: dict[str, Any] = {}
    for model in COMPETITION_MODELS:
        entry = models[model]
        if not isinstance(entry, dict):
            raise PlanError(f"models[{model!r}] must be an object")
        extra_keys = set(entry) - MODEL_KEYS
        if extra_keys:
            raise PlanError(
                f"models[{model!r}] may contain only spipe_path/artifacts; "
                f"model-specific recipe overrides are forbidden: {sorted(extra_keys)}"
            )
        spipe_path = str(entry.get("spipe_path", "")).strip()
        if not spipe_path.endswith(".spipe"):
            raise PlanError(f"models[{model!r}].spipe_path must end in .spipe")
        artifacts = entry.get("artifacts", {})
        if not isinstance(artifacts, dict):
            raise PlanError(f"models[{model!r}].artifacts must be an object")
        if set(artifacts) != artifact_refs:
            missing = sorted(artifact_refs - set(artifacts))
            unused = sorted(set(artifacts) - artifact_refs)
            raise PlanError(
                f"models[{model!r}] artifact bindings mismatch missing={missing} unused={unused}"
            )
        normalized_artifacts: dict[str, Any] = {}
        for name in sorted(artifacts):
            artifact = artifacts[name]
            if not isinstance(artifact, dict):
                raise PlanError(f"artifact {model}:{name} must be an object")
            unknown = set(artifact) - ARTIFACT_KEYS
            if unknown:
                raise PlanError(f"artifact {model}:{name} unsupported keys: {sorted(unknown)}")
            path = str(artifact.get("path", "")).strip()
            source = str(artifact.get("source", "")).strip()
            license_name = str(artifact.get("license", "")).strip()
            if not path or not source or not license_name:
                raise PlanError(f"artifact {model}:{name} requires path/source/license")
            sha256 = _validate_sha256(artifact.get("sha256"), field=f"artifact {model}:{name}.sha256")
            normalized_artifacts[name] = {
                "path": path,
                "sha256": sha256,
                "source": source,
                "license": license_name,
            }
            if require_files:
                file_path = root / path
                if not file_path.is_file():
                    raise PlanError(f"artifact file missing: {file_path}")
                digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if digest != sha256:
                    raise PlanError(f"artifact hash mismatch: {file_path}")
        if require_files:
            if not (root / spipe_path).is_file():
                raise PlanError(f".spipe file missing: {root / spipe_path}")
        model_rows[model] = {"spipe_path": spipe_path, "artifacts": normalized_artifacts}

    controls = raw.get("custom_controls", [])
    if not isinstance(controls, list) or any(not isinstance(item, str) or not item.strip() for item in controls):
        raise PlanError("custom_controls must be a list of non-empty source paths")
    signature = hashlib.sha256(_canonical_json(recipe).encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "schema_version": 1,
        "guide_version": guide_version,
        "toolkit_commit": toolkit_commit,
        "competition_models": list(COMPETITION_MODELS),
        "recipe": recipe,
        "recipe_structure_sha256": signature,
        "derived_track": derived_track,
        "artifact_placeholders": sorted(artifact_refs),
        "models": model_rows,
        "custom_controls": list(controls),
        "starter_kit_checker_still_required": True,
    }


def load_plan(path: str | Path, *, require_files: bool = False) -> dict[str, Any]:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanError(f"invalid plan JSON: {source}") from exc
    return validate_plan(raw, require_files=require_files, base_dir=source.parent)
