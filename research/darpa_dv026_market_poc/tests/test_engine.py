from __future__ import annotations

import copy
import unittest

from research.darpa_dv026_market_poc import (
    ContractError,
    build_observation,
    collect_black_box_orders,
    evaluate,
    parse_orders,
    parse_scenario,
    verify_receipt,
)


def scenario_dict(*, adapter_kind: str = "EXTERNAL_BLACK_BOX", news=None):
    buyer_values = [120, 110, 100, 90, 80]
    seller_costs = [10, 20, 30, 40, 50]
    participants = []
    for i, value in enumerate(buyer_values, 1):
        participants.append(
            {
                "participant_id": f"b{i}",
                "role": "BUYER",
                "reservation_minor": value,
                "quantity": 1,
                "model_id": f"model-b{i}",
                "adapter_kind": adapter_kind,
            }
        )
    for i, cost in enumerate(seller_costs, 1):
        participants.append(
            {
                "participant_id": f"s{i}",
                "role": "SELLER",
                "reservation_minor": cost,
                "quantity": 1,
                "model_id": f"model-s{i}",
                "adapter_kind": adapter_kind,
            }
        )
    return {
        "schema": "darpa-dv026-market-scenario/v1",
        "scenario_id": "panel-10",
        "asset": "SIM",
        "participants": participants,
        "news": [] if news is None else news,
    }


def truthful_orders(scenario):
    out = []
    for p in scenario.participants:
        obs = build_observation(scenario, p)
        out.append(
            {
                "participant_id": p.participant_id,
                "side": "BUY" if p.role == "BUYER" else "SELL",
                "price_minor": obs["reservation_minor"],
                "quantity": p.quantity,
            }
        )
    return out


class ScriptedAdapter:
    def __init__(self, model_id, adapter_kind, price):
        self.model_id = model_id
        self.adapter_kind = adapter_kind
        self.price = price

    def decide(self, observation):
        return {
            "participant_id": observation["participant_id"],
            "side": "BUY" if observation["role"] == "BUYER" else "SELL",
            "price_minor": self.price,
            "quantity": observation["quantity"],
        }


class MarketPocTests(unittest.TestCase):
    def test_truthful_ten_external_model_panel_reaches_full_efficiency(self):
        scenario = parse_scenario(scenario_dict())
        orders = parse_orders(scenario, truthful_orders(scenario))
        for mechanism in ("CONTINUOUS_DOUBLE_AUCTION", "UNIFORM_PRICE_CALL"):
            receipt = evaluate(scenario, orders, mechanism=mechanism)
            self.assertEqual(receipt["allocative_efficiency_bps"], 10000)
            self.assertTrue(receipt["efficiency_gate_pass"])
            self.assertEqual(receipt["model_panel"]["external_black_box_model_count"], 10)
            self.assertTrue(
                receipt["model_panel"]["ten_distinct_external_model_contract_met"]
            )
            self.assertFalse(receipt["model_panel"]["ten_llm_milestone_claimed"])
            self.assertFalse(receipt["claim_ceiling"]["phase_i_complete"])

    def test_synthetic_stubs_never_satisfy_external_model_contract(self):
        scenario = parse_scenario(scenario_dict(adapter_kind="SYNTHETIC_STUB"))
        orders = parse_orders(scenario, truthful_orders(scenario))
        receipt = evaluate(
            scenario, orders, mechanism="CONTINUOUS_DOUBLE_AUCTION"
        )
        self.assertEqual(receipt["model_panel"]["distinct_model_count"], 10)
        self.assertEqual(receipt["model_panel"]["external_black_box_model_count"], 0)
        self.assertFalse(
            receipt["model_panel"]["ten_distinct_external_model_contract_met"]
        )
        self.assertFalse(receipt["claim_ceiling"]["ten_llm_milestone_satisfied"])

    def test_strategic_misallocation_fails_efficiency_gate(self):
        raw = {
            "schema": "darpa-dv026-market-scenario/v1",
            "scenario_id": "misallocation",
            "asset": "SIM",
            "participants": [
                {
                    "participant_id": "good",
                    "role": "BUYER",
                    "reservation_minor": 100,
                    "quantity": 1,
                    "model_id": "good-model",
                    "adapter_kind": "SYNTHETIC_STUB",
                },
                {
                    "participant_id": "bad",
                    "role": "BUYER",
                    "reservation_minor": 20,
                    "quantity": 1,
                    "model_id": "bad-model",
                    "adapter_kind": "SYNTHETIC_STUB",
                },
                {
                    "participant_id": "seller",
                    "role": "SELLER",
                    "reservation_minor": 0,
                    "quantity": 1,
                    "model_id": "seller-model",
                    "adapter_kind": "SYNTHETIC_STUB",
                },
            ],
            "news": [],
        }
        scenario = parse_scenario(raw)
        orders = parse_orders(
            scenario,
            [
                {"participant_id": "good", "side": "BUY", "price_minor": 10, "quantity": 1},
                {"participant_id": "bad", "side": "BUY", "price_minor": 100, "quantity": 1},
                {"participant_id": "seller", "side": "SELL", "price_minor": 0, "quantity": 1},
            ],
        )
        receipt = evaluate(
            scenario, orders, mechanism="CONTINUOUS_DOUBLE_AUCTION"
        )
        self.assertEqual(receipt["optimal_surplus_minor"], 100)
        self.assertEqual(receipt["realized_surplus_minor"], 20)
        self.assertEqual(receipt["allocative_efficiency_bps"], 2000)
        self.assertFalse(receipt["efficiency_gate_pass"])

    def test_public_news_changes_private_reservation_deterministically(self):
        raw = scenario_dict(
            news=[
                {
                    "seq": 1,
                    "headline": "public demand shock",
                    "buyer_value_delta_minor": 7,
                    "seller_cost_delta_minor": 3,
                },
                {
                    "seq": 2,
                    "headline": "public supply shock",
                    "buyer_value_delta_minor": -2,
                    "seller_cost_delta_minor": 1,
                },
            ]
        )
        scenario = parse_scenario(raw)
        buyer = next(p for p in scenario.participants if p.participant_id == "b1")
        seller = next(p for p in scenario.participants if p.participant_id == "s1")
        self.assertEqual(build_observation(scenario, buyer)["reservation_minor"], 125)
        self.assertEqual(build_observation(scenario, seller)["reservation_minor"], 14)
        self.assertEqual(len(build_observation(scenario, buyer)["public_news"]), 2)

    def test_mechanisms_share_allocation_but_price_semantics_are_distinct(self):
        raw = scenario_dict()
        scenario = parse_scenario(raw)
        orders_raw = truthful_orders(scenario)
        for order in orders_raw:
            if order["participant_id"] == "b1":
                order["price_minor"] = 150
            if order["participant_id"] == "s1":
                order["price_minor"] = 1
        orders = parse_orders(scenario, orders_raw)
        cda = evaluate(scenario, orders, mechanism="CONTINUOUS_DOUBLE_AUCTION")
        call = evaluate(scenario, orders, mechanism="UNIFORM_PRICE_CALL")
        self.assertEqual(
            [(t["buyer_id"], t["seller_id"]) for t in cda["trades"]],
            [(t["buyer_id"], t["seller_id"]) for t in call["trades"]],
        )
        self.assertNotEqual(
            [t["price_minor"] for t in cda["trades"]],
            [t["price_minor"] for t in call["trades"]],
        )

    def test_ties_are_deterministic_by_participant_id(self):
        raw = {
            "schema": "darpa-dv026-market-scenario/v1",
            "scenario_id": "tie",
            "asset": "SIM",
            "participants": [
                {"participant_id": "b2", "role": "BUYER", "reservation_minor": 100, "quantity": 1, "model_id": "m2", "adapter_kind": "SYNTHETIC_STUB"},
                {"participant_id": "b1", "role": "BUYER", "reservation_minor": 100, "quantity": 1, "model_id": "m1", "adapter_kind": "SYNTHETIC_STUB"},
                {"participant_id": "s1", "role": "SELLER", "reservation_minor": 10, "quantity": 1, "model_id": "m3", "adapter_kind": "SYNTHETIC_STUB"},
            ],
            "news": [],
        }
        scenario = parse_scenario(raw)
        orders = parse_orders(
            scenario,
            [
                {"participant_id": "b2", "side": "BUY", "price_minor": 100, "quantity": 1},
                {"participant_id": "b1", "side": "BUY", "price_minor": 100, "quantity": 1},
                {"participant_id": "s1", "side": "SELL", "price_minor": 10, "quantity": 1},
            ],
        )
        receipt = evaluate(scenario, orders, mechanism="CONTINUOUS_DOUBLE_AUCTION")
        self.assertEqual(receipt["trades"][0]["buyer_id"], "b1")

    def test_black_box_collection_binds_model_identity_and_strict_output(self):
        raw = {
            "schema": "darpa-dv026-market-scenario/v1",
            "scenario_id": "adapters",
            "asset": "SIM",
            "participants": [
                {"participant_id": "b1", "role": "BUYER", "reservation_minor": 100, "quantity": 1, "model_id": "alpha", "adapter_kind": "SYNTHETIC_STUB"},
                {"participant_id": "s1", "role": "SELLER", "reservation_minor": 10, "quantity": 1, "model_id": "beta", "adapter_kind": "SYNTHETIC_STUB"},
            ],
            "news": [],
        }
        scenario = parse_scenario(raw)
        orders = collect_black_box_orders(
            scenario,
            {
                "b1": ScriptedAdapter("alpha", "SYNTHETIC_STUB", 100),
                "s1": ScriptedAdapter("beta", "SYNTHETIC_STUB", 10),
            },
        )
        self.assertEqual(len(orders), 2)
        with self.assertRaises(ContractError):
            collect_black_box_orders(
                scenario,
                {"b1": ScriptedAdapter("wrong", "SYNTHETIC_STUB", 100)},
            )

    def test_receipt_verification_rejects_tamper(self):
        scenario = parse_scenario(scenario_dict())
        orders = parse_orders(scenario, truthful_orders(scenario))
        receipt = evaluate(scenario, orders, mechanism="CONTINUOUS_DOUBLE_AUCTION")
        self.assertTrue(verify_receipt(scenario, orders, receipt))
        tampered = copy.deepcopy(receipt)
        tampered["allocative_efficiency_bps"] = 10001
        self.assertFalse(verify_receipt(scenario, orders, tampered))

    def test_fail_closed_contracts_reject_unknown_fields_bool_int_and_bad_news_order(self):
        raw = scenario_dict()
        raw["extra"] = "not allowed"
        with self.assertRaises(ContractError):
            parse_scenario(raw)

        raw = scenario_dict()
        raw["participants"][0]["quantity"] = True
        with self.assertRaises(ContractError):
            parse_scenario(raw)

        raw = scenario_dict(
            news=[
                {
                    "seq": 2,
                    "headline": "gap",
                    "buyer_value_delta_minor": 0,
                    "seller_cost_delta_minor": 0,
                }
            ]
        )
        with self.assertRaises(ContractError):
            parse_scenario(raw)

    def test_receipt_authority_ceiling_is_all_false(self):
        scenario = parse_scenario(scenario_dict())
        orders = parse_orders(scenario, truthful_orders(scenario))
        receipt = evaluate(scenario, orders, mechanism="UNIFORM_PRICE_CALL")
        self.assertTrue(all(v is False for v in receipt["external_authority"].values()))
        self.assertTrue(all(v is False for v in receipt["claim_ceiling"].values()))


if __name__ == "__main__":
    unittest.main()
