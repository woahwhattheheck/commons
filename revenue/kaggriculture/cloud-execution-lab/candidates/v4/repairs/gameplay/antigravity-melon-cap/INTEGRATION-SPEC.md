# INTEGRATION-SPEC — `r04_melon_cap`

Source-only, default-OFF repair. Keep the existing key `r04_melon_cap`; do not
mint a sibling controller.

The guard is a **committed-production** cap, not a sold-only cap. Before any new
MELON proposal is admitted it reserves conservative sold units, MELON already
held in shed/worker inventories, and six units for every live own MELON tile.
Malformed custody fails closed for MELON while non-MELON proposals pass through.

FourthQuadrant proposals are mutually exclusive alternatives: `admit()` returns
one supplied proposal or `None`. Therefore every MELON alternative is checked
independently against the same current reserve; scanning an option must never
spend another option's budget.

Admission authority is the executable producer contract, not shallow metadata.
Every route variant must authenticate exactly one MELON lot per unique outer
selected tile, with each lot's `(tile, plant_step, 1-based worker)` resolving to
`['PLANT','MELON']` in that variant's `patches`. A fitting proposal is preserved
whole and by identity. Oversized, malformed, metadata-only, patch-mismatched, or
route-inconsistent MELON proposals are dropped; they are never partially shrunk.

`MELON_LIFETIME_UNIT_CAP = 28` remains deliberately conservative and is not
claimed to equal exact full-season town-center consumption. The cap itself still
requires current-native engagement and economics before promotion.

Hook only when `configuration.get("r04_melon_cap") is True`, at the one canonical
FourthQuadrant proposal seam. No runtime/default/config/COMPOSITION/archive/Kaggle
activation is implied by this source package.
