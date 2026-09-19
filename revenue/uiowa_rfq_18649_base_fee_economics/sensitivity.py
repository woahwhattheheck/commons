"""Sensitivity analysis: which conclusions survive, and which are corner cases.

A single expected-case number is the least useful output a cost model can
produce, because the one thing a bidder needs to know is how much has to go
right. So the sweep runs every effort case against a band of rate assumptions
and reports the SHAPE of the result:

  * how many of the swept scenarios are profitable at all
  * whether the profitable ones cluster at the optimistic corner
  * how far a single assumption has to move to flip the answer

A conclusion that holds only at the low-effort case with the lowest rate is
labelled as such. That is a different statement from "this bid is profitable",
and the difference is the whole point of running a sweep.

Python 3 standard library only.
"""

from __future__ import annotations

import copy
import json
from decimal import Decimal

import cost_model
import money
from money import UNKNOWN, is_unknown

DEFAULT_RATE_STEPS = (Decimal("0.80"), Decimal("0.90"), Decimal("1.00"),
                      Decimal("1.10"), Decimal("1.20"))


def _scaled(model: cost_model.Model, factor: Decimal) -> cost_model.Model:
    raw = copy.deepcopy(model._raw)
    for key, rate in raw["rates"].items():
        scaled = (money.money(rate["amount"]) * factor).quantize(money.CENT)
        rate["amount"] = str(scaled)
        rate["note"] = (rate.get("note", "") + f" [swept x{factor}]").strip()
    return cost_model.Model(raw)


def sweep(model: cost_model.Model, rate_steps=DEFAULT_RATE_STEPS) -> dict:
    """Every effort case against every rate step."""
    scenarios = []
    for factor in rate_steps:
        variant = _scaled(model, factor)
        for case in cost_model.CASES:
            summary = variant.case_summary(case)
            verdict = variant.verdict(case)
            scenarios.append({
                "rate_factor": str(factor),
                "case": case,
                "total_cost": summary["total_cost"],
                "floor_cost": summary["known_subtotal"],
                "margin": summary["contribution_margin"],
                "margin_pct": summary["contribution_margin_pct"],
                "verdict": verdict["verdict"],
            })

    computed = [s for s in scenarios if s["verdict"] == "MARGIN_COMPUTED"]
    certain_loss = [s for s in scenarios if s["verdict"] == "LOSS_CERTAIN_DESPITE_UNKNOWNS"]
    undetermined = [s for s in scenarios if s["verdict"] == "NOT_COMPUTABLE"]
    profitable = [s for s in computed if not is_unknown(s["margin"]) and s["margin"] > 0]

    # Is every profitable scenario at the optimistic corner? If so, saying
    # "profitable under some assumptions" would be true and misleading.
    corner_only = bool(profitable) and all(
        s["case"] == "low" and Decimal(s["rate_factor"]) <= Decimal("1.00")
        for s in profitable)

    return {
        "rate_steps": [str(f) for f in rate_steps],
        "scenarios": scenarios,
        "counts": {
            "total": len(scenarios),
            "margin_computed": len(computed),
            "profitable": len(profitable),
            "loss_certain": len(certain_loss),
            "not_computable": len(undetermined),
        },
        "profitable_only_at_optimistic_corner": corner_only,
        "conclusion": _conclusion(scenarios, profitable, certain_loss, undetermined, corner_only),
    }


def _conclusion(scenarios, profitable, certain_loss, undetermined, corner_only) -> str:
    n = len(scenarios)
    if not profitable and certain_loss and not undetermined:
        return (f"No swept scenario is profitable, and {len(certain_loss)} of {n} lose money "
                f"regardless of the missing estimates. The proposed fee does not cover the "
                f"modelled effort under any assumption tested.")
    if not profitable and undetermined:
        return (f"No swept scenario is profitable on the evidence available. "
                f"{len(certain_loss)} of {n} lose money regardless of the missing estimates; "
                f"{len(undetermined)} cannot be decided until those estimates exist.")
    if corner_only:
        return (f"Only {len(profitable)} of {n} swept scenarios are profitable, and every one "
                f"of them sits at the low-effort case with rates at or below the assumed card. "
                f"This is a corner result, not a margin: it holds only if effort lands at the "
                f"optimistic end AND rates do not rise.")
    return (f"{len(profitable)} of {n} swept scenarios are profitable, spread across more than "
            f"the optimistic corner. The result is not purely an artifact of the best case.")


def rate_breakeven(model: cost_model.Model, case: str = "expected",
                   rate_key: str = "production") -> dict:
    """How far one rate assumption must move before the answer flips.

    Reported because "we lose money at $70/h" invites the obvious question,
    and a model that cannot answer it sends the reader to a spreadsheet.
    """
    if rate_key not in model.rates:
        raise KeyError(f"unknown rate {rate_key!r}; known: {', '.join(sorted(model.rates))}")
    base = model.case_summary(case)
    if not base["computable"]:
        return {"case": case, "rate": rate_key, "flips_at": UNKNOWN,
                "reason": ("an estimate is missing, so there is no margin to flip. Resolve "
                           f"{', '.join(base['incomplete_packages'])} first.")}

    # Bisection over the multiplier. The relationship is linear in the rate,
    # but bisection needs no assumption about that and survives a future
    # non-linear overhead rule.
    def margin_at(factor: Decimal):
        return _scaled(model, factor).case_summary(case)["contribution_margin"]

    lo, hi = Decimal("0.01"), Decimal("4.00")
    m_lo, m_hi = margin_at(lo), margin_at(hi)
    if (m_lo > 0) == (m_hi > 0):
        return {"case": case, "rate": rate_key, "flips_at": UNKNOWN,
                "reason": ("the sign of the margin does not change anywhere in a 1%-400% "
                           "sweep of this rate; the result is not rate-driven.")}
    for _ in range(60):
        mid = (lo + hi) / 2
        if (margin_at(mid) > 0) == (m_lo > 0):
            lo = mid
        else:
            hi = mid
    factor = ((lo + hi) / 2).quantize(Decimal("0.0001"))
    return {
        "case": case,
        "rate": rate_key,
        "flips_at_factor": factor,
        "current_amount": model.rates[rate_key].amount,
        "flips_at_amount": (model.rates[rate_key].amount * factor).quantize(money.CENT),
        "direction": "below" if margin_at(Decimal("0.5")) > 0 else "above",
        "reason": "",
    }
