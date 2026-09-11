# C1 — intertemporal market-row SELL deferral (strict rescue carrier)

Status: **default-OFF experiment / evidence carrier only**. This directory is outside `overlay/**` and is not read by `build_v3.py`.

## Mechanism

The pinned official interpreter executes each turn in this order:

1. farm/unit actions;
2. player market rows;
3. deterministic town-shop consumption;
4. market-price refresh;
5. plant decay / possible end-of-day refresh.

With the standard `townShopSellInterval=4`, hour 20 is a town-shop demand tick. Live V3.1 already enables R04 `EVENING_FLUSH`, which sells projected shed stock for `WOOL`, `MILK`, `STRAWBERRY`, and `MELON` at hours 21–23. C1 tests one narrow timing factor: if the selected native tape is already selling one of those products at hour 20 and a currently unlocked shop consumes that product at the post-market town tick, leave that native row blank for one callback so the existing hour-21 flush can sell the retained stock after town demand has refreshed the quote.

No town shop consumes MELON in the pinned engine, so MELON is in the flush set but can never satisfy the unlocked-shop demand predicate at hour 20. It is intentionally not granted a special case.

## Why this carrier is stricter than the original development probe

The original fleet development result reported frozen Arlene seeds `2611151001..1008` × both seats as `14 positive / 2 zero / 0 negative`, mean paired ΔM `+53.0`, with cell deltas:

`[95,95,55,55,86,86,34,34,0,0,63,63,55,55,36,36]`.

That result is useful predecessor evidence, **not a score receipt for this exact rescue head**. Before publication the rescue audit found two accounting/capacity boundaries that the prose-level development rule did not prove:

* R04 can synthesize sale rows (E184 sale-window reservations and dynamic layers). Blanking such a row after its parent bookkeeping has advanced can strand or double-account a sale. This carrier therefore requires the complete non-empty current market multiset to equal the selected native tape's SELL-only multiset; any synthesized/quantity-mutated/mixed row fails closed. It also vetoes any item still owned by native/E184 advance debt state.
* `COLLECT_FERTILIZER`, like `HARVEST`, can create carried stock during the hour-20 unit phase. Holding shed stock for the next callback is therefore allowed only when neither operation is currently requested and the observed shed plus all carried inventories already fit within the standard 100-unit shed capacity.

Those guards can only reduce the historical activation set. The `+53.0` development result must be rerun on this exact head before it is used as economics evidence.

## Exact transform contract

A successful transform requires all of the following:

* standard live timing/capacity configuration (`turnsPerDay=24`, `townShopSellInterval=4`, `shedCapacity=100`, `episodeSteps=720`, no market-parameter override);
* exact integer `step` at hour 20 after day 0 and exact player `0`/`1` with two farms;
* known/malformed-free unlocked-shop state and at least one demanded R04 flush item;
* strict nonnegative integer own shed and all worker inventories with `shed + cargo <= 100`;
* no current `HARVEST` or `COLLECT_FERTILIZER` command;
* current market is SELL-only (empty placeholders allowed), and its non-empty row multiset exactly equals the selected native tape market multiset;
* no native/E184 sale debt ownership for the item being deferred.

The transform deep-copies only after proof, then replaces each eligible row with `[]` **at the same market index**. It never compacts/reorders rows, changes a quantity, adds a market order, changes a worker command, or infers hidden rival state. Every rejection returns the exact parent action object.

## Promotion boundary

This is not promotion authority. Required next evidence is:

1. exact-head focused CI and source review;
2. rerun the frozen-8 development panel on the stricter head with activation telemetry;
3. direct exact-V3.1 and opponent-diverse paired cells using Δown / Δrival / ΔM, because withholding supply across a shared market tick can also change the rival's quote path;
4. only then consider composition into the reviewed V3.1 integration spine.

No default, manifest, canonical archive, evaluator/opponent, package, or Kaggle/provider mutation is made here.
