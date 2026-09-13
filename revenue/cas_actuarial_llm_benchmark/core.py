# SPDX-License-Identifier: MPL-2.0
"""Deterministic evidence core for a CAS-style actuarial LLM perception benchmark.

This module is deliberately offline. It validates benchmark/task/data/run evidence,
computes objective metrics, and emits a content-addressed comparison snapshot. It
does not call model providers and does not assert actuarial validity of task content.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import re
from typing import Any


class BenchmarkInputError(ValueError):
    """Raised when benchmark evidence is malformed, ambiguous, or incomplete."""


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,127}$")
_REQUIRED_COMMERCIAL = frozenset({"openai", "anthropic", "google"})
_SUPPORTED_TASK_TYPES = frozenset({"binary", "multiclass"})


def _canon(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BenchmarkInputError("evidence must be canonical JSON without non-finite values") from exc
    return text.encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _plain_key(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise BenchmarkInputError(f"{field} must be a string")
    value = value.strip()
    if not _KEY_RE.fullmatch(value):
        raise BenchmarkInputError(f"{field} must be a stable lowercase key")
    return value


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise BenchmarkInputError(f"{field} must be a lowercase sha256 hex digest")
    return value


def _nonempty(value: Any, field: str, *, max_len: int = 512) -> str:
    if not isinstance(value, str):
        raise BenchmarkInputError(f"{field} must be a string")
    value = value.strip()
    if not value or len(value) > max_len:
        raise BenchmarkInputError(f"{field} must be non-empty and <= {max_len} characters")
    return value


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise BenchmarkInputError(f"{field} must be boolean")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise BenchmarkInputError(f"{field} must be numeric")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise BenchmarkInputError(f"{field} must be decimal text") from exc
        if not result.is_finite():
            raise BenchmarkInputError(f"{field} must be finite")
        return result
    raise BenchmarkInputError(f"{field} must be integer or exact decimal string")


def _ratio(value: Any, field: str) -> Decimal:
    result = _decimal(value, field)
    if result < 0 or result > 1:
        raise BenchmarkInputError(f"{field} must be within [0, 1]")
    return result


def _task(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BenchmarkInputError("each task must be an object")
    task_id = _plain_key(raw.get("task_id"), "task_id")
    version = _plain_key(raw.get("version"), "task version")
    task_type = raw.get("task_type")
    if task_type not in _SUPPORTED_TASK_TYPES:
        raise BenchmarkInputError("task_type must be binary or multiclass")
    labels_raw = raw.get("labels")
    if not isinstance(labels_raw, list) or len(labels_raw) < 2:
        raise BenchmarkInputError("task labels must contain at least two labels")
    labels = [_plain_key(label, "label") for label in labels_raw]
    if len(set(labels)) != len(labels):
        raise BenchmarkInputError("task labels must be unique")
    if task_type == "binary" and len(labels) != 2:
        raise BenchmarkInputError("binary tasks must have exactly two labels")
    dataset = raw.get("dataset")
    if not isinstance(dataset, dict):
        raise BenchmarkInputError("task dataset must be an object")
    dataset_sha256 = _sha(dataset.get("sha256"), "dataset sha256")
    split_sha256 = _sha(dataset.get("split_sha256"), "dataset split_sha256")
    license_status = dataset.get("license_status")
    if license_status != "confirmed_publishable":
        raise BenchmarkInputError("dataset license_status must be confirmed_publishable")
    license_reference = _nonempty(dataset.get("license_reference"), "license_reference")
    provenance = _nonempty(dataset.get("provenance"), "dataset provenance", max_len=1024)
    source_uri = _nonempty(dataset.get("source_uri"), "dataset source_uri", max_len=1024)
    if not source_uri.startswith("https://"):
        raise BenchmarkInputError("dataset source_uri must use https")
    return {
        "task_id": task_id,
        "version": version,
        "task_type": task_type,
        "labels": labels,
        "dataset": {
            "sha256": dataset_sha256,
            "split_sha256": split_sha256,
            "license_status": license_status,
            "license_reference": license_reference,
            "provenance": provenance,
            "source_uri": source_uri,
        },
    }


def _model(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BenchmarkInputError("each model must be an object")
    model_id = _plain_key(raw.get("model_id"), "model_id")
    model_version = _nonempty(raw.get("model_version"), "model_version")
    model_class = raw.get("model_class")
    if model_class not in {"commercial", "open"}:
        raise BenchmarkInputError("model_class must be commercial or open")
    provider = _plain_key(raw.get("provider"), "provider")
    artifact_sha256 = _sha(raw.get("artifact_sha256"), "model artifact_sha256")
    return {
        "model_id": model_id,
        "model_version": model_version,
        "model_class": model_class,
        "provider": provider,
        "artifact_sha256": artifact_sha256,
    }


def _normalize_probabilities(raw: Any, labels: list[str], field: str) -> dict[str, Decimal]:
    if not isinstance(raw, dict) or set(raw) != set(labels):
        raise BenchmarkInputError(f"{field} must provide exactly every task label")
    probs = {label: _ratio(raw[label], f"{field}.{label}") for label in labels}
    total = sum(probs.values(), Decimal(0))
    if total != Decimal(1):
        raise BenchmarkInputError(f"{field} probabilities must sum exactly to 1")
    return probs


def _run(raw: Any, task: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BenchmarkInputError("each run must be an object")
    run_id = _plain_key(raw.get("run_id"), "run_id")
    if raw.get("task_id") != task["task_id"] or raw.get("task_version") != task["version"]:
        raise BenchmarkInputError("run task identity/version does not match task manifest")
    if raw.get("dataset_sha256") != task["dataset"]["sha256"]:
        raise BenchmarkInputError("run dataset digest does not match task manifest")
    if raw.get("split_sha256") != task["dataset"]["split_sha256"]:
        raise BenchmarkInputError("run split digest does not match task manifest")
    if raw.get("model_id") != model["model_id"] or raw.get("model_version") != model["model_version"]:
        raise BenchmarkInputError("run model identity/version does not match model roster")
    if raw.get("model_artifact_sha256") != model["artifact_sha256"]:
        raise BenchmarkInputError("run model artifact digest does not match model roster")
    protocol_sha256 = _sha(raw.get("protocol_sha256"), "protocol_sha256")
    records = raw.get("records")
    if not isinstance(records, list) or not records:
        raise BenchmarkInputError("run records must be a non-empty list")
    seen: set[str] = set()
    normalized_records: list[dict[str, Any]] = []
    labels = task["labels"]
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise BenchmarkInputError("run record must be an object")
        item_id = _plain_key(record.get("item_id"), f"records[{index}].item_id")
        if item_id in seen:
            raise BenchmarkInputError("run item_id values must be unique")
        seen.add(item_id)
        truth = record.get("truth")
        prediction = record.get("prediction")
        if truth not in labels or prediction not in labels:
            raise BenchmarkInputError("truth/prediction must be declared task labels")
        probabilities = _normalize_probabilities(
            record.get("probabilities"),
            labels,
            f"records[{index}].probabilities",
        )
        normalized_records.append(
            {
                "item_id": item_id,
                "truth": truth,
                "prediction": prediction,
                "probabilities": probabilities,
            }
        )
    return {
        "run_id": run_id,
        "protocol_sha256": protocol_sha256,
        "records": normalized_records,
    }


def _macro_f1(records: list[dict[str, Any]], labels: list[str]) -> Decimal:
    scores: list[Decimal] = []
    for label in labels:
        tp = sum(r["truth"] == label and r["prediction"] == label for r in records)
        fp = sum(r["truth"] != label and r["prediction"] == label for r in records)
        fn = sum(r["truth"] == label and r["prediction"] != label for r in records)
        denom = (2 * tp) + fp + fn
        scores.append(Decimal(0) if denom == 0 else Decimal(2 * tp) / Decimal(denom))
    return sum(scores, Decimal(0)) / Decimal(len(scores))


def _metrics(task: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, str]:
    labels = task["labels"]
    count = Decimal(len(records))
    accuracy = Decimal(sum(r["truth"] == r["prediction"] for r in records)) / count
    macro_f1 = _macro_f1(records, labels)
    with localcontext() as ctx:
        ctx.prec = 50
        brier_total = Decimal(0)
        log_loss_total = Decimal(0)
        for record in records:
            for label in labels:
                target = Decimal(1) if record["truth"] == label else Decimal(0)
                delta = record["probabilities"][label] - target
                brier_total += delta * delta
            p_true = record["probabilities"][record["truth"]]
            if p_true == 0:
                log_loss_total = Decimal("Infinity")
            elif log_loss_total.is_finite():
                log_loss_total -= p_true.ln()
        # multiclass Brier is sum of squared errors per item; binary is normalized by
        # two labels so the familiar [0,1] range is retained.
        brier = brier_total / count
        if task["task_type"] == "binary":
            brier /= Decimal(2)
        log_loss = log_loss_total / count if log_loss_total.is_finite() else log_loss_total

    def render(value: Decimal) -> str:
        if not value.is_finite():
            return "Infinity"
        return format(value.quantize(Decimal("0.000000000001")), "f")

    return {
        "accuracy": render(accuracy),
        "macro_f1": render(macro_f1),
        "brier_score": render(brier),
        "log_loss": render(log_loss),
    }


def evaluate_benchmark(evidence: dict[str, Any]) -> dict[str, Any]:
    """Validate benchmark evidence and return a content-addressed comparison snapshot."""
    if not isinstance(evidence, dict):
        raise BenchmarkInputError("evidence must be an object")
    schema_version = evidence.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise BenchmarkInputError("schema_version must be integer 1")
    governance = evidence.get("governance")
    if not isinstance(governance, dict):
        raise BenchmarkInputError("governance must be an object")
    if governance.get("update_policy") != "versioned_no_silent_mutation":
        raise BenchmarkInputError("update_policy must be versioned_no_silent_mutation")
    if governance.get("task_authority") != "qualified_actuarial_reviewer":
        raise BenchmarkInputError("task_authority must remain with qualified_actuarial_reviewer")
    if governance.get("benchmark_license") != "MPL-2.0":
        raise BenchmarkInputError("benchmark_license must be MPL-2.0")

    tasks_raw = evidence.get("tasks")
    models_raw = evidence.get("models")
    runs_raw = evidence.get("runs")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise BenchmarkInputError("tasks must be a non-empty list")
    if not isinstance(models_raw, list) or not models_raw:
        raise BenchmarkInputError("models must be a non-empty list")
    if not isinstance(runs_raw, list):
        raise BenchmarkInputError("runs must be a list")

    tasks = [_task(raw) for raw in tasks_raw]
    models = [_model(raw) for raw in models_raw]
    task_keys = [(t["task_id"], t["version"]) for t in tasks]
    if len(task_keys) != len(set(task_keys)):
        raise BenchmarkInputError("task id/version pairs must be unique")
    model_ids = [m["model_id"] for m in models]
    if len(model_ids) != len(set(model_ids)):
        raise BenchmarkInputError("model_id values must be unique")

    commercial = {m["provider"] for m in models if m["model_class"] == "commercial"}
    missing_commercial = sorted(_REQUIRED_COMMERCIAL - commercial)
    open_models = [m for m in models if m["model_class"] == "open"]
    if missing_commercial:
        raise BenchmarkInputError(
            "commercial roster must include provider families: " + ",".join(missing_commercial)
        )
    if len({m["model_id"] for m in open_models}) < 3:
        raise BenchmarkInputError("roster must include at least three distinct open models")

    task_by_key = {(t["task_id"], t["version"]): t for t in tasks}
    model_by_id = {m["model_id"]: m for m in models}
    normalized_runs: list[dict[str, Any]] = []
    run_pairs: set[tuple[str, str, str]] = set()
    run_ids: set[str] = set()
    for raw in runs_raw:
        if not isinstance(raw, dict):
            raise BenchmarkInputError("each run must be an object")
        key = (raw.get("task_id"), raw.get("task_version"))
        task = task_by_key.get(key)
        if task is None:
            raise BenchmarkInputError("run references unknown task id/version")
        model = model_by_id.get(raw.get("model_id"))
        if model is None:
            raise BenchmarkInputError("run references unknown model_id")
        normalized = _run(raw, task, model)
        if normalized["run_id"] in run_ids:
            raise BenchmarkInputError("run_id values must be unique")
        run_ids.add(normalized["run_id"])
        pair = (model["model_id"], task["task_id"], task["version"])
        if pair in run_pairs:
            raise BenchmarkInputError("model/task pair must appear exactly once")
        run_pairs.add(pair)
        normalized_runs.append(
            {
                "run_id": normalized["run_id"],
                "model_id": model["model_id"],
                "model_version": model["model_version"],
                "model_class": model["model_class"],
                "provider": model["provider"],
                "task_id": task["task_id"],
                "task_version": task["version"],
                "dataset_sha256": task["dataset"]["sha256"],
                "split_sha256": task["dataset"]["split_sha256"],
                "protocol_sha256": normalized["protocol_sha256"],
                "record_count": len(normalized["records"]),
                "metrics": _metrics(task, normalized["records"]),
            }
        )

    expected_pairs = {
        (m["model_id"], t["task_id"], t["version"])
        for m in models
        for t in tasks
    }
    missing_pairs = sorted(expected_pairs - run_pairs)
    if missing_pairs:
        raise BenchmarkInputError(
            f"benchmark matrix incomplete: {len(missing_pairs)} model/task runs missing"
        )

    normalized_runs.sort(key=lambda r: (r["task_id"], r["task_version"], r["model_id"]))
    safe_tasks = sorted(tasks, key=lambda t: (t["task_id"], t["version"]))
    safe_models = sorted(models, key=lambda m: m["model_id"])
    snapshot = {
        "schema_version": 1,
        "status": "PROPOSAL_TECHNICAL_EVIDENCE_READY",
        "authority": {
            "actuarial_task_validity": False,
            "cas_submission": False,
            "model_provider_action": False,
            "contract": False,
            "payment": False,
            "recognized_revenue": False,
        },
        "governance": {
            "update_policy": governance["update_policy"],
            "task_authority": governance["task_authority"],
            "benchmark_license": governance["benchmark_license"],
        },
        "tasks": safe_tasks,
        "models": safe_models,
        "runs": normalized_runs,
        "signals": {
            "task_count": len(tasks),
            "model_count": len(models),
            "commercial_provider_families": sorted(commercial),
            "open_model_count": len(open_models),
            "run_count": len(normalized_runs),
            "matrix_complete": True,
            "all_datasets_confirmed_publishable": True,
        },
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    return snapshot


def verify_snapshot(snapshot: dict[str, Any]) -> bool:
    """Verify content-addressed integrity of an emitted snapshot."""
    if not isinstance(snapshot, dict):
        return False
    claimed = snapshot.get("snapshot_sha256")
    if not isinstance(claimed, str) or not _SHA256_RE.fullmatch(claimed):
        return False
    body = dict(snapshot)
    body.pop("snapshot_sha256", None)
    return hashlib.sha256(_canon(body)).hexdigest() == claimed
