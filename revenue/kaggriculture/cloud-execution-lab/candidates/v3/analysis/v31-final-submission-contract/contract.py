# SPDX-License-Identifier: Apache-2.0
"""Source contract for the final V3.1 score-facing config transform.

Analysis-only: production ``make_submission.py`` must explicitly consume/review this
contract on the literal assembled post-L3/post-row-shed package.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping

DEFAULT_SUBMISSION_HORIZON = 8
PRESERVED_TRUE_KEYS = (
    "r04_row_order",
    "r04_evening_flush",
    "r04_sale_fertilizer",
    "r04_strawberry_topup",
    "r04_no_late_sale_advance",
    "r04_b5_carrot_fertilizer",
    "r04_b5_jit_fertilize",
    "r04_row_shed",
)
PRESERVED_FALSE_KEYS = (
    "r04_kill_late_water",
    "r04_strawberry_endgame",
)
TRANSFORM_KEYS = frozenset(
    ("r04_sale_window", "r04_sale_horizon", "r04_sale_fertilizer", "r04_cattle_early")
)


def _require_exact_bool(config: Mapping[str, object], key: str, expected: bool) -> None:
    if key not in config or type(config[key]) is not bool or config[key] is not expected:
        raise AssertionError(f"{key} must be literal {str(expected).lower()} before submission transform")


def _require_exact_int(config: Mapping[str, object], key: str, expected: int) -> None:
    value = config.get(key)
    if type(value) is not int or value != expected:
        raise AssertionError(f"{key} must be exact integer {expected}")


def require_final_input(config: Mapping[str, object]) -> None:
    """Fail closed unless the complete held winning assembly is already present."""
    if not isinstance(config, Mapping):
        raise AssertionError("TITAN-CONFIG must be a mapping")

    # The LAST score transform may not manufacture a gameplay decision.  The currently
    # held S34 context is H8 + native ROW_ORDER/flush/opening with cattle already OFF and
    # strict row-shed already ON.  Any later reviewed winner must change this theorem first.
    _require_exact_bool(config, "r04_sale_window", False)
    _require_exact_int(config, "r04_sale_horizon", DEFAULT_SUBMISSION_HORIZON)
    _require_exact_int(config, "r04_open_roundtrip", 0)
    _require_exact_int(config, "r04_strawberry_max_plants", 8)
    _require_exact_int(config, "r04_no_late_sale_advance_step", 648)

    for key in PRESERVED_TRUE_KEYS:
        _require_exact_bool(config, key, True)
    for key in PRESERVED_FALSE_KEYS:
        _require_exact_bool(config, key, False)
    _require_exact_bool(config, "r04_cattle_early", False)


def require_only_transform_keys_changed(before: Mapping[str, object], after: Mapping[str, object]) -> None:
    """Prove the score-facing transform did not consume ownership of upstream lanes."""
    if set(before) != set(after):
        raise AssertionError("submission transform may not add or remove config keys")
    for key in before:
        if key in TRANSFORM_KEYS:
            continue
        if type(before[key]) is not type(after[key]) or before[key] != after[key]:
            raise AssertionError(f"non-score-facing config drift: {key}")


def require_final_output(before: Mapping[str, object], after: Mapping[str, object]) -> None:
    """Bind the exact score-facing post-state and preservation theorem."""
    require_final_input(before)
    if not isinstance(after, Mapping):
        raise AssertionError("transformed TITAN-CONFIG must be a mapping")
    require_only_transform_keys_changed(before, after)
    expected = {
        "r04_sale_window": True,
        "r04_sale_horizon": DEFAULT_SUBMISSION_HORIZON,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": False,
    }
    for key, value in expected.items():
        if key not in after or type(after[key]) is not type(value) or after[key] != value:
            raise AssertionError(f"final score tuple drift: {key}={after.get(key)!r}, expected {value!r}")


def transform(config: Mapping[str, object], horizon: int | None = None) -> dict[str, object]:
    """Return the exact H8 score-facing config after validating the full input tuple.

    ``horizon`` is accepted only as an explicit H8 restatement for source compatibility.
    A different horizon is a gameplay decision and must first be promoted into this contract
    by a separately reviewed final-stack theorem; the LAST submission transform cannot choose it.
    """
    require_final_input(config)
    if horizon is not None and (type(horizon) is not int or horizon != DEFAULT_SUBMISSION_HORIZON):
        raise AssertionError(
            f"submission horizon override must equal held H{DEFAULT_SUBMISSION_HORIZON} decision"
        )
    out = copy.deepcopy(dict(config))
    out["r04_sale_window"] = True
    out["r04_sale_horizon"] = DEFAULT_SUBMISSION_HORIZON
    out["r04_sale_fertilizer"] = True
    out["r04_cattle_early"] = False
    require_final_output(config, out)
    return out
