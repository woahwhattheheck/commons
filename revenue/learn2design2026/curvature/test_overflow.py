"""Finite-input numerical regressions; analytic evidence, not organizer physics."""
from pathlib import Path
import unittest

import jax
import jax.numpy as jnp
import numpy as np

from synthetic import SyntheticObjective, load_candidate

MOD = load_candidate(Path(__file__).with_name("submission.py"), "_curvature_overflow")


def advance_kernel(armijo=1e-4):
    return MOD._kernels(4, 0.5, 4.0, armijo, 0.5, 1e-8, 16, 256, 1e-10)


def accepted_base(dtype=jnp.float32, magnitude=1e38):
    x = jnp.zeros((2, 64), dtype=dtype)
    st = MOD._empty(x, 4, 0.5)
    g = jnp.full_like(x, magnitude)
    f = jnp.full((2,), magnitude, dtype=dtype)
    fresh = jnp.full_like(x, 3.0)
    st, accepted, restarted = advance_kernel()(st, f, g, fresh)
    return st, g, fresh, accepted, restarted


class FiniteGradientOverflowTests(unittest.TestCase):
    def assert_valid_improvement(self, dtype, magnitude):
        st, g, fresh, accepted, restarted = accepted_base(dtype, magnitude)
        self.assertTrue(bool(jnp.all(accepted)))
        self.assertFalse(bool(jnp.any(restarted)))
        self.assertTrue(bool(jnp.all(jnp.isfinite(st.direction))))
        # This is the overflowing predecessor intermediate, not an invalid input.
        self.assertTrue(bool(jnp.all(jnp.isneginf(jnp.sum(g * st.direction, axis=1)))))
        decrease = jnp.sum((1e-4 * g) * st.direction, axis=1)
        loss = st.f * jnp.asarray(0.99, dtype=dtype)
        self.assertTrue(bool(jnp.all(jnp.isfinite(st.f + decrease))))
        self.assertTrue(bool(jnp.all(loss < st.f + decrease)))
        result, accepted, restarted = advance_kernel()(st, loss, g, fresh)
        self.assertTrue(bool(jnp.all(accepted)))
        self.assertFalse(bool(jnp.any(restarted)))
        np.testing.assert_array_equal(result.x, st.trial)
        np.testing.assert_array_equal(result.f, loss)

    def test_float32_finite_threshold_accepts_improvement(self):
        self.assert_valid_improvement(jnp.float32, 1e38)

    @unittest.skipUnless(jax.config.x64_enabled, "requires JAX_ENABLE_X64=true")
    def test_float64_finite_threshold_accepts_improvement(self):
        self.assert_valid_improvement(jnp.float64, 6e307)

    def test_backtrack_recovers_using_retained_large_gradient(self):
        st, g, fresh, _, _ = accepted_base()
        rejected, accepted, restarted = advance_kernel()(st, st.f * 1.1, g, fresh)
        self.assertFalse(bool(jnp.any(accepted)))
        self.assertFalse(bool(jnp.any(restarted)))
        for name in ("x", "f", "g", "s", "y", "rho", "head", "count"):
            np.testing.assert_array_equal(getattr(rejected, name), getattr(st, name))
        np.testing.assert_array_equal(rejected.step, [0.5, 0.5])
        result, accepted, restarted = advance_kernel()(rejected, st.f * 0.99, g, fresh)
        self.assertTrue(bool(jnp.all(accepted)))
        self.assertFalse(bool(jnp.any(restarted)))
        np.testing.assert_array_equal(result.x, rejected.trial)

    def test_nonfinite_trial_is_still_rejected_independently(self):
        st, g, fresh, _, _ = accepted_base()
        loss = (st.f * 0.99).at[1].set(jnp.inf)
        result, accepted, restarted = advance_kernel()(st, loss, g, fresh)
        np.testing.assert_array_equal(accepted, [True, False])
        self.assertFalse(bool(jnp.any(restarted)))
        np.testing.assert_array_equal(result.x[1], st.x[1])
        np.testing.assert_array_equal(result.g[1], st.g[1])

    def test_true_nonrepresentable_decrement_does_not_accept(self):
        st, g, fresh, _, _ = accepted_base()
        # A longer bounded direction makes the scaled threshold itself overflow.
        d = st.direction * 4.0
        st = st._replace(direction=d, trial=st.x + st.step[:, None] * d)
        self.assertTrue(bool(jnp.all(jnp.isneginf(jnp.sum((0.49 * g) * d, axis=1)))))
        result, accepted, _ = advance_kernel(armijo=0.49)(st, st.f * 0.99, g, fresh)
        self.assertFalse(bool(jnp.any(accepted)))
        np.testing.assert_array_equal(result.x, st.x)

    def test_descent_validation_keeps_non_gradient_curvature_direction(self):
        x = jnp.zeros((2, 64), dtype=jnp.float32)
        st = MOD._empty(x, 4, 0.5)
        g = jnp.full_like(x, 1e38)
        # One valid pair changes coordinate zero's inverse curvature. Products
        # in the two-loop recursion stay finite; only the final slope overflows.
        s = st.s.at[:, 0, :2].set(jnp.array([1.0, 1.0], dtype=x.dtype))
        y = st.y.at[:, 0, :2].set(jnp.array([1.0, 2.0], dtype=x.dtype))
        st = st._replace(f=jnp.ones(2, dtype=x.dtype), g=g, s=s, y=y,
                         rho=st.rho.at[:, 0].set(1.0 / 3.0),
                         head=jnp.ones(2, dtype=jnp.int32),
                         count=jnp.ones(2, dtype=jnp.int32))
        result, accepted, _ = advance_kernel()(st, st.f, g, jnp.full_like(x, 3.0))
        self.assertTrue(bool(jnp.all(accepted)))
        self.assertTrue(bool(jnp.all(jnp.isfinite(result.direction))))
        ss, yy = np.asarray(s[0, 0], dtype=np.float64), np.asarray(y[0, 0], dtype=np.float64)
        gg = np.asarray(g[0], dtype=np.float64)
        rho = float(np.asarray(st.rho[0, 0]))
        alpha = rho * np.dot(ss, gg)
        q = gg - alpha * yy
        r = np.dot(ss, yy) / np.dot(yy, yy) * q
        r = r + ss * (alpha - rho * np.dot(yy, r))
        expected = -r / np.linalg.norm(r) * 0.625
        np.testing.assert_allclose(result.direction[0], expected, rtol=2e-6, atol=1e-7)
        self.assertNotAlmostEqual(float(result.direction[0, 0]), float(result.direction[0, 1]), places=5)
        self.assertTrue(bool(jnp.all(jnp.sum(result.direction, axis=1) < 0)))

    def test_end_to_end_finite_gradient_optimization(self):
        obj = SyntheticObjective(lambda x: jnp.asarray(1e38, x.dtype) * jnp.exp(jnp.sum(x)),
                                 dimension=64, budget_batches=12, initial_scale=0.0,
                                 dtype=np.float32)
        MOD.BatchedCurvaturePortfolio().optimize(obj, random_seed=7, population_size=8)
        self.assertEqual(len(obj.history), 12)
        self.assertTrue(all(np.isfinite(x).all() for x in obj.history))
        self.assertTrue(all(np.isfinite(x).all() for x in obj.loss_history))
        # Each gradient coordinate equals the finite objective value.
        self.assertLess(obj.best_loss, 1e20)


if __name__ == "__main__":
    unittest.main()
