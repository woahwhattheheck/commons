# SPDX-License-Identifier: Apache-2.0
"""Evaluation-only composition hook for Riot L3 + ASTRA H4.

This file is outside overlay/** and is not part of the deterministic V3 package. It
exists only to give a practice/bench evaluator one unambiguous way to arm both already-
gated mechanisms while preserving the live V3.1 R04 baseline. It is not a 1:1 official
gate candidate under the fleet fidelity standard because experiments/** is not built by
build_v3.py.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as base  # noqa: E402
import r04_h4_strawberry as h4  # noqa: E402


# Exact live V3.1 R04 baseline. These are intentionally pinned here instead of
# inheriting r04_full_router.py's published/source defaults, which differ for four
# knobs (row order, evening flush, fertilizer advancement, early cattle).
V31_SALE_HORIZON = 8
V31_OPEN_ROUNDTRIP = 0
V31_ROW_ORDER = True
V31_EVENING_FLUSH = True
V31_SALE_FERTILIZER = True
V31_CATTLE_EARLY = True
V31_NO_LATE_SALE_ADVANCE_STEP = 648


def _fixed(name, supplied, expected):
    """Accept omitted/exact baseline values; reject bench contamination."""
    if supplied is None:
        return expected
    if type(supplied) is not type(expected) or supplied != expected:
        raise ValueError(
            "%s is fixed to live V3.1 baseline %r, got %r"
            % (name, expected, supplied)
        )
    return expected


def verify_joint_state():
    """Fail closed unless the imported arm is exactly V3.1 + H4 + L3@648."""
    expected = (
        ("SALE_HORIZON", base.SALE_HORIZON, V31_SALE_HORIZON),
        ("OPEN_ROUNDTRIP", base.OPEN_ROUNDTRIP, V31_OPEN_ROUNDTRIP),
        ("ROW_ORDER", base.ROW_ORDER, V31_ROW_ORDER),
        ("EVENING_FLUSH", base.EVENING_FLUSH, V31_EVENING_FLUSH),
        ("SALE_EXCLUDED", base.SALE_EXCLUDED, ("WHEAT",)),
        ("_V231_EARLY", base._V231_EARLY, V31_CATTLE_EARLY),
        ("STRAWBERRY_TOPUP", h4.STRAWBERRY_TOPUP, True),
        ("NO_LATE_SALE_ADVANCE", base.NO_LATE_SALE_ADVANCE, True),
        ("NO_LATE_SALE_ADVANCE_STEP", base.NO_LATE_SALE_ADVANCE_STEP,
         V31_NO_LATE_SALE_ADVANCE_STEP),
    )
    for name, actual, wanted in expected:
        if type(actual) is not type(wanted) or actual != wanted:
            raise RuntimeError(
                "joint arm baseline drift: %s=%r, expected %r"
                % (name, actual, wanted)
            )
    return True


def install_joint(host=None, horizon=None, opening=None, row_order=None,
                  evening_flush=None, sale_fertilizer=None, cattle_early=None,
                  no_late_sale_advance_step=V31_NO_LATE_SALE_ADVANCE_STEP):
    """Return the exact live-V3.1 R04 baseline with H4 + Riot L3 enabled.

    The optional legacy arguments remain only for caller compatibility. Omitting them
    pins the live V3.1 values; supplying the exact same value is accepted; any other
    value fails before mutating R04 globals. L1/L2 remain at their parent defaults.
    """
    horizon = _fixed("horizon", horizon, V31_SALE_HORIZON)
    opening = _fixed("opening", opening, V31_OPEN_ROUNDTRIP)
    row_order = _fixed("row_order", row_order, V31_ROW_ORDER)
    evening_flush = _fixed("evening_flush", evening_flush, V31_EVENING_FLUSH)
    sale_fertilizer = _fixed("sale_fertilizer", sale_fertilizer, V31_SALE_FERTILIZER)
    cattle_early = _fixed("cattle_early", cattle_early, V31_CATTLE_EARLY)
    no_late_sale_advance_step = _fixed(
        "no_late_sale_advance_step",
        no_late_sale_advance_step,
        V31_NO_LATE_SALE_ADVANCE_STEP,
    )

    candidate = h4.install(
        host,
        horizon,
        opening,
        row_order,
        evening_flush,
        sale_fertilizer,
        cattle_early,
        strawberry_topup=True,
    )
    base.install(
        no_late_sale_advance=True,
        no_late_sale_advance_step=no_late_sale_advance_step,
    )
    verify_joint_state()
    return candidate


# Standard evaluator entrypoint. Importing this module arms exactly the live V3.1 R04
# baseline + H4 + L3@648 and exposes the same module-level callable contract as a normal
# Kaggriculture agent. This avoids an untracked ad-hoc wrapper in a practice harness.
agent = install_joint()
