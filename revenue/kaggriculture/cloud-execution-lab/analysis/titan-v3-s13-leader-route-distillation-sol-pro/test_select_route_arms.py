# SPDX-License-Identifier: Apache-2.0
import unittest
from select_route_arms import classify, metrics


class SelectorTests(unittest.TestCase):
    def report(self, own=(10, 2), margin=(5, 1), changed=2, outcomes=None):
        outcomes = outcomes or [("win", "win"), ("loss", "loss")]
        pairs = []
        for i, (o, m) in enumerate(zip(own, margin)):
            pairs.append({
                "opponent": "arlene",
                "candidate_seat": i,
                "own_cash_delta": o,
                "margin_delta": m,
                "control_outcome": outcomes[i][0],
                "candidate_outcome": outcomes[i][1],
            })
        return {"verdict": "ADVANCE", "overall": {"trace_changed_cells": changed}, "pairs": pairs}

    def test_strict_positive_candidate_advances(self):
        value = metrics(self.report())
        ok, reasons = classify(value)
        self.assertTrue(ok, reasons)

    def test_rival_harm_blocks_despite_own_gain(self):
        value = metrics(self.report(own=(10, 10), margin=(-100, -100)))
        ok, reasons = classify(value)
        self.assertFalse(ok)
        self.assertIn("negative_global_margin", reasons)

    def test_zero_activation_blocks(self):
        value = metrics(self.report(changed=0))
        ok, reasons = classify(value)
        self.assertFalse(ok)
        self.assertIn("zero_action_activation", reasons)

    def test_new_loss_blocks(self):
        value = metrics(self.report(outcomes=[("win", "loss"), ("loss", "loss")]))
        ok, reasons = classify(value)
        self.assertFalse(ok)
        self.assertIn("new_losses", reasons)

    def test_negative_seat_stratum_blocks_masked_global(self):
        value = metrics(self.report(own=(20, -1), margin=(20, -1)))
        ok, reasons = classify(value)
        self.assertFalse(ok)
        self.assertTrue(any(r.startswith("negative_stratum") for r in reasons))


if __name__ == "__main__":
    unittest.main()
