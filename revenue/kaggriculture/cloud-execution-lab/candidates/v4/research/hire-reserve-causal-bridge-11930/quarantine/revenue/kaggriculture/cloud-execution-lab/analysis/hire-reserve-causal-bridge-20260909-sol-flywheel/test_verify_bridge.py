from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

import verify_bridge as bridge

HERE = Path(__file__).resolve().parent


def farm(cash: int, hands: int, *, hires: int = 0) -> dict:
    return {
        "farmer": [4, 4],
        "hands": [[4, 4] for _ in range(hands)],
        "hires_today": hires,
        "money": float(cash),
        "tiles": [[None]],
        "unlocked_quadrants": ["NW"],
    }


def private(tag: int = 0) -> dict:
    return {
        "inventories": [{}],
        "seeds": {"MELON": tag},
        "shed": {"WHEAT": 1},
    }


def observation(seat: int, cash: int, hands: int, *, hires: int = 0,
                private_tag: int = 0) -> dict:
    farms = [farm(0, 0), farm(0, 0)]
    farms[seat] = farm(cash, hands, hires=hires)
    return {
        "player": seat,
        "day": 0,
        "hour": 0,
        "farms": farms,
        "private": private(private_tag),
        "market": {"inventory": {}},
        "town": {"unlocked_shops": []},
    }


def action(*, hand_rows: int = 0, hires: int = 0,
           other_market: list | None = None) -> dict:
    market = [["HIRE"] for _ in range(hires)]
    if other_market:
        market.extend(copy.deepcopy(other_market))
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(hand_rows)],
        "market": market,
    }


def record(obs: dict, act: dict) -> dict:
    return {"observation": obs, "action": act, "reward": 0, "status": "ACTIVE", "info": {}}


def synthetic_bridge(*, private_mismatch: bool = False,
                     other_market: list | None = None) -> dict:
    # Row 1 action is selected from row 0. Row 1's post-state intentionally
    # differs in hand count, so a post-state orientation mutant misses the twin.
    row0 = [
        record(observation(0, 42, 0), action()),
        record(observation(1, 6, 0, private_tag=int(private_mismatch)), action()),
    ]
    shared = action(hires=4, other_market=other_market)
    if other_market:
        # The detector must reject this as not an isolated HIRE transition; post
        # cash is deliberately arbitrary because the action is never admitted.
        after_cash = (35, 2)
    else:
        after_cash = (35, 2)
    row1 = [
        record(observation(0, after_cash[0], 4, hires=4), copy.deepcopy(shared)),
        record(observation(1, after_cash[1], 3, hires=3), copy.deepcopy(shared)),
    ]
    row2 = [
        record(observation(0, 35, 4, hires=4), action(hand_rows=4)),
        record(observation(1, 2, 3, hires=3), action(hand_rows=4)),
    ]
    row3 = [
        record(observation(0, 35, 4, hires=4), action(hand_rows=4)),
        record(observation(1, 2, 3, hires=3), action(hand_rows=3)),
    ]
    return {
        "configuration": {
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "turnsPerDay": 24,
        },
        "steps": [row0, row1, row2, row3],
        "info": {"EpisodeId": 1, "Agents": [{"Name": "A"}, {"Name": "B"}]},
        "rewards": [1, 0],
    }


class PrimitiveContractTest(unittest.TestCase):
    def test_exact_fibonacci_hire_costs(self) -> None:
        self.assertEqual(bridge.hire_costs(0, 6), [1, 1, 2, 3, 5, 8])
        self.assertEqual(bridge.minimum_cash_for_hires(0, 4), 7)

    def test_one_dollar_flips_fourth_hire(self) -> None:
        six = bridge.simulate_hires(6, 0, 4)
        seven = bridge.simulate_hires(7, 0, 4)
        self.assertEqual((six["executed"], six["remaining_cash"]), (3, 2.0))
        self.assertEqual((seven["executed"], seven["remaining_cash"]), (4, 0.0))

    def test_strict_json_rejects_duplicate_and_nonfinite(self) -> None:
        with self.assertRaises(bridge.BridgeError):
            bridge.strict_loads(b'{"x":1,"x":2}')
        with self.assertRaises(bridge.BridgeError):
            bridge.strict_loads(b'{"x":NaN}')

    def test_bool_is_not_cash_or_whole_number(self) -> None:
        with self.assertRaises(bridge.BridgeError):
            bridge.simulate_hires(True, 0, 1)
        with self.assertRaises(bridge.BridgeError):
            bridge.hire_costs(True, 1)


class DetectorTest(unittest.TestCase):
    def test_uses_action_k_with_observation_k_minus_one(self) -> None:
        document = synthetic_bridge()
        found = bridge._find_bridge(document)
        self.assertEqual(found["observation_row"], 0)
        self.assertEqual(found["action_row"], 1)
        self.assertEqual(found["hands_before"], [0, 0])
        self.assertEqual(found["hands_after"], [4, 3])
        self.assertEqual(found["minimum_extra_cash_for_constrained_seat"], 1)
        self.assertFalse(bridge.own_noncash_equal(document, 1))

    def test_private_difference_breaks_cash_only_twin(self) -> None:
        with self.assertRaisesRegex(bridge.BridgeError, "no cash-only"):
            bridge._find_bridge(synthetic_bridge(private_mismatch=True))

    def test_non_hire_market_order_breaks_isolation(self) -> None:
        with self.assertRaisesRegex(bridge.BridgeError, "no cash-only"):
            bridge._find_bridge(
                synthetic_bridge(other_market=[["SELL", "WHEAT", 1]])
            )

    def test_downstream_block_uses_previous_observation_hands(self) -> None:
        found = bridge._find_bridge(synthetic_bridge())
        block = found["downstream"]
        self.assertEqual((block["start_action_row"], block["end_action_row"]), (2, 2))
        self.assertEqual(block["rows"], 1)
        self.assertEqual(block["unreachable_actions"], [["PASS"]])

    def test_observed_transition_mismatch_fails_closed(self) -> None:
        document = synthetic_bridge()
        document["steps"][1][1]["observation"]["farms"][1]["money"] = 3.0
        with self.assertRaisesRegex(bridge.BridgeError, "observed cash"):
            bridge._find_bridge(document)


class ReceiptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.receipt = bridge.strict_loads((HERE / "BRIDGE.json").read_bytes())

    def test_committed_receipt_verifies(self) -> None:
        valid, detail = bridge.verify_receipt(self.receipt)
        self.assertTrue(valid, detail)
        self.assertEqual(
            self.receipt["report_sha256"],
            "1a66999a5aa86d3c4bf9d3e585a02f92b1d7e1c23af82dad10182c5348e6bfa5",
        )

    def test_digest_tamper_is_rejected(self) -> None:
        changed = copy.deepcopy(self.receipt)
        changed["candidate_target"]["minimum_extra_cash"] = 2
        valid, detail = bridge.verify_receipt(changed)
        self.assertFalse(valid)
        self.assertIn("report SHA-256", detail)

    def test_rehashed_fact_tamper_is_rejected(self) -> None:
        changed = copy.deepcopy(self.receipt)
        changed["candidate_target"]["minimum_extra_cash"] = 2
        changed = bridge.seal(changed)
        valid, detail = bridge.verify_receipt(changed)
        self.assertFalse(valid)
        self.assertIn("candidate target cash", detail)

    def test_raw_replay_reproduction_when_supplied(self) -> None:
        path = os.environ.get("TITAN_REPLAY_107130860")
        if not path:
            self.skipTest("exact Slack custody object not supplied")
        document, source = bridge.load_replay(Path(path))
        recomputed = bridge.audit_document(document, source=source)
        self.assertEqual(bridge.canonical_bytes(recomputed), bridge.canonical_bytes(self.receipt))


if __name__ == "__main__":
    unittest.main()
