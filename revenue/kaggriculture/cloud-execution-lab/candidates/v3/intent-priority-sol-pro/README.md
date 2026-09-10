# TITAN V3 current-main intent-priority integration

Operation: `TITAN-V3-CURRENT-INTENT-PRIORITY-INTEGRATION-20260910-01`

This lane ports one admitted SELL scheduling factor onto the exact current
canonical archive. It does **not** cherry-pick the historical V2 runtime used
to discover the factor.

## Factor

Current canonical builds the candidate target mapping in global `PRODUCTS`
order. The enabled arm keeps the exact same target domain and the exact same
full-shed quantity for every product, but changes first insertion order to:

1. products already present in the scheduler's pending intent;
2. products encountered first in inherited baseline SELL orders;
3. all remaining products in canonical `PRODUCTS` order.

The optimizer's strict-greater rank comparison is unchanged, so the factor
only resolves equal-ranked cross-product choices. Unit execution, prices,
receipt math, target quantities, market emission, production, funding, land,
crop release, and all non-SELL behavior remain outside this factor.

## Why this factor

The exact source screen in PR #11963 completed 32 paired cells / 64 official
offline games on a frozen V2 control. Six cells changed candidate actions.
The admitted arm produced:

- mean own cash `+8.375`, median `0`;
- 6 positive / 26 zero / 0 negative cells;
- mean margin `+6.25`;
- zero new losses and zero lost wins;
- nonnegative mean own cash in every opponent-by-seat stratum.

Source workflow run: `34516136132`.

Retained source artifact: `10168056904`.

Source artifact SHA-256:
`528f7557a899c1376c8fe04ed328c70a17a760aa3a725e190710ea13ad7e13f8`.

That screen is mechanism evidence, not permission to reuse its stale V2
closure. This lane therefore reruns the factor against current canonical
bytes.

## Current-source boundary

Pinned canonical base:
`98a98108998efac9e53a8b045f0fb2c85a4b19e2`.

Pinned current archive SHA-256:
`17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`.

Pinned current scheduler Git blob:
`a483b24dd72b580d7d8811636b54d2d44f391575`.

`materialize.py` validates the current release receipt, archive bytes,
`SOURCE.json`, every member digest, tar member safety, scheduler blob, and
single replacement cardinality before writing output.

The default-off arm extracts the archive exactly and must have zero changed
files. The enabled arm must have the same file inventory with exactly one
changed member: `scheduler.py`. The archive `SOURCE.json` intentionally stays
as the source-control manifest; the separate materialization receipt records
the candidate closure and one-file delta.

## Execution binding

`bind.py` inventories each materialized closure and emits a tiny entry wrapper
that recomputes the closure before importing `main.py`. A changed dependency,
new file, removed file, symlink, or wrapper mismatch fails before the agent can
run.

The workflow uses the source-pinned candidate-action evaluator repair from
`c3c2668d4822713afb126579f2f253788372f6ea`. Candidate returned actions are
hashed after both agents return and before the official interpreter applies
them. The comparator independently binds:

- materialized control and candidate closures;
- bound entry wrapper hashes;
- current archive and scheduler pins;
- patched evaluator source and output hashes;
- engine, loader, opponents, seeds, limits, and complete 719-action episodes.

## Fresh admission panel

The workflow runs both arms on the same 32-cell grid:

- opponents: Arlene and V1;
- seeds: `539131249`, `1834999074`, `2609097301`, `2609097302`,
  `2609097303`, `2609097304`, `2611092201`, `2611092207`;
- both candidate seats;
- official interpreter, 720 episode steps, 719 returned candidate actions;
- fixed agent RNG seed `20260909`;
- 1.0-second action RPC deadline.

Admission requires candidate-action activation, survival of at least one known
activating seed, positive mean own cash and margin, nonnegative median, zero
negative own-cash cells, zero new losses, zero lost wins, and nonnegative
opponent-by-seat strata.

## Local contracts

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v3/intent-priority-sol-pro
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v \
  test_materialize.py test_bind.py test_compare_panel.py
```

## Authority boundary

This is an additive, default-off candidate and evidence lane. It does not
modify canonical runtime source, `TITAN-CONFIG.json`, the current archive,
release pointers, provider state, Kaggle notebooks, or submissions. A passing
offline panel is not hosted leaderboard scoring or submission authorization.
