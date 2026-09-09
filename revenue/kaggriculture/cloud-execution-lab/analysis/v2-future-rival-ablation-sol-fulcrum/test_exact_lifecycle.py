# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating contracts for the exact official lifecycle."""
from __future__ import annotations

import unittest

import compare as target
from test_compare import HEAD, receipt, report


def rewrite_lifecycle(evidence: dict, steps: int) -> None:
    """Keep both reports internally self-consistent while truncating every game."""
    for game in evidence["games"]:
        game["steps"] = steps
        game["action_digest_steps_by_seat"] = [steps, steps]
        game["candidate_action_digest_steps"] = steps


class ExactLifecycleTests(unittest.TestCase):
    def test_mutually_noncanonical_complete_reports_fail_closed(self) -> None:
        # The predecessor accepted each of these because it required only
        # 1 <= steps <= 720 and made the action counts equal that self-declared
        # value. Mutating both arms also evades its paired-step equality check.
        for steps in (1, 718, 720):
            with self.subTest(steps=steps):
                control = report("control")
                ablation = report("ablation")
                rewrite_lifecycle(control, steps)
                rewrite_lifecycle(ablation, steps)
                with self.assertRaisesRegex(
                    target.CompareError,
                    "exact 720-state/719-action lifecycle",
                ):
                    target.analyze(
                        control,
                        ablation,
                        receipt("control"),
                        receipt("ablation"),
                        HEAD,
                    )


if __name__ == "__main__":
    unittest.main()
