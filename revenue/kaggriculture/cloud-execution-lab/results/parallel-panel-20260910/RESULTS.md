# Parallel eval throughput — measured results (2026-09-10)

Tool: `revenue/kaggriculture/cloud-execution-lab/parallel_panel.py`
(`riot/parallel-eval`). Reports: `results/parallel-panel-20260910/*.json`.

Environment: this VM (2 vCPUs). Pinned evaluator + KESTREL candidate,
self-play, seeds 1..32 × both seats = 64 runs per full panel.
Per-game deterministic RNG seed (`rng_seed + cell index`), same in both modes.

## 64-run panel, 2 workers (parallel)

| metric | measured |
|---|---|
| wall time | **562.2 s** |
| driver CPU | 61.2 s |
| child (actor) call CPU | 655.6 s |
| per-run wall | mean 17.54 s, min 14.88 s, max 26.26 s |
| per-move (92,032 moves) | mean 10.08 ms, **worst 349.7 ms** |
| 35 ms per-move budget | mean under budget; worst move over budget in **64/64 games** |
| outcomes | 64 completed, 0 failed |
| infra retries (step-0 RPC timeout) | 0 |
| pool deadline misses / requeues / steals / late completions | 0 / 0 / 0 / 0 |

## Serial vs parallel speedup (measured, identical 8-game cells, seeds 1–4)

| mode | wall | per-run mean |
|---|---|---|
| `--serial` | 100.6 s | 12.57 s |
| 2 workers | 67.8 s | 16.95 s |

**Speedup: 1.48x** on identical cells — not 2x. Per-move mean rose
7.22 ms → 9.73 ms under 2-worker contention (4 actor subprocesses on
2 vCPUs), so per-game wall is slower in parallel; the win comes from
overlapping games. On a wider machine the speedup should approach 2x
for 2 workers; the 24-wide contract beam needs real hardware.

## Infrastructure finding

Cold page cache makes the candidate's first move intermittently exceed
the evaluator's 1.0 s action RPC deadline (`Agent RPC wall-clock
deadline exceeded`, step 0, phase `action`) — reproduced standalone:
3 of 6 fresh games failed at step 0 before the cache warmed. The panel
retries only never-started games (no game state exists to condition on),
bounded, predeclared, and recorded (`outcomes.infra_retries`,
`_attempts` per game). Crashes and mid-game failures are never retried.

## Isolation

`PanelIsolationTests` (real pinned evaluator): parallel-vs-serial game
fingerprints (status, trace SHA-256, scores) match across modes and
repeated serial runs; no driver-side module/global leakage detected
(`_INSTANCE` null, no candidate modules, no cross-run state keys).
This exercises the agent through fresh pinned-evaluator `Actor`
subprocesses per game — not same-process agent loading; the older
same-process `_FACTORY_LOCK` + temporary global mutation path is
superseded by process isolation in this harness.
