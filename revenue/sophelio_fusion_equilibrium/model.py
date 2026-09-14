"""Shot-balanced PCA + ridge modeling and grouped validation."""
from __future__ import annotations
from typing import Sequence
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import RobustScaler
try:
    from .contract import ContractError, D3D_COMPOSITE_GATE, GRID_SHAPE, Prediction, ProxyScore
    from .resampling import balanced_frame_indices, shot_group_folds
except ImportError:
    from contract import ContractError, D3D_COMPOSITE_GATE, GRID_SHAPE, Prediction, ProxyScore
    from resampling import balanced_frame_indices, shot_group_folds

class ShotGroupedPCARidge:
    """Deterministic target-compression baseline with a robust ridge ensemble."""

    def __init__(
        self,
        n_components: int = 24,
        alphas: Sequence[float] = (0.03, 0.3, 3.0),
        max_frames_per_shot: int = 48,
        seed: int = 42,
    ) -> None:
        if n_components < 1:
            raise ValueError("n_components must be positive")
        if not alphas or any(a <= 0 for a in alphas):
            raise ValueError("alphas must be positive")
        self.n_components = int(n_components)
        self.alphas = tuple(float(a) for a in alphas)
        self.max_frames_per_shot = int(max_frames_per_shot)
        self.seed = int(seed)
        self.scaler: RobustScaler | None = None
        self.pca: PCA | None = None
        self.coef_models: list[Ridge] = []
        self.scalar_models: list[Ridge] = []

    def fit(
        self,
        x: np.ndarray,
        psirz: np.ndarray,
        q95: np.ndarray,
        beta_n: np.ndarray,
        shot_ids: Sequence[str],
    ) -> "ShotGroupedPCARidge":
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(psirz, dtype=np.float64)
        q = np.asarray(q95, dtype=np.float64).reshape(-1)
        b = np.asarray(beta_n, dtype=np.float64).reshape(-1)
        ids = np.asarray([str(s) for s in shot_ids], dtype=object)
        n = x.shape[0]
        if x.ndim != 2 or y.shape != (n, *GRID_SHAPE) or q.size != n or b.size != n or ids.size != n:
            raise ContractError("training arrays disagree")
        if len(set(ids.tolist())) < 2:
            raise ContractError("training requires at least two shots")
        if not (np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(q).all() and np.isfinite(b).all()):
            raise ContractError("training arrays must be finite")
        take = balanced_frame_indices(ids, self.max_frames_per_shot, self.seed)
        if take.size < 2:
            raise ContractError("not enough balanced frames")
        xs = x[take]
        flat = y[take].reshape(take.size, -1)
        ncomp = min(self.n_components, take.size - 1, flat.shape[1])
        self.scaler = RobustScaler(quantile_range=(10.0, 90.0)).fit(xs)
        xz = self.scaler.transform(xs)
        self.pca = PCA(n_components=ncomp, svd_solver="full").fit(flat)
        z = self.pca.transform(flat)
        scalars = np.column_stack([q[take], b[take]])
        self.coef_models = []
        self.scalar_models = []
        for alpha in self.alphas:
            self.coef_models.append(Ridge(alpha=alpha).fit(xz, z))
            self.scalar_models.append(Ridge(alpha=alpha).fit(xz, scalars))
        return self

    def predict(self, x: np.ndarray) -> Prediction:
        if self.scaler is None or self.pca is None or not self.coef_models:
            raise RuntimeError("model not fitted")
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 2 or not np.isfinite(x).all():
            raise ContractError("prediction features invalid")
        xz = self.scaler.transform(x)
        z = np.mean([m.predict(xz) for m in self.coef_models], axis=0)
        scal = np.mean([m.predict(xz) for m in self.scalar_models], axis=0)
        psi = self.pca.inverse_transform(z).reshape((-1, *GRID_SHAPE)).astype(np.float32)
        return Prediction(psi, scal[:, 0].astype(np.float32), scal[:, 1].astype(np.float32))


def _proxy_score(y_true: np.ndarray, q_true: np.ndarray, b_true: np.ndarray, pred: Prediction, shot_ids: Sequence[str]) -> ProxyScore:
    yt = np.asarray(y_true, dtype=np.float64).reshape(len(pred.q95), -1)
    yp = np.asarray(pred.psirz, dtype=np.float64).reshape(len(pred.q95), -1)
    rpsi = float(r2_score(yt.reshape(-1), yp.reshape(-1)))
    rs = 0.5 * (
        float(r2_score(np.asarray(q_true), np.asarray(pred.q95)))
        + float(r2_score(np.asarray(b_true), np.asarray(pred.betaN)))
    )
    # Only the terms we can reproduce without the organizer's LCFS/consistency
    # scorer. Never call this the competition composite.
    partial = 0.55 * rpsi + 0.15 * rs
    return ProxyScore(rpsi, rs, partial, len(pred.q95), len(set(map(str, shot_ids))))


def grouped_cross_validate(
    x: np.ndarray,
    psirz: np.ndarray,
    q95: np.ndarray,
    beta_n: np.ndarray,
    shot_ids: Sequence[str],
    *,
    n_splits: int = 3,
    n_components: int = 12,
    max_frames_per_shot: int = 32,
    seed: int = 42,
) -> list[ProxyScore]:
    ids = np.asarray([str(s) for s in shot_ids], dtype=object)
    folds = shot_group_folds(ids.tolist(), n_splits=n_splits, seed=seed)
    scores: list[ProxyScore] = []
    for fold in folds:
        train_mask = np.isin(ids, fold.train_shots)
        valid_mask = np.isin(ids, fold.valid_shots)
        if np.any(train_mask & valid_mask):
            raise AssertionError("shot leakage")
        model = ShotGroupedPCARidge(
            n_components=n_components,
            max_frames_per_shot=max_frames_per_shot,
            seed=seed,
        ).fit(x[train_mask], psirz[train_mask], q95[train_mask], beta_n[train_mask], ids[train_mask])
        pred = model.predict(x[valid_mask])
        scores.append(_proxy_score(psirz[valid_mask], q95[valid_mask], beta_n[valid_mask], pred, ids[valid_mask]))
    return scores


def transfer_retention(d3d_score: float, mast_score: float, gate: float = D3D_COMPOSITE_GATE) -> float:
    """Challenge-2 ratio semantics, with the organizer's DIII-D gate."""
    if not (np.isfinite(d3d_score) and np.isfinite(mast_score)):
        raise ValueError("scores must be finite")
    if d3d_score < gate or d3d_score <= 0:
        return 0.0
    return float(mast_score / d3d_score)


