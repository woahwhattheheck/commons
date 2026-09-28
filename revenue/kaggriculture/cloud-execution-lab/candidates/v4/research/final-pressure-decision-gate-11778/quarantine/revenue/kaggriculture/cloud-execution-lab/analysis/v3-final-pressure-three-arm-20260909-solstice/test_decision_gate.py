from __future__ import annotations

import hashlib
import unittest

import decision_gate
import panel_analysis


def comparison(*, margin: float, own: float, rival: float, classifications: list[str], new: int = 0, resolved: int = 0):
    divergence = {
        "identical": (None, None),
        "syntactic_only": (0, None),
        "state_only": (None, 0),
        "realized": (0, 0),
    }
    paired = [
        {
            "classification": value,
            "first_candidate_action_divergence": divergence[value][0],
            "first_post_state_divergence": divergence[value][1],
        }
        for value in classifications
    ]
    return {
        "cells": len(paired),
        "candidate_action_changed_cells": sum(value in ("syntactic_only", "realized") for value in classifications),
        "post_state_changed_cells": sum(value in ("state_only", "realized") for value in classifications),
        "syntactic_only_cells": sum(value == "syntactic_only" for value in classifications),
        "identical_cells": sum(value == "identical" for value in classifications),
        "new_losses": new,
        "resolved_losses": resolved,
        "mean_margin_delta": margin,
        "median_margin_delta": margin,
        "min_margin_delta": margin,
        "max_margin_delta": margin,
        "mean_candidate_score_delta": own,
        "mean_opponent_score_delta": rival,
        "earliest_candidate_action_divergence": 0,
        "earliest_post_state_divergence": 0,
        "verdict_transitions": {},
        "paired_cells": paired,
    }


def summary(*, leader: str, final_off: dict, final_legacy: dict, legacy_off: dict):
    signals = {
        "final_boundary": "FINAL_BOUNDARY_LEADS_DEVELOPMENT",
        "legacy_in_pipeline": "LEGACY_IN_PIPELINE_LEADS_DEVELOPMENT",
        "pressure_off": "PRESSURE_OFF_LEADS_DEVELOPMENT",
    }
    return {
        "by_variant": {},
        "comparisons": {
            "final_boundary_minus_pressure_off": final_off,
            "final_boundary_minus_legacy_in_pipeline": final_legacy,
            "legacy_in_pipeline_minus_pressure_off": legacy_off,
        },
        "development_signal": signals[leader],
        "leaders_by_mean_margin": [leader],
        "scope": "development attribution only",
    }


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def game(variant: str, seat: int) -> dict:
    own, rival = ((9, 0) if variant == "final_boundary" else (10, 5))
    scores = [own, rival] if seat == 0 else [rival, own]
    action_label = "final" if variant == "final_boundary" else "shared"
    state_label = "final" if variant == "final_boundary" else "shared"
    return {
        "variant": variant,
        "opponent": "op",
        "seed": 1,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "scores": scores,
        "steps": 1,
        "episode_steps": 2,
        "candidate_action_trace_sha256": digest(variant + "-actions"),
        "post_state_trace_sha256": digest(variant + "-states"),
        "step_digests": [
            {
                "step": 0,
                "candidate_action_sha256": digest(action_label),
                "post_state_sha256": digest(state_label),
            }
        ],
        "actors": [
            {"max_rpc_seconds": 0.01},
            {"max_rpc_seconds": 0.02},
        ],
    }


class DecisionGateTests(unittest.TestCase):
    @unittest.skipUnless(
        hasattr(panel_analysis, "validate_games"),
        "requires the exact repository panel_analysis module",
    )
    def test_exact_predecessor_emits_margin_only_false_leader(self):
        rows = [
            game(name, seat)
            for name in decision_gate.arm_defs.VARIANTS
            for seat in (0, 1)
        ]
        arms = [{"name": name} for name in decision_gate.arm_defs.VARIANTS]
        predecessor = panel_analysis.summarize(rows, arms, ["op"], [1])
        self.assertEqual(
            predecessor["development_signal"],
            "FINAL_BOUNDARY_LEADS_DEVELOPMENT",
        )
        self.assertEqual(
            decision_gate.classify_summary(predecessor)["development_signal"],
            "MARGIN_ONLY_LEADER_HOLD",
        )

    def test_final_leader_requires_realized_own_score_positive_evidence(self):
        value = summary(
            leader="final_boundary",
            final_off=comparison(margin=3, own=2, rival=-1, classifications=["realized", "identical"]),
            final_legacy=comparison(margin=2, own=1, rival=-1, classifications=["realized", "realized"]),
            legacy_off=comparison(margin=1, own=1, rival=0, classifications=["syntactic_only", "identical"]),
        )
        decision = decision_gate.classify_summary(value)
        self.assertEqual(decision["development_signal"], "FINAL_BOUNDARY_LEADS_DEVELOPMENT")
        self.assertTrue(decision["qualified_directional_leader"])

    def test_predecessor_margin_only_false_leader_is_held(self):
        # Final loses one point of own score but depresses the rival by five,
        # so the predecessor's margin-only rule labels it the development leader.
        value = summary(
            leader="final_boundary",
            final_off=comparison(margin=4, own=-1, rival=-5, classifications=["realized", "realized"]),
            final_legacy=comparison(margin=4, own=-1, rival=-5, classifications=["realized", "realized"]),
            legacy_off=comparison(margin=0, own=0, rival=0, classifications=["identical", "identical"]),
        )
        self.assertEqual(value["development_signal"], "FINAL_BOUNDARY_LEADS_DEVELOPMENT")
        decision = decision_gate.classify_summary(value)
        self.assertEqual(decision["development_signal"], "MARGIN_ONLY_LEADER_HOLD")
        self.assertFalse(decision["qualified_directional_leader"])
        self.assertIn(
            "final_boundary_vs_pressure_off:positive_mean_candidate_score",
            decision["failed_checks"],
        )

    def test_state_only_divergence_overrides_headline(self):
        value = summary(
            leader="final_boundary",
            final_off=comparison(margin=2, own=2, rival=0, classifications=["state_only", "identical"]),
            final_legacy=comparison(margin=2, own=2, rival=0, classifications=["state_only", "identical"]),
            legacy_off=comparison(margin=0, own=0, rival=0, classifications=["identical", "identical"]),
        )
        decision = decision_gate.classify_summary(value)
        self.assertEqual(decision["development_signal"], "STATE_ONLY_HOLD")
        self.assertEqual(decision["state_only_cells_across_pairings"], 2)

    def test_post_state_before_action_is_causal_order_hold(self):
        bad = comparison(
            margin=2, own=2, rival=0, classifications=["realized", "identical"]
        )
        bad["paired_cells"][0]["first_candidate_action_divergence"] = 4
        bad["paired_cells"][0]["first_post_state_divergence"] = 3
        value = summary(
            leader="final_boundary",
            final_off=bad,
            final_legacy=comparison(
                margin=2, own=2, rival=0, classifications=["realized", "identical"]
            ),
            legacy_off=comparison(
                margin=0, own=0, rival=0, classifications=["identical", "identical"]
            ),
        )
        decision = decision_gate.classify_summary(value)
        self.assertEqual(decision["development_signal"], "CAUSAL_ORDER_HOLD")
        self.assertEqual(
            decision["state_precedes_action_cells_across_pairings"], 1
        )

    def test_reverse_direction_uses_resolved_losses_as_new_losses(self):
        value = summary(
            leader="legacy_in_pipeline",
            final_off=comparison(margin=-1, own=-1, rival=0, classifications=["realized"]),
            final_legacy=comparison(
                margin=-2,
                own=-2,
                rival=0,
                classifications=["realized"],
                new=0,
                resolved=1,
            ),
            legacy_off=comparison(margin=1, own=1, rival=0, classifications=["realized"]),
        )
        decision = decision_gate.classify_summary(value)
        self.assertEqual(decision["development_signal"], "NEW_LOSS_HOLD")
        self.assertEqual(decision["comparisons"]["final_boundary"]["new_losses"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
