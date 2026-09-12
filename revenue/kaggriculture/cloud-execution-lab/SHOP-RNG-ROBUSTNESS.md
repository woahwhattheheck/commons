# Shop unlock RNG robustness research carrier

Status: **research-only / default OFF / not wired into TITAN runtime**.

## Pinned engine theorem

The repository-pinned Kaggriculture engine has a compact deterministic end-of-day RNG path:

1. Construct `random.Random((seed * 1_000_003) ^ day)` once.
2. Refresh plants and animals for player 0, then call `_spawn_weeds`.
3. `_spawn_weeds` calls `rng.random()` exactly once for every tile whose value is `None` at that point.
4. Repeat the same refresh + weed pass for player 1 using the **same RNG instance**.
5. After both farms finish, let `next_day = day + 1`. If `next_day % townShopUnlockInterval == 0` and fewer than 8 shop instances are unlocked, append `rng.choice(sorted(SHOPS))`.

There is no RNG consumer between the two weed passes and the shop choice. Weed outcomes do not change how many RNG calls the same pass makes: each tile is visited once, and only the original `None` test controls whether `random()` is called. Therefore the shop cursor is determined by the engine seed/day and the **sum of the two post-refresh empty-tile counts**.

This does not mean a player can freely force a shop. Both farms contribute to the cursor. A rival final-tick PLANT, BUILD, DIG, annual HARVEST, or other legal board change can alter the number of `None` tiles that reach the weed pass.

## Analyzer contract

`shop_rng_robustness.py` reproduces only the pinned cursor mechanics. The caller supplies:

- current own and rival empty-tile counts;
- a set of own empty-count deltas that the caller has already proven legal;
- an explicit bounded set of rival empty-count deltas that the caller wants covered; and
- one target shop.

For every own candidate, the helper replays every supplied rival delta. It reports a candidate robust only if **every** replay lands on the exact target shop. Invalid deltas are rejected rather than silently removed, because dropping an inconvenient rival state would strengthen the certificate incorrectly.

The report names the bound explicitly: `robust_within_supplied_rival_bound`. It is not a probability estimate and it is not a claim about rival states omitted by the caller.

## Non-goals

This carrier does not:

- infer which own empty-count deltas are strategically or physically legal;
- predict a distribution for rival actions;
- use live leaderboard/shop payout observations as engine truth;
- alter town procurement, sell queues, routes, or finalizers;
- activate an `r04_shop_first` policy; or
- change `TITAN-CONFIG.json`, release archives, or Kaggle source.

Those are separate research/composition decisions. In particular, the SHOP-FARMER loss autopsy is motivation for studying the mechanism, not evidence used by this helper.

## Tests

`test_shop_rng_robustness.py` compares the analyzer against a literal independent replay of Python's pinned `Random` sequence, checks the `next_day` unlock boundary and 8-instance cap, verifies every supplied rival delta is evaluated, demonstrates that broadening the rival bound can destroy a narrow certificate, and fails closed on impossible board-count bounds.
