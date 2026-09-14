"""Public facade for deterministic DaT V2 features, training and inference."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .contract import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    RUNTIME_COMMIT,
    SCHEMA_VERSION,
    ModelContractError,
    canonical_json,
    sha256_json,
)
from .features import extract_features, feature_matrix, robust_normalize
from .model import (
    apply_calibrator,
    binary_log_loss,
    predict_feature_matrix,
    train_feature_model,
    validate_model_artifact,
)


def predict_volume(volume: np.ndarray, artifact: Mapping[str, object]) -> float:
    vector, names = extract_features(volume)
    if list(names) != artifact.get("feature_names"):
        raise ModelContractError("feature schema does not match model artifact")
    return float(predict_feature_matrix(vector, artifact)[0])


__all__ = [
    "FEATURE_NAMES", "FEATURE_VERSION", "RUNTIME_COMMIT", "SCHEMA_VERSION",
    "ModelContractError", "canonical_json", "sha256_json", "robust_normalize",
    "extract_features", "feature_matrix", "binary_log_loss", "apply_calibrator",
    "train_feature_model", "validate_model_artifact", "predict_feature_matrix",
    "predict_volume",
]
