# DEMANDVEL × COMEBACK — residual public-supply tail pressure

This is a research-only composition of two canonical Gemini descendants in the existing V4 market-baseline authority. It does not sell, retime, choose a product, add a runtime key, or authorize an action.

## The missing question

Authenticated COMEBACK answers a local question: if Apex is going to sell at `t`, does our `t-1` sale improve immediate gross relative margin versus waiting until `t+1`?

DEMANDVEL answers a different question: how much public supply can source-exact NPC demand absorb over an episode, including the seeded weed/shop RNG stream?

Neither one alone asks whether the public inventory created by a locally attractive counter-ambush is small enough for the **remaining** low-tail NPC demand after that event. `tail_pressure.py` closes that gap without becoming a decision rule.

For the authenticated STRAWBERRY counter event it:

1. runs the existing COMEBACK `predump_counterfactual` at `t/t+1`;
2. compares its post-`t+1` public inventory with the same starting inventory under no player/rival sale event, so `$1` sales that do not add public inventory contribute zero supply;
3. runs the source-exact no-action town baseline over seeds 1..100;
4. measures only NPC absorption **after** the already-modeled `t+1` callback; and
5. compares residual event supply with the floor of the p10 remaining-absorption tail.

The output is a pressure certificate only. `decision_authority=false`, `timing_authority=false`, `opponent_future_supply_accounted=false` are hard scope fields.

## Authenticated examples

With the current pinned sources:

- Apex 380/381 STRAWBERRY event, eight source-real units from us and eight from Apex, with eight strawberry-consuming shop instances at step 380: the combined event leaves 16 public units relative to the no-event path. The p10 remaining NPC absorption after step 381 is 132.8 units (floor budget 132). Immediate relative-margin swing is positive and low-tail headroom remains.
- Apex 402/403 with the same 8+8 units and no immediate shop drain: residual event supply is again 16. The p10 remaining absorption after step 403 has fallen to 127.3 (floor 127). The event still fits, but the later event has less unwind capacity.
- Synthetic control at the 402/403 timing, starting inventory 9,700 with our 128 units plus Apex's 8: COMEBACK still reports a positive immediate relative-margin swing, but 136 residual public units exceed the p10 remaining budget of 127. The composite therefore emits `POSITIVE_IMMEDIATE_COUNTER_TAIL_UNWIND_NOT_CERTIFIED`.
- At a saturated `$1` STRAWBERRY state, sales that do not move public inventory produce zero residual supply rather than an invented pressure penalty.

The third case is the useful new invariant: **positive immediate counter economics are not enough to certify public-inventory unwind**.

## Limits

The tail is the unconditional seeded no-action town/RNG panel, not a posterior conditioned on the exact current shop history. It also excludes future rival/player supply and does not price terminal inventory directly. A warning therefore means “low-tail unwind not certified,” not “do not sell,” while positive headroom means only that this one pressure objection is absent.

The module intentionally stays STRAWBERRY-only because that is where the authenticated Apex `t-1/t` counter witness currently exists. Other products should not be generalized by analogy without a source-real rival event contract.

## Source custody

The composite refuses helper drift from the current canonical blobs:

- `market_baseline.py` Git blob `8c62e0161152910ee365596577b59a9cea36eb2c`;
- `demand_velocity.py` Git blob `d66036db64f2c937d59df6cf04a1dca08e2455d0`;
- `counter_ambush.py` Git blob `041b47d3741bdb1f4bd676325fb9949c36ffe51e`.

It also requires COMEBACK's Apex schedule authentication and DEMANDVEL's shared canonical market-baseline module identity.

## Next gate

Feed this certificate into the existing market-pressure/economics analysis only as a feature or rejection witness. A current-native gate should use observed public inventory and actual unlocked shops, then test whether adding the tail-pressure feature improves terminal margin without suppressing profitable natural sales. Do not wire it directly to a SELL action or a timing trigger.

Validation from this directory:

```bash
python test_tail_pressure.py
python -O test_tail_pressure.py
python -m py_compile tail_pressure.py test_tail_pressure.py
python tail_pressure.py
```
