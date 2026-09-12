# TITAN V4 RNGREACH — authored callback reachability

**Disposition:** research-only current-policy reachability gate; no gameplay/default/activation authority.

This is the missing layer above the canonical `SHOPSTREAM`/`TOWNRNG` mechanism and the canonical `WEEDBANK` reversible occupancy-lease authority. It does not invent a tile action. It consumes the action **already authored by the current TITAN callback** and asks a narrower question:

> immediately before a shop-unlock EOD, did the authored unit phase actually change the number of `None` farm tiles that advance the shared weed/shop RNG cursor?

That distinction matters. Actor/HIRE occupancy does not occupy `farm["tiles"]`, so HIRE/spawn steering is excluded. Only source-real tile transitions can move the SHOPSTREAM vacancy cursor.

## Source boundary

`rng_reachability.py` pins the same official engine authority already used by SHOPSTREAM:

- engine Git blob `3c202c7ee921da239356789e266b694635103fc4`
- engine SHA-256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`

The authored projection mirrors the official interpreter facts relevant to vacancy:

- main farmer executes before existing hands;
- same-crop PLANT demand is preflighted atomically across the authored farmer + hands vector;
- even an extra authored hand row participates in that PLANT preflight before only existing hands execute;
- successful `PLANT`, `BUILD_COOP`, and `BUILD_PASTURE` turn `None` into occupied tile state;
- legal `DIG` turns a non-animal owned tile back into `None`;
- `DIG` cannot remove a placed animal;
- movement, PASS, service rows, and market/HIRE rows do not change tile vacancy in the unit phase;
- a town unlock is relevant only when `(day + 1) % townShopUnlockInterval == 0` and fewer than eight shop instances already exist.

The optional exact-engine bytes input fails closed on source drift. A replay runner that supplies the pinned engine bytes upgrades `source_authenticated` to true; pure unit tests deliberately do not pretend a full checkout was mounted.

## Current-policy gate

`authored_vacancy_projection(...)` simulates only the vacancy consequence of the already-returned callback action, preserving source execution order and atomic PLANT blocking. It returns:

- exact empty-tile count before and after;
- total authored vacancy delta;
- each effectful actor/tile transition;
- blocked same-crop PLANT set;
- `natural_engagement`, which is true only when the authored callback really changes vacancy;
- `invented_action=False`.

`reachability_report(...)` then applies the official shop-unlock boundary. Only when the callback is both unlock-adjacent and naturally vacancy-changing does it run an explicit **offline** SHOPSTREAM sensitivity panel. The panel never becomes live seed knowledge and never emits a preferred shop.

As a regression against the canonical SHOPSTREAM witness, a single authored `-1` vacancy delta on day argument 2 with `[25,25]` baseline empties reproduces exactly:

- seeds 1..512: **337 shop changes**
- **175 unchanged**
- hidden seed live input: **false**
- desired-shop targeting authority: **false**

## Canonical WEEDBANK dependency

RNGREACH does **not** carry a second occupancy-lease implementation. Deliberate reversible BUILD→DIG lease economics, cleanup-policy semantics, and reclamation obligations remain owned by the earlier canonical `research/rng-steering/` WEEDBANK carrier (#13044). Once that carrier lands, RNGREACH should bind to that authority rather than copy or reimplement it.

RNGREACH's independent responsibility is narrower: determine whether current TITAN naturally authored a vacancy-changing callback at the exact shop-unlock boundary. A positive reachability result may be joined with canonical WEEDBANK economics later; it never grants RNG steering authority by itself.

## Authored validation

Fresh local authored bytes:

- `python -B test_rng_reachability.py`: **14/14 PASS**
- `python -O -B test_rng_reachability.py`: **14/14 PASS**
- `py_compile rng_reachability.py test_rng_reachability.py`: **PASS**

The local harness also covers malformed-PLANT fail-closed refusal, atomic PLANT oversubscription, nonexistent-hand PLANT preflight poisoning, same-tile sequential BUILD→DIG net-neutrality, animal-safe DIG refusal, HIRE/movement non-vacancy, unlock cap/schedule, and the canonical SHOPSTREAM 337/175 sensitivity regression.

## Next gate: current-native census

The useful next evidence is replay/native, not another oracle:

1. run the **current single V4** on both seats over a fixed panel;
2. inspect only callbacks immediately preceding shop-unlock EODs;
3. capture public farms/town/day plus own private seeds and the exact TITAN-returned action;
4. feed that action to `reachability_report`;
5. report natural engagement rate, authored delta distribution, affected action families, and SHOPSTREAM offline sensitivity;
6. keep opponent same-turn occupancy unknown unless the completed replay supplies it;
7. do not infer that an authored PLANT/BUILD/DIG was selected *because* of RNG;
8. do not promote a deliberate occupancy steering policy without separate both-seat economics and WEEDBANK/productive-route opportunity-cost evidence.

A zero natural-engagement census falsifies current-policy reachability without touching runtime. A positive census only opens economics; it does not authorize hidden-seed targeting or a standalone RNG controller.
