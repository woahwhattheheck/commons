# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_v224_raw_slots``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_v224_raw_slots.py
"""

from __future__ import annotations

import copy
import json
import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_v224_raw_slots as lane  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}


class StructConfig:
    maxMarketOrdersPerTurn = 10


def action(market):
    return {"farmer": ["PASS"], "hands": [], "market": copy.deepcopy(market)}


def observation(step=0):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": 1000,
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    prices = {product: 10 for product in r04.PRODUCTS}
    inventory = {product: 10000 for product in r04.PRODUCTS}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": {}, "seeds": {}},
            "market": {"prices": prices, "inventory": inventory},
            "town": {"unlocked_shops": []}}


def _official_milk_price(inventory):
    """Pinned engine MILK quote for inventory >= I0 (engine blob 3c202c7e...)."""
    base = 160
    i0 = 10000
    target = 1.60
    production_window = 122
    assert inventory >= i0
    amp = target * base / production_window
    return max(1, int(round(base - amp * (inventory - i0))))


def _official_lockstep_milk_sales(own_market, rival_market):
    """Execute the pinned engine's SELL/MILK lockstep subset.

    This is deliberately tiny: it preserves the official `_process_market`
    contract that raw list indices define rounds, both players quote from the
    same pre-commit inventory in a round, and successful sales then increase
    market inventory. Each player begins with two MILK, enough for this witness.
    """
    queues = [list(own_market), list(rival_market)]
    cash = [0, 0]
    shed = [2, 2]
    inventory = 10000

    for row_index in range(max(len(queue) for queue in queues)):
        remaining = [0, 0]
        for player_id, queue in enumerate(queues):
            if row_index >= len(queue):
                continue
            row = queue[row_index]
            if (isinstance(row, list) and len(row) >= 3
                    and row[0] == "SELL" and row[1] == "MILK"
                    and type(row[2]) is int and row[2] > 0):
                remaining[player_id] = row[2]

        while any(remaining):
            # Official engine quotes both current units before either commit.
            quote = _official_milk_price(inventory)
            quotes = [quote if remaining[player_id] else None for player_id in range(2)]
            committed = False
            for player_id, price in enumerate(quotes):
                if price is None:
                    continue
                if shed[player_id] <= 0:
                    remaining[player_id] = 0
                    continue
                shed[player_id] -= 1
                cash[player_id] += price
                if price > 1:
                    inventory += 1
                remaining[player_id] -= 1
                committed = True
            if not committed:
                break

    return cash, inventory


class V224RawSlots(unittest.TestCase):
    def tearDown(self):
        r04.V224_RAW_SLOTS = False

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_v224_raw_slots"], False)
        self.assertIs(Features(**data).r04_v224_raw_slots, False)

    def test_falsey_slot_is_hard_barrier_and_parent_object_is_retained(self):
        parent = action([["HIRE"], [], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertIs(out, parent)
        self.assertEqual(out["market"], [["HIRE"], [], ["SELL", "WOOL", 2]])

    def test_none_slot_is_hard_barrier(self):
        parent = action([["HIRE"], None, ["SELL", "WOOL", 2]])
        self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_sell_bubbles_across_contiguous_effectful_rows(self):
        parent = action([["HIRE"], ["BUY_SEED", "WHEAT", 1], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertIsNot(out, parent)
        self.assertEqual(out["market"],
                         [["SELL", "WOOL", 2], ["HIRE"], ["BUY_SEED", "WHEAT", 1]])
        self.assertEqual(parent["market"],
                         [["HIRE"], ["BUY_SEED", "WHEAT", 1], ["SELL", "WOOL", 2]])

    def test_same_item_product_buy_remains_barrier(self):
        parent = action([["HIRE"], ["BUY_PRODUCT", "WOOL", 1], ["SELL", "WOOL", 2]])
        self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_unrelated_product_buy_keeps_v224_crossing_semantics(self):
        parent = action([["BUY_PRODUCT", "WHEAT", 1], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertEqual(out["market"],
                         [["SELL", "WOOL", 2], ["BUY_PRODUCT", "WHEAT", 1]])

    def test_zero_quantity_and_malformed_rows_are_barriers(self):
        for barrier in (["BUY_SEED", "WHEAT", 0], ["BUY_SEED"], "bad"):
            parent = action([["HIRE"], barrier, ["SELL", "WOOL", 2]])
            with self.subTest(barrier=barrier):
                self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_unknown_positive_verb_is_malformed_barrier(self):
        parent = action([["HIRE"], ["BOGUS", "WOOL", 1], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertIs(out, parent)
        self.assertEqual(out["market"],
                         [["HIRE"], ["BOGUS", "WOOL", 1], ["SELL", "WOOL", 2]])

    def test_known_verbs_with_unknown_items_are_malformed_barriers(self):
        for barrier in (["BUY_PRODUCT", "BOGUS", 1],
                        ["BUY_ANIMAL", "BOGUS", 1],
                        ["BUY_SEED", "BOGUS", 1]):
            parent = action([["HIRE"], barrier, ["SELL", "WOOL", 2]])
            with self.subTest(barrier=barrier):
                self.assertIs(lane.sales_first_raw_slots(parent), parent)

        malformed_sell = action([["HIRE"], ["SELL", "BOGUS", 1]])
        self.assertIs(lane.sales_first_raw_slots(malformed_sell), malformed_sell)

    def test_engine_rejected_buy_product_item_is_malformed_barrier(self):
        # `_process_market` only accepts BUY_PRODUCT for WHEAT/FERTILIZER even
        # though MILK is a valid SELL product. The no-op row must remain a raw
        # timing barrier rather than being crossed by a later SELL.
        parent = action([["HIRE"], ["BUY_PRODUCT", "MILK", 1], ["SELL", "WOOL", 2]])
        self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_changed_prefix_retains_raw_cardinality(self):
        parent = action([["HIRE"], ["SELL", "WOOL", 2], [],
                         ["BUY_SEED", "WHEAT", 1], ["SELL", "MILK", 3]])
        out = lane.sales_first_raw_slots(parent)
        self.assertEqual(len(out["market"]), len(parent["market"]))
        self.assertEqual(out["market"][2], [])
        self.assertEqual(out["market"],
                         [["SELL", "WOOL", 2], ["HIRE"], [],
                          [["SELL", "MILK", 3]][0], ["BUY_SEED", "WHEAT", 1]])

    def test_over_cap_frozen_change_keeps_only_raw_executable_prefix(self):
        parent = action([[], *[["HIRE"] for _ in range(9)], ["SELL", "WOOL", 1]])
        out = lane.sales_first_raw_slots(parent, max_orders=10)
        self.assertIsNot(out, parent)
        self.assertEqual(len(parent["market"]), 11)
        self.assertEqual(out["market"], parent["market"][:10])
        self.assertEqual(out["market"][0], [])
        self.assertNotIn(["SELL", "WOOL", 1], out["market"])

    def test_over_cap_unchanged_frozen_prefix_does_not_truncate_parent(self):
        parent = action([["HIRE"] for _ in range(10)] + [["SELL", "WOOL", 1]])
        out = lane.sales_first_raw_slots(parent, max_orders=10)
        self.assertIs(out, parent)
        self.assertEqual(len(out["market"]), 11)
        self.assertEqual(out["market"][-1], ["SELL", "WOOL", 1])

    def test_over_cap_malformed_barrier_preserves_prefix_but_hides_tail(self):
        prefix = [["BOGUS", "WOOL", 1], ["SELL", "WOOL", 2]]
        prefix += [["HIRE"] for _ in range(8)]
        parent = action(prefix + [["SELL", "MILK", 1]])
        out = lane.sales_first_raw_slots(parent, max_orders=10)
        self.assertIsNot(out, parent)
        self.assertEqual(out["market"], prefix)
        self.assertEqual(out["market"][0], ["BOGUS", "WOOL", 1])
        self.assertEqual(out["market"][1], ["SELL", "WOOL", 2])
        self.assertNotIn(["SELL", "MILK", 1], out["market"])

    def test_router_flag_off_preserves_frozen_v224_compaction(self):
        parent = action([[], ["SELL", "WOOL", 2]])
        r04.V224_RAW_SLOTS = False
        out = r04._v224_sales_first(copy.deepcopy(parent))
        self.assertEqual(out["market"], [["SELL", "WOOL", 2]])

    def test_router_flag_on_prevents_falsey_compaction(self):
        parent = action([[], ["SELL", "WOOL", 2]])
        r04.V224_RAW_SLOTS = True
        out = r04._v224_sales_first(parent, dict(CONFIG))
        self.assertIs(out, parent)
        self.assertEqual(out["market"], [[], ["SELL", "WOOL", 2]])

    def test_router_flag_on_accepts_struct_configuration(self):
        parent = action([[], ["SELL", "WOOL", 2]])
        r04.V224_RAW_SLOTS = True
        out = r04._v224_sales_first(parent, StructConfig())
        self.assertIs(out, parent)
        self.assertEqual(out["market"], [[], ["SELL", "WOOL", 2]])

    def test_nonstandard_or_missing_market_cap_fails_closed_to_parent(self):
        nonstandard_struct = StructConfig()
        nonstandard_struct.maxMarketOrdersPerTurn = 5
        for configuration in (None, {}, {"maxMarketOrdersPerTurn": 5},
                              nonstandard_struct,
                              {"maxMarketOrdersPerTurn": True}):
            with self.subTest(configuration=configuration):
                parent = action([[], ["SELL", "WOOL", 2]])
                r04.V224_RAW_SLOTS = True
                out = r04._v224_sales_first(parent, configuration)
                self.assertIs(out, parent)
                self.assertEqual(out["market"], [[], ["SELL", "WOOL", 2]])

    def test_router_flag_on_preserves_reorder_telemetry(self):
        r04.V224_RAW_SLOTS = True
        before = r04._V224_REPORT["reordered_market_turns"]
        parent = action([["HIRE"], ["SELL", "WOOL", 2]])
        out = r04._v224_sales_first(parent, dict(CONFIG))
        self.assertIsNot(out, parent)
        self.assertEqual(out["market"], [["SELL", "WOOL", 2], ["HIRE"]])
        self.assertEqual(r04._V224_REPORT["reordered_market_turns"], before + 1)

        before = r04._V224_REPORT["reordered_market_turns"]
        barrier = action([[], ["SELL", "WOOL", 2]])
        out = r04._v224_sales_first(barrier, dict(CONFIG))
        self.assertIs(out, barrier)
        self.assertEqual(r04._V224_REPORT["reordered_market_turns"], before)

    def test_generated_callers_forward_runtime_configuration(self):
        source = (ROOT / "r04_full_router.py").read_text(encoding="utf-8")
        self.assertIn("_v224_sales_first(action, configuration)", source)
        self.assertNotIn("_v224_sales_first(action)\n", source)

    def test_raw_slot_changes_lockstep_receipt_against_rival_sell(self):
        # Rival sells MILK in row 0. With the authored None barrier our SELL is
        # row 1 and sees the post-rival inventory; frozen V224 compaction moves
        # it into row 0, where both players quote from the same pre-commit state.
        parent = action([None, ["SELL", "MILK", 1]])
        rival = [["SELL", "MILK", 1], None]

        r04.V224_RAW_SLOTS = False
        compacted = r04._v224_sales_first(copy.deepcopy(parent))
        self.assertEqual(compacted["market"], [["SELL", "MILK", 1]])

        r04.V224_RAW_SLOTS = True
        preserved = r04._v224_sales_first(parent, dict(CONFIG))
        self.assertIs(preserved, parent)
        self.assertEqual(preserved["market"], [None, ["SELL", "MILK", 1]])

        compact_cash, compact_inventory = _official_lockstep_milk_sales(
            compacted["market"], rival)
        preserved_cash, preserved_inventory = _official_lockstep_milk_sales(
            preserved["market"], rival)

        self.assertEqual(compact_cash[0], 160)
        self.assertEqual(preserved_cash[0], 158)
        self.assertEqual(compact_inventory, 10002)
        self.assertEqual(preserved_inventory, 10002)
        self.assertGreater(compact_cash[0], preserved_cash[0])

    def test_install_and_titan_diagnostics_carry_key(self):
        r04.install(v224_raw_slots=True)
        self.assertIs(r04.V224_RAW_SLOTS, True)
        r04.install(v224_raw_slots=False)
        self.assertIs(r04.V224_RAW_SLOTS, False)

        agent = TitanAgent(Features(r04_sale_window=True, r04_v224_raw_slots=True))
        agent.act(observation(), dict(CONFIG))
        self.assertIs(r04.V224_RAW_SLOTS, True)
        self.assertIs(agent.diagnostics["v224_raw_slots"], True)


# Additional bounded structural properties; no router/strength verdict.
# Literal, independently declared alphabets; never derived from helper predicates.
VALID_ROWS = (
    ['HIRE'], ['BUY_LAND'], ['BUY_SEED', 'WHEAT', 1],
    ['BUY_PRODUCT', 'WHEAT', 1], ['BUY_PRODUCT', 'FERTILIZER', 2],
    ['BUY_ANIMAL', 'COW', 1], ['SELL', 'MILK', 1],
    ['SELL', 'WHEAT', 1], ['SELL', 'FERTILIZER', 2],
)
BARRIER_ROWS = (
    [], None, 'bad', 0, False, {}, ['BOGUS', 'MILK', 1],
    ['BUY_PRODUCT', 'MILK', 1], ['SELL', 'MILK', 0],
    ['BUY_SEED', 'WHEAT', True], ['BUY_ANIMAL', 'BOGUS', 1],
)
COUNTS = {}


def _case(rows):
    return {'farmer': ['PASS'], 'hands': [], 'market': copy.deepcopy(rows)}


def _positive_segment_oracle(rows):
    """Insertion-form oracle only for the declared all-positive alphabet.

    Unlike the implementation's swaps, insert each new SELL after the nearest
    prior SELL or same-product purchase; all other rows retain their order.
    It deliberately does not call any helper predicate or frozen projection.
    """
    result = []
    for row in rows:
        insertion = len(result)
        if row[0] == 'SELL':
            for earlier in range(len(result) - 1, -1, -1):
                prior = result[earlier]
                if (prior[0] == 'SELL'
                        or (prior[0] in ('BUY_PRODUCT', 'BUY_ANIMAL')
                            and prior[1] == row[1])):
                    insertion = earlier + 1
                    break
            else:
                insertion = 0
        result.insert(insertion, copy.deepcopy(row))
    return result


class V224RawSlotProperties(unittest.TestCase):
    def _check_preservation(self, parent, before, out, expected):
        self.assertEqual(out['market'], expected)
        self.assertEqual(parent, before)
        self.assertIs(out['farmer'], parent['farmer'])
        self.assertIs(out['hands'], parent['hands'])
        if expected == before['market']:
            self.assertIs(out, parent)
        self.assertIs(lane.sales_first_raw_slots(out), out)

    def test_all_positive_short_queues_match_independent_oracle(self):
        count = 0
        for length in range(5):
            for sequence in itertools.product(VALID_ROWS, repeat=length):
                parent = _case(list(sequence))
                before = copy.deepcopy(parent)
                out = lane.sales_first_raw_slots(parent)
                self._check_preservation(
                    parent, before, out, _positive_segment_oracle(sequence))
                count += 1
        self.assertEqual(count, 7381)
        COUNTS['positive_queue_parity'] = count

    def test_barriers_separate_independent_ordering_segments(self):
        segments = [sequence for length in range(3)
                    for sequence in itertools.product(VALID_ROWS, repeat=length)]
        count = 0
        for barrier, left, right in itertools.product(BARRIER_ROWS, segments, segments):
            parent = _case(list(left) + [barrier] + list(right))
            before = copy.deepcopy(parent)
            out = lane.sales_first_raw_slots(parent)
            expected = (_positive_segment_oracle(left) + [barrier]
                        + _positive_segment_oracle(right))
            self._check_preservation(parent, before, out, expected)
            # Absolute raw barrier index is invariant, even when both sides move.
            self.assertEqual(out['market'][len(left)], barrier)
            count += 1
        self.assertEqual(count, 91091)
        COUNTS['barrier_segment_cases'] = count

    def test_capped_suffix_never_becomes_executable(self):
        tails = ([['SELL', 'MILK', 999]], [None, ['HIRE']], ['bad', {'tail': 1}])
        count = 0
        for length in range(4):
            for sequence in itertools.product(VALID_ROWS, repeat=length):
                prefix = list(sequence) + [None] * (10 - length)
                expected = _positive_segment_oracle(sequence) + [None] * (10 - length)
                for tail in tails:
                    parent = _case(prefix + tail)
                    before = copy.deepcopy(parent)
                    out = lane.sales_first_raw_slots(parent)
                    self._check_preservation(parent, before, out, expected)
                    self.assertEqual(len(out['market']), 10)
                    count += 1
        self.assertEqual(count, 2460)
        COUNTS['capped_suffix_cases'] = count

    def test_unchanged_frozen_prefix_keeps_original_tail_and_identity(self):
        # The lane must not unconditionally truncate: frozen V224 leaves this
        # prefix unchanged, so its downstream visibility must also be preserved.
        parent = _case([['HIRE']] * 10 + [['SELL', 'MILK', 999]])
        self.assertIs(lane.sales_first_raw_slots(parent), parent)
        self.assertEqual(len(parent['market']), 11)

    def test_argument_free_atomic_orders_remain_crossable(self):
        # Pinned _parse_order accepts both verbs with no second argument;
        # requiring a quadrant for BUY_LAND would be an incorrect new barrier.
        for atomic in (['HIRE'], ['BUY_LAND'], ['BUY_LAND', 'ignored']):
            parent = _case([atomic, ['SELL', 'MILK', 1]])
            self.assertEqual(lane.sales_first_raw_slots(parent)['market'],
                             [['SELL', 'MILK', 1], atomic])

    def test_same_product_funding_dependency_is_not_crossed(self):
        for product in ('WHEAT', 'FERTILIZER'):
            parent = _case([['HIRE'], ['BUY_PRODUCT', product, 1],
                            ['SELL', product, 2]])
            self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_malformed_quantities_remain_absolute_barriers(self):
        for quantity in (False, True, 0, -1, 1.0, '1', None, [], {}):
            parent = _case([['HIRE'], ['BUY_SEED', 'WHEAT', quantity],
                            ['SELL', 'MILK', 1]])
            self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_unavailable_overflow_projection_keeps_parent(self):
        for quantity in (float('inf'), -float('inf')):
            parent = _case([['SELL', 'MILK', quantity]] + [['HIRE']] * 9
                           + [['SELL', 'WOOL', 1]])
            self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_invalid_helper_cap_is_exact_identity(self):
        # The generated router's stricter exact-10 guard has separate coverage.
        # Here only the helper's public parameter boundary is under test.
        for cap in (None, False, True, 0, -1, 10.0, '10', [], {}):
            parent = _case([['HIRE'], ['SELL', 'MILK', 1]])
            self.assertIs(lane.sales_first_raw_slots(parent, max_orders=cap), parent)

    def test_non_market_surfaces_are_not_rewritten(self):
        for parent in (None, [], 'bad', {}, {'market': None}, {'market': ()}):
            self.assertIs(lane.sales_first_raw_slots(parent), parent)


if __name__ == "__main__":
    unittest.main()
