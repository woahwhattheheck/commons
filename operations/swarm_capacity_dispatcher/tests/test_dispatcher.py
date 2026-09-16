import copy
import unittest

from operations.swarm_capacity_dispatcher.dispatcher import (
    ContractError,
    dispatch,
    verify_receipt,
)


WORKERS = [
    {
        "id": "claude-max",
        "capabilities": ["coding", "research", "math"],
        "capacity": 2,
        "token_budget": 100,
    },
    {
        "id": "grok-heavy",
        "capabilities": ["coding", "research", "outbound"],
        "capacity": 2,
        "token_budget": 120,
    },
    {
        "id": "muse",
        "capabilities": ["coordination", "outbound"],
        "capacity": 1,
        "token_budget": 50,
    },
]


class DispatcherTests(unittest.TestCase):
    def test_revenue_priority_and_deterministic_replay(self):
        orders = [
            {"id": "low", "required_capabilities": ["coding"], "revenue_usd_expected": 100, "token_cost": 10},
            {"id": "high", "required_capabilities": ["coding"], "revenue_usd_expected": 10000, "token_cost": 10},
        ]
        a = dispatch(WORKERS, orders, [])
        b = dispatch(list(reversed(WORKERS)), list(reversed(orders)), [])
        self.assertEqual(a, b)
        self.assertTrue(verify_receipt(WORKERS, orders, [], a))
        assigned = {x["order_id"]: x["worker_id"] for x in a["assignments"]}
        self.assertEqual(set(assigned), {"low", "high"})

    def test_live_claim_prevents_duplicate_assignment(self):
        orders = [{"id": "taken", "required_capabilities": ["coding"], "token_cost": 1}]
        leases = [{"order_id": "taken", "kind": "CLAIM", "owner": "peer", "active": True}]
        result = dispatch(WORKERS, orders, leases)
        self.assertEqual(result["assignments"], [])
        self.assertEqual(result["unassigned"], [{"order_id": "taken", "reason": "LEASE_HELD"}])

    def test_released_claim_does_not_block(self):
        orders = [{"id": "free", "required_capabilities": ["coding"], "token_cost": 1}]
        leases = [{"order_id": "free", "kind": "CLAIM", "owner": "peer", "active": False}]
        result = dispatch(WORKERS, orders, leases)
        self.assertEqual(len(result["assignments"]), 1)

    def test_outbound_requires_muse_lease(self):
        orders = [{"id": "email", "required_capabilities": ["outbound"], "outbound": True, "token_cost": 1}]
        blocked = dispatch(WORKERS, orders, [])
        self.assertEqual(blocked["unassigned"], [{"order_id": "email", "reason": "MUSE_LEASE_REQUIRED"}])
        leases = [{"order_id": "email", "kind": "MUSE", "owner": "muse", "active": True}]
        allowed = dispatch(WORKERS, orders, leases)
        self.assertEqual(len(allowed["assignments"]), 1)
        self.assertTrue(allowed["assignments"][0]["muse_lease_present"])
        self.assertFalse(allowed["authority"]["external_contact"])

    def test_dnr_and_hold_never_assign(self):
        orders = [
            {"id": "dead", "status": "DNR"},
            {"id": "hold", "status": "HOLD"},
        ]
        result = dispatch(WORKERS, orders, [])
        self.assertEqual(
            result["unassigned"],
            [{"order_id": "dead", "reason": "DNR"}, {"order_id": "hold", "reason": "HOLD"}],
        )

    def test_capability_mismatch(self):
        orders = [{"id": "lean", "required_capabilities": ["lean4"], "token_cost": 1}]
        result = dispatch(WORKERS, orders, [])
        self.assertEqual(result["unassigned"], [{"order_id": "lean", "reason": "CAPABILITY_MISMATCH"}])

    def test_capacity_exhaustion(self):
        workers = [{"id": "one", "capabilities": ["coding"], "capacity": 1, "token_budget": 99}]
        orders = [
            {"id": "a", "required_capabilities": ["coding"], "revenue_usd_expected": 2, "token_cost": 1},
            {"id": "b", "required_capabilities": ["coding"], "revenue_usd_expected": 1, "token_cost": 1},
        ]
        result = dispatch(workers, orders, [])
        self.assertEqual([a["order_id"] for a in result["assignments"]], ["a"])
        self.assertEqual(result["unassigned"], [{"order_id": "b", "reason": "CAPACITY_EXHAUSTED"}])

    def test_token_budget_exhaustion(self):
        workers = [{"id": "one", "capabilities": ["coding"], "capacity": 2, "token_budget": 5}]
        orders = [{"id": "a", "required_capabilities": ["coding"], "token_cost": 6}]
        result = dispatch(workers, orders, [])
        self.assertEqual(result["unassigned"], [{"order_id": "a", "reason": "TOKEN_BUDGET_EXHAUSTED"}])

    def test_preferred_worker_wins_when_eligible(self):
        orders = [
            {
                "id": "math",
                "required_capabilities": ["math"],
                "preferred_workers": ["claude-max"],
                "token_cost": 1,
            }
        ]
        result = dispatch(WORKERS, orders, [])
        self.assertEqual(result["assignments"][0]["worker_id"], "claude-max")

    def test_receipt_tamper_fails(self):
        orders = [{"id": "x", "required_capabilities": ["coding"], "token_cost": 1}]
        receipt = dispatch(WORKERS, orders, [])
        tampered = copy.deepcopy(receipt)
        tampered["assignments"][0]["worker_id"] = "intruder"
        self.assertFalse(verify_receipt(WORKERS, orders, [], tampered))

    def test_non_boolean_authority_fields_are_rejected(self):
        with self.assertRaises(ContractError):
            dispatch(
                [{"id": "w", "capabilities": [], "capacity": 1, "token_budget": 1, "active": "yes"}],
                [],
                [],
            )
        with self.assertRaises(ContractError):
            dispatch(WORKERS, [{"id": "x", "outbound": 1}], [])
        with self.assertRaises(ContractError):
            dispatch(
                WORKERS,
                [{"id": "x"}],
                [{"order_id": "x", "kind": "CLAIM", "owner": "peer", "active": "false"}],
            )

    def test_unknown_lease_order_is_rejected(self):
        with self.assertRaises(ContractError):
            dispatch(WORKERS, [], [{"order_id": "ghost", "kind": "CLAIM", "owner": "x"}])


if __name__ == "__main__":
    unittest.main()
