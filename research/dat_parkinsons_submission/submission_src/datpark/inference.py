from __future__ import annotations

from pathlib import Path
import numpy as np
import torch
from .bundle import load_bundle
from .preprocess import load_and_preprocess


@torch.inference_mode()
def predict_one(path: str | Path, *, models, temperatures, config, device: str) -> float:
    volume = load_and_preprocess(path, config)
    tensor = torch.from_numpy(volume)[None, None].to(device=device, dtype=torch.float32)
    probabilities = []
    for model, temperature in zip(models, temperatures, strict=True):
        if not np.isfinite(temperature) or temperature <= 0: raise ValueError("invalid calibration temperature")
        probabilities.append(torch.sigmoid(model(tensor) / temperature).item())
    probability = float(np.mean(probabilities))
    if not np.isfinite(probability): raise ValueError("non-finite model probability")
    return float(np.clip(probability, 1e-6, 1 - 1e-6))


def load_predictor(bundle_dir: str | Path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    models, temperatures, config, _ = load_bundle(bundle_dir, device)
    return device, models, temperatures, config
