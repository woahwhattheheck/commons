from __future__ import annotations

import copy
import itertools
import json
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.costed_work_batch.planner import (  # noqa: E402
    ScenarioError,
    canonical_json,
    exhaustive_optimum,
    load_strict_json,
    optimize,
    parse_scenario,
    verify_result,
)


def family(fid: str, cash: int = 0, effort_cost: int = 0, minutes: int = 0):
    return {
        "family_id": fid,
        "setup_cash_minor": cash,
        "setup_effort_cost_minor": effort_cost,
        "setup_minutes": minutes,
    }


def job(
    op: str,
    fid: str,
    *,
    payout: int | None = 10_000,
    success: int | None = 1_000_000,
    collection: int | None = 1_000_000,
    duration: int = 10,
    cash: int = 0,
    effort_cost: int = 0,
    deadline: int = 100,
    available: bool = True,
    owned: bool = False,
):
    return {
        "operation_id": op,
        "family_id": fid,
        "available": available,
        "already_owned": owned,
        "duration_minutes": duration,
        "cash_cost_minor": cash,
        "effort_cost_minor": effort_cost,
        "payout_minor": payout,
        "success_probability_ppm": success,
        "collection_probability_ppm": collection,
        "deadline_minutes": deadline,
    }


def scenario(
    jobs,
    families=None,
    *,
    cash_limit=1_000_000,
    effort_limit=10_000,
    horizon=10_000,
    minimum_net=1,
    node_budget=100_000,
):
    if families is None:
        family_ids = sorted({row["family_id"] for row in jobs})
        families = [family(fid) for fid in family_ids]
    return {
        "schema": "costed-work-batch/v1",
        "limits": {
            "cash_limit_minor": cash_limit,
            "effort_limit_minutes": effort_limit,
            "horizon_minutes": horizon,
            "minimum_batch_net_minor": minimum_net,
            "node_budget": node_budget,
        },
        "families": families,
        "jobs": jobs,
    }


def independent_eval(raw, selected_ids):
    fam = {row["family_id"]: row for row in raw["families"]}
    chosen = [
        row for row in raw["jobs"] if row["operation_id"] in selected_ids
    ]
    chosen.sort(key=lambda row: (row["deadline_minutes"], row["operation_id"]))
    elapsed = 0
    cash = 0
    econ_effort = 0
    expected = 0
    used = set()
    for row in chosen:
        f = fam[row["family_id"]]
        if row["family_id"] not in used:
            elapsed += f["setup_minutes"]
            cash += f["setup_cash_minor"]
            econ_effort += f["setup_effort_cost_minor"]
            used.add(row["family_id"])
        elapsed += row["duration_minutes"]
        cash += row["cash_cost_minor"]
        econ_effort += row["effort_cost_minor"]
        success_value = (
            row["payout_minor"] * row["success_probability_ppm"] // 1_000_000
        )
        expected += (
            success_value * row["collection_probability_ppm"] // 1_000_000
        )
        if elapsed > row["deadline_minutes"]:
            return None
    limits = raw["limits"]
    if cash > limits["cash_limit_minor"]:
        return None
    if elapsed > limits["effort_limit_minutes"]:
        return None
    if elapsed > limits["horizon_minutes"]:
        return None
    return expected - cash - econ_effort


def independent_best(raw):
    eligible = [
        row
        for row in raw["jobs"]
        if row["available"]
        and not row["already_owned"]
        and row["payout_minor"] is not None
        and (
            (
                row["payout_minor"] * row["success_probability_ppm"]
                // 1_000_000
            )
            * row["collection_probability_ppm"]
            // 1_000_000
            - row["cash_cost_minor"]
            - row["effort_cost_minor"]
        )
        > 0
    ]
    best_ids = ()
    best_net = 0
    for count in range(len(eligible) + 1):
        for combo in itertools.combinations(eligible, count):
            ids = tuple(sorted(row["operation_id"] for row in combo))
            net = independent_eval(raw, set(ids))
            if net is None:
                continue
            if net > best_net or (net == best_net and ids < best_ids):
                best_ids, best_net = ids, net
    return best_ids, best_net


class PlannerTests(unittest.TestCase):
    def test_shared_setup_paid_once(self):
        raw = scenario(
            [
                job("A", "mail", payout=10_000),
                job("B", "mail", payout=10_000),
            ],
            [family("mail", cash=3_000, effort_cost=1_000, minutes=5)],
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["selected_operation_ids"], ["A", "B"])
        self.assertEqual(result["batch"]["cash_cost_minor"], 3_000)
        self.assertEqual(result["batch"]["effort_cost_minor"], 1_000)
        self.assertEqual(
            sum(1 for row in result["batch"]["schedule"] if row["kind"] == "SETUP"),
            1,
        )
        self.assertEqual(result["batch"]["net_minor"], 16_000)

    def test_earliest_deadline_schedule_is_contract(self):
        raw = scenario(
            [
                job("later", "x", payout=8_000, duration=5, deadline=20),
                job("early", "x", payout=8_000, duration=5, deadline=10),
            ]
        )
        result = optimize(parse_scenario(raw))
        jobs = [
            row["operation_id"]
            for row in result["batch"]["schedule"]
            if row["kind"] == "JOB"
        ]
        self.assertEqual(jobs, ["early", "later"])

    def test_setup_time_can_make_deadline_infeasible(self):
        raw = scenario(
            [job("A", "x", payout=50_000, duration=5, deadline=10)],
            [family("x", minutes=6)],
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["selected_operation_ids"], [])
        self.assertEqual(result["decision"], "NO_BATCH_MEETS_MINIMUM")

    def test_unknown_payout_remains_visible(self):
        raw = scenario(
            [
                job(
                    "mystery",
                    "x",
                    payout=None,
                    success=None,
                    collection=None,
                )
            ]
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(
            result["excluded"],
            [{"operation_id": "mystery", "reason": "UNVALUED_PAYOUT"}],
        )

    def test_owned_and_unavailable_not_selected(self):
        raw = scenario(
            [
                job("owned", "x", owned=True),
                job("off", "x", available=False),
                job("live", "x"),
            ]
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["selected_operation_ids"], ["live"])
        reasons = {row["operation_id"]: row["reason"] for row in result["excluded"]}
        self.assertEqual(reasons["owned"], "ALREADY_OWNED")
        self.assertEqual(reasons["off"], "UNAVAILABLE")

    def test_cash_limit_forces_subset(self):
        raw = scenario(
            [
                job("A", "a", payout=12_000, cash=6_000),
                job("B", "b", payout=9_000, cash=4_000),
            ],
            cash_limit=6_000,
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["selected_operation_ids"], ["A"])

    def test_effort_limit_forces_subset(self):
        raw = scenario(
            [
                job("A", "x", payout=10_000, duration=7),
                job("B", "x", payout=9_000, duration=7),
            ],
            effort_limit=7,
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["selected_operation_ids"], ["A"])

    def test_minimum_net_is_decision_gate_not_fake_value(self):
        raw = scenario([job("A", "x", payout=900)], minimum_net=1_000)
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["net_minor"], 900)
        self.assertEqual(result["decision"], "NO_BATCH_MEETS_MINIMUM")

    def test_conservative_two_stage_rounding(self):
        raw = scenario(
            [
                job(
                    "A",
                    "x",
                    payout=101,
                    success=500_000,
                    collection=500_000,
                )
            ],
            minimum_net=0,
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["batch"]["expected_collection_minor"], 25)

    def test_node_budget_never_claims_optimal_when_incomplete(self):
        raw = scenario(
            [job(f"J{i}", "x", payout=10_000 + i) for i in range(12)],
            node_budget=1,
        )
        result = optimize(parse_scenario(raw))
        self.assertEqual(result["search"]["proof"], "BOUNDED_SEARCH_INCOMPLETE")
        self.assertGreaterEqual(
            result["search"]["upper_bound_net_minor"],
            result["search"]["incumbent_net_minor"],
        )
        self.assertGreaterEqual(result["search"]["optimality_gap_minor"], 0)

    def test_exhaustive_oracle_matches_simple_case(self):
        raw = scenario(
            [
                job("A", "x", payout=9_000, duration=5, deadline=5),
                job("B", "x", payout=8_000, duration=5, deadline=9),
                job("C", "y", payout=7_000, duration=1, deadline=20),
            ]
        )
        parsed = parse_scenario(raw)
        ids, evaluation = exhaustive_optimum(parsed)
        result = optimize(parsed)
        self.assertEqual(tuple(result["batch"]["selected_operation_ids"]), ids)
        self.assertEqual(result["batch"]["net_minor"], evaluation.net_minor)

    def test_randomized_differential_against_independent_oracle(self):
        rng = random.Random(20260917)
        for case in range(80):
            fams = [
                family(
                    "a",
                    cash=rng.randrange(0, 500),
                    effort_cost=rng.randrange(0, 300),
                    minutes=rng.randrange(0, 4),
                ),
                family(
                    "b",
                    cash=rng.randrange(0, 500),
                    effort_cost=rng.randrange(0, 300),
                    minutes=rng.randrange(0, 4),
                ),
            ]
            jobs = []
            for i in range(rng.randrange(1, 8)):
                payout = rng.randrange(100, 5_000)
                jobs.append(
                    job(
                        f"C{case}J{i}",
                        rng.choice(["a", "b"]),
                        payout=payout,
                        success=rng.randrange(100_000, 1_000_001),
                        collection=rng.randrange(100_000, 1_000_001),
                        duration=rng.randrange(1, 8),
                        cash=rng.randrange(0, 700),
                        effort_cost=rng.randrange(0, 500),
                        deadline=rng.randrange(4, 30),
                    )
                )
            raw = scenario(
                jobs,
                fams,
                cash_limit=rng.randrange(300, 3_000),
                effort_limit=rng.randrange(5, 35),
                horizon=rng.randrange(5, 35),
                minimum_net=0,
                node_budget=1_000_000,
            )
            expected_ids, expected_net = independent_best(raw)
            result = optimize(parse_scenario(raw))
            with self.subTest(case=case):
                self.assertEqual(
                    tuple(result["batch"]["selected_operation_ids"]),
                    expected_ids,
                )
                self.assertEqual(result["batch"]["net_minor"], expected_net)
                self.assertEqual(result["search"]["proof"], "OPTIMAL")
                self.assertEqual(result["search"]["optimality_gap_minor"], 0)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ScenarioError):
            load_strict_json('{"schema":"a","schema":"b"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ScenarioError):
            load_strict_json('{"x":NaN}')

    def test_bool_is_not_integer(self):
        raw = scenario([job("A", "x")])
        raw["limits"]["cash_limit_minor"] = True
        with self.assertRaises(ScenarioError):
            parse_scenario(raw)

    def test_partial_payout_tuple_rejected(self):
        raw = scenario([job("A", "x")])
        raw["jobs"][0]["collection_probability_ppm"] = None
        with self.assertRaises(ScenarioError):
            parse_scenario(raw)

    def test_unknown_family_rejected(self):
        raw = scenario([job("A", "x")])
        raw["jobs"][0]["family_id"] = "missing"
        with self.assertRaises(ScenarioError):
            parse_scenario(raw)

    def test_result_verification_detects_tamper(self):
        raw = scenario([job("A", "x")])
        result = optimize(parse_scenario(raw))
        self.assertTrue(verify_result(raw, result))
        tampered = copy.deepcopy(result)
        tampered["batch"]["net_minor"] += 1
        self.assertFalse(verify_result(raw, tampered))

    def test_input_order_does_not_change_result(self):
        raw = scenario(
            [
                job("C", "x", payout=8_000),
                job("A", "x", payout=10_000),
                job("B", "y", payout=9_000),
            ],
            [family("y"), family("x")],
        )
        a = optimize(parse_scenario(copy.deepcopy(raw)))
        shuffled = copy.deepcopy(raw)
        shuffled["jobs"].reverse()
        shuffled["families"].reverse()
        b = optimize(parse_scenario(shuffled))
        # Scenario digest binds source ordering, but the chosen economics/schedule
        # and proof must stay semantically identical.
        self.assertEqual(a["batch"], b["batch"])
        self.assertEqual(a["search"], b["search"])
        self.assertEqual(a["decision"], b["decision"])

    def test_cli_canonical_json_and_human_schedule(self):
        raw = scenario([job("A", "x", payout=12_345)])
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "scenario.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            env = dict(**__import__("os").environ)
            env["PYTHONPATH"] = str(ROOT)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.costed_work_batch.cli",
                    str(path),
                    "--json",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)
            json_line = next(
                line for line in reversed(proc.stdout.splitlines())
                if line.startswith("{")
            )
            parsed = json.loads(json_line)
            self.assertEqual(parsed["batch"]["selected_operation_ids"], ["A"])

            proc2 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.costed_work_batch.cli",
                    str(path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=20,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stdout)
            self.assertIn("SELECT_BATCH", proc2.stdout)
            self.assertIn("JOB A", proc2.stdout)

    def test_authority_is_always_false(self):
        raw = scenario([job("A", "x")])
        result = optimize(parse_scenario(raw))
        self.assertTrue(result["authority"])
        self.assertFalse(any(result["authority"].values()))


if __name__ == "__main__":
    unittest.main()
