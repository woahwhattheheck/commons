# SPDX-License-Identifier: Apache-2.0
"""Independent execution contracts for the intraday-hoarding strategy hypotheses.

Uses the existing archived evaluator/loader and unmodified pinned interpreter.
This is an acceptance companion, NOT another agent, strategy harness, or V4 root.
All worlds are constructed fixtures, not competitive gameplay evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import platform
import sys
import unittest

ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
RUNTIME = None
MUTATION = None
RECEIPT = {}
COUNTS = {"initializations": 0, "transitions": 0}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def action(unit=None, market=None, hands=None):
    return {"farmer": list(unit or ["PASS"]), "hands": copy.deepcopy(hands or []),
            "market": copy.deepcopy(market or [])}


def load_engine(root):
    root = Path(root).resolve()
    folder = root / "checks/reference"
    engine_path = folder / "engine/kaggriculture.py"
    if digest(engine_path) != ENGINE_SHA256:
        raise ValueError("Engine SHA256 mismatch; no silent rebaseline is permitted")
    evaluator = folder / "evaluator/evaluate.py"
    loader = folder / "evaluator/loader.py"
    # Their hashes are recorded as well as the loader's own three-file source gate.
    spec = importlib.util.spec_from_file_location("intraday_contract_evaluator", evaluator)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load the archived evaluator")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    engine, hashes = ev.get_engine(folder / "engine", loader)
    RECEIPT["source"] = {
        "engine_sha256": hashes, "engine_git_blob": ENGINE_BLOB,
        "evaluator_sha256": digest(evaluator), "loader_sha256": digest(loader),
        "contract_sha256": digest(__file__),
    }
    return engine, ev


def apply_mutation(engine, name):
    """Scratch in-memory semantic faults, never edits pinned source files."""
    table = {
        "allow_hinge_buys": ("_process_market", 'item in ("WHEAT", "FERTILIZER")',
                            'item in PRODUCTS'),
        "forbid_negative_inventory": ("_commit_unit", 'if op == "BUY_PRODUCT":\n',
            'if op == "BUY_PRODUCT":\n        if market["inventory"][item] <= 0:\n            return False\n'),
        "quote_prebuy_inventory": ("_process_market", 'market["inventory"][item] - 1',
                                   'market["inventory"][item]'),
        "disable_buy_capacity": ("_commit_unit", 'if sum(private["shed"].values()) >= shed_capacity:',
                                 'if False:'),
        "cap_hand_inventory": ("_inv_add", 'inv.get(item, 0) + n',
                               'min(100, inv.get(item, 0) + n)'),
        "retain_eod_overflow": ("_drop_inventories_to_shed", 'room = max(0, capacity - current)',
                                'room = n'),
        "admit_floor_sales": ("_commit_unit", 'if price > 1:', 'if True:'),
        "town_before_market": ("interpreter", '    _process_market(state, env)\n    _town_consume(env, state, step)',
            '    _town_consume(env, state, step)\n    _process_market(state, env)'),
        "cap_pickup_quantity": ("_apply_unit_action", 'n = min(n, available)',
                               'n = min(n, available, 1)'),
    }
    if name not in table:
        raise ValueError("Unknown semantic fault: " + name)
    target, old, new = table[name]
    source = inspect.getsource(getattr(engine, target))
    if old not in source:
        raise ValueError("Mutation seam not found: " + name)
    patched = source.replace(old, new)
    exec(compile(patched, engine.__file__ + "#contract-mutant-" + name, "exec"), engine.__dict__)
    RECEIPT["mutation"] = {"name": name, "target": target,
                            "function_sha256": hashlib.sha256(patched.encode()).hexdigest()}


class IntradayMarketContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e, cls.ev = load_engine(RUNTIME)
        if MUTATION:
            apply_mutation(cls.e, MUTATION)

    def world(self, seat=0, item="WHEAT", inventory=10000, cash=1000000,
              shed=0, capacity=100, shops=()):
        e, S = self.e, self.ev.Struct
        cfg = S({k: v.get("default") if isinstance(v, dict) else v
                 for k, v in e.specification["configuration"].items()})
        cfg.weedSpawnChance = 0
        cfg.shedCapacity = capacity
        cfg.seed = 9183321
        env = S(configuration=cfg, done=False, info={})
        states = [S(observation=S(), action=action(), status="ACTIVE", reward=0) for _ in range(2)]
        e.interpreter(states, env)
        COUNTS["initializations"] += 1
        for farm in states[0].observation.farms:
            farm["money"] = cash
        states[0].observation.market["inventory"][item] = inventory
        e._refresh_prices(states[0].observation.market)
        states[0].observation.town["unlocked_shops"] = list(shops)
        states[seat].observation.private["shed"][item] = shed
        return states, env

    def tick(self, states, env, step, seat=0, own=None, rival=None):
        for i, s in enumerate(states):
            s.observation.step = step
            s.observation.day = step // int(env.configuration.turnsPerDay)
            s.observation.hour = step % int(env.configuration.turnsPerDay)
            s.action = copy.deepcopy((own if i == seat else rival) or action())
        self.e.interpreter(states, env)
        COUNTS["transitions"] += 1
        return states[seat].observation

    @staticmethod
    def wealth(obs):
        return obs.farms[obs.player]["money"]

    @staticmethod
    def carried(obs, item):
        return sum(inv.get(item, 0) for inv in obs.private["inventories"])

    def test_01_product_purchase_capability_is_execution_not_parse(self):
        rows = []
        for seat in (0, 1):
            for item in self.e.PRODUCTS:
                with self.subTest(seat=seat, item=item):
                    s, env = self.world(seat=seat, item=item)
                    order = ["BUY_PRODUCT", item, 7]
                    self.assertIsNotNone(self.e._parse_order(order))
                    obs = self.tick(s, env, 1, seat, action(market=[order]))
                    expected = 7 if item in ("WHEAT", "FERTILIZER") else 0
                    self.assertEqual(obs.private["shed"][item], expected)
                    self.assertEqual(obs.market["inventory"][item], 10000 - expected)
                    if expected == 0:
                        self.assertEqual(self.wealth(obs), 1000000)
                    rows.append({"seat": seat, "item": item, "requested": 7, "filled": expected})
        RECEIPT["product_capabilities"] = rows

    def test_02_hinge_quote_does_not_make_a_crop_purchasable(self):
        rows = []
        for seat in (0, 1):
            for item in ("CARROT", "TOMATO", "EGG"):
                with self.subTest(seat=seat, item=item):
                    s, env = self.world(seat=seat, item=item, cash=10**9)
                    obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", item, 5000]]))
                    self.assertEqual(obs.private["shed"][item], 0)
                    self.assertEqual(obs.market["inventory"][item], 10000)
                    self.assertEqual(self.wealth(obs), 10**9)
                    hypothetical = self.e.market_price(item, 5000)
                    self.assertGreater(hypothetical, self.e.market_price(item, 10000))
                    rows.append({"seat": seat, "item": item, "requested_buy": 5000,
                                 "actual_fill": 0, "hypothetical_price_at_inventory_5000": hypothetical})
        RECEIPT["hinge_buy_counterexamples"] = rows

    def test_03_zero_and_negative_inventory_do_not_block_buyers(self):
        rows = []
        for seat in (0, 1):
            for item in ("WHEAT", "FERTILIZER"):
                for inv in (1, 0, -1, -100):
                    with self.subTest(seat=seat, item=item, inventory=inv):
                        s, env = self.world(seat=seat, item=item, inventory=inv)
                        cost = sum(self.e.market_price(item, inv - i) for i in range(1, 4))
                        obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", item, 3]]))
                        self.assertEqual(obs.private["shed"][item], 3)
                        self.assertEqual(obs.market["inventory"][item], inv - 3)
                        self.assertEqual(self.wealth(obs), 1000000 - cost)
                        rows.append({"seat": seat, "item": item, "inventory_before": inv,
                                     "filled": 3, "cash_cost": cost, "inventory_after": inv-3})
        RECEIPT["negative_inventory_buys"] = rows

    def test_04_cash_prefix_not_requested_quantity_determines_fill(self):
        rows = []
        for seat in (0, 1):
            for item in ("WHEAT", "FERTILIZER"):
                for cash in (0, 1, 24, 26, 100, 3000):
                    with self.subTest(seat=seat, item=item, cash=cash):
                        remaining, n = cash, 0
                        for k in range(1, 101):
                            price = self.e.market_price(item, 10000-k)
                            if remaining < price:
                                break
                            remaining -= price
                            n += 1
                        s, env = self.world(seat=seat, item=item, cash=cash)
                        obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", item, 5000]]))
                        self.assertEqual(obs.private["shed"][item], n)
                        self.assertEqual(self.wealth(obs), remaining)
                        rows.append({"seat": seat, "item": item, "initial_cash": cash,
                                     "requested": 5000, "filled": n, "cash_remaining": remaining})
        RECEIPT["funding_prefixes"] = rows

    def test_05_shared_shed_capacity_counts_other_goods(self):
        for seat in (0, 1):
            for capacity in (1, 7, 100):
                with self.subTest(seat=seat, capacity=capacity):
                    s, env = self.world(seat=seat, capacity=capacity)
                    s[seat].observation.private["shed"]["MILK"] = capacity-1
                    obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", "WHEAT", 5000]]))
                    self.assertEqual(obs.private["shed"]["WHEAT"], 1)
                    self.assertEqual(sum(obs.private["shed"].values()), capacity)

    def test_06_pickup_cannot_read_a_purchase_from_same_callback(self):
        for seat in (0, 1):
            s, env = self.world(seat=seat)
            obs = self.tick(s, env, 1, seat, action(["PICKUP", "WHEAT", 100], [["BUY_PRODUCT", "WHEAT", 100]]))
            self.assertEqual(self.carried(obs, "WHEAT"), 0)
            self.assertEqual(obs.private["shed"]["WHEAT"], 100)
            obs = self.tick(s, env, 2, seat, action(["PICKUP", "WHEAT", 100], [["BUY_PRODUCT", "WHEAT", 100]]))
            self.assertEqual(self.carried(obs, "WHEAT"), 100)
            self.assertEqual(obs.private["shed"]["WHEAT"], 100)

    def test_07_funded_hand_hoarding_really_exceeds_shed_capacity(self):
        rows = []
        for seat in (0, 1):
            s, env = self.world(seat=seat)
            for step in range(1, 7):
                obs = self.tick(s, env, step, seat, action(["PICKUP", "WHEAT", 100], [["BUY_PRODUCT", "WHEAT", 100]]))
            self.assertEqual(self.carried(obs, "WHEAT"), 500)
            self.assertEqual(obs.private["shed"]["WHEAT"], 100)
            rows.append({"seat": seat, "initial_cash": 1000000, "callbacks": 6,
                         "carried_wheat": 500, "shed_wheat": 100,
                         "cash_cost": 1000000-self.wealth(obs)})
        RECEIPT["hoarding_positive_controls"] = rows

    def test_08_full_day_without_liquidation_discards_hoard(self):
        rows = []
        for seat in (0, 1):
            s, env = self.world(seat=seat)
            for step in range(24):
                obs = self.tick(s, env, step, seat, action(["PICKUP", "WHEAT", 100], [["BUY_PRODUCT", "WHEAT", 100]]))
                if step == 22:
                    self.assertEqual(self.carried(obs, "WHEAT"), 2200)
            self.assertEqual(obs.private["inventories"], [{}])
            self.assertEqual(obs.private["shed"]["WHEAT"], 100)
            rows.append({"seat": seat, "purchased": 2400, "retained_after_eod": 100,
                         "discarded": 2300, "cash_cost": 1000000-self.wealth(obs)})
        RECEIPT["full_day_no_liquidation"] = rows

    def test_09_place_preserves_overflow_but_drop_destroys_it(self):
        rows = []
        for seat in (0, 1):
            for op in ("PLACE", "DROP"):
                s, env = self.world(seat=seat, shed=80)
                s[seat].observation.private["inventories"][0]["WHEAT"] = 50
                unit = ["PLACE", "WHEAT", 50] if op == "PLACE" else ["DROP"]
                obs = self.tick(s, env, 1, seat, action(unit))
                self.assertEqual(obs.private["shed"]["WHEAT"], 100)
                expected = 30 if op == "PLACE" else 0
                self.assertEqual(self.carried(obs, "WHEAT"), expected)
                rows.append({"seat": seat, "unit": op, "shed_after": 100,
                             "hand_after": expected, "discarded": 30-expected})
        RECEIPT["transfer_overflow"] = rows

    def test_10_lossless_place_sell_unwinds_a_constructed_warehouse(self):
        for seat in (0, 1):
            s, env = self.world(seat=seat, shed=100)
            s[seat].observation.private["inventories"][0]["WHEAT"] = 250
            for step in range(1, 5):
                obs = self.tick(s, env, step, seat, action(["PLACE", "WHEAT", 100], [["SELL", "WHEAT", 100]]))
            self.assertEqual(self.carried(obs, "WHEAT"), 0)
            self.assertEqual(obs.private["shed"]["WHEAT"], 0)
            self.assertEqual(obs.market["inventory"]["WHEAT"], 10350)

    def test_11_one_actor_roundtrip_is_cash_neutral_without_external_flow(self):
        rows = []
        for seat in (0, 1):
            for item in ("WHEAT", "FERTILIZER"):
                for inv in (9000, 9999, 10000, 10020):
                    for qty in (1, 7, 100):
                        with self.subTest(seat=seat, item=item, inv=inv, qty=qty):
                            s, env = self.world(seat=seat, item=item, inventory=inv)
                            obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", item, qty], ["SELL", item, qty]]))
                            self.assertEqual(self.wealth(obs), 1000000)
                            self.assertEqual(obs.private["shed"][item], 0)
                            self.assertEqual(obs.market["inventory"][item], inv)
                            rows.append({"seat": seat, "item": item, "inventory": inv,
                                         "quantity": qty, "cash_delta": 0})
        RECEIPT["unchanged_market_roundtrips"] = rows

    def test_12_floor_roundtrip_is_cash_neutral_but_not_inventory_neutral(self):
        for seat in (0, 1):
            s, env = self.world(seat=seat, item="FERTILIZER", inventory=11000)
            self.assertEqual(self.e.market_price("FERTILIZER", 10900), 1)
            obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", "FERTILIZER", 100], ["SELL", "FERTILIZER", 100]]))
            self.assertEqual(self.wealth(obs), 1000000)
            self.assertEqual(obs.private["shed"]["FERTILIZER"], 0)
            self.assertEqual(obs.market["inventory"]["FERTILIZER"], 10900)

    def test_13_rival_buy_flow_can_make_a_roundtrip_profitable(self):
        rows = []
        for seat in (0, 1):
            s, env = self.world(seat=seat, item="FERTILIZER")
            obs = self.tick(s, env, 1, seat,
                action(market=[["BUY_PRODUCT", "FERTILIZER", 100], ["SELL", "FERTILIZER", 100]]),
                action(market=[["BUY_PRODUCT", "FERTILIZER", 100]]))
            gain = self.wealth(obs)-1000000
            expected = sum(self.e.market_price("FERTILIZER", 9800+i) for i in range(100)) - sum(
                self.e.market_price("FERTILIZER", 9999-2*i) for i in range(100))
            self.assertEqual(gain, expected)
            self.assertGreater(gain, 0)
            self.assertEqual(obs.private["shed"]["FERTILIZER"], 0)
            self.assertEqual(obs.market["inventory"]["FERTILIZER"], 9900)
            self.assertEqual(s[1-seat].observation.private["shed"]["FERTILIZER"], 100)
            rows.append({"seat": seat, "own_cash_delta": gain,
                         "rival_buys": 100, "own_terminal_goods": 0,
                         "rival_terminal_goods": 100, "market_inventory_after": 9900})
        RECEIPT["rival_buy_positive_control"] = rows

    def test_14_known_town_tick_supports_funded_nonzero_profit(self):
        rows = []
        for seat in (0, 1):
            for n_shops in (0, 8):
                s, env = self.world(seat=seat, shops=["BAKERY"]*n_shops)
                expected_cost = sum(self.e.market_price("WHEAT", 10000-i) for i in range(1, 101))
                obs = self.tick(s, env, 4, seat, action(market=[["BUY_PRODUCT", "WHEAT", 100]]))
                self.assertEqual(1000000-self.wealth(obs), expected_cost)
                self.assertEqual(obs.market["inventory"]["WHEAT"], 9900-n_shops)
                obs = self.tick(s, env, 5, seat, action(market=[["SELL", "WHEAT", 100]]))
                gain = self.wealth(obs)-1000000
                expected_sale = sum(self.e.market_price("WHEAT", 9900-n_shops+i) for i in range(100))
                self.assertEqual(gain, expected_sale-expected_cost)
                self.assertEqual(obs.private["shed"]["WHEAT"], 0)
                self.assertGreater(gain, 0) if n_shops else self.assertEqual(gain, 0)
                rows.append({"seat": seat, "bakery_copies": n_shops, "cash_cost": expected_cost,
                             "cash_delta": gain, "own_terminal_goods": 0})
        RECEIPT["town_demand_positive_control"] = rows

    def test_15_rival_supply_reverses_the_town_carry_gain(self):
        for seat in (0, 1):
            s, env = self.world(seat=seat, shops=["BAKERY"]*8)
            s[1-seat].observation.private["shed"]["WHEAT"] = 100
            self.tick(s, env, 4, seat, action(market=[["BUY_PRODUCT", "WHEAT", 100]]))
            obs = self.tick(s, env, 5, seat, action(market=[["SELL", "WHEAT", 100]]),
                            action(market=[["SELL", "WHEAT", 100]]))
            self.assertLess(self.wealth(obs), 1000000)
            self.assertEqual(obs.private["shed"]["WHEAT"], 0)

    def test_16_zero_market_inventory_does_not_starve_a_funded_animal(self):
        rows = []
        price = self.e.market_price("WHEAT", -1)
        for seat in (0, 1):
            for funded in (False, True):
                cash = price if funded else price-1
                s, env = self.world(seat=seat, inventory=0, cash=cash)
                farm = s[seat].observation.farms[seat]
                x, y = farm["farmer"]
                animal = self.e._new_animal("COW", 0)
                animal["consecutive_unfed"] = 1
                farm["tiles"][y][x] = animal
                self.tick(s, env, 20, seat, action(market=[["BUY_PRODUCT", "WHEAT", 1]]))
                self.tick(s, env, 21, seat, action(["PICKUP", "WHEAT", 1]))
                self.tick(s, env, 22, seat, action(["FEED"]))
                obs = self.tick(s, env, 23, seat)
                tile = farm["tiles"][y][x]
                self.assertEqual(tile.get("animal") == "COW", funded)
                if funded:
                    self.assertEqual(tile["consecutive_unfed"], 0)
                rows.append({"seat": seat, "initial_market_inventory": 0, "cash": cash,
                             "required_price": price, "survives_eod": funded})
        RECEIPT["starvation_cash_boundary"] = rows

    def test_17_market_order_budget_cannot_be_bypassed_by_long_queue(self):
        for seat in (0, 1):
            s, env = self.world(seat=seat)
            env.configuration.maxMarketOrdersPerTurn = 2
            obs = self.tick(s, env, 1, seat, action(market=[["BUY_PRODUCT", "WHEAT", 1]]*10))
            self.assertEqual(obs.private["shed"]["WHEAT"], 2)

    def test_18_carry_goods_cannot_be_sold_until_in_shed(self):
        for seat in (0, 1):
            s, env = self.world(seat=seat)
            s[seat].observation.private["inventories"][0]["WHEAT"] = 100
            obs = self.tick(s, env, 1, seat, action(market=[["SELL", "WHEAT", 100]]))
            self.assertEqual(self.wealth(obs), 1000000)
            self.assertEqual(self.carried(obs, "WHEAT"), 100)
            obs = self.tick(s, env, 2, seat, action(["PLACE", "WHEAT", 100], [["SELL", "WHEAT", 100]]))
            self.assertEqual(self.carried(obs, "WHEAT"), 0)
            self.assertGreater(self.wealth(obs), 1000000)


def main(argv=None):
    global RUNTIME, MUTATION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True,
                        help="Extracted canonical package containing checks/reference/engine")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mutation", help="Negative control ONLY; never a baseline engine")
    args = parser.parse_args(argv)
    RUNTIME, MUTATION = args.runtime_root, args.mutation
    RECEIPT.update(schema="titan.intraday-market-contract.v1", python=sys.version,
                   platform=platform.platform(), optimized=not __debug__,
                   evidence_class="constructed_interpreter_contracts",
                   mutation=MUTATION, full_games=0, agent_callbacks=0,
                   production_modified=False, promotion_claim=False,
                   slack_posted=False, github_merged=False)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IntradayMarketContract))
    RECEIPT.update(passed=result.wasSuccessful(), tests_run=result.testsRun,
                   failures=[{"test": str(test), "traceback": msg} for test, msg in result.failures],
                   errors=[{"test": str(test), "traceback": msg} for test, msg in result.errors],
                   skipped=result.skipped, engine_calls=dict(COUNTS))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(RECEIPT, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({k: RECEIPT[k] for k in (
        "passed", "tests_run", "engine_calls", "full_games", "optimized", "mutation")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
