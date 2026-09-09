from __future__ import annotations

import copy
import unittest

import action_cardinality_gate as gate
from test_support import _farm, _record, _replay


class AnalyzeReplayTests(unittest.TestCase):
    def test_exact_cardinality_passes(self) -> None:
        replay = _replay([2, 2], [["PASS"], ["WEST"]], seat=1)
        replay["steps"][0][1]["action"]["hands"] = [["PASS"], ["PASS"]]
        replay["steps"][1][1]["action"]["hands"] = [["WEST"], ["WATER"]]
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["over_cardinality_transition_count"], 0)
        self.assertEqual(result["omitted_hand_rows_total"], 0)

    def test_under_cardinality_is_explicit_but_allowed(self) -> None:
        replay = _replay([3, 3], [[["PASS"]], [["PASS"]]], seat=1)
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["over_cardinality_transition_count"], 0)
        self.assertEqual(result["omitted_hand_rows_total"], 4)

    def test_day5_same_step_trap_uses_previous_observation(self) -> None:
        replay = _replay(
            [4, 5],
            [
                [["PASS"] for _ in range(4)],
                [["WEST"] for _ in range(5)],
            ],
            seat=1,
        )
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["over_cardinality_transition_count"], 1)
        violation = result["violations"][0]
        self.assertEqual(violation["step"], 1)
        self.assertEqual(violation["pre_observation_step"], 0)
        self.assertEqual(violation["observable_hands"], 4)
        self.assertEqual(violation["submitted_hand_rows"], 5)
        self.assertEqual(violation["trailing_rows"], [["WEST"]])

    def test_failed_hire_boundary_witness_rejects(self) -> None:
        replay = _replay(
            [3, 3],
            [
                [["PASS"] for _ in range(3)],
                [["PASS"] for _ in range(3)] + [["PICKUP", "WHEAT"]],
            ],
            seat=1,
            markets=[[["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]], []],
        )
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["over_cardinality_transition_count"], 1)
        self.assertEqual(result["trailing_opcode_counts"], {"PICKUP": 1})

    def test_bootstrap_step_uses_its_initial_observation(self) -> None:
        replay = _replay([0], [[["PASS"]]], seat=1)
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["over_cardinality_transition_count"], 1)
        self.assertEqual(result["violations"][0]["alignment"], "bootstrap-same-step")

    def test_own_farm_index_not_opponent_index(self) -> None:
        replay = _replay([4, 4], [[], [["PASS"] for _ in range(5)]], seat=1)
        replay["steps"][0][1]["observation"]["farms"][0] = _farm(9)
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["violations"][0]["observable_hands"], 4)

    def test_consecutive_violations_collapse_into_range(self) -> None:
        replay = _replay(
            [4, 4, 4, 4],
            [[["PASS"] for _ in range(4)]]
            + [[[["WEST"]][0] for _ in range(5)] for _ in range(3)],
            seat=1,
        )
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["over_cardinality_transition_count"], 3)
        self.assertEqual(
            result["violation_ranges"],
            [
                {
                    "start_step": 1,
                    "end_step": 3,
                    "count": 3,
                    "observable_hands": 4,
                    "submitted_hand_rows": 5,
                    "start_day": 0,
                    "start_hour": 0,
                    "end_day": 0,
                    "end_hour": 2,
                }
            ],
        )

    def test_move_opcodes_are_grouped(self) -> None:
        replay = _replay([1, 1], [["PASS"], [["NORTH"], ["WEST"], ["WATER"]]], seat=1)
        replay["steps"][0][1]["action"]["hands"] = [["PASS"]]
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["trailing_opcode_counts"], {"MOVE": 1, "WATER": 1})

    def test_canonical_market_no_order_is_not_absence(self) -> None:
        replay = _replay(
            [0],
            [[]],
            seat=1,
            markets=[[gate.CANONICAL_MARKET_NO_ORDER, []]],
        )
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["canonical_market_no_order_row_count"], 1)
        self.assertEqual(result["empty_market_row_count"], 1)

    def test_false_quantity_is_not_canonical_zero(self) -> None:
        replay = _replay([0], [[]], seat=1, markets=[[['SELL', 'WHEAT', False]]])
        result = gate.analyze_replay(replay, seat=1)
        self.assertEqual(result["canonical_market_no_order_row_count"], 0)

    def test_missing_hands_field_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        del replay["steps"][0][1]["action"]["hands"]
        with self.assertRaisesRegex(gate.GateInputError, "action.hands is absent"):
            gate.analyze_replay(replay, seat=1)

    def test_missing_market_field_is_invalid_not_empty(self) -> None:
        replay = _replay([0], [[]], seat=1)
        del replay["steps"][0][1]["action"]["market"]
        with self.assertRaisesRegex(gate.GateInputError, "action.market is absent"):
            gate.analyze_replay(replay, seat=1)

    def test_empty_hand_row_is_invalid(self) -> None:
        replay = _replay([1], [[[]]], seat=1)
        with self.assertRaisesRegex(gate.GateInputError, "non-empty action row"):
            gate.analyze_replay(replay, seat=1)

    def test_bool_player_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        replay["steps"][0][1]["observation"]["player"] = True
        with self.assertRaisesRegex(gate.GateInputError, "exact integer"):
            gate.analyze_replay(replay, seat=1)

    def test_wrong_player_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        replay["steps"][0][1]["observation"]["player"] = 0
        with self.assertRaisesRegex(gate.GateInputError, "expected seat 1"):
            gate.analyze_replay(replay, seat=1)

    def test_missing_own_farm_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        replay["steps"][0][1]["observation"]["farms"] = [_farm(0)]
        with self.assertRaisesRegex(gate.GateInputError, "no own farm"):
            gate.analyze_replay(replay, seat=1)

    def test_bool_day_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        replay["steps"][0][1]["observation"]["day"] = False
        with self.assertRaisesRegex(gate.GateInputError, "exact integer"):
            gate.analyze_replay(replay, seat=1)

    def test_expected_episode_and_agent_are_bound(self) -> None:
        replay = _replay([0], [[]], seat=1, episode_id=77, agent_name="Titan")
        result = gate.analyze_replay(
            replay, seat=1, expected_episode_id=77, expected_agent_name="Titan"
        )
        self.assertEqual((result["episode_id"], result["agent_name"]), (77, "Titan"))
        with self.assertRaisesRegex(gate.GateInputError, "episode id mismatch"):
            gate.analyze_replay(replay, seat=1, expected_episode_id=78)
        with self.assertRaisesRegex(gate.GateInputError, "agent name mismatch"):
            gate.analyze_replay(replay, seat=1, expected_agent_name="Other")

    def test_wrong_environment_is_invalid(self) -> None:
        replay = _replay([0], [[]], seat=1)
        replay["name"] = "not-kaggriculture"
        with self.assertRaisesRegex(gate.GateInputError, "replay.name"):
            gate.analyze_replay(replay, seat=1)

    def test_transition_ledger_is_deterministic(self) -> None:
        replay = _replay([2, 2], [[["PASS"], ["PASS"]], [["WEST"], ["WATER"]]], seat=1)
        first = gate.analyze_replay(copy.deepcopy(replay), seat=1)
        second = gate.analyze_replay(copy.deepcopy(replay), seat=1)
        self.assertEqual(first["transition_ledger_sha256"], second["transition_ledger_sha256"])

if __name__ == "__main__":
    unittest.main()
