# SPDX-License-Identifier: Apache-2.0
"""Install one source-isolated carry haircut into V3's selected SELL optimizer.

Submitted V1 valued stock left beyond its artificial planning horizon at 95%
of modeled future receipts. V2 and current V3 use 100%. Current V3's frozen
seller does not call ``scheduler.optimize_lot``: it imports the production
optimizer from ``selected_sell_core``. This module wraps that class only and
changes only the carry contribution in the first score component.
"""
from __future__ import annotations

from typing import Any

DEFAULT_CARRY_DISCOUNT = 0.95
_MARKER = "_sol_kepler_horizon_liquidity_discount"


def _discount(value: float) -> float:
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("carry discount must be finite and in (0, 1]")
    if not 0.0 < value <= 1.0:
        raise ValueError("carry discount must be finite and in (0, 1]")
    return value


def install(selected_sell_core_module: Any, *, discount: float = DEFAULT_CARRY_DISCOUNT) -> dict[str, Any]:
    """Wrap ``selected_sell_core.MarketPath`` exactly once.

    The base method still computes inventory evolution, dated rival orders,
    absorption caching, receipts, terminal behavior, and the return tuple. The
    wrapper derives the already-computed carry contribution from that tuple and
    multiplies only that contribution by ``discount``.
    """
    factor = _discount(discount)
    base = getattr(selected_sell_core_module, "MarketPath")
    prior = getattr(base, _MARKER, None)
    if prior is not None:
        if float(prior) != factor:
            raise RuntimeError(
                f"MarketPath already carries a different liquidity factor: {prior}"
            )
        return {
            "installed": False,
            "idempotent": True,
            "factor": factor,
            "target": "selected_sell_core.MarketPath",
            "base": f"{base.__module__}.{base.__qualname__}",
        }

    class HorizonLiquidityMarketPath(base):
        """Current selected SELL valuation with V1's 0.95 carry factor."""

        def score(self, plan, quantity, rival, alignment, terminal=False):
            value, own_cash, other_cash, remaining = super().score(
                plan, quantity, rival, alignment, terminal
            )
            if remaining and not terminal:
                carry = float(value) - float(own_cash) + float(other_cash)
                value = float(own_cash) + factor * carry - float(other_cash)
            return value, own_cash, other_cash, remaining

    HorizonLiquidityMarketPath.__name__ = "HorizonLiquidityMarketPath"
    HorizonLiquidityMarketPath.__qualname__ = "HorizonLiquidityMarketPath"
    HorizonLiquidityMarketPath.__module__ = base.__module__
    setattr(HorizonLiquidityMarketPath, _MARKER, factor)
    selected_sell_core_module.MarketPath = HorizonLiquidityMarketPath
    return {
        "installed": True,
        "idempotent": False,
        "factor": factor,
        "target": "selected_sell_core.MarketPath",
        "base": f"{base.__module__}.{base.__qualname__}",
        "replacement": (
            f"{HorizonLiquidityMarketPath.__module__}."
            f"{HorizonLiquidityMarketPath.__qualname__}"
        ),
    }
