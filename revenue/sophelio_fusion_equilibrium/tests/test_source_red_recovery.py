from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(HERE))

from toolkit import (  # noqa: E402
    ContractError,
    D3D_TRAIN_SHOTS,
    Prediction,
    ShotGroupedPCARidge,
    capture_public_test_lengths,
    compile_bundle,
    compile_real_bundle,
    target_storage_bytes,
    validate_prediction_arrays,
    verify_bundle,
    verify_real_bundle,
)


def _pred(t: int, value: float = 0.0) -> Prediction:
    return Prediction(
        np.full((t, 65, 65), value, dtype=np.float32),
        np.zeros(t, dtype=np.float32),
        np.zeros(t, dtype=np.float32),
    )


def _rows(count: int, length: int = 1):
    for _ in range(count):
        yield {"efit_times": np.arange(length, dtype=np.float64)}


class _IndexOnlyTargets:
    """Array-like that fails if the model attempts whole-fold materialization."""

    def __init__(self, data: np.ndarray):
        self.data = data
        self.shape = data.shape
        self.full_array_conversions = 0
        self.indexed_frames = 0

    def __array__(self, *args, **kwargs):
        self.full_array_conversions += 1
        raise AssertionError("whole-fold target materialization attempted")

    def __getitem__(self, index):
        result = self.data[index]
        if getattr(result, "ndim", 0) == 3:
            self.indexed_frames += int(result.shape[0])
        else:
            self.indexed_frames += 1
        return result


class MemoryBoundedTrainingTests(unittest.TestCase):
    def test_batch_fit_selects_before_target_conversion(self):
        rng = np.random.default_rng(11)
        shots = 160
        ids = np.repeat([f"s{i}" for i in range(shots)], 2)
        x = rng.normal(size=(ids.size, 4))
        y = rng.normal(scale=0.01, size=(ids.size, 65, 65)).astype(np.float32)
        q = rng.normal(size=ids.size)
        b = rng.normal(size=ids.size)
        guarded = _IndexOnlyTargets(y)
        model = ShotGroupedPCARidge(
            n_components=2,
            max_frames_per_shot=2,
            max_retained_frames=180,
            pca_batch_size=32,
        ).fit(x, guarded, q, b, ids)
        self.assertEqual(guarded.full_array_conversions, 0)
        self.assertEqual(guarded.indexed_frames, 180)
        self.assertEqual(model.retained_frame_count, 180)
        self.assertLessEqual(model.retained_target_bytes, target_storage_bytes(180))

    def test_stream_fit_has_hard_global_target_budget(self):
        rng = np.random.default_rng(12)
        expected_shots = 9

        def stream():
            for shot in range(expected_shots):
                n = 8
                x = rng.normal(size=(n, 5))
                y = rng.normal(scale=0.01, size=(n, 65, 65)).astype(np.float32)
                q = rng.normal(size=n)
                b = rng.normal(size=n)
                yield f"s{shot}", x, y, q, b

        model = ShotGroupedPCARidge(
            n_components=3,
            max_frames_per_shot=8,
            max_retained_frames=20,
            pca_batch_size=8,
        ).fit_shot_stream(stream(), expected_shots=expected_shots)
        self.assertEqual(model.retained_frame_count, 20)
        self.assertLessEqual(model.retained_target_bytes, target_storage_bytes(20))

    def test_real_scale_memory_receipt_closes_predecessor_shape(self):
        lower_bound_frames = ((D3D_TRAIN_SHOTS + 1) // 2) * 241 + (D3D_TRAIN_SHOTS // 2)
        self.assertGreater(target_storage_bytes(lower_bound_frames, itemsize=8), 20 * 1024**3)
        self.assertLess(target_storage_bytes(8192), 256 * 1024**2)


class FullFoldBundleAuthorityTests(unittest.TestCase):
    def test_incomplete_and_extra_public_fold_streams_fail(self):
        with self.assertRaises(ContractError):
            capture_public_test_lengths(_rows(873), "DIII-D", source_receipt_sha256="a" * 64)
        with self.assertRaises(ContractError):
            capture_public_test_lengths(_rows(1205), "MAST", source_receipt_sha256="b" * 64)
        with self.assertRaises(ContractError):
            capture_public_test_lengths(_rows(875), "DIII-D", source_receipt_sha256="a" * 64)

    def test_length_order_is_receipt_bound(self):
        a = capture_public_test_lengths(
            ({"efit_times": np.arange(1 if i < 873 else 2, dtype=np.float64)} for i in range(874)),
            "DIII-D",
            source_receipt_sha256="a" * 64,
        )
        b = capture_public_test_lengths(
            ({"efit_times": np.arange(2 if i == 0 else 1, dtype=np.float64)} for i in range(874)),
            "DIII-D",
            source_receipt_sha256="a" * 64,
        )
        self.assertNotEqual(a.sha256, b.sha256)

    def test_fixture_bundle_is_never_real_terminal_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            compile_bundle(out, [_pred(2)], [2], [_pred(3)], [3])
            fixture = verify_bundle(out)
            self.assertTrue(fixture["truth"]["fixture_only"])
            with self.assertRaises(ContractError):
                verify_real_bundle(
                    out,
                    expected_d3d_fold_sha256="0" * 64,
                    expected_mast_fold_sha256="1" * 64,
                )

    def test_real_compiler_rejects_partial_predictions_before_publication(self):
        d3d = capture_public_test_lengths(_rows(874), "DIII-D", source_receipt_sha256="a" * 64)
        mast = capture_public_test_lengths(_rows(1206), "MAST", source_receipt_sha256="b" * 64)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ContractError):
                compile_real_bundle(
                    td,
                    [_pred(1)],
                    d3d,
                    [_pred(1)],
                    mast,
                    expected_d3d_fold_sha256=d3d.sha256,
                    expected_mast_fold_sha256=mast.sha256,
                )
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_real_compiler_requires_independently_retained_fold_root(self):
        d3d = capture_public_test_lengths(_rows(874), "DIII-D", source_receipt_sha256="a" * 64)
        mast = capture_public_test_lengths(_rows(1206), "MAST", source_receipt_sha256="b" * 64)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ContractError):
                compile_real_bundle(
                    td,
                    [],
                    d3d,
                    [],
                    mast,
                    expected_d3d_fold_sha256="0" * 64,
                    expected_mast_fold_sha256=mast.sha256,
                )

    def test_mast_nonfinite_prediction_fails_closed(self):
        p = _pred(2)
        bad = p.psirz.copy()
        bad[0, 0, 0] = np.nan
        arrays = {
            "shot_0000_psirz": bad,
            "shot_0000_q95": p.q95,
            "shot_0000_betaN": p.betaN,
        }
        with self.assertRaises(ContractError):
            validate_prediction_arrays(arrays, [2], "MAST")


if __name__ == "__main__":
    unittest.main(verbosity=2)
