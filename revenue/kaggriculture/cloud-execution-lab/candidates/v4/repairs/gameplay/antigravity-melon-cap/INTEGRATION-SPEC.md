# INTEGRATION-SPEC — `r04_melon_cap`

Source-only, default-OFF repair. Keep the existing key `r04_melon_cap`; do not
mint a sibling controller.

The guard is a **committed-production** cap, not a sold-only cap. Before any new
MELON proposal is admitted it reserves: conservative sold units, MELON already
held in shed/worker inventories, and six units for every live own MELON tile.
Malformed custody fails closed for MELON while non-MELON proposals pass through.
The aggregate budget is consumed across the whole proposal batch.

`MELON_LIFETIME_UNIT_CAP = 28` is historical fallback evidence only. The stronger
`liquidation_bound.py` successor must consume a caller-certified remaining
realization budget instead of assuming a fixed lifetime ceiling.

## Current-route realization producer

`route_realization_certificate.py` provides the first conservative producer for
that stronger seam. It captures the current frozen Arlene source bytes exactly
once, authenticates Git blob `bdb9cf58148a3c7961c085f4902759537decabf6`,
and compiles/executes those same captured bytes in memory. It never verifies one
pathname read and then reopens mutable authority bytes for execution. The decoded
720-step route bank and source-declared route-switch decision turns therefore
share one immutable authenticated source snapshot.

It credits only literal positive `SELL MELON` quantities that:

1. occur on the caller-authenticated current route;
2. are at or after both the current step and a caller-proved `not_before_step`
   when the new MELON production can actually be present in shed custody;
3. lie inside Arlene's executable first 10 market rows for that callback; and
4. occur strictly before the next unresolved Arlene `DECISIONS` turn.

The fourth rule matters because Arlene evaluates a route switch before selecting
the action at the decision callback. Prefix compatibility proves only the past;
it does not make a later tail's SELL rows unconditional. A certificate produced
at step 225 therefore cannot spend capacity from decision step 226 or later. A
caller that reaches step 226 must first bind the post-decision route id and build
a fresh certificate, whose next horizon is the following authenticated decision.
After the last decision, the horizon is the route end.

The producer deliberately does **not** credit Arlene's dynamic dead-stock seller,
terminal settlement, town consumption, or inferred future stock. Those paths can
increase real outlet capacity, but each needs additional shed/product/chronology
custody proof before it is safe to spend as a production budget. Omitting them can
only under-credit the #13032 realization bound.

Malformed source, source drift, source execution failure, unknown route id,
malformed/duplicated decision turn evidence, malformed executable market rows,
poisoned step/cap evidence, or poisoned MELON quantities returns no certificate.
A zero-unit certificate is valid and distinct from missing proof. The packet
serializes both `credited_before_step_exclusive` and all later authenticated
decision turns so a consumer cannot mistake a bounded route segment for a
terminal-route proof.

The packet field `certified_remaining_realization_units` can be passed directly
to `liquidation_bound.py`; the producer itself has no decision authority.

The caller still owns two critical proofs: exact current route id and the earliest
step at which newly committed MELON can reach shed custody. `not_before_step`
must mean the new production is available to the credited seller from that point;
this module does not infer growth, WATER, HARVEST, movement, DROP, or maturity
timing, and it does not prove that a proposed production plan will realize the
credited outlet slots.

Focused source tests include a deterministic path-swap-after-capture predecessor:
the source file is overwritten with throwing bytes immediately after the one
captured read, yet route decoding must still execute only the authenticated
captured snapshot. This protects the producer from verify→reopen divergence.

Hook only when `configuration.get("r04_melon_cap") is True`, at the one canonical
proposal seam. OFF identity, current-native engagement, economics, route-id and
maturity custody, and graph composition remain separate gates before activation.
