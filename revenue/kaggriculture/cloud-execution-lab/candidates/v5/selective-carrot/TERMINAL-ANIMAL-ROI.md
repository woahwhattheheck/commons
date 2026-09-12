# TITAN V5 terminal animal ROI arm

This is an additive experiment over the exact `production-v3` V5 archive, not a
sibling policy tree and not a CURRENT/default/release mutation.

## Source custody

- parent archive SHA256: `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`
- exact parent `main.py` SHA256: `381b50f858212727a9d95d11ae8ff5ba4ab830b35e1d5cd6d1e6a1d375d2e83`
- exact submitted V3.1 R04 source remains inside that parent unchanged.
- the enabled treatment changes only `main.py` and adds `terminal_animal_roi.py`.
- the disabled materialization must reproduce the parent archive byte-for-byte.

The filter is deliberately post-policy: route choice, worker positions, shop
ordering, crop admission, seller/fertilizer logic, delivery choice and the R04
router all run first. It only removes well-formed `BUY_ANIMAL` rows from the
returned market action at or after a selected suffix boundary. Uncertain action
or observation shapes are identity.

## Experimental ladder

Start with `--min-step 718 --enable`. This is the final executable callback and
therefore the narrowest causal probe. The builder exposes only four predeclared
suffix arms (`718`, `696`, `672`, `648`) so any widening is explicit and bounded.
Do not promote an earlier boundary merely because it engages more often.

Eligibility for any active composition requires, in order:

1. guard-off archive identity proof;
2. natural `BUY_ANIMAL` engagement count against exact production-v3;
3. source/action diff showing no non-animal market row or unit action changed;
4. paired native own-score and margin against both Apex and Arlene;
5. hold if engagement is zero, own score regresses, or the result conflicts with
   the current production-v3 source-custody receipt.

No seed IDs, future towns, opponent internals or RNG state are inputs to the
filter. `CURRENT`, default, release and Kaggle submission paths remain untouched.
