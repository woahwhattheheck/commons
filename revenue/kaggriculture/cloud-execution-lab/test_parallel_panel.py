# SPDX-License-Identifier: Apache-2.0
"""Tests for parallel_panel: pool mechanics, deadline handling, cost
accounting, and isolation of real evaluator panels under parallelism.

Pool-mechanics tests use synthetic tasks and are fast.  Panel tests run real
games through the pinned evaluator; they are slower and assert:

- parallel schedules produce byte-identical game traces to serial (#11792:
  no cross-run contamination under parallelism);
- the driver process never loads or constructs an agent and never mutates
  the live titan_runtime.TitanAgent symbol (#11779: no global mutation).
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from parallel_panel import (  # noqa: E402
    EVAL_CONTRACT,
    WorkerPool,
    build_cells,
    cost_report,
    run_panel,
)


class PoolMechanicsTests(unittest.TestCase):
    def test_all_tasks_complete_with_sharded_scheduling(self):
        pool = WorkerPool(3)
        seen = []
        lock = threading.Lock()
        for i in range(30):
            pool.submit(lambda i=i: (time.sleep(0.01), i)[1],
                        task_id=f"t{i}")
        pool.join()
        counts = pool.outcome_counts()
        self.assertEqual(counts.get("completed"), 30)
        self.assertEqual(pool.deadline_misses, 0)
        self.assertEqual(pool.requeues, 0)
        # every submitted task has exactly one recorded outcome: none dropped
        self.assertEqual(len(pool.tasks), 30)
        self.assertTrue(all(t.outcome == "completed"
                            for t in pool.tasks.values()))

    def test_work_stealing_moves_tasks_across_shards(self):
        # autostart=False lets us stage shards deterministically, then drive
        # _next_task by hand: worker 1 must steal from worker 0's backlog.
        pool = WorkerPool(2, autostart=False)
        for i in range(4):
            pool.submit(lambda: None, task_id=f"s{i}", _shard=0)
        stolen = pool._next_task(1)
        self.assertIsNotNone(stolen)
        self.assertGreaterEqual(pool.steals, 1)
        self.assertEqual(len(pool.shards[0]), 3)

    def test_errors_are_recorded_not_dropped(self):
        pool = WorkerPool(2)

        def boom():
            raise RuntimeError("synthetic failure")

        pool.submit(boom, task_id="bad")
        pool.submit(lambda: "ok", task_id="good")
        pool.join()
        self.assertEqual(pool.tasks["bad"].outcome, "error")
        self.assertIn("RuntimeError", pool.tasks["bad"].error)
        self.assertEqual(pool.tasks["good"].outcome, "completed")
        self.assertEqual(pool.tasks["good"].result, "ok")

    def test_deadline_kill_requeue_then_success(self):
        release = threading.Event()
        kill_calls = []
        attempts = []

        def fn():
            attempts.append(1)
            if len(attempts) == 1:
                # first attempt hangs until the watchdog kills it
                release.wait(timeout=30)
                return "first"
            return "second"

        def kill():
            kill_calls.append(1)
            release.set()

        pool = WorkerPool(2, watchdog_interval=0.05)
        pool.submit(fn, kill=kill, deadline_s=0.3, max_retries=1,
                    task_id="flaky")
        pool.join()
        task = pool.tasks["flaky"]
        self.assertEqual(task.outcome, "completed")
        self.assertEqual(task.result, "second")
        self.assertEqual(pool.deadline_misses, 1)
        self.assertEqual(pool.requeues, 1)
        self.assertEqual(len(kill_calls), 1)
        self.assertEqual(task.retries, 1)

    def test_overrun_exhausts_retries_then_failed(self):
        # kill() must promptly release the worker thread, mirroring how
        # Actor.close() makes a real ev.play() return; each attempt blocks
        # on its own event so a kill only releases the current attempt.
        kill_calls = []
        attempt_events = []

        def fn():
            event = threading.Event()
            attempt_events.append(event)
            event.wait(timeout=30)
            return "finished"

        def kill():
            kill_calls.append(1)
            if attempt_events:
                attempt_events[-1].set()

        pool = WorkerPool(1, watchdog_interval=0.05)
        pool.submit(fn, kill=kill, deadline_s=0.2, max_retries=1,
                    task_id="stuck")
        pool.join()
        task = pool.tasks["stuck"]
        # one retry allowed: two deadline misses, then recorded failed
        self.assertEqual(task.outcome, "failed")
        self.assertEqual(task.error, "deadline_exhausted")
        self.assertEqual(pool.deadline_misses, 2)
        self.assertEqual(pool.requeues, 1)
        self.assertEqual(len(kill_calls), 2)
        # accounting: every submitted task settled exactly once
        self.assertEqual(pool.outcome_counts().get("failed"), 1)

    def test_late_completion_after_kill_is_not_double_counted(self):
        release = threading.Event()

        def fn():
            release.wait(timeout=30)
            return "late"

        pool = WorkerPool(1, watchdog_interval=0.05)
        pool.submit(fn, kill=release.set, deadline_s=0.2, max_retries=0,
                    task_id="late")
        pool.join()
        task = pool.tasks["late"]
        self.assertEqual(task.outcome, "failed")
        self.assertGreaterEqual(pool.late_completions, 1)
        counts = pool.outcome_counts()
        self.assertEqual(sum(counts.values()), 1)


class CostReportTests(unittest.TestCase):
    def test_cost_report_compares_against_contract(self):
        cells = build_cells([1, 2], (0, 1))
        results = []
        for seed, seat in cells:
            results.append({
                "status": "complete", "seed": seed, "candidate_seat": seat,
                "wall_seconds": 10.0, "trace_sha256": "x" * 64,
                "actors": [
                    {"calls": 719, "mean_call_seconds": 0.008,
                     "max_call_seconds": 0.020, "call_cpu_seconds": 5.0},
                    {"calls": 719, "mean_call_seconds": 0.009,
                     "max_call_seconds": 0.040, "call_cpu_seconds": 5.2},
                ],
            })
        report = cost_report(
            cells=cells, results=results, wall_seconds=42.0,
            driver_cpu_seconds=3.0,
            pool_stats={"workers": 2, "deadline_misses": 0, "requeues": 0,
                        "steals": 5, "late_completions": 0,
                        "outcomes": {"completed": 4}},
            serial=False,
            candidate="cand.py::agent", opponent=None,
            engine_hashes={"kaggriculture.py": "abc"},
            pythonpath="/tmp", workers=2, task_deadline_s=300.0,
            max_retries=1, serial_baseline_wall=80.0)
        self.assertEqual(report["contract"], EVAL_CONTRACT)
        self.assertEqual(report["panel"]["runs"], 4)
        self.assertEqual(report["outcomes"]["completed"], 4)
        self.assertEqual(report["per_move"]["total_moves"], 4 * 2 * 719)
        self.assertAlmostEqual(report["per_move"]["worst_ms"], 40.0)
        # 40ms worst move exceeds the 35ms budget: the report must say so
        self.assertFalse(report["vs_contract"]["per_move_budget_met"])
        self.assertEqual(
            report["per_move"]["games_with_worst_move_over_budget"], 4)
        self.assertAlmostEqual(report["speedup_vs_serial"], 80.0 / 42.0)
        self.assertEqual(report["vs_contract"]["runs"], "4/64")

    def test_contract_constants(self):
        self.assertEqual(EVAL_CONTRACT["runs_per_panel"], 64)
        self.assertEqual(EVAL_CONTRACT["beam_width"], 24)
        self.assertEqual(EVAL_CONTRACT["per_move_budget_ms"], 35.0)


# ---------------------------------------------------------------------------
# Real evaluator panels (slower).
# ---------------------------------------------------------------------------

CANDIDATE = str(LAB / "candidates/v3-kestrel-capital-execution"
                "/candidate_main.py::agent")


def _driver_agent_hygiene():
    """Snapshot driver-process invariants for #11792/#11779."""
    import titan_runtime  # noqa: PLC0415
    return {
        "titan_agent": titan_runtime.TitanAgent,
        "candidate_modules": sorted(
            name for name in sys.modules if name.startswith("candidate_")),
    }


class PanelIsolationTests(unittest.TestCase):
    """Real games through the pinned evaluator, serial vs parallel."""

    def _fingerprints(self, results):
        return {(g["_cell"]["seed"], g["_cell"]["candidate_seat"]):
                (g["status"], g.get("trace_sha256"), g.get("scores"))
                for g in results}

    def test_parallel_matches_serial_traces(self):
        """#11792: no cross-run contamination under parallelism."""
        seeds = [11, 12]
        before = _driver_agent_hygiene()
        serial_results, _ = run_panel(
            candidate=CANDIDATE, seeds=seeds, seats=(0, 1), serial=True,
            work_dir=str(Path("/tmp/pp-test-serial")))
        parallel_results, report = run_panel(
            candidate=CANDIDATE, seeds=seeds, seats=(0, 1), workers=2,
            work_dir=str(Path("/tmp/pp-test-parallel")))
        self.assertEqual(self._fingerprints(serial_results),
                         self._fingerprints(parallel_results))
        for game in list(serial_results) + list(parallel_results):
            self.assertEqual(game["status"], "complete", game.get("failure"))
        self.assertEqual(report["outcomes"]["completed"], 4)
        self.assertEqual(report["outcomes"]["deadline_misses"], 0)
        # #11779: the driver never constructed an agent or mutated the live
        # runtime symbol; #11792: no evaluator load leaked into this process.
        after = _driver_agent_hygiene()
        self.assertIs(after["titan_agent"], before["titan_agent"])
        self.assertEqual(after["candidate_modules"], [])
        self.assertEqual(before["candidate_modules"], [])

    def test_serial_panel_is_deterministic(self):
        first, _ = run_panel(candidate=CANDIDATE, seeds=[21], seats=(0, 1),
                             serial=True,
                             work_dir=str(Path("/tmp/pp-test-det1")))
        second, _ = run_panel(candidate=CANDIDATE, seeds=[21], seats=(0, 1),
                              serial=True,
                              work_dir=str(Path("/tmp/pp-test-det2")))
        self.assertEqual(self._fingerprints(first), self._fingerprints(second))

    def test_parallel_cost_report_shape(self):
        results, report = run_panel(
            candidate=CANDIDATE, seeds=[31], seats=(0,), workers=2,
            work_dir=str(Path("/tmp/pp-test-cost")))
        self.assertEqual(report["panel"]["runs"], 1)
        self.assertEqual(report["outcomes"]["completed"], 1)
        self.assertGreater(report["wall_seconds"], 0)
        self.assertGreater(report["per_move"]["total_moves"], 0)
        self.assertIn("runs", report["vs_contract"])
        self.assertIn("per_move_budget_met", report["vs_contract"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
