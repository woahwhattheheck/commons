from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class PreprocessConfig:
    shape: tuple[int, int, int] = (64, 96, 96)
    lower_q: float = 0.01
    upper_q: float = 0.995
    foreground_fraction: float = 0.05
    margin: int = 4


def _validate_volume(array: np.ndarray) -> np.ndarray:
    x = np.asarray(array, dtype=np.float32)
    x = np.squeeze(x)
    if x.ndim != 3: raise ValueError(f"expected one 3-D NIfTI volume, got shape {x.shape}")
    if min(x.shape) < 4: raise ValueError(f"volume is implausibly small: {x.shape}")
    if not np.isfinite(x).all(): raise ValueError("volume contains NaN or infinite values")
    return x


def foreground_crop(array: np.ndarray, *, fraction: float, margin: int) -> np.ndarray:
    x = _validate_volume(array); vmax = float(x.max())
    if vmax <= 0: return x
    mask = x > vmax * float(fraction)
    if not mask.any(): return x
    coords = np.where(mask); slices = []
    for axis, values in enumerate(coords):
        lo = max(0, int(values.min()) - margin); hi = min(x.shape[axis], int(values.max()) + margin + 1); slices.append(slice(lo, hi))
    return x[tuple(slices)]


def robust_normalize(array: np.ndarray, *, lower_q: float, upper_q: float) -> np.ndarray:
    x = _validate_volume(array); positive = x[x > 0]; reference = positive if positive.size >= 32 else x.reshape(-1)
    lo, hi = np.quantile(reference, [lower_q, upper_q]).astype(np.float64)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo: return np.zeros_like(x, dtype=np.float32)
    x = np.clip(x, lo, hi); x = (x - lo) / (hi - lo); return x.astype(np.float32, copy=False)


def resize_trilinear(array: np.ndarray, shape: tuple[int, int, int]) -> np.ndarray:
    import torch
    import torch.nn.functional as F
    x = torch.from_numpy(_validate_volume(array))[None, None]
    with torch.no_grad(): y = F.interpolate(x, size=shape, mode="trilinear", align_corners=False)
    return y[0, 0].cpu().numpy().astype(np.float32, copy=False)


def preprocess_array(array: np.ndarray, config: PreprocessConfig = PreprocessConfig()) -> np.ndarray:
    x = foreground_crop(array, fraction=config.foreground_fraction, margin=config.margin)
    x = robust_normalize(x, lower_q=config.lower_q, upper_q=config.upper_q)
    return resize_trilinear(x, config.shape)


def load_nifti(path: str | Path) -> np.ndarray:
    import nibabel as nib
    image = nib.as_closest_canonical(nib.load(str(path)))
    return _validate_volume(np.asarray(image.get_fdata(dtype=np.float32)))


def load_and_preprocess(path: str | Path, config: PreprocessConfig = PreprocessConfig()) -> np.ndarray:
    return preprocess_array(load_nifti(path), config)
