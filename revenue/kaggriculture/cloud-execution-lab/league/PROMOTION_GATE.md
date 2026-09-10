# TITAN matched-cell promotion gate

## Why this exists

The adversarial league's persisted Elo is useful for longitudinal monitoring,
but it is not a champion selector. `record_results()` updates ratings one game
at a time. When contestants face a common opponent field, whichever contestant
is folded first changes each opponent's rating before the next contestant is
folded. A displayed Elo lead can therefore be caused by row order even when
both contestants have the same W/T/L record.

The first league run demonstrates the second failure mode: aggregate wins and
positive mean cash can hide a severe matched-cell regression. The challenger
`v3-final-crop-binding` and canonical `v3-kestrel-capital-execution` both went
24-0 against the reduced field. The challenger averaged +3,982.667 own cash,
yet lost 60,938 own cash in one exact cell, lost five of 24 matched cells, and
had four negative opponent-by-seat mean strata. It must not replace canonical.

`promotion.py` makes promotion a separate, fail-closed decision over exact
`(opponent, seed, candidate_seat)` pairs. Input ordering cannot affect the
result.

## Default contract

A challenger is promoted only when:

- reference and challenger each have every cell declared by `plan.json`;
- every row is complete, finite, unique, and failure-free;
- no matched cell loses own cash versus canonical;
- no opponent-by-seat stratum loses own cash on average;
- mean own-cash delta and mean margin delta are nonnegative; and
- at least one matched cell strictly improves own cash.

Thresholds live in `promotion_policy.json`. Relaxations are explicit data, not
hidden code paths.

## Run it

```bash
python league/promotion.py \
  --games bank/v3-adversarial/league/runs/<stamp>/games.jsonl \
  --plan bank/v3-adversarial/league/runs/<stamp>/plan.json \
  --reference v3-kestrel-capital-execution \
  --policy league/promotion_policy.json \
  --json-out bank/v3-adversarial/league/runs/<stamp>/PAIRWISE_PROMOTION.json \
  --markdown-out bank/v3-adversarial/league/runs/<stamp>/PAIRWISE_PROMOTION.md
```

Exit `0` means a challenger is selected. Exit `3` means canonical is retained.
Malformed or ambiguous evidence raises `PromotionData` and fails closed.

The machine report includes exact coverage, matched-cell deltas, worst cell,
per-stratum deltas, rejection reasons, and the selected contestant. Multi-
challenger selection is deterministic: only eligible challengers enter the
ranking, ordered by mean own cash, mean margin, worst-cell cash, then name.

## First-run receipt

The audited receipt for run `20260910T191342Z` is committed beside the original
run as `PAIRWISE_PROMOTION.json` and `PAIRWISE_PROMOTION.md`. Its verdict is:

- selected: `v3-kestrel-capital-execution`;
- promotion: `NO`;
- challenger mean own-cash delta: `+3982.667`;
- challenger mean margin delta: `+4953.708`;
- matched cells: `+7 / =12 / -5`;
- worst own-cash delta: `-60938` at `official_random`, seed `2611031003`, seat 0;
- rejection: cell own-cash regression and stratum-mean own-cash regression.

This does not say the crop-binding mechanism is useless. It says the current
reduced panel does not prove it safe enough to displace canonical. Expand the
field and repair the negative cells, then rerun this gate.
