from __future__ import annotations

from datetime import date
from decimal import Decimal


class ExchangeRateError(ValueError):
    pass


class ExchangeBook:
    def __init__(self, rows: list[dict[str, str]]):
        self._rates: dict[tuple[date, str, str], Decimal] = {}
        for r in rows:
            self._rates[(date.fromisoformat(r["rate_date"]), r["from_currency"], r["to_currency"])] = Decimal(r["rate"])

    def convert(self, amount: Decimal, currency: str, home_currency: str, on_date: date) -> Decimal:
        if currency == home_currency:
            return amount
        key = (on_date, currency, home_currency)
        if key in self._rates:
            return amount * self._rates[key]
        # The challenge promises the required dated direction. Inverse is accepted only
        # as a defensive fallback so a malformed fixture still fails conservatively rather
        # than silently using a live rate.
        inverse = (on_date, home_currency, currency)
        if inverse in self._rates and self._rates[inverse] != 0:
            return amount / self._rates[inverse]
        raise ExchangeRateError(f"missing fixed rate for {currency}->{home_currency} on {on_date}")
