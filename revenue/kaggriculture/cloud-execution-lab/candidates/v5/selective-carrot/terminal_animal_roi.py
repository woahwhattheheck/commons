# SPDX-License-Identifier: Apache-2.0
"""Reference source for the bounded TITAN V5 terminal animal-purchase filter.

The marked region is source-hash-bound and inlined into the authenticated
production-v3 ``main.py`` by ``build_terminal_animal_roi.py``.  The helper is
not added to the runnable archive; that keeps the treatment replacement-only.
"""

# TITAN_TERMINAL_ANIMAL_ROI_INLINE_BEGIN
_TERMINAL_ROI_ANIMALS = frozenset(("GOOSE", "COW", "SHEEP"))


def _terminal_roi_plain_positive_int(value) -> bool:
    return type(value) is int and value > 0


def _terminal_roi_animal_buy(order) -> bool:
    return (
        isinstance(order, (list, tuple))
        and len(order) == 3
        and order[0] == "BUY_ANIMAL"
        and order[1] in _TERMINAL_ROI_ANIMALS
        and _terminal_roi_plain_positive_int(order[2])
    )


def terminal_animal_roi_filter(observation, action, *, min_step: int = 718):
    """Drop valid ``BUY_ANIMAL`` rows at/after ``min_step``; otherwise identity."""
    if type(min_step) is not int or not 0 <= min_step <= 718:
        return action
    if not isinstance(observation, dict) or type(observation.get("step")) is not int:
        return action
    if observation["step"] < min_step:
        return action
    if not isinstance(action, dict):
        return action
    market = action.get("market")
    if not isinstance(market, list):
        return action

    filtered = [order for order in market if not _terminal_roi_animal_buy(order)]
    if len(filtered) == len(market):
        return action

    changed = dict(action)
    changed["market"] = filtered
    return changed
# TITAN_TERMINAL_ANIMAL_ROI_INLINE_END
