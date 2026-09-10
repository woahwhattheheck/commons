# TITAN V3 — rival crop-decay decontamination

**Operation:** `titan-v3-rival-decay-decontamination-20260910-01`  
**Fresh source:** `main@2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb`  
**Status:** default-off executable candidate; canonical runtime/config/archive unchanged.

## Defect

The configured `FrozenSelected` consumer inherits `SellScheduler.observe()`. That
observer records every public rival `yield_units` decline as a recently harvested
lot. The pinned official interpreter also performs a deterministic crop transition:
for a surviving plant at or beyond `max_lifespan_step`, every even parity step
subtracts exactly one unit. The incumbent therefore manufactures rival supply from
crop age alone and retains it for eight observations.

A source-bound official-engine witness drives MELON `4 → 3 → 2 → 1` across decay
steps 100, 102 and 104. Current TITAN records three harvested units and reports
rival stress 3 despite only one visible unit. This candidate records no hidden lot
and reports visible stress 1.

That difference reaches an executed economic decision. For the retained concrete
MELON state (`inventory=80`, `quantity=2`, `now=100`, dates 100/104/108), stress 3
keeps the reference `SELL 2` at step 100 with zero worst-case gain. Correct stress 1
selects carry to step 108 with worst-case relative gain greater than 100.

## Repair boundary

`decay_observer.is_exact_age_decay()` subtracts one only when all of these public
conditions hold:

- observations are contiguous;
- both tiles are surviving plants at the same coordinate;
- crop, planted day and lifespan step are unchanged;
- yield changes exactly `a → a-1` with `a > 1`;
- the transition is at/after lifespan on exact official even parity.

Everything ambiguous remains byte-for-byte incumbent semantics: skipped
observations, plant disappearance or WEED conversion, animals, replacements,
larger drops, wrong parity, pre-lifespan changes and malformed values.

## Executable custody

`candidate.py` verifies Git object identities for canonical `main.py`,
`scheduler.py`, `frozen_selected.py`, `titan_runtime.py`, and the vendored official
engine. It then asserts that configured `FrozenSelected` still inherits the exact
observer seam, installs a process-local subclass, and loads canonical `main.py`
unchanged. `TitanAgent._initialize()` and its timeout/fallback replay both resolve
that subclass through the existing `frozen_selected.FrozenSelected` import.

The committed canonical package is not imported from this directory and no
feature flag is enabled. All-off behavior is canonical byte identity.

## Gates

The workflow runs:

1. helper-domain and 400-case incumbent-parity contracts;
2. exact official interpreter transition witness;
3. concrete optimizer decision flip;
4. source-drift refusal and canonical executable-consumer installation;
5. clean-tree and compile checks;
6. retained `WITNESS.json`, hashes and test transcript.

Advancement requires a fresh paired current-control opponent panel with returned-
action custody, nonzero activation, positive mean own cash, nonnegative median,
zero negative own-cash cells and no negative opponent×seat mean. This carrier does
not enable production policy or authorize a Kaggle upload.
