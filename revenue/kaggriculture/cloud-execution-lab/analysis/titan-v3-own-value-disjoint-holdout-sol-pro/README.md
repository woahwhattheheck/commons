# TITAN V3 own-value one-shot disjoint holdout — SOL-PRO

## Purpose

Spend one precommitted confirmation bank on the exact own-value SELL objective
that advanced from PR #11965. The experiment compares the unchanged selected
TITAN archive with the same archive plus one source overlay:

```text
MarketPath.score()[0]
  control:   own_cash + carry - rival_cash
  candidate: own_cash + carry
```

This lane does not alter the canonical runtime, selected archive, configuration,
provider state, release pointer, Kaggle state, or submission state.

## Exact parent and development evidence

The branch is a direct child of reviewed executable head
`b6b9a8a4ca26152bbfe1a3833380ca885e5c4cae`.

That parent retained the current-package development screen from run
`34521455981`, artifact `10170277744`:

- 32 paired cells / 64 complete official-interpreter games;
- 32/32 tested-seat returned-action streams changed;
- mean / median own cash delta `+159.25 / +118.5`;
- total own cash delta `+5,096`;
- mean margin delta `+530.96875`;
- control `31W/1L`, candidate `32W/0L`;
- zero new losses and zero lost wins;
- every opponent × candidate-seat stratum passed the parent nonregression gate.

Those rows selected the hypothesis. They are not reused here.

## Precommitted holdout

The seed bank was derived before any holdout game existed with:

```text
uint31(first4bytes(sha256(
  "titan-v3-own-value-disjoint-holdout-sol-pro-20260910-01" + ":" + index
)))
```

Exact seeds, in execution order:

```text
1201189346,2053792019,684357706,572159600,
1619590821,1748784700,2100322278,1851971276
```

They have zero overlap with the eight development seeds in PR #11965.

Frozen opponent order:

1. Apex;
2. Kaito v43;
3. COK v10;
4. public BT12;
5. frozen V1;
6. frozen V2.

Both candidate seats are run for every opponent and seed. Each arm therefore
contains 96 complete cells; the comparison consumes 192 official-interpreter
games total. Exactly one candidate hypothesis is spent on this bank. The
economic result is terminal evidence and must not be tuned and rerun on these
seeds.

## Evidence and admission

The run:

- binds the exact parent commit and all five changed paths;
- verifies current archive, source-manifest, objective, carrier, evaluator, and
  opponent entry bytes;
- rebuild-checks the selected archive without mutation;
- materializes independent control and candidate roots from the same archive;
- captures the tested seat's returned action after both actors return and before
  interpretation;
- requires the literal 720-observation / 719-action lifecycle;
- requires complete, finite, unique, score-to-terminal-bank-consistent rows;
- verifies the runtime trees before and after the panel;
- derives every own-cash, rival-cash, margin, trace, action, and outcome delta
  from retained raw reports.

`ADMIT` requires all parent gates on the literal 96-cell grid:

- nonzero candidate-action activation;
- positive global mean own cash and mean margin;
- nonnegative global median own cash;
- at least as many positive as negative own-cash cells;
- zero new losses and zero lost wins;
- for every opponent × candidate-seat stratum: nonnegative mean and median own
  cash, nonnegative mean margin, at least as many positive as negative cells,
  and no outcome regression.

The workflow uploads all evidence even when the economic verdict is `REJECT` or
`INACTIVE`, then marks the check successful only for `ADMIT`.

## Boundary

This is an offline causal holdout, not a leaderboard claim, release approval, or
Kaggle submission authorization. Integration remains with the one-tree owner.
