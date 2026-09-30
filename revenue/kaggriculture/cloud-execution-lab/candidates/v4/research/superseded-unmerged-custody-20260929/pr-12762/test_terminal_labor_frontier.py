import copy
import unittest

import terminal_labor_frontier as tlf


class Mechanics:
    PRODUCTS = ["WHEAT"]

    def _hire_cost(self, n, mult=1):
        a, b = 1, 1
        for _ in range(n):
            a, b = b, a + b
        return mult * a

    def _do_hire(self, farm, private, board, mult=1):
        cost = self._hire_cost(farm["hires_today"], mult)
        if farm["money"] < cost:
            return
        farm["money"] -= cost
        farm["hires_today"] += 1
        farm["hands"].append([4 + (len(farm["hands"]) % 2), 4])
        private["inventories"].append({})

    def _apply_unit_action(self, farm, private, idx, action, board, day, day_len, cap):
        if action and action[0] == "CASH_BURN":
            farm["money"] -= action[1]


class Terminal:
    """Each available worker can capture one descending-value terminal job."""

    def assign_routes(self, farm, inventories, now, final, day, prices, cap, seed_routes=None):
        jobs = list(farm.get("job_values", []))
        n = 1 + len(farm["hands"])
        values = jobs[:n]
        evaluations = [(float(v), 1, [["PASS"]], {}) for v in values]
        evaluations += [(0.0, 0, [], {}) for _ in range(n - len(evaluations))]
        return [[] for _ in range(n)], evaluations


def obs(step=697, cash=3000, hires_today=0, hands=0, jobs=(1000, 800, 600, 400, 200)):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    farm = {
        "money": float(cash),
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [[5, 4] for _ in range(hands)],
        "hires_today": hires_today,
        "job_values": list(jobs),
    }
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": {
            "shed": {"WHEAT": 0},
            "seeds": {},
            "inventories": [{} for _ in range(1 + hands)],
        },
        "market": {"prices": {"WHEAT": 25}},
    }


class Tests(unittest.TestCase):
    def setUp(self):
        self.m = Mechanics()
        self.t = Terminal()
        self.cfg = {}

    def test_disabled_exact_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        out, report = tlf.propose_terminal_hires(self.m, self.t, obs(), self.cfg, action)
        self.assertIs(out, action)
        self.assertEqual(report["reason"], "disabled")

    def test_only_final_hour_one(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for step in (696, 698, 718):
            report = tlf.terminal_hire_frontier(self.m, self.t, obs(step=step), self.cfg, action)
            self.assertFalse(report["eligible"])
            self.assertEqual(report["reason"], "not_terminal_hire_decision")

    def test_first_ten_hires_cost_143(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        report = tlf.terminal_hire_frontier(
            self.m, self.t, obs(jobs=(1000,) * 20), self.cfg, action, max_extra_hires=10
        )
        self.assertTrue(report["eligible"])
        self.assertEqual(report["frontier"][-1]["cumulative_hire_cost"], 143)

    def test_exact_fibonacci_continues_from_existing_hires(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
        report = tlf.terminal_hire_frontier(
            self.m,
            self.t,
            obs(hires_today=2, hands=2, jobs=(1000,) * 20),
            self.cfg,
            action,
            max_extra_hires=2,
        )
        self.assertTrue(report["eligible"])
        self.assertEqual([r["cumulative_hire_cost"] for r in report["frontier"]], [3, 8])

    def test_market_cap_limits_new_hires(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"] for _ in range(8)]}
        report = tlf.terminal_hire_frontier(
            self.m, self.t, obs(cash=10000, jobs=(1000,) * 20), self.cfg, action, max_extra_hires=10
        )
        self.assertEqual(report["market_slots"], 2)
        self.assertEqual(len(report["frontier"]), 2)

    def test_nonhire_market_prefix_fails_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        report = tlf.terminal_hire_frontier(self.m, self.t, obs(), self.cfg, action)
        self.assertFalse(report["eligible"])
        self.assertEqual(report["reason"], "nonhire_market_prefix")

    def test_cash_burn_unit_is_accounted_before_hires(self):
        action = {"farmer": ["CASH_BURN", 99], "hands": [], "market": []}
        report = tlf.terminal_hire_frontier(
            self.m, self.t, obs(cash=100, jobs=(1000,) * 10), self.cfg, action, max_extra_hires=3
        )
        self.assertTrue(report["eligible"])
        self.assertEqual(len(report["frontier"]), 1)

    def test_no_jobs_means_no_hire(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        out, report = tlf.propose_terminal_hires(
            self.m, self.t, obs(jobs=()), self.cfg, action, enabled=True, min_surplus=0
        )
        self.assertIs(out, action)
        self.assertFalse(report["changed"])

    def test_selects_best_marginal_count_not_fixed_mass_hire(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        out, report = tlf.propose_terminal_hires(
            self.m,
            self.t,
            obs(jobs=(1000, 700, 300, 20)),
            self.cfg,
            action,
            enabled=True,
            min_surplus=1,
            max_extra_hires=3,
        )
        self.assertTrue(report["changed"])
        self.assertEqual(report["chosen"]["extra_hires"], 3)
        self.assertEqual(out["market"], [["HIRE"], ["HIRE"], ["HIRE"]])

    def test_threshold_can_stop_low_value_extra_worker(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        out, report = tlf.propose_terminal_hires(
            self.m,
            self.t,
            obs(jobs=(1000, 300, 1)),
            self.cfg,
            action,
            enabled=True,
            min_surplus=250,
            max_extra_hires=2,
        )
        self.assertTrue(report["changed"])
        self.assertEqual(report["chosen"]["extra_hires"], 1)

    def test_incumbent_unfunded_hire_fails_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"], ["HIRE"]]}
        report = tlf.terminal_hire_frontier(
            self.m, self.t, obs(cash=1, jobs=(1000,) * 10), self.cfg, action
        )
        self.assertFalse(report["eligible"])
        self.assertEqual(report["reason"], "incumbent_hire_not_funded")


if __name__ == "__main__":
    unittest.main()
