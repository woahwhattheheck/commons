# Titan v3 proven-snapshot restoration

This lane turns the frozen September 7 finite-horizon SELL policy into a clean
`main.py::agent` candidate **without importing today's canonical wrapper or any
of its later feature flags**.

The source is already retained in `exports/titan-sell-v3-source.tar.gz`. Its
recorded source identity is commit `9f89a2cd75c5c89198caa1617a9e399900553ce3`,
archive SHA-256 `a14f9bbc7e10753fef2d5e983e9746e107940d7081b8934fb499561191e9c3c7`,
and source entrypoint `candidate.py::agent`.

The repository also retains exact development and held-out ledgers for those
bytes. Materialization no longer trusts a handwritten “12-0 / 8-0” statement:
it opens both ledgers, verifies their byte identities against `FILES.json`,
binds their source and execution closures, reconstructs every required
seed/opponent/seat cell, and derives W/T/L plus paired cash deltas from the game
rows. Those results remain historical local official-interpreter evidence, not
a hosted leaderboard score.

## Why this candidate exists

`candidate.py` exposes the measured `scheduler.agent` directly. The current
canonical `main.py` instead constructs `TitanAgent` from `TITAN-CONFIG.json`,
which presently enables later redundant-hire, market-pressure, operating-stock,
idle-fertilizer, crop-release, and early-capital transforms. Several release
entries explicitly say those increments lack a new full-game score panel. A
clean restoration candidate separates the measured policy from wrapper drift
and gives the official both-seat evaluator an honest strong-control boundary.

This does not claim that every later transform is bad. It creates the missing
control needed to discover which composition actually wins.

## Materialize

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python titan-v3/proven-snapshot/restore.py \
  --output /tmp/titan-v3-proven.tar.gz \
  --receipt /tmp/titan-v3-proven.receipt.json
```

The command fails unless all of the following agree:

* the hard-coded source commit, archive length, archive SHA-256, member count,
  and source-freeze SHA-256;
* `exports/ARTIFACTS.json`, `exports/FILES.json`, and every source archive byte;
* the five source identities in `SOURCE-FREEZE.json`;
* the exact 15-member runtime allowlist and deterministic tar metadata;
* compilable Python, closed local imports, and the thin
  `candidate.py -> scheduler.agent` contract;
* exact immutable identities for `runtime/development-v3.json` and
  `runtime/heldout-v3.json`;
* strict JSON with no duplicate keys, non-finite values, bool-as-integer seats,
  unexpected cells, duplicate cells, missing cells, incomplete games, score /
  seat mismatches, or summary drift;
* identical engine, evaluator, benchmark/opponent, scheduler, mechanics, and
  candidate identities across both ledgers;
* an isolated import of the generated `main.py::agent` package.

The output preserves every frozen source byte and adds only:

```python
from candidate import agent
```

Its tar and gzip metadata are deterministic. The JSON receipt binds every
member, source archive, generated entrypoint, final candidate hash, ledger hash,
and derived result. Existing outputs are never overwritten unless `--overwrite`
is explicit.

## Derived evidence boundary

The exact retained ledgers derive:

* development candidate: 12 W / 0 T / 0 L across 12 complete cells;
* held-out candidate: 8 W / 0 T / 0 L across 8 complete cells;
* held-out paired own-cash delta: +1,317 total, +164.625 mean;
* held-out minimum paired own-cash delta: -1,031;
* held-out negative paired cells: 1 of 8.

The final two facts matter. The frozen v3 is a strong measured control, but it
is **not** uniformly non-regressing. The receipt therefore emits
`BOUND_CONTROL_ONLY`, sets `hosted_leaderboard_claim` to false, and requires a
full current matched panel before promotion.

## Acceptance

```bash
python -m unittest discover -s titan-v3/proven-snapshot -p 'test_*.py' -v
python titan-v3/proven-snapshot/restore.py --output /tmp/titan-v3-proven.tar.gz \
  --receipt /tmp/titan-v3-proven.receipt.json
```

The unit suite covers exact materialization, byte determinism, artifact and
member-manifest drift, source-freeze drift, undeclared imports, entrypoint
mutation, traversal, symlink, duplicate members, tar metadata drift, overwrite
protection, pre-publication receipt conflicts, ledger hash drift, strict JSON,
source/engine custody, complete unique cell domains, bool-seat rejection,
derived summaries, paired cash reconciliation, and incomplete-game rejection.

## Promotion boundary

Treat the emitted archive as a challenger/control, not as an automatic release.
Run it against current canonical and independently materialized V1/V2 closures
on an identical, complete, both-seat official-engine panel. Preserve exact
archive hashes and cell identities. Rank own final cash before rivalry margin;
only complete measured outcomes authorize selection or upload.
