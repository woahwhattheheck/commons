# TITAN V3 market-carry candidate

Operation: `op:titan-v3-market-carry-20260909-01`

This additive candidate tests one direct score hypothesis against the exact current
TITAN controller: the current policy can leave deterministic town demand
unmonetized because it produces and sells goods but does not buy a temporarily
cheap product immediately before the already-visible town consumes market
inventory.

## Mechanism

`main.py` calls the canonical `cloud-execution-lab/main.py::agent` once.  The
completed action is then passed to `MarketCarry`, which may append exactly one
`BUY_PRODUCT` order at the end of the executable market queue.

A lot is admitted only when all of the following are true:

- the current action contains only existing `SELL`, `PASS`, or empty market rows;
- there is a free trailing market slot, so no inherited row is shifted or lost;
- the exact post-unit projection has shed room;
- observed cash alone funds the lot while preserving both an absolute reserve and
  a fractional spend cap; current-turn sale proceeds are never credited;
- the current step has deterministic demand from already-unlocked shops or the
  town center;
- exact sequential official quotes remain profitable under two conservative
  cases: public-plus-unseen rival supply and a rival-buy quote stress;
- the same product is not already being sold by the canonical action;
- the opening and final 48 decisions remain untouched.

The wrapper never changes `farmer`, `hands`, or an inherited market row.  It does
not reserve or post-edit later sales.  On subsequent observations, the existing
canonical seller sees the purchased stock and retains exclusive authority over
liquidation and its pending ledger.  One active-lot guard prevents stacking until
the stock is observed sold, the attempted purchase is observed unfilled, or a
bounded cooldown expires.

## Why this lane is separate

This is not LAND timing, sheep recovery, early-capital ordering, terminal
liquidation, fertilizer cycling, seller deferral, or a route selector.  It adds a
new, append-only inventory acquisition at a deterministic demand boundary and
leaves every existing mechanism intact.

## Validation

Local focused contracts:

```text
python -m py_compile market_carry.py main.py test_market_carry.py
python -m unittest -v test_market_carry.py
11 tests PASS, including 300 randomized prefix/invariant cases
```

The PR workflow additionally runs:

```bash
cd revenue/kaggriculture/cloud-execution-lab
python build_integrated.py --check
cd candidates/v3-market-carry
python -m unittest -v test_market_carry.py test_official_engine.py
python run_development_screen.py \
  --repo-root "$GITHUB_WORKSPACE" \
  --runner-head "$(git rev-parse HEAD)" \
  --seeds 2609099701,2609099702 \
  --output /tmp/titan-market-carry/SCREEN.json \
  --markdown /tmp/titan-market-carry/SCREEN.md
```

The exact-engine contracts prove the projected trade against the preserved
official market and town phases, verify post-unit capacity, and verify inherited
market fills are unchanged.  The development screen is eight full games:
current-control and candidate, both seats, seeds `2609099701..2609099702`,
against the exact public Arlene source.  The report binds the workflow head,
candidate/control/config/archive/source manifest, evaluator/loader/engine, and
the complete opponent source bundle.  It checkpoints after every game and fails
closed.

These two seeds are development-only.  No held seed, private opponent, Kaggle
upload, current archive mutation, promotion, or leaderboard-strength claim is
made by this candidate.
