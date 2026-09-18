import copy
import itertools
import json
import random
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from revenue.delivery_backplanner.cli import command_solve, command_verify
from revenue.delivery_backplanner.engine import BackplannerError, load_spec_text, normalize_spec, solve, validate_schedule, verify_result

BASE = {"version": "delivery-backplanner/v1", "horizon_start": "2026-09-21", "deadline": "2026-10-30", "search_limit": 250000, "calendars": [{"id": "std", "weekdays": [0, 1, 2, 3, 4], "holidays": []}], "resources": [{"id": "eng", "daily_capacity": 1}, {"id": "review", "daily_capacity": 1}], "commitments": [], "tasks": []}


def task(tid, duration, release="2026-09-21", resources=None, deps=None, latest=None):
    row = {"id": tid, "duration_workdays": duration, "calendar": "std", "release_date": release, "resources": resources or {"eng": 1}}
    if deps is not None:
        row["dependencies"] = deps
    if latest is not None:
        row["latest_finish"] = latest
    return row


class DeliveryBackplannerTests(unittest.TestCase):
    def test_six_week_lead_time_and_holiday(self):
        spec = copy.deepcopy(BASE)
        spec["deadline"] = "2026-11-20"
        spec["calendars"][0]["holidays"] = ["2026-10-12"]
        spec["tasks"] = [task("paperwork", 1, resources={"review": 1}), task("build", 20, release="2026-10-05", deps=[{"task_id": "paperwork", "lag_workdays": 0}]), task("accept", 2, resources={"review": 1}, deps=[{"task_id": "build", "lag_workdays": 1}])]
        result = solve(spec)
        self.assertEqual(result["status"], "PLAN_FOUND")
        schedule = {row["task_id"]: row for row in result["schedule"]}
        self.assertGreaterEqual(schedule["build"]["start"], "2026-10-05")
        self.assertNotIn("2026-10-12", schedule["build"]["workdays"])
        self.assertTrue(verify_result(spec, result)["valid"])

    def test_resource_contention_respects_retained_commitment(self):
        spec = copy.deepcopy(BASE)
        spec["commitments"] = [{"id": "retained", "start": "2026-09-21", "end": "2026-09-23", "resources": {"eng": 1}}]
        spec["tasks"] = [task("new", 2)]
        result = solve(spec)
        self.assertEqual(result["status"], "PLAN_FOUND")
        self.assertEqual(result["schedule"][0]["start"], "2026-09-24")

    def test_greedy_failure_backtracks_to_feasible_plan(self):
        spec = copy.deepcopy(BASE)
        spec["deadline"] = "2026-09-25"
        spec["tasks"] = [task("a-flex", 2, latest="2026-09-25"), task("b-tight", 2, latest="2026-09-23")]
        result = solve(spec)
        self.assertEqual(result["status"], "PLAN_FOUND")
        schedule = {row["task_id"]: row for row in result["schedule"]}
        self.assertEqual(schedule["b-tight"]["start"], "2026-09-21")
        self.assertEqual(schedule["a-flex"]["start"], "2026-09-23")

    def test_unsatisfiable_is_exhaustive_no_feasible(self):
        spec = copy.deepcopy(BASE)
        spec["deadline"] = "2026-09-23"
        spec["tasks"] = [task("a", 2), task("b", 2)]
        result = solve(spec)
        self.assertEqual(result["status"], "NO_FEASIBLE_PLAN")
        self.assertTrue(verify_result(spec, result)["valid"])

    def test_search_limit_is_inconclusive_not_negative(self):
        spec = copy.deepcopy(BASE)
        spec["deadline"] = "2026-09-25"
        spec["search_limit"] = 1
        spec["tasks"] = [task("a", 2), task("b", 2)]
        result = solve(spec)
        self.assertEqual(result["status"], "SEARCH_LIMIT")
        self.assertIn("inconclusive", result["blockers"][0])

    def test_dependency_lag_uses_dependent_calendar(self):
        spec = copy.deepcopy(BASE)
        spec["calendars"][0]["holidays"] = ["2026-09-23"]
        spec["tasks"] = [task("a", 1), task("b", 1, deps=[{"task_id": "a", "lag_workdays": 1}])]
        result = solve(spec)
        rows = {row["task_id"]: row for row in result["schedule"]}
        self.assertEqual(rows["a"]["finish"], "2026-09-21")
        self.assertEqual(rows["b"]["start"], "2026-09-24")

    def test_strict_json_duplicate_nonfinite_unknown_and_cycles(self):
        with self.assertRaises(BackplannerError):
            load_spec_text('{"version":"delivery-backplanner/v1","version":"delivery-backplanner/v1"}')
        with self.assertRaises(BackplannerError):
            load_spec_text('{"x":NaN}')
        spec = copy.deepcopy(BASE)
        spec["surprise"] = True
        with self.assertRaises(BackplannerError):
            normalize_spec(spec)
        spec = copy.deepcopy(BASE)
        spec["tasks"] = [task("a", 1, deps=[{"task_id": "b"}]), task("b", 1, deps=[{"task_id": "a"}])]
        with self.assertRaises(BackplannerError):
            normalize_spec(spec)

    def test_tampered_schedule_and_result_reject(self):
        spec = copy.deepcopy(BASE)
        spec["tasks"] = [task("a", 1)]
        result = solve(spec)
        bad = copy.deepcopy(result)
        bad["schedule"][0]["workdays"] = ["2026-09-22"]
        self.assertFalse(verify_result(spec, bad)["valid"])
        bad2 = copy.deepcopy(result)
        bad2["result_sha256"] = "0" * 64
        self.assertFalse(verify_result(spec, bad2)["valid"])

    def test_cli_create_exclusive_and_verify(self):
        spec = copy.deepcopy(BASE)
        spec["tasks"] = [task("a", 1)]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            out = root / "out"
            self.assertEqual(command_solve(spec_path, out), 0)
            self.assertEqual(command_verify(spec_path, out / "result.json"), 0)
            with self.assertRaises(BackplannerError):
                command_solve(spec_path, out)

    def test_reference_crosscheck_small_random_instances(self):
        rng = random.Random(20260916)
        for case in range(50):
            spec = copy.deepcopy(BASE)
            spec["deadline"] = "2026-09-25"
            spec["search_limit"] = 100000
            rows = []
            for i in range(rng.randint(1, 4)):
                deps = []
                if i and rng.random() < 0.35:
                    deps = [{"task_id": f"t{rng.randrange(i)}", "lag_workdays": rng.randint(0, 1)}]
                rows.append(task(f"t{i}", rng.randint(1, 2), deps=deps))
            spec["tasks"] = rows
            actual = solve(spec)
            expected_feasible = self._reference_feasible(spec)
            self.assertEqual(actual["status"] == "PLAN_FOUND", expected_feasible, (case, spec, actual))
            if actual["status"] == "PLAN_FOUND":
                self.assertTrue(validate_schedule(spec, actual["schedule"])["valid"])

    @staticmethod
    def _reference_feasible(spec):
        model = normalize_spec(spec)
        days = [d for d in (model.horizon_start + timedelta(days=i) for i in range((model.deadline-model.horizon_start).days+1)) if model.calendars["std"].eligible(d)]
        blocks = {}
        for tid, t in model.tasks.items():
            options = []
            for i in range(len(days)):
                block = tuple(days[i:i+t.duration])
                if len(block) == t.duration and block[0] >= t.release and block[-1] <= t.latest_finish:
                    options.append(block)
            blocks[tid] = options
        tids = sorted(model.tasks)
        for choice in itertools.product(*(blocks[tid] for tid in tids)):
            sched = dict(zip(tids, choice))
            okay = True
            for tid, t in model.tasks.items():
                for dep, lag in t.dependencies:
                    after = [d for d in days if d > sched[dep][-1]]
                    if len(after) <= lag or sched[tid][0] < after[lag]:
                        okay = False
                        break
            if not okay:
                continue
            for day in days:
                used = sum(dict(model.tasks[tid].resources).get("eng", 0) for tid, block in sched.items() if day in block)
                used += sum(dict(c.resources).get("eng", 0) for c in model.commitments if c.start <= day <= c.end)
                if used > model.resource_capacity["eng"]:
                    okay = False
                    break
            if okay:
                return True
        return False

    def test_duration_one_root_rejects_ineligible_days(self):
        spec = copy.deepcopy(BASE)
        spec["calendars"][0]["holidays"] = ["2026-09-22"]
        spec["tasks"] = [task("a", 1, resources={"eng": 1})]
        weekend = [{"task_id": "a", "calendar": "std", "start": "2026-09-26", "finish": "2026-09-26", "workdays": ["2026-09-26"], "resources": {"eng": 1}}]
        holiday = [{"task_id": "a", "calendar": "std", "start": "2026-09-22", "finish": "2026-09-22", "workdays": ["2026-09-22"], "resources": {"eng": 1}}]
        self.assertFalse(validate_schedule(spec, weekend)["valid"])
        self.assertFalse(validate_schedule(spec, holiday)["valid"])
        result = solve(spec)
        self.assertEqual(result["status"], "PLAN_FOUND")
        self.assertTrue(validate_schedule(spec, result["schedule"])["valid"])
        self.assertNotIn("2026-09-26", result["schedule"][0]["workdays"])
        self.assertNotIn("2026-09-22", result["schedule"][0]["workdays"])

    def test_load_spec_text_surrogate_is_backplanner_error(self):
        with self.assertRaises(BackplannerError):
            load_spec_text("{\"x\": \"\ud800\"}")

    def test_command_solve_rollback_preserves_foreign_successor(self):
        spec = copy.deepcopy(BASE)
        spec["tasks"] = [task("a", 1)]
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            import revenue.delivery_backplanner.cli as cli
            original = cli._write_exclusive
            calls = {"n": 0}

            def wrapped(path, text):
                calls["n"] += 1
                if calls["n"] == 1:
                    owned = original(path, text)
                    aside = path.with_name(path.name + ".aside")
                    path.rename(aside)
                    path.write_bytes(b"FOREIGN-SUCCESSOR-BYTES\n")
                    return owned
                raise OSError("induced sibling write failure")

            cli._write_exclusive = wrapped
            try:
                with self.assertRaises(OSError):
                    command_solve(spec_path, out_dir)
            finally:
                cli._write_exclusive = original
            successor = out_dir / "result.json"
            self.assertTrue(successor.exists())
            self.assertEqual(successor.read_bytes(), b"FOREIGN-SUCCESSOR-BYTES\n")
            self.assertFalse((out_dir / "timeline.md").exists())


if __name__ == "__main__":
    unittest.main()
