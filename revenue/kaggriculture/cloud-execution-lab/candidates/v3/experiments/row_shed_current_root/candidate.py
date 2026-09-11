# SPDX-License-Identifier: Apache-2.0
"""Executable S33 row-shed wrapper for the shipped 8e3 V3.1 feature tuple.

This is an evidence carrier, not a package/default mutation.  It calls the current R04
module in-process with native ROW_ORDER and EVENING_FLUSH temporarily delegated to this
wrapper so row-shed can occupy the exact ordering seam without copying the router.
"""

from row_shed import apply_row_shed


CURRENT_8E3 = dict(
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
    kill_late_water=False,
    strawberry_endgame=False,
    strawberry_max_plants=8,
    no_late_sale_advance=True,
    no_late_sale_advance_step=648,
    strawberry_topup=True,
    b5_carrot_fertilizer=True,
    b5_jit_fertilize=True,
)


def install(r04, *, row_shed=True, **overrides):
    """Return a current-root candidate callable.

    ``overrides`` exists for controlled one-key interaction experiments (notably cattle
    ON/OFF).  Unknown keys are rejected.  With ``row_shed=False`` this delegates exactly to
    the native current-root install tuple.
    """
    settings = dict(CURRENT_8E3)
    unknown = set(overrides) - set(settings)
    if unknown:
        raise TypeError("unknown R04 settings: " + ", ".join(sorted(unknown)))
    settings.update(overrides)

    if not row_shed or not settings["row_order"]:
        return r04.install(
            None, settings["horizon"], settings["opening"], settings["row_order"],
            settings["evening_flush"], settings["sale_fertilizer"], settings["cattle_early"],
            settings["kill_late_water"], settings["strawberry_endgame"],
            settings["strawberry_max_plants"], settings["no_late_sale_advance"],
            settings["no_late_sale_advance_step"], settings["strawberry_topup"],
            settings["b5_carrot_fertilizer"], settings["b5_jit_fertilize"],
        )

    # Native R04 sequence is H4 -> L1 -> L2 -> ROW_ORDER -> EVENING_FLUSH -> opening -> B5.
    # We disable only the two market-order stages and replay them outside.  Opening is a
    # step-0 BUY-leading block, so ROW_ORDER is inert there.  B5 changes PASS to FERTILIZE;
    # projected_shed() models only PICKUP/DROP/PLACE, so moving row-shed after B5 does not
    # change its private-stock projection.  EVENING_FLUSH is then replayed after row-shed,
    # preserving its native relative order.
    base = r04.install(
        None, settings["horizon"], settings["opening"], False, False,
        settings["sale_fertilizer"], settings["cattle_early"], settings["kill_late_water"],
        settings["strawberry_endgame"], settings["strawberry_max_plants"],
        settings["no_late_sale_advance"], settings["no_late_sale_advance_step"],
        settings["strawberry_topup"], settings["b5_carrot_fertilizer"],
        settings["b5_jit_fertilize"],
    )

    def candidate(observation, configuration=None):
        action = base(observation, configuration)
        action = apply_row_shed(observation, action, r04, configuration)
        if settings["evening_flush"]:
            action = r04.evening_flush(observation, action)
        return action

    candidate.row_shed_settings = dict(settings)
    candidate.row_shed_enabled = True
    return candidate
