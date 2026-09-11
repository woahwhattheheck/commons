# SPDX-License-Identifier: Apache-2.0
"""Evaluation-only composition hook for Riot L3 + ASTRA H4.

This file is outside overlay/** and is not part of the deterministic V3 package.  It
exists only to give the official evaluator one unambiguous way to arm both already-
gated mechanisms without changing defaults or integration ownership.
"""

from __future__ import annotations

import r04_full_router as base
import r04_h4_strawberry as h4


def install_joint(host=None, horizon=None, opening=None, row_order=None,
                  evening_flush=None, sale_fertilizer=None, cattle_early=None,
                  no_late_sale_advance_step=648):
    """Return H4's agent with Riot L3 explicitly enabled.

    L1/L2 remain at their parent defaults.  H4's own reconcile function detects the
    L3 globals and becomes exact identity/no-debt at and after the configured cutoff.
    """
    candidate = h4.install(host, horizon, opening, row_order, evening_flush,
                           sale_fertilizer, cattle_early, strawberry_topup=True)
    base.install(no_late_sale_advance=True,
                 no_late_sale_advance_step=no_late_sale_advance_step)
    return candidate


# Standard evaluator entrypoint. Importing this module arms exactly H4 + L3 and
# exposes the same module-level callable contract as a normal Kaggriculture agent.
# This avoids an untracked ad-hoc wrapper in the benchmark harness.
agent = install_joint()
