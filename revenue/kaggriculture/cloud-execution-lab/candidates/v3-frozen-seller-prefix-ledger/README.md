# TITAN V3 — Frozen seller exact-prefix ledger

Operation: `op:titan-v3-frozen-seller-phantom-tail-ledger-20260909-01`
Worker: **SOL-RECKONER**

## Defect

The pinned official market copies only the first `maxMarketOrdersPerTurn` rows
before execution. Canonical `FrozenSelected.transform()` instead totals every
returned SELL row when it writes `pending`, and pops `planned` when that full-list
total appears to cover the post-unit shed. A sale in the inactive suffix can
therefore be checkpointed as completed despite no stock or cash transition.

## Candidate boundary

This candidate changes no returned action and creates no sale. It wraps the
existing selected seller before `TitanAgent` takes its completed state snapshot:

- capture the exact pre-transform future plan;
- use the matching completed post-unit shed;
- replay only physical own SELL fills in the official first-N prefix;
- correct `pending` when a suffix row created phantom completion;
- restore future rows only from the newly chosen, post-transform, or exact
  pre-transform seller plan; never invent a date or quantity;
- reinstall after every controller/consumer reconstruction;
- fail closed to canonical state on malformed input or snapshot mismatch.

L02 remains a separate late-sale policy candidate. This lane neither imports nor
modifies L02 and does not enlarge, append, reorder, or remove any market row.

## Evidence

`test_current_source_contract.py` executes the exact current
`FrozenSelected.transform()` to show the predecessor erases an owned future plan,
and invokes the pinned engine to show the suffix sale leaves shed and cash
unchanged. `test_prefix_ledger.py` covers duplicate stock budgets, partial fills,
chosen-plan precedence, transactional malformed rows, action immutability,
idempotent install, and replacement-consumer reinstallation.

The path-scoped workflow also verifies the canonical archive and runs a small,
source-bound public-Arlene paired screen. That screen is only activation and
regression evidence; it is not a leaderboard or promotion claim.
