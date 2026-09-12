# DEMANDVEL × COMEBACK — residual public-supply tail pressure

This is a research-only composition of two canonical Gemini descendants in the existing V4 market-baseline authority. It does not sell, retime, choose a product, add a runtime key, or authorize an action.

## The missing question

COMEBACK supplies a source-authenticated **conditional** Apex STRAWBERRY sell schedule. DEMANDVEL supplies source-exact seeded NPC absorption. This package asks a second question: if we evaluate the source-declared maximum rival SELL envelope at one authenticated callback, are the public units left by our `t-1` / rival `t` counter small enough for the remaining low-tail NPC demand after `t`?

The distinction matters: the Apex source proves a rule and a maximum quantity, not that a replay actually fired or filled the row. `tail_pressure.py` therefore never upgrades the hypothetical max-envelope input into realized-event evidence.

For a certified event it:

1. requires `t = pre_step + 1` to be one of the pinned Apex STRAWBERRY event steps;
2. requires `rival_units` to equal that event's source-declared `max_sell`, explicitly as a conditional max envelope rather than a realized quantity;
3. runs the existing COMEBACK `predump_counterfactual` at `t-1/t`;
4. compares its post-`t` public inventory with the same starting inventory under no player/rival sale event, so `$1` sales that do not add public inventory contribute zero supply;
5. measures NPC absorption strictly after `t` on the canonical DEMANDVEL panel only: q=0.10, seeds 1..100; and
6. compares residual event supply with the floor of that p10 remaining-absorption tail.

The output is pressure evidence only. `decision_authority=false`, `timing_authority=false`, `opponent_future_supply_accounted=false`, and `realized_rival_quantity_authenticated=false` are hard boundaries.

## Authenticated conditional examples

With the current pinned sources:

- Apex 380/381 STRAWBERRY max-envelope event, eight units from us and the source-declared rival max of eight, with eight strawberry-consuming shop instances at step 380: the combined event leaves 16 public units relative to the no-event path. The canonical p10 remaining NPC absorption after step 381 is 132.8 units (floor budget 132). Immediate relative-margin swing is positive and low-tail headroom remains.
- Apex 402/403 with the same 8+8 max-envelope quantities and no immediate shop drain: residual event supply is again 16. The canonical p10 remaining absorption after step 403 is 127.3 (floor 127). The event still fits, but the later event has less unwind capacity.
- Synthetic public-state control at the authenticated 402/403 timing, starting inventory 9,700 with our 128 units plus the rival max-envelope eight: immediate COMEBACK swing remains positive, but 136 residual public units exceed the p10 budget of 127. The composite emits `POSITIVE_IMMEDIATE_COUNTER_TAIL_UNWIND_NOT_CERTIFIED`.
- At a saturated `$1` STRAWBERRY state, sales that do not move public inventory produce zero residual supply rather than an invented pressure penalty.

The third case is the useful invariant: **positive immediate counter economics are not enough to certify public-inventory unwind**.

## Fail-closed evidence coordinates

The certificate does not accept arbitrary STRAWBERRY timing, rival quantity, quantile, or seed panels. Those values determine the evidence claim itself, so allowing caller-selected coordinates would let a fabricated event or cherry-picked panel inherit the same authenticated-helper disposition.

`remaining_absorption_tail()` still permits custom finite q / strict integer seed tuples as sensitivity analysis, but labels them `canonical_panel=false`. Only q=0.10 and exact seeds 1..100 can enter `pressure_certificate()`.

## Limits

The tail is the unconditional seeded no-action town/RNG panel, not a posterior conditioned on exact current shop history. It excludes future rival/player supply and does not price terminal inventory directly. A warning means “low-tail unwind not certified,” not “do not sell”; positive headroom means only that this one pressure objection is absent.

The event rule is source-authenticated, but a real replay still needs separate state/returned-row evidence before anyone may claim the rival event actually occurred or sold the maximum quantity.

The module intentionally stays STRAWBERRY-only because that is where the authenticated Apex counter schedule exists. Other products must not be generalized by analogy without their own source-real event contract.

## Source custody

The composite refuses helper drift from these canonical blobs:

- `market_baseline.py` Git blob `8c62e0161152910ee365596577b59a9cea36eb2c`;
- `demand_velocity.py` Git blob `d66036db64f2c937d59df6cf04a1dca08e2455d0`;
- `counter_ambush.py` Git blob `041b47d3741bdb1f4bd676325fb9949c36ffe51e`.

It captures all three helper byte snapshots before execution, requires COMEBACK's schedule flag/engine identity, and requires DEMANDVEL to share the exact authenticated in-memory market-baseline module.

## Next gate

Feed this certificate into existing market-pressure/economics analysis only as a feature or rejection witness. A current-native gate should use observed public inventory and actual unlocked shops, then bind replay evidence if it wants to upgrade the conditional rival max envelope to a realized event. Do not wire this directly to a SELL action or timing trigger.

Validation from this directory:

```bash
python test_tail_pressure.py
python -O test_tail_pressure.py
python -m py_compile tail_pressure.py test_tail_pressure.py
python tail_pressure.py
```
