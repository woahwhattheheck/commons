# B6 intraday market sweep — practice arm

## Hypothesis

R04 already ships `EVENING_FLUSH=True`, which sells projected shed stock of
`WOOL`, `MILK`, `STRAWBERRY`, and `MELON` at hours 21–23.  The source explicitly
classifies those four products as steep-curve products that no farm action consumes.
B6 tests one additional, earlier sale opportunity: on the first hour in 10–14 with
eligible stock, sell the same safe product set once, then leave the shipped evening
flush unchanged.

The expected upside is adversarial timing, not extra production: newly available
stock can hit the public market before later same-day rival sales push those steep
curves down.  The arm makes no realized-profit claim until paired execution proves it.

## Exact baseline custody

The raw evaluator entrypoint pins the deterministic V3.1 R04 settings from
`apply_v3.py` at canonical base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`:

- sale horizon `8`
- opening round trip `0`
- row order ON
- evening flush ON
- fertilizer sale advancement ON (`SALE_EXCLUDED == ('WHEAT',)`)
- cattle-early ON

No `overlay/**`, `apply_v3.py`, `TITAN-CONFIG.json`, package input, evaluator,
opponent, or Kaggle artifact is modified by this experiment.

## Safety boundary

`intraday_sweep()` deliberately reuses R04's own `FarmView`, `projected_shed`,
`FLUSH_ITEMS`, `MAX_ORDERS`, and evening-flush selection rule.

The transform:

1. is exact identity when disabled, on day 0, outside hours 10–14, at terminal turn,
   or after a successful sweep already fired that day;
2. sells only `WOOL/MILK/STRAWBERRY/MELON`;
3. subtracts any same-item quantity already sold by the parent action;
4. preserves every parent market row and uses only free order slots;
5. does not consume the day's chance if the order cap blocks the sweep;
6. uses the parent's same-turn shed projection, including reachable `DROP` effects;
7. resets its per-player latch when the game step restarts.

Telemetry records activations, sell rows, units advanced, current posted quote-value,
and order-cap declines.  `posted_quote_value` is **not** realized proceeds.

## Kill / promotion criteria

Kill or redesign B6 if any focused/native trace shows a farm-consumption shortfall,
row-cap displacement, parent-row mutation, game-restart state leak, or interaction that
changes the shipped evening-flush/cattle/fertilizer/terminal semantics beyond the added
midday sales.

Do not promote from source tests alone.  Economics must first clear a paired panel and
opponent-diversity check.  Under the current SIM FIDELITY STANDARD, this
`experiments/**` arm is practice/factor evidence only; a 1:1 gate additionally requires
canonical build/materialization + live submission config, the pinned official
interpreter, the frozen paired seed panel, and an exact opponent fingerprint.
