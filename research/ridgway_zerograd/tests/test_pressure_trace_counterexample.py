import unittest

from pressure_trace_counterexample import (
    certificate,
    fully_weak_low_degree_witness,
    local_p4_boundary_triangle_witness,
    square_annulus_witness,
)


class PressureTraceCounterexampleTests(unittest.TestCase):
    def test_low_degree_weak_boundary_defect_is_exact(self):
        w = fully_weak_low_degree_witness()
        self.assertEqual(w["velocity_degree"], 0)
        self.assertEqual(w["divergence"], "0")
        self.assertEqual(w["forcing_pairing"], "1")
        self.assertEqual(w["pressure_volume_pairing"], "0")
        self.assertEqual(w["pressure_boundary_flux"], "1")
        self.assertEqual(w["pressure_free_kernel_lhs_at_u_zero"], "0")
        self.assertEqual(w["consistency_defect_lhs_minus_rhs"], "-1")

    def test_p4_compatible_boundary_triangle_is_exactly_divergence_free(self):
        w = local_p4_boundary_triangle_witness()
        self.assertEqual(w["velocity_degree"], 3)
        self.assertTrue(w["contained_in_full_P4_velocity_space"])
        self.assertEqual(w["divergence_polynomial"], {})
        self.assertTrue(w["zero_extension_trace_zero"])

    def test_p4_compatible_boundary_triangle_exposes_pressure_defect(self):
        w = local_p4_boundary_triangle_witness()
        self.assertEqual(w["forcing_pairing"], "1/30")
        self.assertEqual(w["pressure_boundary_flux"], "1/30")
        self.assertEqual(w["pressure_volume_pairing"], "0")
        self.assertEqual(w["pressure_free_kernel_lhs_at_u_zero"], "0")
        self.assertEqual(w["consistency_defect_lhs_minus_rhs"], "-1/30")

    def test_mixed_boundary_witness_has_zero_strong_outer_trace(self):
        w = square_annulus_witness()
        self.assertTrue(w["strong_outer_trace_zero"])
        self.assertEqual(w["velocity_degree"], 8)
        self.assertEqual(w["divergence_polynomial"], {})

    def test_mixed_boundary_pressure_flux_matches_forcing(self):
        w = square_annulus_witness()
        self.assertEqual(w["forcing_pairing"], "-2436/5")
        self.assertEqual(w["pressure_boundary_flux"], "-2436/5")
        self.assertEqual(w["pressure_volume_pairing"], "0")
        self.assertEqual(w["consistency_defect_lhs_minus_rhs"], "2436/5")

    def test_mixed_boundary_edge_flux_partition_is_exact(self):
        w = square_annulus_witness()
        self.assertEqual(
            w["inner_edge_fluxes"],
            {
                "inner_right_x=1": "-162",
                "inner_left_x=-1": "-162",
                "inner_top_y=1": "-816/5",
                "inner_bottom_y=-1": "0",
            },
        )

    def test_certificate_truth_ceiling_stays_partial(self):
        ceiling = certificate()["theorem_ceiling"]
        self.assertIn("does not prove the full prize convergence theorem", ceiling)
        self.assertIn("curved-domain error lower bound", ceiling)


if __name__ == "__main__":
    unittest.main()
