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
    "r04_sale_fertilizer",
    "r04_strawberry_topup",
    "r04_no_late_sale_advance",
    "r04_b5_carrot_fertilizer",
    "r04_b5_jit_fertilize",
    "r04_row_shed",
)
TRANSFORM_KEYS = frozenset(
    ("r04_sale_window", "r04_sale_horizon", "r04_sale_fertilizer", "r04_cattle_early")
)


def _require_exact_bool(config: Mapping[str, object], key: str, expected: bool) -> None:
    if key not in config or type(config[key]) is not bool or config[key] is not expected:
        raise AssertionError(f"{key} must be literal {str(expected).lower()} before submission transform")


def _require_positive_int(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise AssertionError(f"{label} must be a positive non-bool integer")
    return value


def require_final_input(config: Mapping[str, object]) -> None:
    """Fail closed unless the complete winning assembly is already present."""
    if not isinstance(config, Mapping):
        raise AssertionError("TITAN-CONFIG must be a mapping")
    _require_exact_bool(config, "r04_sale_window", False)
    _require_positive_int(config.get("r04_sale_horizon"), "r04_sale_horizon")
    for key in PRESERVED_TRUE_KEYS:
        _require_exact_bool(config, key, True)
    _require_exact_bool(config, "r04_cattle_early", False)
    if type(config.get("r04_no_late_sale_advance_step")) is not int:
        raise AssertionError("r04_no_late_sale_advance_step must be an exact integer")
    if config["r04_no_late_sale_advance_step"] != 648:
        raise AssertionError("r04_no_late_sale_advance_step must equal 648")


def transform(config: Mapping[str, object], horizon: int | None = None) -> dict[str, object]:
    """Return a detached score-facing config after validating the full input tuple."""
    require_final_input(config)
    target = DEFAULT_SUBMISSION_HORIZON if horizon is None else _require_positive_int(
        horizon, "submission horizon"
    )
    out = copy.deepcopy(dict(config))
    out["r04_sale_window"] = True
    out["r04_sale_horizon"] = target
    out["r04_sale_fertilizer"] = True
    out["r04_cattle_early"] = False
    return out


def require_only_transform_keys_changed(before: Mapping[str, object], after: Mapping[str, object]) -> None:
    """Prove the score-facing transform did not consume ownership of upstream lanes."""
    if set(before) != set(after):
        raise AssertionError("submission transform may not add or remove config keys")
    for key in before:
        if key in TRANSFORM_KEYS:
            continue
        if type(before[key]) is not type(after[key]) or before[key] != after[key]:
            raise AssertionError(f"non-score-facing config drift: {key}")
