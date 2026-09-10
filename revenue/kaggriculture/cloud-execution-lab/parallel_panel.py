# SPDX-License-Identifier: Apache-2.0
"""Deadline-aware worker pool for panel-scale same-process self-play.

Runs real panels through the pinned official evaluator
(``reference/evaluator/evaluate.py``, engine ref
``28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c``) with N worker threads in one
driver process.  Each game is one pool task with a per-task deadline; a
watchdog kills overrunning workers (via their actor process groups) and
requeues the task, so no task is ever silently dropped.  A game that fails
with an RPC timeout at step 0 never produced game state; it is retried as
predeclared, outcome-blind infrastructure recovery (bounded, recorded per
game), never as outcome-conditioned selection.  Cost is tracked
per panel: wall-clock, CPU time, and per-run cost, compared against the
evaluation contract.  A ``--serial`` mode keeps the single-process
deterministic path intact and reproduces the evaluator's serial game loop.

Evaluation contract (work-item specification; not located in-repo):

- ``runs_per_panel = 64``: 64 games per panel (32 seed/opponent cells x 2
  seats, the E16 screen shape).
- ``beam_width = 24``: reference parallel scheduling width (max lanes).
- ``per_move_budget_ms = 35``: per-move compute budget tracked per agent call.

These constants were searched for across the lab (E16 64-game screens,
TITAN-CONFIG 1.0s action budget, SCORE-SCHEDULE p99 ~21ms per move) and were
not found in-repo; they are encoded here from the work-item specification.

Isolation design (builds on #11792 load isolation and #11779 no-global-mutation):

- The driver process never loads or constructs an agent.  Every game runs
  its two agents in fresh pinned-evaluator ``Actor`` subprocesses, which is
  strictly stronger than same-process load isolation: there is no shared
  ``_INSTANCE``, no shared ``candidate_*`` module, and no
  ``titan_runtime.TitanAgent`` symbol for a worker to mutate.
- Each worker thread registers only its own task's actors (thread-keyed
  registry) so a deadline kill closes exactly that task's process groups.
- Determinism: per-game ``rng_seed`` is derived from the fixed task index,
  so serial and parallel schedules produce identical traces.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import itertools
import json
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

LAB = Path(__file__).resolve().parent
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

EVAL_CONTRACT = {
    "runs_per_panel": 64,
    "beam_width": 24,
    "per_move_budget_ms": 35.0,
    "provenance": (
        "work-item specification; searched cloud-execution-lab (E16 64-game "
        "screens, TITAN-CONFIG 1.0s action budget, SCORE-SCHEDULE p99 ~21ms "
        "per move) and did not locate these exact constants in-repo"
    ),
}

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


# ---------------------------------------------------------------------------
# Deadline-aware worker pool: sharded scheduling with work stealing.
# ---------------------------------------------------------------------------

class _Task:
    """One unit of work with a per-task deadline and bounded retries."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"

    def __init__(self, task_id, fn, kill, deadline_s, max_retries):
        self.task_id = task_id
        self.fn = fn
        self.kill = kill or (lambda: None)
        self.deadline_s = deadline_s
        self.max_retries = max_retries
        self.retries = 0
        self.run_id = 0
        self.state = _Task.PENDING
        self.deadline_at = 0.0
        self.submit_time = time.time()
        self.start_time = 0.0
        self.end_time = 0.0
        self.wall_seconds = 0.0
        self.outcome = None  # completed | error | failed | killed_exhausted
        self.result = None
        self.error = None


class WorkerPool:
    """N workers over per-worker sharded queues with idle work stealing.

    A watchdog thread enforces per-task deadlines: an overrunning task is
    killed via its ``kill`` hook and requeued while retries remain, else
    recorded failed.  Every submitted task ends in exactly one recorded
    outcome; nothing is silently dropped.
    """

    def __init__(self, n_workers, *, watchdog_interval=0.5, autostart=True):
        if n_workers < 1:
            raise ValueError("n_workers must be >= 1")
        self.n_workers = n_workers
        self.shards = [collections.deque() for _ in range(n_workers)]
        self._rr = itertools.count()
        self._cond = threading.Condition(threading.Lock())
        self._submitted = 0
        self._settled = 0
        self._shutdown = False
        self.tasks = {}  # task_id -> _Task, every submitted task, forever
        self.deadline_misses = 0
        self.requeues = 0
        self.steals = 0
        self.late_completions = 0
        self._watchdog_interval = watchdog_interval
        self._threads = []
        self._watchdog = None
        if autostart:
            self.start()

    def start(self):
        with self._cond:
            if self._threads:
                return
            for wid in range(self.n_workers):
                thread = threading.Thread(
                    target=self._worker, args=(wid,),
                    name=f"panel-worker-{wid}", daemon=True)
                self._threads.append(thread)
                thread.start()
            self._watchdog = threading.Thread(
                target=self._watch, name="panel-watchdog", daemon=True)
            self._watchdog.start()

    def submit(self, fn, *, kill=None, deadline_s=None, max_retries=1,
               task_id=None, _shard=None):
        """Submit work. ``deadline_s`` is the per-task wall-clock budget."""
        task = _Task(task_id if task_id is not None else f"task-{next(self._rr)}",
                     fn, kill, deadline_s, max_retries)
        with self._cond:
            if self._shutdown:
                raise RuntimeError("pool is shut down")
            shard = next(self._rr) % self.n_workers if _shard is None else _shard
            self.shards[shard].append(task)
            self.tasks[task.task_id] = task
            self._submitted += 1
            self._cond.notify_all()
        return task.task_id

    # -- scheduling ------------------------------------------------------
    def _pending_total(self):
        return sum(len(shard) for shard in self.shards)

    def _next_task(self, wid):
        """Own shard head, else steal from the longest other shard's tail."""
        with self._cond:
            while True:
                if self.shards[wid]:
                    return self.shards[wid].popleft()
                donor = max(
                    (i for i in range(self.n_workers) if i != wid),
                    key=lambda i: len(self.shards[i]), default=None)
                if donor is not None and self.shards[donor]:
                    self.steals += 1
                    return self.shards[donor].pop()
                if self._shutdown and self._settled >= self._submitted:
                    return None
                self._cond.wait(timeout=self._watchdog_interval)

    # -- execution --------------------------------------------------------
    def _worker(self, wid):
        while True:
            task = self._next_task(wid)
            if task is None:
                return
            with self._cond:
                if task.state is not _Task.PENDING:
                    continue  # stale queue entry; state machine owns it
                task.state = _Task.RUNNING
                task.run_id += 1
                run_id = task.run_id
                task.start_time = time.time()
                if task.deadline_s is not None:
                    task.deadline_at = task.start_time + task.deadline_s
            outcome, result, error = "completed", None, None
            try:
                result = task.fn()
            except Exception as exc:  # noqa: BLE001 - recorded, never dropped
                outcome, error = "error", f"{type(exc).__name__}: {exc}"[:500]
            with self._cond:
                # Only the live run may settle the task; a watchdog overrun
                # invalidates run_id, so a late return is ignored, not double
                # counted.
                if task.state is _Task.RUNNING and task.run_id == run_id:
                    task.state = _Task.DONE
                    task.end_time = time.time()
                    task.wall_seconds = task.end_time - task.start_time
                    task.outcome = outcome
                    task.result = result
                    task.error = error
                    self._settled += 1
                    self._cond.notify_all()
                else:
                    self.late_completions += 1

    def _watch(self):
        while True:
            with self._cond:
                if self._shutdown and self._settled >= self._submitted:
                    return
                now = time.time()
                expired = [task for task in self.tasks.values()
                           if task.state is _Task.RUNNING
                           and task.deadline_s is not None
                           and now > task.deadline_at]
                for task in expired:
                    # Invalidate the running worker's completion first, under
                    # the lock, so its late return cannot settle the task.
                    task.run_id += 1
                    task.state = _Task.DONE  # transient; reset below
                    self.deadline_misses += 1
                kills = [(task, task.kill) for task in expired]
            for task, kill in kills:
                try:
                    kill()
                except Exception:  # noqa: BLE001 - kill is best-effort
                    pass
                with self._cond:
                    if task.retries < task.max_retries:
                        task.retries += 1
                        task.state = _Task.PENDING
                        self.shards[hash(task.task_id) % self.n_workers].append(task)
                        self.requeues += 1
                    else:
                        task.state = _Task.DONE
                        task.end_time = time.time()
                        task.wall_seconds = task.end_time - task.start_time
                        task.outcome = "failed"
                        task.error = "deadline_exhausted"
                        self._settled += 1
                    self._cond.notify_all()
            with self._cond:
                self._cond.wait(timeout=self._watchdog_interval)

    def join(self, timeout=None):
        """Block until every submitted task has a recorded outcome."""
        deadline = None if timeout is None else time.time() + timeout
        with self._cond:
            while self._settled < self._submitted:
                remaining = None if deadline is None else deadline - time.time()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("pool join timed out")
                self._cond.wait(timeout=remaining)
            self._shutdown = True
            self._cond.notify_all()
        for thread in self._threads:
            thread.join(timeout=30)
        if self._watchdog is not None:
            self._watchdog.join(timeout=30)

    def outcome_counts(self):
        counts = collections.Counter()
        for task in self.tasks.values():
            counts[task.outcome or "unsettled"] += 1
        return dict(counts)


# ---------------------------------------------------------------------------
# Pinned-evaluator panel layer.
# ---------------------------------------------------------------------------

def _load_patched_evaluator(work_dir):
    """Import a copy of the pinned evaluator with the PYTHONPATH seam patched.

    Mirrors run_p02_live_panel.patch_evaluator: the pinned
    reference/evaluator/evaluate.py is never modified; the copy passes
    TITAN_P02_PYTHONPATH through to the stripped worker environments so the
    lab's root modules (observed_clone, seller_snapshot, ...) import.
    """
    from run_p02_live_panel import (  # noqa: PLC0415 - lab-local import
        isolated_source_pythonpath, patch_evaluator)
    pythonpath = isolated_source_pythonpath(LAB)
    patched = Path(work_dir) / "evaluate_parallel_panel.py"
    patch_evaluator(LAB / "reference/evaluator/evaluate.py", patched)
    name = "panel_patched_evaluator_" + hashlib.sha256(
        str(patched).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, patched)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    os.environ["TITAN_P02_PYTHONPATH"] = pythonpath
    return module, pythonpath


def _install_actor_tracking(ev):
    """Register each game task's actors for deadline kills.

    Replaces ``Actor`` on the patched evaluator module (the pinned file is
    untouched).  play() resolves the module-global ``Actor`` at call time, so
    games still run the real Actor machinery; the wrapper records instances
    in the calling worker thread's registry so the pool watchdog can close
    exactly that task's process groups on overrun.
    """
    base = ev.Actor
    active = {}  # thread ident -> registry list for the running task
    active_lock = threading.Lock()

    class TrackingActor(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            with active_lock:
                registry = active.get(threading.get_ident())
            if registry is not None:
                with registry[1]:
                    registry[0].append(self)

    ev.Actor = TrackingActor
    return active, active_lock


def _play_game_with_infra_retries(play_fn, max_attempts):
    """Play one game, retrying only never-started games.

    A game that fails with an RPC timeout at step 0 never produced any game
    state, so retrying it cannot condition on game outcomes; the retry is
    predeclared, outcome-blind, and recorded per game in ``_attempts``.
    Crashes and mid-game failures are never retried: they are real results.
    """
    attempts = 0
    while True:
        attempts += 1
        game = play_fn()
        game["_attempts"] = attempts
        failure = game.get("failure") or {}
        infrastructural = (
            game.get("status") != "complete"
            and game.get("steps", 0) == 0
            and failure.get("kind") == "timeout"
            and failure.get("phase") in ("action", "startup")
        )
        if not infrastructural or attempts > max_attempts:
            return game


def _tracked_game(ev, active, active_lock, engine, pair, engine_dir, loader,
                  seed, seat, index, timeouts, rng_seed, max_attempts):
    """Run one real evaluator game; returns (game_dict, registry)."""
    registry = ([], threading.Lock())
    ident = threading.get_ident()
    with active_lock:
        active[ident] = registry
    cpu0 = time.process_time()
    try:
        game = _play_game_with_infra_retries(
            lambda: ev.play(engine, pair, engine_dir, loader, seed, seat,
                            rng_seed=rng_seed + index, **timeouts),
            max_attempts)
    finally:
        with active_lock:
            active.pop(ident, None)
    game["_driver_cpu_seconds"] = time.process_time() - cpu0
    game["_cell"] = {"seed": seed, "candidate_seat": seat}
    return game, registry


def _kill_registry(registry):
    """Close exactly one task's actor process groups (best effort)."""
    actors, lock = registry
    with lock:
        live = list(actors)
    # Close exactly this task's actor process groups.  play() observes the
    # exits and returns a failed game result; the watchdog then requeues or
    # records the miss.  Actor.close is idempotent, so racing play()'s own
    # cleanup is safe.
    for actor in live:
        try:
            actor.close()
        except Exception:  # noqa: BLE001 - best effort
            pass


def build_cells(seeds, seats):
    """Fixed panel order: seed-major, then seat.  Same in serial/parallel."""
    return [(seed, seat) for seed in seeds for seat in seats]


def _game_specs(ev, candidate, opponent, cells):
    """Resolve the two agent specs per cell; self-play when opponent is None."""
    specs = []
    for seed, seat in cells:
        if opponent is None:
            pair = [candidate, candidate]
        elif seat == 0:
            pair = [candidate, opponent]
        else:
            pair = [opponent, candidate]
        specs.append(pair)
    return specs


def run_panel(*, candidate, opponent=None, seeds, seats=(0, 1),
              workers=2, serial=False, task_deadline_s=300.0, max_retries=1,
              action_timeout=1.0, startup_timeout=10.0, game_timeout=120.0,
              rng_seed=20260907, engine_dir=None, loader=None,
              serial_baseline_wall=None, work_dir=None):
    """Run a full panel through the pinned evaluator.

    Returns (results, report): per-cell game dicts in fixed panel order and
    the cost report.  ``opponent=None`` means self-play (candidate vs
    candidate).  ``serial=True`` runs the single-process deterministic path:
    the same ev.play calls in the same cell order, one at a time.
    """
    work = Path(work_dir) if work_dir else Path(
        tempfile.mkdtemp(prefix="parallel-panel-"))
    work.mkdir(parents=True, exist_ok=True)
    ev, pythonpath = _load_patched_evaluator(work)
    engine_dir = str(engine_dir or (LAB / "reference/engine"))
    loader = str(loader or (LAB.parent / "20260907-offline-agent/evaluate.py").resolve())
    engine, engine_hashes = ev.get_engine(engine_dir, loader)
    if getattr(ev, "ENGINE_REF", ENGINE_REF) != ENGINE_REF:
        raise ValueError("evaluator engine ref moved; update explicitly")

    candidate_spec = ev.resolve_spec(candidate)
    opponent_spec = ev.resolve_spec(opponent) if opponent else None
    cells = build_cells(seeds, seats)
    specs = _game_specs(ev, candidate_spec, opponent_spec, cells)

    panel_started = time.time()
    driver_cpu_started = time.process_time()
    results = [None] * len(cells)

    if serial:
        for index, ((seed, seat), pair) in enumerate(zip(cells, specs)):
            cpu0 = time.process_time()

            def play_once(index=index, seed=seed, seat=seat, pair=pair):
                return ev.play(engine, pair, engine_dir, loader, seed, seat,
                               rng_seed=rng_seed + index,
                               action_timeout=action_timeout,
                               startup_timeout=startup_timeout,
                               game_timeout=game_timeout)

            game = _play_game_with_infra_retries(play_once, 1 + max_retries)
            game["_driver_cpu_seconds"] = time.process_time() - cpu0
            game["_cell"] = {"seed": seed, "candidate_seat": seat}
            results[index] = game
        pool_stats = {"workers": 1, "deadline_misses": 0, "requeues": 0,
                      "steals": 0, "late_completions": 0,
                      "outcomes": {"completed": len(cells)}}
    else:
        active, active_lock = _install_actor_tracking(ev)
        pool = WorkerPool(workers)
        timeouts = {"action_timeout": action_timeout,
                    "startup_timeout": startup_timeout,
                    "game_timeout": game_timeout}

        def make_task(index, seed, seat, pair):
            holder = {}

            def run():
                game, registry = _tracked_game(
                    ev, active, active_lock, engine, pair, engine_dir,
                    loader, seed, seat, index, timeouts, rng_seed,
                    1 + max_retries)
                holder["registry"] = registry
                return game

            def kill():
                registry = holder.get("registry")
                if registry is not None:
                    _kill_registry(registry)

            return run, kill

        for index, ((seed, seat), pair) in enumerate(zip(cells, specs)):
            run, kill = make_task(index, seed, seat, pair)
            pool.submit(run, kill=kill, deadline_s=task_deadline_s,
                        max_retries=max_retries,
                        task_id=f"game-{index:04d}-seed{seed}-seat{seat}")
        pool.join()
        for index, (seed, seat) in enumerate(cells):
            task = pool.tasks[f"game-{index:04d}-seed{seed}-seat{seat}"]
            if task.outcome == "completed":
                results[index] = task.result
            else:
                results[index] = {
                    "status": "pool_failed", "seed": cells[index][0],
                    "candidate_seat": cells[index][1],
                    "_cell": {"seed": cells[index][0],
                              "candidate_seat": cells[index][1]},
                    "pool_outcome": task.outcome, "pool_error": task.error,
                    "retries": task.retries,
                    "_driver_cpu_seconds": 0.0,
                    "actors": [],
                }
        pool_stats = {"workers": workers,
                      "deadline_misses": pool.deadline_misses,
                      "requeues": pool.requeues, "steals": pool.steals,
                      "late_completions": pool.late_completions,
                      "outcomes": pool.outcome_counts()}

    wall_seconds = time.time() - panel_started
    driver_cpu_seconds = time.process_time() - driver_cpu_started
    report = cost_report(
        cells=cells, results=results, wall_seconds=wall_seconds,
        driver_cpu_seconds=driver_cpu_seconds, pool_stats=pool_stats,
        serial=serial, candidate=candidate, opponent=opponent,
        engine_hashes=engine_hashes, pythonpath=pythonpath,
        workers=pool_stats["workers"], task_deadline_s=task_deadline_s,
        max_retries=max_retries, serial_baseline_wall=serial_baseline_wall)
    return results, report


def cost_report(*, cells, results, wall_seconds, driver_cpu_seconds,
                pool_stats, serial, candidate, opponent, engine_hashes,
                pythonpath, workers, task_deadline_s, max_retries,
                serial_baseline_wall=None):
    """Per-panel cost report compared against the evaluation contract."""
    budget_ms = EVAL_CONTRACT["per_move_budget_ms"]
    per_run_wall = []
    total_moves = 0
    weighted_move_ms = 0.0
    worst_move_ms = 0.0
    games_over_budget = 0
    child_cpu_seconds = 0.0
    completed = failed = 0
    infra_retries = 0
    for game in results:
        per_run_wall.append(game.get("wall_seconds", 0.0))
        infra_retries += max(0, game.get("_attempts", 1) - 1)
        if game.get("status") == "complete":
            completed += 1
        else:
            failed += 1
        for actor in game.get("actors", []) or []:
            calls = actor.get("calls", 0) or 0
            mean_ms = (actor.get("mean_call_seconds", 0.0) or 0.0) * 1000.0
            max_ms = (actor.get("max_call_seconds", 0.0) or 0.0) * 1000.0
            total_moves += calls
            weighted_move_ms += mean_ms * calls
            worst_move_ms = max(worst_move_ms, max_ms)
            child_cpu_seconds += (actor.get("call_cpu_seconds", 0.0) or 0.0)
        game_max = max(((a.get("max_call_seconds", 0.0) or 0.0)
                        for a in game.get("actors", []) or []), default=0.0)
        if game_max * 1000.0 > budget_ms:
            games_over_budget += 1
    mean_move_ms = weighted_move_ms / total_moves if total_moves else 0.0
    runs = len(cells)
    report = {
        "schema": "titan.parallel-panel-cost.v1",
        "contract": EVAL_CONTRACT,
        "panel": {
            "mode": "self_play" if opponent is None else "paired",
            "candidate": candidate,
            "opponent": opponent,
            "cells": [{"seed": seed, "candidate_seat": seat}
                      for seed, seat in cells],
            "runs": runs,
            "engine_ref": ENGINE_REF,
            "engine_sha256": engine_hashes,
            "isolated_pythonpath": pythonpath,
            "scheduler": "serial" if serial else "deadline_aware_worker_pool",
            "workers": workers,
            "task_deadline_s": task_deadline_s,
            "max_retries": max_retries,
        },
        "outcomes": {
            "completed": completed,
            "failed": failed,
            # Predeclared, outcome-blind retries of never-started games
            # (step-0 RPC timeout: cold-start infrastructure flake).
            "infra_retries": infra_retries,
            **{k: v for k, v in pool_stats.items()
               if k in ("deadline_misses", "requeues", "steals",
                        "late_completions")},
            "pool_outcomes": pool_stats.get("outcomes", {}),
        },
        "wall_seconds": wall_seconds,
        "driver_cpu_seconds": driver_cpu_seconds,
        "child_cpu_seconds": child_cpu_seconds,
        "per_run": {
            "mean_wall_s": statistics.mean(per_run_wall) if per_run_wall else 0.0,
            "max_wall_s": max(per_run_wall, default=0.0),
            "min_wall_s": min(per_run_wall, default=0.0),
        },
        "per_move": {
            "total_moves": total_moves,
            "mean_ms": mean_move_ms,
            "worst_ms": worst_move_ms,
            "budget_ms": budget_ms,
            "games_with_worst_move_over_budget": games_over_budget,
        },
        "vs_contract": {
            "runs": f"{runs}/{EVAL_CONTRACT['runs_per_panel']}",
            "runs_complete": runs == EVAL_CONTRACT["runs_per_panel"],
            "workers_vs_beam_width": (
                f"{workers}/{EVAL_CONTRACT['beam_width']}"),
            "per_move_budget_ms": budget_ms,
            "worst_move_ms": worst_move_ms,
            "per_move_budget_met": worst_move_ms <= budget_ms,
        },
    }
    if serial_baseline_wall is not None and wall_seconds > 0 and not serial:
        report["speedup_vs_serial"] = serial_baseline_wall / wall_seconds
        report["serial_baseline_wall_s"] = serial_baseline_wall
    return report


def _default_seeds():
    return list(range(1, 33))


def _parse_seeds(text):
    seeds = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            seeds.extend(range(int(lo), int(hi) + 1))
        else:
            seeds.append(int(part))
    return seeds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",
                        default=str(LAB / "candidates/v3-kestrel-capital-execution"
                                    "/candidate_main.py::agent"))
    parser.add_argument("--opponent", default=None,
                        help="path.py::fn for a paired panel; omit for self-play")
    parser.add_argument("--seeds", default=",".join(map(str, _default_seeds())),
                        help="comma-separated seeds; default 1..32 (64 runs)")
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--workers", type=int,
                        default=min(EVAL_CONTRACT["beam_width"],
                                    os.cpu_count() or 1))
    parser.add_argument("--serial", action="store_true",
                        help="single-process deterministic path")
    parser.add_argument("--task-deadline-s", type=float, default=300.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--action-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=120.0)
    parser.add_argument("--rng-seed", type=int, default=20260907)
    parser.add_argument("--engine-dir", type=Path, default=None)
    parser.add_argument("--loader", type=Path, default=None)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--serial-baseline-wall", type=float, default=None,
                        help="measured serial wall seconds for speedup math")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    seeds = _parse_seeds(args.seeds)
    seats = [int(s) for s in args.seats.split(",") if s.strip()]
    results, report = run_panel(
        candidate=args.candidate, opponent=args.opponent, seeds=seeds,
        seats=seats, workers=args.workers, serial=args.serial,
        task_deadline_s=args.task_deadline_s, max_retries=args.max_retries,
        action_timeout=args.action_timeout,
        startup_timeout=args.startup_timeout, game_timeout=args.game_timeout,
        rng_seed=args.rng_seed, engine_dir=args.engine_dir,
        loader=args.loader,
        serial_baseline_wall=args.serial_baseline_wall,
        work_dir=args.work_dir)

    summary = report["vs_contract"]
    print(f"panel: {report['panel']['mode']} runs={len(results)} "
          f"workers={report['panel']['workers']} "
          f"scheduler={report['panel']['scheduler']}")
    print(f"outcomes: completed={report['outcomes']['completed']} "
          f"failed={report['outcomes']['failed']} "
          f"infra_retries={report['outcomes']['infra_retries']} "
          f"deadline_misses={report['outcomes']['deadline_misses']} "
          f"requeues={report['outcomes']['requeues']} "
          f"steals={report['outcomes'].get('steals', 0)}")
    print(f"wall: {report['wall_seconds']:.1f}s "
          f"driver_cpu: {report['driver_cpu_seconds']:.1f}s "
          f"child_cpu: {report['child_cpu_seconds']:.1f}s")
    print(f"per_run: mean={report['per_run']['mean_wall_s']:.2f}s "
          f"max={report['per_run']['max_wall_s']:.2f}s")
    print(f"per_move: mean={report['per_move']['mean_ms']:.2f}ms "
          f"worst={report['per_move']['worst_ms']:.1f}ms "
          f"budget={report['per_move']['budget_ms']:.0f}ms "
          f"games_over={report['per_move']['games_with_worst_move_over_budget']}")
    print(f"vs_contract: runs={summary['runs']} "
          f"workers_vs_beam_width={summary['workers_vs_beam_width']} "
          f"budget_met={summary['per_move_budget_met']}")
    if "speedup_vs_serial" in report:
        print(f"speedup_vs_serial: {report['speedup_vs_serial']:.2f}x")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Game dicts carry full actor stats; keep the report file lean.
        slim = dict(report)
        slim["games"] = [
            {k: g.get(k) for k in ("seed", "candidate_seat", "status",
                                   "scores", "steps", "wall_seconds",
                                   "trace_sha256", "_cell",
                                   "_driver_cpu_seconds")
             if k in g} | ({"pool_outcome": g["pool_outcome"],
                            "pool_error": g.get("pool_error")}
                           if g.get("status") == "pool_failed" else {})
            for g in results
        ]
        args.out.write_text(json.dumps(slim, indent=2, allow_nan=False) + "\n")
        print(f"report: {args.out}")
    failed = report["outcomes"]["failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
