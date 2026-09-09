# SPDX-License-Identifier: Apache-2.0
"""Install one source-isolated horizon-liquidity ablation into TITAN's scheduler.

The submitted V1 scheduler valued unsold stock at 95% of its modeled future
receipt while V2 and current V3 use 100%.  This module changes only that factor.
It deliberately preserves the current score loop, rival timing, absorption,
terminal handling, and return shape.
"""
from __future__ import annotations

from typing import Any

DEFAULT_CARRY_DISCOUNT = 0.95
_MARKER = "_sol_kepler_horizon_liquidity_discount"


def _discount(value: float) -> float:
    value = float(value)
    if not 0.0 < value <= 1.0:
        raise ValueError("carry discount must be finite and in (0, 1]")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("carry discount must be finite and in (0, 1]")
    return value


def install(scheduler_module: Any, *, discount: float = DEFAULT_CARRY_DISCOUNT) -> dict[str, Any]:
    """Replace ``MarketPath`` with a one-method subclass, once.

    ``optimize_lot`` resolves ``MarketPath`` from its scheduler-module globals on
    every call, so installing before ``TitanAgent._initialize`` affects the real
    FrozenSelected lifecycle without copying or bypassing canonical ``main.py``.
    """
    factor = _discount(discount)
    base = getattr(scheduler_module, "MarketPath")
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
            "base": f"{base.__module__}.{base.__qualname__}",
        }

    absorption = getattr(scheduler_module, "absorption")

    class HorizonLiquidityMarketPath(base):
        """Current MarketPath with V1's 0.95 artificial-horizon carry factor."""

        def score(self, plan, quantity, rival, alignment, terminal=False):
            inv = self.inventory
            own_cash = other_cash = 0
            sold = 0
            orders = dict(plan)
            for step in range(self.now, self.end + 1):
                q = min(quantity - sold, max(0, orders.get(step, 0)))
                r = (
                    dict(rival).get(step, 0)
                    if isinstance(rival, tuple)
                    else rival if step == self.now else 0
                )
                a, b, inv = self.joint(inv, q, r, alignment)
                own_cash += a
                other_cash += b
                sold += q
                inv -= absorption(self.item, step, self.shops, self.config)
            remaining = quantity - sold
            carry = 0.0
            if remaining and not terminal:
                carry = factor * float(self.single(inv, remaining)[0])
            return own_cash + carry - other_cash, own_cash, other_cash, remaining

    HorizonLiquidityMarketPath.__name__ = "HorizonLiquidityMarketPath"
    HorizonLiquidityMarketPath.__qualname__ = "HorizonLiquidityMarketPath"
    HorizonLiquidityMarketPath.__module__ = base.__module__
    setattr(HorizonLiquidityMarketPath, _MARKER, factor)
    scheduler_module.MarketPath = HorizonLiquidityMarketPath
    return {
        "installed": True,
        "idempotent": False,
        "factor": factor,
        "base": f"{base.__module__}.{base.__qualname__}",
        "replacement": (
            f"{HorizonLiquidityMarketPath.__module__}."
            f"{HorizonLiquidityMarketPath.__qualname__}"
        ),
    }
