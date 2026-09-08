# Independent repro of the reported full-game runtime failure

Reported by WIDEFIELD on this same VM and retained as theirs, not restated as
mine: seed 9921012 versus COK10, candidate seat 1, **step 569, RPC 1.56202 s**
against a 1 s limit, prior maximum **returned** agent execution 0.49109 s, engine
`28b6d8af`, evaluator RNG 20260907, **jobs 2**. Opponent timeouts also occurred.

Everything below is a separate run at **jobs 1** on the exact archive
`titan-current.tar.gz`, 195,741 bytes, sha256
`70554dc01f8e84336ede169cf109f3d61152e169dce8ad5265b9625216fe52cb`, `SOURCE.json`
sha256 `5f6aab68a5c286e574adc80c998733c83680ac41ef92350b19867ffe9be52ef2`, fetched
from the immutable URL and verified before use. No file in it was edited,
repacked or substituted. **This VM is not Kaggle hardware and nothing here claims
it is.**

## 1. The failure does not reproduce at jobs=1

Full 719-action game, seat 1 versus COK10, archive default entrypoint:

| | |
|---|---:|
| actions | 719 |
| **step 569 in-process call** | **0.004268 s** |
| max in-process call (step 654) | 0.150724 s |
| p99 / p50 call | 0.017401 s / 0.003315 s |
| max guard-internal elapsed | 0.150606 s |
| **deadline fallbacks** | **0** |
| guard-budget breaches | 0 |
| max pickle round trip (obs + action) | 0.000994 s |
| max observation size | 16,896 B |
| warm import | 0.000282 s |
| peak RSS | 325 MB |
| terminal | own 104,882 / rival 86,871 |

Step 569 costs **4.3 ms** of agent computation here — about **366× under** the
1.56 s RPC that was observed. Import and serialization are not the gap either:
the whole marshalling round trip is under 1 ms on a ≤17 KB observation.

## 2. Total RPC versus internal action time: a structural gap

The guard starts its budget at `TitanAgent.act` entry and stops when it returns.
A tournament RPC is judged on

```
transport in + deserialize + [ act ] + serialize + transport out
```

so a **returned** maximum of 0.49 s and an RPC of 1.56 s are not in
contradiction — they measure different intervals. With `budget_seconds = 1.0`
against a 1 s RPC limit the guard has, by construction, **zero headroom** for
anything outside its own scope.

## 3. The guard does return under a deadline it cannot meet — but overshoots badly

120 real cards from this game, replayed with only `Features(budget_seconds=…)`
overlaid. Archive source unchanged; the overlay is recorded, not written back.

| budget | fallbacks | all returns legal | max wall | **overshoot** | over budget | fallback stages |
|---:|---:|---|---:|---:|---:|---|
| 1.000 s | 0 | yes | 0.0227 s | — | 0 | — |
| 0.050 s | 0 | yes | 0.0205 s | — | 0 | — |
| 0.010 s | 120 | yes | 0.0834 s | **+0.0734 s (8.3×)** | 4 | cold_start, production, selected_transform |
| 0.003 s | 120 | yes | 0.0396 s | **+0.0366 s (13×)** | 6 | cold_start |

**Every fallback returned a legal, well-formed action for the seat.** The guard
is sound in that sense. What it is not is *prompt*: at a tight budget it
overshoots by 73 ms, and the stage it overshoots in is `cold_start`.

### The cascade, which is the actual defect

`TitanAgent.act` sets `self.ready = False` on a deadline fallback. The comment
gives a correct reason — a cancelled mutation must not leave a half-updated
ledger in use. But the lever is wrong: the very next action then re-runs
`_initialize()`, which re-loads modules and rebuilds `SeedBudget` over the whole
route table, **inside the next budget**. One slow action therefore converts into
a permanently slow mode, and the re-entered stage is the one the guard is least
able to interrupt: SIGALRM is delivered on time, but CPython only runs the
handler at a bytecode boundary on the main thread, and module execution spends
long stretches below that boundary. That is exactly why the 0.003 s row is 120
fallbacks all from `cold_start`.

Cold start measured separately: step 0 of the full game costs 0.0526 s including
construction, and the 0.003 s probe's overshoot of 0.0366 s is the uninterruptible
part of it.

## 4. Contention inflates wall time while CPU stays flat

Same 120 cards, replayed against K competing CPU burners on this 4-core VM:

| competing burners | wall mean | wall max | **cpu mean** | cpu max | wall / cpu |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.005991 s | 0.022762 s | 0.005992 s | 0.022759 s | **1.000** |
| 2 | 0.005939 s | 0.022154 s | 0.005908 s | 0.022152 s | **1.005** |
| 6 | 0.010061 s | 0.041108 s | **0.006032 s** | 0.021186 s | **1.668** |

CPU per action is flat to three decimal places across all three loads; wall time
nearly doubles once the box is oversubscribed. The agent does not get slower — it
gets **descheduled**. No policy change can fix that, and it is the one mechanism
consistent with the reported opponent timeouts, which a defect inside this
candidate cannot explain at all.

## Minimal compatible patch proposal — for T08 integration owner GPT `6a9ef70e`

Ordered by value, all inside `titan_runtime.py`; none changes a decision, a
ledger or any policy output.

1. **Do not discard readiness on a deadline fallback.** Split `_initialize()`
   into an idempotent `_load_modules()` (module loads, `SeedBudget` construction)
   that is cached and never invalidated, and a cheap `_reset_state()` that clears
   only the mutable per-turn state. On `DeadlineExceeded`, call `_reset_state()`
   and leave `ready` true. This keeps the safety property the comment is
   protecting while removing the cascade, and it is a few lines.
2. **Raise the reserve to cover the measured uninterruptible window.**
   `reserve_seconds = 0.01` presumes the guard can stop within 10 ms; measured
   overshoot at a tight budget is 73 ms. Given the limit is on the RPC rather
   than on `act`, `budget_seconds ≈ 0.85–0.90` with `reserve_seconds ≥ 0.05` is
   the honest setting for a 1 s RPC. `1.0 / 0.01` leaves nothing for transport,
   scheduling, or the guard's own exit.
3. **Refuse to enter `cold_start` when the remaining budget cannot cover it.**
   Record the observed cold-start cost on the first successful initialization and,
   when the remaining budget is below it, return the legal fallback immediately
   instead of entering a stage the guard cannot interrupt promptly.

None of these is required for correctness of the *returned action* — every
fallback observed was legal. They are required for the guard to be prompt, and
for one slow turn not to poison the rest of the episode.

## What this does not establish

It does not prove the reported 1.56 s was scheduling. It shows the agent's own
computation at that cell is 4.3 ms at jobs=1, that marshalling is under 1 ms,
that the guard returns legally, and that wall-versus-CPU divergence under
oversubscription is real and measured on this box. WIDEFIELD's jobs=2 outcome
stands as theirs; this is an independent run, not a replacement, and no
tournament limit was relaxed to obtain it.
