# SPDX-License-Identifier: Apache-2.0
# TITAN v3 adversarial league

Weekly round-robin: the canonical v3 candidate
(`candidates/v3-kestrel-capital-execution/`) plus every registered
challenger play the vendored public-opponent bank
(`bank/v3-adversarial/`), **both seats, identical seeds**, through the
unmodified reference evaluator with the pinned official engine. No
simplified mechanics anywhere: every cell is real candidate entrypoints
vs real opponent code, and scoring comes from the engine itself.

## What it produces

Under `bank/v3-adversarial/league/`:

- `ledger.json` — Elo/lean ledger (both contestants and opponents rated),
  plus the per-contestant joint `(opponent, seat)` own-cash baseline.
- `runs/<utc-stamp>/` — staging fingerprints, per-shard evaluator
  reports, `games.jsonl` (one row per cell), `report.json`,
  `SUMMARY.md`, `ALARMS.md`.
- `ALARMS.md` — latest week's own-cash alarms.

## Own-cash alarms (generalized #11907)

`alarms.py` derives the exact joint `(opponent, candidate_seat)` strata
for each contestant and alarms when:

- `negative_own_cash` — stratum mean own-cash below `alarm_floor`
  (default 0.0). This is the #11907 witness: a stratum can lose on every
  seed while the global, per-opponent, and per-seat marginals all stay
  nonnegative.
- `own_cash_regression` — stratum mean dropped more than
  `alarm_drop_tolerance` below the prior week's ledger baseline.
- `incomplete_stratum` — fewer cells than required (fail-closed).

## Registering a challenger

```sh
python3 league/registration.py \
  --name v3-final-crop-binding \
  --entry cloud-execution-lab/candidates/v3-final-crop-binding/candidate_main.py \
  --support cloud-runtime-pulse/observed_clone.py \
  --support cloud-quickstep/seller_snapshot.py \
  --notes "what changed" \
  --check
```

Paths are relative to `revenue/kaggriculture/`. The entrypoint SHA-256 is
recorded at registration and re-verified every week; drift fails closed
(the challenger is skipped, not played). `--check` imports the
entrypoint and verifies the callable. Only `active: true` registrations
play.

## Running a panel

```sh
# plan + staging only
python3 league/run_league.py --dry-run
# full weekly panel (12 opponents x 8 seeds x 2 seats per contestant)
python3 league/run_league.py
# reduced field, e.g. for smoke panels
python3 league/run_league.py --opponents official_pass,official_random \
  --seeds 2611031001,2611031002 --workers 4
```

Each contestant is staged under the run dir: verbatim copies of its
declared support modules plus a generated bootstrap that imports the
real candidate entrypoint by absolute path. Candidate sources are never
copied or edited; fingerprints (SHA-256 of entry, support modules,
bootstrap) go into `report.json`.

Seeds are sharded across evaluator subprocesses (disjoint subsets, one
process per shard) exactly like `gauntlet_s11.py`; shard assignment
cannot change any game result.

## Environment notes

The evaluator's worker processes run with a stripped environment, so two
local prerequisites must exist on the league host:

1. `/tmp/v25/engine/kaggriculture.{py,json}` + `utils.py` — symlinks to
   the pinned `reference/engine/` sources (the three official bank
   agents hardcode this path), plus a minimal `kaggle_environments`
   package shim (`__init__.py`, `utils.py` symlink, `errors.py` with the
   two exception types the pinned `utils.py` imports, empty
   `schemas.json` — the interpreter never reads schemas).
2. The pinned engine sources themselves, already vendored at
   `reference/engine/` (git-blob SHA-1 verified by the evaluator).

## Tests

```sh
cd cloud-execution-lab/league
python3 -m unittest test_league_alarms test_league_ledger \
  test_league_registration test_league_runner
```
