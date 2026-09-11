# C1 — intertemporal STRAWBERRY SELL deferral (provenance-repaired carrier)

Status: **default-OFF frozen experiment / evidence carrier only**. This directory is outside `overlay/**` and is not read by `build_v3.py`. The source lineage remains the frozen pre-ship V3.1 base; since canonical V3.1 advanced to `a6120d0e...`, any score-facing use must be explicitly rebound and re-evaluated on current canonical bytes.

## Mechanism

The pinned official interpreter executes each turn in this order:

1. farm/unit actions;
2. player market rows;
3. deterministic town-shop consumption;
4. market-price refresh;
5. plant decay / possible end-of-day refresh.

With the standard `townShopSellInterval=4`, hour 20 is a town-shop demand tick. Frozen V3.1 already enables R04 `EVENING_FLUSH`, which sells projected shed stock for `WOOL`, `MILK`, `STRAWBERRY`, and `MELON` at hours 21–23. C1 now tests one deliberately narrow timing factor: when the selected native tape is already selling **STRAWBERRY** at hour 20 and a currently unlocked shop consumes STRAWBERRY at that post-market town tick, leave the proven-native row blank for one callback so the incumbent hour-21 flush can sell retained stock after town demand refreshes the quote.

## Why the repaired theorem is STRAWBERRY-only

Exact-head review of the earlier rescue carrier found that final SELL-multiset equality is not a provenance proof. Frozen R04 contains same-item incumbent accounting that can cancel a native row and replace the same quantity before C1 sees the final parent action:

- V231 can add physically harvested `MILK` credit into an existing MILK sale row;
- V233 can append credited `WOOL` sales;
- E184 can subtract a current-due sale debt and can synthesize a current sale from future authored rows.

Therefore a final WOOL or MILK multiset can look exactly native after dynamic accounting has already spent credit. C1 no longer claims either item. Neither V231 nor V233 synthesizes STRAWBERRY, so STRAWBERRY can be proven with an additional E184/native-sale snapshot.

The agent now snapshots strict sale-accounting state **before** the parent callback and requires all of the following for STRAWBERRY:

- post-288 E184 regime only (`step >= ADVANCE_START`), avoiding the legacy pre-288 one-turn reservation path;
- no pre-parent legacy/native `advanced_sales[STRAWBERRY]` ownership;
- no pre-parent `sale_window_debts[step][STRAWBERRY]` current-due cancellation;
- the exact future STRAWBERRY debt tuple is unchanged across the parent callback, proving E184 did not synthesize a future-tape STRAWBERRY sale now;
- post-parent target accounting remains empty/currently unowned;
- after those accounting proofs, the non-empty current SELL multiset still exactly equals the selected native tape SELL multiset.

The full pre/post accounting containers are schema-validated before use, including unrelated entries, so poison that the parent would pop/prune cannot disappear before C1 evaluates it.

## Additional fail-closed repairs

Exact review also found that `None`, `{}`, or partial configuration silently inherited theorem-critical defaults, and that shed-capacity accounting did not bind inventory-cardinality to represented actors. The repaired carrier therefore requires explicit standard values for:

- `turnsPerDay=24`;
- `townShopSellInterval=4`;
- `shedCapacity=100`;
- `episodeSteps=720`;
- `maxMarketOrdersPerTurn=10`;
- explicit empty `marketParams={}`.

Missing/partial/coerced fields fail to exact parent identity. The number of private inventory maps must also equal `1 + len(action.hands)` (farmer plus every hand) before shed-plus-cargo capacity is computed. Missing actor inventory can no longer undercount retained stock.

`HARVEST` and `COLLECT_FERTILIZER` remain vetoed because they can create carried stock during the same unit phase. Strict own shed plus all represented carried inventories must already fit within the standard 100-unit capacity. PICKUP/DROP-style movement remains allowed because it does not create total stock.

## Exact transform contract

A successful transform requires all of the following:

- complete explicit standard configuration above;
- exact integer post-288 hour-20 step and exact player `0`/`1` with two farms;
- known/malformed-free unlocked-shop state with at least one shop that consumes STRAWBERRY;
- strict pre/post sale-accounting provenance proof for STRAWBERRY;
- strict nonnegative own shed and exactly one inventory map per represented actor, with `shed + cargo <= 100`;
- no current `HARVEST` or `COLLECT_FERTILIZER` command;
- current market is SELL-only (empty placeholders allowed), and its non-empty row multiset exactly equals the selected native tape market multiset;
- at least one current STRAWBERRY SELL row.

The transform deep-copies only after proof, then replaces each proven STRAWBERRY row with `[]` **at the same raw market index**. It never compacts/reorders rows, changes a quantity, adds a market order, changes a worker command, or infers hidden rival state. Every rejection returns the exact parent action object.

## Evidence boundary

The original fleet development result reported frozen Arlene seeds `2611151001..1008` × both seats as `14 positive / 2 zero / 0 negative`, mean paired `DeltaM +53.0`, with cells:

`[95,95,55,55,86,86,34,34,0,0,63,63,55,55,36,36]`.

That is **predecessor evidence only**. The provenance repair intentionally removes WOOL/MILK activations and strengthens config/cardinality guards, so activation and economics may shrink or vanish. Required next evidence is:

1. exact-head focused CI and independent source/custody rereview;
2. rerun the frozen development panel with activation telemetry showing proven STRAWBERRY deferral -> later incumbent flush realization;
3. direct current-stack / opponent-diverse paired `DeltaOwn / DeltaRival / DeltaM`, because withholding supply across a shared market tick can change the rival quote path;
4. only after that, a direct rebase onto canonical `a6120d0e...` or later with deterministic package/off-identity custody.

No default, manifest, canonical archive, evaluator/opponent, package, or Kaggle/provider mutation is made here.
