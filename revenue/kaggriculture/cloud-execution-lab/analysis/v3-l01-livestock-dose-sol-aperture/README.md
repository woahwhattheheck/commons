# TITAN V3 — bounded livestock-dose ablation (SOL-APERTURE)

Operation: `TITAN-V3-L01-LIVESTOCK-DOSE-20260910-01`

## Question

The retained L01 panel established two facts that must be kept separate:

1. public leader policies are sheep-heavy; and
2. rewriting **every** post-opening COW buy to SHEEP was catastrophic across the
   six-opponent, 192-game panel.

That result rejects the unlimited substitution. It does not measure whether a
small early sheep dose helps. This lane isolates that missing dose response.

## Factor

The canonical opening pair at step 1 is immutable. For dose `N`, only the first
`N` complete `BUY_ANIMAL COW q` orders after step 1 and no later than step 143
may change animal name to `SHEEP`. The transform never inserts, deletes, moves,
resizes, or re-quantifies an order. If exact dose `N` would require splitting an
order or exceeds the eligible units, the entire transform is identity and the
receipt says why.

The production carrier wraps the canonical instance's lazy `_initialize`, calls
its parent exactly once, and patches each newly constructed controller once.
It never reads environment variables, time, RNG, opponent identity, hidden seed,
or network state.

## Planned arms and gate

Exact current canonical control versus doses `1, 2, 3, 4`, both seats, fixed
public seed bank, frozen Arlene plus frozen submitted V1. A dose can advance only
with a different pre-interpreter candidate-action digest, positive mean own cash,
nonnegative median own cash, nonnegative own-cash mean in every opponent × seat
stratum, and zero new losses. Otherwise the dose-response rejection remains the
result.

No canonical source, current archive, pointer, config, provider, Kaggle account,
or submission is changed by this evidence lane.
