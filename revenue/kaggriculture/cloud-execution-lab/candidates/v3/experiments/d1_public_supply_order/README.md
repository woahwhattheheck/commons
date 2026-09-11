# D1 public rival-supply SELL ordering

Claim: `TITAN-V31-D1-PUBLIC-RIVAL-SUPPLY-FORECAST-20260911-01`

Muse's private-replay D-series handoff identified public rival tiles as a potentially useful market-timing signal. This experiment tests the smallest live-V3.1 mechanism implied by that observation. It does **not** predict an exact future price and does not infer hidden rival shed, worker inventory, seeds, or market orders.

## Mechanism

The pinned official interpreter exposes both farms publicly while `private` remains per-player. Crop/animal tiles include their current standing `yield_units`. Market orders then execute row-by-row in lockstep, with both players receiving the same pre-commit quote for a unit at a given row index.

D1 therefore leaves the final R04 action unchanged except for one possible mutation: inside its contiguous **leading SELL block**, stable-promote SELL rows whose product has positive visible standing yield on the rival farm. Parent order is retained inside the pressured group and inside the unpressured group.

The factor:

- never changes a SELL quantity;
- never creates/deletes a market row;
- never moves a sale across turns;
- never crosses the first non-SELL or malformed row;
- never changes farmer/hand commands;
- never reads rival private state;
- fails closed under custom `marketParams`, malformed public counters, non-two-player shape, or absent signal;
- returns the exact parent object when no mutation is justified.

This is deliberately narrower than extending E184's horizon. Horizon-10 produced a strong self-play signal but failed the frozen Arlene generalization gate, so D1 begins with row position only.

## D3 paired externality gate

The dedicated workflow rebuilds exact V3.1 from frozen source base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14` and canonical SHA-256 `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`, carried by immutable commit `c580f7805cc7468094c0e880f4923133d45d70d0`.

It first evaluates exact V3.1 against itself, then evaluates D1 against the **same exact V3.1 opponent** on seeds `2611151001..2611151008`, both candidate seats. The receipt pairs cells and reports:

- `delta_own`;
- `delta_rival`;
- `delta_margin = delta_own - delta_rival`;
- positive/tie/negative cells and mean/median/range;
- changed evaluator traces;
- exact source/package/evaluator digests.

The candidate is built only in runner temp by adding this experiment module and an evaluation-only final-R04 wrapper. `TITAN-CONFIG.json` must remain byte-equivalent as parsed, and every baseline package file except the candidate R04 wrapper must retain its digest. No checked-out production file is edited.

## Truth boundary

Positive direct-V3.1 paired margin would justify a third-opponent/generalization screen, **not** default enablement. Negative or mixed externality evidence is retained as a rejection/conditioning signal. Any future production carrier needs independent review, exact materialized-package custody, representative opponent-mixture evidence, and explicit integration authority.

This PR changes no `overlay/**`, runtime, package input, config/default, canonical archive, evaluator semantics, opponent implementation, provider state, or Kaggle submission.
