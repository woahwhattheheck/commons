"""Focused and preserved-engine contracts for TITAN P22 terminal payback."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from p22_terminal_payback import (
    CompletionEvent,
    TerminalCandidate,
    compare_candidates,
    evaluate_candidate,
    terminal_decision_step,
)

EVALUATOR = HERE / "reference/evaluator/evaluate.py"
LOADER = HERE / "reference/evaluator/loader.py"
ENGINE_DIR = HERE / "reference/engine"
ENGINE_JSON = ENGINE_DIR / "kaggriculture.json"


def event(event_id, ready, delivery, sale, gross, cost=0):
    return CompletionEvent(event_id, ready, delivery, sale, gross, cost)


class TerminalPaybackPureTests(unittest.TestCase):
    def test_01_terminal_boundary_is_episode_steps_minus_two_and_718_sale_counts(self):
        self.assertEqual(terminal_decision_step(720), 718)
        candidate = TerminalCandidate(
            "last-sale",
            "new_investment",
            [event("at-718", 716, 717, 718, 11, 1), event("at-719", 717, 718, 719, 1000, 0)],
            entry_cost=5,
        )
        decision = evaluate_candidate(candidate, current_step=715)
        self.assertEqual(decision.mode, "invest")
        self.assertEqual(decision.complete_event_ids, ("at-718",))
        self.assertEqual(decision.incomplete_event_ids, ("at-719",))
        self.assertEqual(decision.net_value, 5)

    def test_02_same_step_can_admit_fast_crop_and_reject_slow_asset(self):
        carrot = TerminalCandidate(
            "carrot-cycle",
            "new_investment",
            [event("carrot-sale", 714, 716, 717, 45, 5)],
            entry_cost=20,
        )
        cow = TerminalCandidate(
            "cow",
            "new_investment",
            [event("milk-after-end", 719, 720, 721, 1000, 0)],
            entry_cost=400,
        )
        decisions = compare_candidates([carrot, cow], current_step=712)
        self.assertEqual([decision.mode for decision in decisions], ["invest", "liquidate"])

    def test_03_sunk_productive_service_survives_when_new_investment_is_closed(self):
        existing = TerminalCandidate(
            "existing-crop",
            "sunk_service",
            [event("final-harvest", 716, 717, 718, 35, 2)],
        )
        replacement = TerminalCandidate(
            "replacement",
            "new_investment",
            [event("same-final-harvest", 716, 717, 718, 35, 2)],
            entry_cost=50,
        )
        decisions = compare_candidates([existing, replacement], current_step=715)
        self.assertEqual(decisions[0].mode, "service")
        self.assertEqual(decisions[0].net_value, 33)
        self.assertEqual(decisions[1].mode, "liquidate")
        self.assertEqual(decisions[1].net_value, -17)

    def test_04_sweeps_all_complete_events_instead_of_using_a_calendar_cutoff(self):
        one_event = TerminalCandidate(
            "single",
            "new_investment",
            [event("sale-1", 700, 701, 702, 20, 1)],
            entry_cost=25,
        )
        two_events = TerminalCandidate(
            "repeat",
            "new_investment",
            [
                event("sale-1", 700, 701, 702, 20, 1),
                event("sale-2", 710, 711, 712, 20, 1),
                event("sale-too-late", 718, 719, 720, 500, 0),
            ],
            entry_cost=25,
        )
        decisions = compare_candidates([one_event, two_events], current_step=699)
        self.assertEqual(decisions[0].mode, "liquidate")
        self.assertEqual(decisions[1].mode, "invest")
        self.assertEqual(decisions[1].complete_event_ids, ("sale-1", "sale-2"))
        self.assertEqual(decisions[1].net_value, 13)

    def test_05_exact_tie_and_post_terminal_value_are_noops(self):
        tie = TerminalCandidate(
            "tie",
            "new_investment",
            [event("sale", 710, 711, 712, 11, 1)],
            entry_cost=10,
        )
        late = TerminalCandidate(
            "late",
            "new_investment",
            [event("huge-but-late", 718, 719, 719, 10000, 0)],
            entry_cost=1,
        )
        self.assertEqual(evaluate_candidate(tie, current_step=709).mode, "liquidate")
        self.assertEqual(evaluate_candidate(late, current_step=717).mode, "liquidate")
        terminal = evaluate_candidate(late, current_step=719)
        self.assertEqual(terminal.reason, "terminal boundary already reached")
        self.assertEqual(terminal.net_value, 0)

    def test_06_rejects_invalid_or_double_countable_event_contracts(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(
                TerminalCandidate(
                    "duplicate",
                    "new_investment",
                    [event("x", 1, 2, 3, 5), event("x", 4, 5, 6, 5)],
                ),
                current_step=0,
            )
        with self.assertRaises(ValueError):
            evaluate_candidate(
                TerminalCandidate("bad-order", "new_investment", [event("x", 5, 4, 6, 5)]),
                current_step=0,
            )
        with self.assertRaises(ValueError):
            evaluate_candidate(
                TerminalCandidate("sunk", "sunk_service", [event("x", 5, 5, 5, 5)], entry_cost=1),
                current_step=0,
            )
        with self.assertRaises(ValueError):
            evaluate_candidate(
                TerminalCandidate("nan", "new_investment", [event("x", 5, 5, 5, float("nan"))]),
                current_step=0,
            )

    def test_10_rejects_negative_minimum_net(self):
        candidate = TerminalCandidate(
            "zero-net",
            "new_investment",
            [event("sale", 710, 711, 712, 10, 0)],
            entry_cost=10,
        )
        with self.assertRaises(ValueError) as ctx:
            evaluate_candidate(candidate, current_step=709, minimum_net=-1)
        self.assertIn("minimum_net", str(ctx.exception))

        with self.assertRaises(ValueError):
            evaluate_candidate(candidate, current_step=709, minimum_net=float("-inf"))

    def test_11_zero_and_negative_net_remain_liquidate_under_nonneg_floor(self):
        zero = TerminalCandidate(
            "zero-net",
            "new_investment",
            [event("sale", 710, 711, 712, 10, 0)],
            entry_cost=10,
        )
        neg = TerminalCandidate(
            "neg-net",
            "new_investment",
            [event("sale", 710, 711, 712, 5, 0)],
            entry_cost=10,
        )
        # Default floor 0: exact zero and negative stay liquidate.
        self.assertEqual(evaluate_candidate(zero, current_step=709).mode, "liquidate")
        self.assertEqual(evaluate_candidate(neg, current_step=709).mode, "liquidate")
        # Explicit non-negative floor still rejects them.
        self.assertEqual(
            evaluate_candidate(zero, current_step=709, minimum_net=0.0).mode, "liquidate"
        )
        self.assertEqual(
            evaluate_candidate(neg, current_step=709, minimum_net=0.0).mode, "liquidate"
        )


@unittest.skipUnless(
    EVALUATOR.exists() and LOADER.exists() and ENGINE_DIR.exists(),
    "preserved engine not materialized",
)
class ExactEngineTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("p22_evaluator", EVALUATOR)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load evaluator at {EVALUATOR}")
        cls.ev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ev)
        cls.engine, cls.hashes = cls.ev.get_engine(ENGINE_DIR, LOADER)
        cls.config = json.loads(ENGINE_JSON.read_text())["configuration"]
        cls.episode_steps = int(cls.config["episodeSteps"])

    def fixture(self, *, step, money0=1234, money1=5678):
        e, S = self.engine, self.ev.Struct
        cfg = S({
            key: value.get("default") if isinstance(value, dict) else value
            for key, value in e.specification["configuration"].items()
        })
        cfg.weedSpawnChance = 0
        farms = [e._new_farm(10, money0), e._new_farm(10, money1)]
        market = e._new_market()
        town = {"unlocked_shops": []}
        state = []
        for seat in range(2):
            private = e._new_private()
            state.append(S(
                observation=S(
                    player=seat,
                    step=step,
                    day=step // 24,
                    hour=step % 24,
                    farms=farms,
                    private=private,
                    market=market,
                    town=town,
                ),
                action={"farmer": ["PASS"], "hands": [], "market": []},
                status="ACTIVE",
                reward=0,
            ))
        return state, S(configuration=cfg, done=False, info={"seed": 9600803})

    def test_07_preserved_config_and_helper_share_exact_terminal_boundary(self):
        self.assertEqual(self.episode_steps, 720)
        self.assertEqual(terminal_decision_step(self.episode_steps), 718)

    def test_08_exact_interpreter_settles_at_718_to_actual_money(self):
        state, env = self.fixture(step=718)
        self.engine.interpreter(state, env)
        self.assertEqual([s.status for s in state], ["DONE", "DONE"])
        self.assertEqual([s.reward for s in state], [1234.0, 5678.0])

    def test_09_step_717_is_not_terminal_settlement(self):
        state, env = self.fixture(step=717)
        self.engine.interpreter(state, env)
        self.assertEqual([s.status for s in state], ["ACTIVE", "ACTIVE"])
        self.assertEqual([s.reward for s in state], [0, 0])


if __name__ == "__main__":
    unittest.main()
