# INTEGRATION-SPEC — `r04_melon_cap`

Source-only, default-OFF repair. Keep the existing key `r04_melon_cap`; do not
mint a sibling controller.

The guard is a **committed-production** cap, not a sold-only cap. Before any new
MELON proposal is admitted it reserves: conservative sold units, MELON already
held in shed/worker inventories, and six units for every live own MELON tile.
Malformed custody fails closed for MELON while non-MELON proposals pass through.

FourthQuadrant proposals are mutually exclusive alternatives: admission returns
one supplied proposal or `None`. For every MELON alternative, require unique
outer `tiles`, exact MELON `seed_units`, and every canonical
`variants[*].bundle.lots[*]` record to bind the same tile set through its exact
`plant_step` and 1-based `worker` back to a `PLANT MELON` action in that route's
`variants[*].patches` program. All route variants must agree. Keep the original
proposal object unchanged only when that whole executable commitment fits the
current reserve. Never shallow-shrink metadata and never consume reserve merely
by inspecting another alternative.

`MELON_LIFETIME_UNIT_CAP = 28` is deliberately conservative and is not claimed
to equal the exact number of full-season town-center consumption ticks.

Hook only when `configuration.get("r04_melon_cap") is True`, at the one canonical
proposal seam. OFF identity, current-native engagement, economics, and graph
composition remain separate gates before activation.
