# INTEGRATION-SPEC — `r04_melon_cap`

Source-only, default-OFF repair. Keep the existing key `r04_melon_cap`; do not
mint a sibling controller.

The guard is a **committed-production** cap, not a sold-only cap. Before any new
MELON proposal is admitted it reserves: conservative sold units, MELON already
held in shed/worker inventories, and six units for every live own MELON tile.
Malformed custody fails closed for MELON while non-MELON proposals pass through.
The aggregate budget is consumed across the whole proposal batch.

`MELON_LIFETIME_UNIT_CAP = 28` is deliberately conservative and is not claimed
to equal the exact number of full-season town-center consumption ticks.

Hook only when `configuration.get("r04_melon_cap") is True`, at the one canonical
proposal seam. OFF identity, current-native engagement, economics, and graph
composition remain separate gates before activation.
