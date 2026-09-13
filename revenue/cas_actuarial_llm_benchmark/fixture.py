# SPDX-License-Identifier: MPL-2.0
"""Synthetic acceptance fixture for the CAS actuarial LLM benchmark evidence core."""

from __future__ import annotations

import hashlib
from typing import Any


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


MODELS = [
    ("commercial-openai", "commercial", "openai"),
    ("commercial-anthropic", "commercial", "anthropic"),
    ("commercial-google", "commercial", "google"),
    ("open-model-a", "open", "community-a"),
    ("open-model-b", "open", "community-b"),
    ("open-model-c", "open", "community-c"),
]


def synthetic_evidence() -> dict[str, Any]:
    tasks = [
        {
            "task_id": "claim-triage",
            "version": "v1",
            "task_type": "binary",
            "labels": ["routine", "escalate"],
            "dataset": {
                "sha256": _sha("claim-triage-dataset-v1"),
                "split_sha256": _sha("claim-triage-split-v1"),
                "license_status": "confirmed_publishable",
                "license_reference": "synthetic-fixture-publication-authority-v1",
                "provenance": "Synthetic records generated for repository acceptance testing only.",
                "source_uri": "https://example.invalid/cas-fixture/claim-triage-v1",
            },
        },
        {
            "task_id": "risk-segmentation",
            "version": "v1",
            "task_type": "multiclass",
            "labels": ["low", "medium", "high"],
            "dataset": {
                "sha256": _sha("risk-segmentation-dataset-v1"),
                "split_sha256": _sha("risk-segmentation-split-v1"),
                "license_status": "confirmed_publishable",
                "license_reference": "synthetic-fixture-publication-authority-v1",
                "provenance": "Synthetic records generated for repository acceptance testing only.",
                "source_uri": "https://example.invalid/cas-fixture/risk-segmentation-v1",
            },
        },
    ]
    models = [
        {
            "model_id": model_id,
            "model_version": "fixture-2026-09",
            "model_class": model_class,
            "provider": provider,
            "artifact_sha256": _sha(f"{model_id}-artifact"),
        }
        for model_id, model_class, provider in MODELS
    ]
    runs = []
    for model_index, (model_id, _model_class, _provider) in enumerate(MODELS):
        model = models[model_index]
        for task in tasks:
            labels = task["labels"]
            records = []
            for i in range(12):
                truth = labels[i % len(labels)]
                # deterministic spread: stronger fixture rows still include errors
                correct = (i + model_index) % 5 != 0
                prediction = truth if correct else labels[(labels.index(truth) + 1) % len(labels)]
                if len(labels) == 2:
                    p_pred = "0.80"
                    p_other = "0.20"
                    probabilities = {
                        label: (p_pred if label == prediction else p_other)
                        for label in labels
                    }
                else:
                    probabilities = {
                        label: ("0.70" if label == prediction else "0.15")
                        for label in labels
                    }
                records.append(
                    {
                        "item_id": f"item-{i:03d}",
                        "truth": truth,
                        "prediction": prediction,
                        "probabilities": probabilities,
                    }
                )
            runs.append(
                {
                    "run_id": f"{model_id}-{task['task_id']}-v1",
                    "model_id": model_id,
                    "model_version": model["model_version"],
                    "model_artifact_sha256": model["artifact_sha256"],
                    "task_id": task["task_id"],
                    "task_version": task["version"],
                    "dataset_sha256": task["dataset"]["sha256"],
                    "split_sha256": task["dataset"]["split_sha256"],
                    "protocol_sha256": _sha("fixed-evaluation-protocol-v1"),
                    "records": records,
                }
            )
    return {
        "schema_version": 1,
        "governance": {
            "update_policy": "versioned_no_silent_mutation",
            "task_authority": "qualified_actuarial_reviewer",
            "benchmark_license": "MPL-2.0",
        },
        "tasks": tasks,
        "models": models,
        "runs": runs,
    }
