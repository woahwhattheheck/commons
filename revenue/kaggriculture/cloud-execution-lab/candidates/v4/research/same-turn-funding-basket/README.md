# Same-turn funding basket — completed research, PARKED

This is one source-bound adapter for the existing native FrozenSelected funding call, in the sole canonical main V4 workspace. It is not a second controller, a successor V4, or an enabled production feature. `bind(native)` returns the identical native function by default. No runtime source, key, default, archive, workflow, or Kaggle submission was changed.

## Finding and implemented response

The current native `fund_same_turn_acquisition` considers one later SELL source at a time. A fixed buy can therefore fail even when two already-authored sale lots jointly finance it. Standard-price witness: cash 0, post-unit shed EGG 1 / CARROT 1, market `[[], [], ["BUY_SEED","MELON",1], ["SELL","EGG",1], ["SELL","CARROT",1]]`. The native method returns `no-safe-prefix-sale`. Moving the two sales to the two existing empty positions buys one MELON seed and leaves 5 cash; the parent buys none and leaves 85. This is acquisition feasibility, NOT an 80-cash gain or a terminal-value improvement.

The experimental fallback retains successful existing single-source results and their rank. It groups later lots by product, searches moved-unit layers under a deterministic slot-placement convention, reuses only earlier empty/same-product SELL slots, and debits original source rows. Default budget is 256 allocation vectors; an unfinished layer returns the unchanged input, never an uncertified best-so-far. Completed layers minimize moved units within this convention, then maximize modeled post-target cash. It does not enumerate every market permutation.

The fallback checks physical post-unit shed stock, raw market cap before parsing, unchanged suffix positions, exact sale totals, a frozen public rival estimate, the full fixed-buy requirement, and preservation of every baseline acquisition fill including downstream partial fills. It will not perform basket completion across an active BUY_PRODUCT anywhere in the queue. Existing operating-product policy and single-source rank proposal #12062 are not rewritten. Source drift is an error at binding, not a silent port. The supported research domain is bounded to 16 live rows and 256 units; these are NOT new game rules.

## Executed evidence

The source-bound suite passes **26/26 normally and 26/26 with `python -O`**. Each mode includes 353 real official `_process_market` calls and 233 interpreter calls, of which 219 initialize worlds and 14 execute full callbacks. The latter include both-seat native selected-transform composition and actual DROP -> market -> end-of-day/terminal-step controls. The independent small-grid oracle executes 276 official-market allocations across 37 native no-safe-prefix cases. All four fixed-acquisition types are exercised, including conservative rejection when stressed proceeds are insufficient.

Nine behavioral mutants are rejected in BOTH modes after unmodified green controls: downstream-fill theft, unavailable stock, ignored budget, disabled source pin, live suffix admission, undebited sales, default ON, maximum movement, and single-source-only search. Mutation bootstrap/parse failure is not accepted as evidence.

## Natural engagement result: do not enable

Two complete instrumented current-package trajectories, seed 17, official starter opponent, both seats: 719 callbacks each; all 1,438 runtime callbacks completed without deadline fallback. Across 1,436 native funding calls, 1,292 had no failing target and 144 stopped at BUY_PRODUCT; **zero `no-safe-prefix-sale` cases and zero basket opportunities**. Both runs returned the ORIGINAL funding output. The runner records its own hash and all counters. Its instrumentation can affect wall-clock budgets, and this is only one seed/opponent family, not a matched economic comparison.

Decision: preserve this reusable implementation and evidence, but PARK it. No open builder request and no automatic runtime integration. Reopening requires an observed competitive-opponent funding gap, fresh current-source/finalizer composition, and matched economic evidence. Feasibility alone can justify buying an asset too late to earn back its cost; the direct-helper terminal-step control intentionally does not pretend otherwise. The actual native terminal-settlement branch bypasses this funding seam.

## Reproduce offline

Use the already-existing GitHub artifact **10175943272**, run **34537404363**. Verify the ZIP SHA256 `3a3b74936d238bf884f89a1b279f42676cda35c590f131a6a3548de52d61b4e8`, then extract its `checked-package/exports/titan-current.tar.gz`. That tar must hash to `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`. Set `PACKAGE` to the unpacked tar directory. The test runner authenticates SOURCE.json and all 109 runtime-map files before importing native code or the official engine. No network fetch is needed or triggered for an authenticated package.

```sh
python test_funding_basket.py --package "$PACKAGE"
python -O test_funding_basket.py --package "$PACKAGE"
python check_mutations.py --package "$PACKAGE" --output mutations.json
python census_funding_basket.py --package "$PACKAGE" --seed 17 --seat 0 --output census-seat0.json
python census_funding_basket.py --package "$PACKAGE" --seed 17 --seat 1 --output census-seat1.json
```

For an isolated composition experiment only, `fs.fund_same_turn_acquisition = funding_basket.bind(fs, enabled=True)` binds the existing native module. The caller must supply its real post-unit state, and the original function must be restored afterward. No production config flag was added.

Exact source identities, execution totals, mutation outcomes, and both census results are in VALIDATION.json. Custody starts at main commit `116110c06219bcd0f178c0a7ea211e0ee2f0e1f4`; delivery uses only a temporary evidence-transport PR back to main after a non-forced concurrent-write conflict. Claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789180526995049
