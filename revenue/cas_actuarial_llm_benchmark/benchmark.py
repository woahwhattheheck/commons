#!/usr/bin/env python3
"""Deterministic scorer for the CAS actuarial-perception benchmark demonstrator.

The demo is deliberately provider-neutral and stdlib-only.  It scores closed-label
perception/classification tasks with accuracy, macro-F1, multiclass Brier score,
and log loss, while binding every result to the exact canonical benchmark bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

SCORER_VERSION = "cas-perception-demo/1.0.0"
ALLOWED_METRICS = ("accuracy", "macro_f1", "brier", "log_loss")


class BenchmarkError(ValueError):
    """Raised when benchmark or prediction material violates the contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _strict_probability(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise BenchmarkError(f"{field} must be finite and in [0, 1]")
    return number


def validate_benchmark(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise BenchmarkError("benchmark must be an object")
    if set(document) != {"benchmark_id", "license", "provenance", "tasks"}:
        raise BenchmarkError("benchmark has unexpected top-level keys")
    if document["license"] != "CC0-1.0":
        raise BenchmarkError("demo fixtures must be publishable under CC0-1.0")
    provenance = document["provenance"]
    if not isinstance(provenance, dict) or provenance.get("kind") != "project-authored-synthetic":
        raise BenchmarkError("demo provenance must be project-authored-synthetic")
    if provenance.get("contains_real_claims") is not False:
        raise BenchmarkError("demo may not claim to contain real insurance records")
    tasks = document["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise BenchmarkError("tasks must be a non-empty list")

    seen: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise BenchmarkError(f"task[{index}] must be an object")
        required = {"id", "category", "task_type", "prompt", "labels", "gold_label"}
        if set(task) != required:
            raise BenchmarkError(f"task[{index}] has unexpected keys")
        task_id = task["id"]
        if not isinstance(task_id, str) or not task_id:
            raise BenchmarkError(f"task[{index}].id must be non-empty")
        if task_id in seen:
            raise BenchmarkError(f"duplicate task id: {task_id}")
        seen.add(task_id)
        if task["task_type"] != "classification":
            raise BenchmarkError(f"task {task_id} is not an objective classification task")
        labels = task["labels"]
        if (
            not isinstance(labels, list)
            or len(labels) < 2
            or any(not isinstance(label, str) or not label for label in labels)
            or len(set(labels)) != len(labels)
        ):
            raise BenchmarkError(f"task {task_id} labels must be unique non-empty strings")
        if task["gold_label"] not in labels:
            raise BenchmarkError(f"task {task_id} gold label is not in labels")
        if not isinstance(task["category"], str) or not task["category"]:
            raise BenchmarkError(f"task {task_id} category must be non-empty")
        if not isinstance(task["prompt"], str) or not task["prompt"].strip():
            raise BenchmarkError(f"task {task_id} prompt must be non-empty")
    return json.loads(canonical_json(document))


def validate_predictions(predictions: Any, benchmark: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(predictions, list):
        raise BenchmarkError("predictions must be a list")
    tasks = {task["id"]: task for task in benchmark["tasks"]}
    if len(predictions) != len(tasks):
        raise BenchmarkError("predictions must contain exactly one row per task")

    rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(predictions):
        if not isinstance(row, dict) or set(row) != {"task_id", "label", "probabilities"}:
            raise BenchmarkError(f"prediction[{index}] has unexpected keys")
        task_id = row["task_id"]
        if task_id not in tasks:
            raise BenchmarkError(f"prediction references unknown task: {task_id}")
        if task_id in rows:
            raise BenchmarkError(f"duplicate prediction for task: {task_id}")
        task = tasks[task_id]
        labels = task["labels"]
        if row["label"] not in labels:
            raise BenchmarkError(f"prediction label for {task_id} is outside task labels")
        probabilities = row["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != set(labels):
            raise BenchmarkError(f"prediction probabilities for {task_id} must cover labels exactly")
        normalized = {
            label: _strict_probability(probabilities[label], field=f"{task_id}.{label}")
            for label in labels
        }
        if not math.isclose(sum(normalized.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise BenchmarkError(f"prediction probabilities for {task_id} must sum to 1")
        rows[task_id] = {
            "task_id": task_id,
            "label": row["label"],
            "probabilities": normalized,
        }
    return rows


def _macro_f1(tasks: Iterable[Mapping[str, Any]], rows: Mapping[str, Mapping[str, Any]]) -> float:
    labels = sorted({label for task in tasks for label in task["labels"]})
    scores: list[float] = []
    task_list = list(tasks)
    for label in labels:
        tp = fp = fn = 0
        for task in task_list:
            gold = task["gold_label"]
            pred = rows[task["id"]]["label"]
            tp += int(gold == label and pred == label)
            fp += int(gold != label and pred == label)
            fn += int(gold == label and pred != label)
        if tp == fp == fn == 0:
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def _metrics(tasks: list[Mapping[str, Any]], rows: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    correct = 0
    brier_total = 0.0
    log_loss_total = 0.0
    epsilon = 1e-15
    for task in tasks:
        row = rows[task["id"]]
        gold = task["gold_label"]
        correct += int(row["label"] == gold)
        for label in task["labels"]:
            target = 1.0 if label == gold else 0.0
            brier_total += (row["probabilities"][label] - target) ** 2
        log_loss_total += -math.log(max(row["probabilities"][gold], epsilon))
    count = len(tasks)
    return {
        "accuracy": correct / count,
        "macro_f1": _macro_f1(tasks, rows),
        "brier": brier_total / count,
        "log_loss": log_loss_total / count,
    }


def score(benchmark_document: Any, predictions_document: Any, *, model_id: str) -> dict[str, Any]:
    if not isinstance(model_id, str) or not model_id.strip():
        raise BenchmarkError("model_id must be non-empty")
    benchmark = validate_benchmark(benchmark_document)
    rows = validate_predictions(predictions_document, benchmark)
    tasks = benchmark["tasks"]
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for task in tasks:
        grouped[task["category"]].append(task)
    return {
        "schema_version": 1,
        "scorer_version": SCORER_VERSION,
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": sha256_json(benchmark),
        "model_id": model_id,
        "task_count": len(tasks),
        "metrics": _metrics(tasks, rows),
        "categories": {
            category: {"task_count": len(category_tasks), "metrics": _metrics(category_tasks, rows)}
            for category, category_tasks in sorted(grouped.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = score(
        json.loads(args.benchmark.read_text(encoding="utf-8")),
        json.loads(args.predictions.read_text(encoding="utf-8")),
        model_id=args.model_id,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
