#!/usr/bin/env python3
"""Transparent five-year cost sensitivity model for proposal planning.

All rates are caller inputs. The repository intentionally contains no invented company rates.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP


def money(x: Decimal) -> str:
    return f"${x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--year1-hours", type=Decimal, required=True)
    p.add_argument("--maintenance-hours-per-year", type=Decimal, required=True)
    p.add_argument("--hourly-rate", type=Decimal, required=True)
    p.add_argument("--hosting-per-year", type=Decimal, required=True)
    p.add_argument("--other-fixed", type=Decimal, default=Decimal("0"))
    a = p.parse_args()
    vals = [a.year1_hours, a.maintenance_hours_per_year, a.hourly_rate, a.hosting_per_year, a.other_fixed]
    if any(v < 0 for v in vals):
        raise SystemExit("all inputs must be non-negative")
    y1_labor = a.year1_hours * a.hourly_rate
    maint_labor = a.maintenance_hours_per_year * a.hourly_rate * Decimal(4)
    hosting = a.hosting_per_year * Decimal(5)
    total = y1_labor + maint_labor + hosting + a.other_fixed
    print(f"year1_labor={money(y1_labor)}")
    print(f"years2_5_labor={money(maint_labor)}")
    print(f"five_year_hosting={money(hosting)}")
    print(f"other_fixed={money(a.other_fixed)}")
    print(f"five_year_total={money(total)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
