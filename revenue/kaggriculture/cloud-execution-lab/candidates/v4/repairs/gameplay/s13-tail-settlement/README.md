# S13 tail settlement: recovered source and boundary repair

Canonical home: `main:revenue/kaggriculture/cloud-execution-lab/candidates/v4/repairs/gameplay/s13-tail-settlement/`.

## Recovery

Claude's final September 10, 2026 shop-clock correction was recovered from Slack file `F0C0ME68M0X`, attached at https://tokenjunkielabs.slack.com/archives/C0BRB1M9RL6/p1789090590817619. It is exactly 20,360 bytes, SHA256 `ead794d663a01967723932613fef800a0345b67daabefcf6799c812c933a6a54`, Git blob `6a08f2febbe1c5012482ccc5ee1ed2b787ae75f4`. The same Git object was already server-readable when checked; it is reused, not recreated. `legacy/tail_settlement.py` preserves those bytes without editing their historical claims.

Yusuf's earlier S13 integration claim at https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789090067373799 referenced older `d535558e...` bytes. Exact-name Slack/code/PR searches found no later completion or current canonical consumer. This package consumes the later `ead794d...` source, not the older snapshot. Recovery/build claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789178568722269.

## What the adapter repairs

`s13_tail_settlement.compose_tail_settlement` is a default-OFF boundary around the byte-pinned donor; it does not fork the donor's raw/net-new/reserve quantity algorithms.

1. A string such as `shop_consumed="MILK"` can no longer become a character set and falsely certify no MILK shop demand. Only explicit collections of known product strings are accepted. `None` remains conservative.
2. Both consumption periods come from `townShopSellInterval` and `townCenterSellInterval`. Explicit old-style arguments must agree with configuration. For shop-consumed/unknown products, the later final shop OR center pulse governs admission.
3. Invalid configuration, calendar, flags, reserve evidence, or projection fails closed. Disabled and unchanged calls return the exact parent action object. OFF calls do not inspect opaque inputs or load the donor.
4. Only the raw executable market prefix must be sale-only. Inert suffix rows, including HIRE/malformed/overfunded rows, cannot veto a funded prefix or manufacture a receipt. Their positions and bytes are preserved; reachable invalid/mixed rows still reject.

Configuration names, product domain, and two-clock order were read from pinned `reference/engine/kaggriculture.py` blob `3c202c7ee921da239356789e266b694635103fc4`, especially `_town_consume` and `interpreter`. The checked-in ENGINE-SEMANTICS.md separately records market-before-consumption timing.

## Executed validation

From this directory:

```sh
python -B test_s13_tail_settlement.py
python -O -B test_s13_tail_settlement.py
```

Python 3.13.5: **30/30 normal and 30/30 optimized**. Includes 15,552 independently enumerated clock cases, 800 funded-prefix quantity cases, 216 valid standard-domain comparisons with the exact original donor, and five executed predecessor discriminators (string evidence, later center pulse, configuration drift, malformed config, inert suffix veto). Syntax compilation also passed. These are isolated callback/clock/quantity checks using a documented contract projector; they are NOT full-engine transitions, generated-package acceptance, hosted games, or economic measurements. The historical reported 25-case suite was not supplied and is not counted as rerun here.

## Integration boundary

No production/runtime, key/config/default, archive, workflow, opponent, or Kaggle submission changed. The function requires explicit `enabled=True` AND a caller-supplied exact selected-unit projector. Current-runtime projector binding remains a separate integration gate; do not invoke an old R04 materializer to obtain it. This preterminal helper is distinct from the T01 final-step adapter being ported by ASTRA-ENDPORT.

When supplied, `shop_consumed` is still a caller certificate covering all shop products through the remaining horizon; an incomplete but well-typed set is not magically verified. Leave it `None` without that proof. Future operational reserves likewise need an actual provider; missing per-product reserves hold that product only with `require_certified_reserve=True`. No monotone whole-game cash claim follows from `execution_certified`, even after the final town pulse: future input demand and rival behavior still matter. The raw `consumption_safe=False` arm is deliberately retained only for controlled comparison.

The single V4 assembler should consume this package, bind the current projector once, then compare OFF/raw/net-new/reserve arms on matched seed/opponent/seat cells, reporting activations, own/rival scores, margin changes and new-loss/lost-win cells. Do not enable or call this a win based on the source tests.
