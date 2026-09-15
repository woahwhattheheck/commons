"""POLAR-20260911-SEED-SHADOW: prospective seed-value calculator.

Research-only SYNTHETIC LINEAR book, not an official-engine price model.
Sequential per-unit liquidation versus naive current_quote * extra_yield.
The following are reference pins, not proof of price parity: interpreter
465f4263da1c98acf78889d67cdd21b61dbba145 and engine blob
3c202c7ee921da239356789e266b694635103fc4 as source pins.

Does not mutate runtime, keys, config, gameplay spine, canonical
ref, Actions, or Kaggle. A result here is not permission to skip
authored PLANT or BUY_SEED.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Iterable, List

INTERPRETER_SHA = "465f4263da1c98acf78889d67cdd21b61dbba145"
ENGINE_BLOB_SHA = "3c202c7ee921da239356789e266b694635103fc4"
CLAIM = "POLAR-20260911-SEED-SHADOW"


# Reject ambiguous quantities and nonfinite economics rather than silently
# truncating inputs or allowing NaN to turn every comparison into False.
def _count(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a plain nonnegative int")
    return value


def _finite(value: object, name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite number, not a bool or coercion")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _nonnegative(value: object, name: str) -> float:
    result = _finite(value, name)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _product(left: float, right: int, name: str) -> float:
    try:
        return _finite(left * right, name)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc


def _book(value: object) -> MarketBook:
    if not isinstance(value, MarketBook):
        raise ValueError("book must be a synthetic MarketBook")
    return value


@dataclass(frozen=True)
class MarketBook:
    """Synthetic nonincreasing linear book; not the pinned engine curve."""

    quote0: float
    impact: float
    floor: float = 0.0

    def __post_init__(self) -> None:
        quote = _nonnegative(self.quote0, "quote0")
        _nonnegative(self.impact, "impact")
        floor = _nonnegative(self.floor, "floor")
        if floor > quote:
            raise ValueError("floor cannot exceed quote0")

    def price_after(self, sold: int) -> float:
        _count(sold, "sold")
        displacement = _product(float(self.impact), sold, "price displacement")
        price = _finite(float(self.quote0) - displacement, "price")
        return max(float(self.floor), price)


@dataclass(frozen=True)
class SeedCase:
    """One isolated liquidation scenario.

    owned_seed: already held; purchase cost is sunk (not charged).
    buy_seed: fresh purchases; charged at seed_price each.
    committed_output: yield already promised / in inventory; sold first.
    extra_yield: externally supplied realized output, not a yield forecast.
    realized_yield_per_seed: nonnegative metadata; does not multiply extra_yield.
    """

    book: MarketBook
    committed_output: int
    extra_yield: int
    owned_seed: int = 0
    buy_seed: int = 0
    seed_price: float = 0.0
    realized_yield_per_seed: float = 1.0

    def __post_init__(self) -> None:
        _book(self.book)
        for name in ("committed_output", "extra_yield", "owned_seed", "buy_seed"):
            _count(getattr(self, name), name)
        _nonnegative(self.seed_price, "seed_price")
        _nonnegative(self.realized_yield_per_seed, "realized_yield_per_seed")


@dataclass(frozen=True)
class Valuation:
    naive_incremental: float
    sequential_incremental: float
    committed_revenue: float
    extra_revenue: float
    purchase_cost: float
    net_sequential: float
    sign_flip: bool
    interpreter_sha: str = INTERPRETER_SHA
    engine_blob_sha: str = ENGINE_BLOB_SHA
    claim: str = CLAIM
    # Append fields so historical positional source-pin arguments retain order.
    naive_net_incremental: float = 0.0
    pricing_model: str = "synthetic-linear"


def liquidate(book: MarketBook, units: int, start_sold: int = 0) -> List[float]:
    _book(book)
    _count(units, "units")
    _count(start_sold, "start_sold")
    return [book.price_after(start_sold + i) for i in range(units)]


def revenue(book: MarketBook, units: int, start_sold: int = 0) -> float:
    _book(book)
    _count(units, "units")
    _count(start_sold, "start_sold")
    try:
        # No per-unit list allocation; stable summation at float boundaries.
        total = math.fsum(book.price_after(start_sold + i) for i in range(units))
    except OverflowError as exc:
        raise ValueError("revenue must be finite") from exc
    return _finite(total, "revenue")


def naive_incremental(quote: float, extra_yield: int) -> float:
    quote = _nonnegative(quote, "quote")
    _count(extra_yield, "extra_yield")
    return _product(quote, extra_yield, "naive revenue")


def _purchase_cost(case: SeedCase) -> float:
    return _product(float(case.seed_price), case.buy_seed, "purchase cost")


def evaluate(case: SeedCase) -> Valuation:
    if not isinstance(case, SeedCase):
        raise ValueError("case must be a SeedCase")
    committed = case.committed_output
    extra = case.extra_yield
    purchase = _purchase_cost(case)
    committed_rev = revenue(case.book, committed, 0)
    extra_rev = revenue(case.book, extra, committed)
    naive = naive_incremental(case.book.quote0, extra)
    net = _finite(extra_rev - purchase, "sequential net")
    naive_net = _finite(naive - purchase, "naive net")
    return Valuation(
        naive_incremental=naive,
        sequential_incremental=extra_rev,
        committed_revenue=committed_rev,
        extra_revenue=extra_rev,
        purchase_cost=purchase,
        net_sequential=net,
        # Compare like with like. Zero is break-even, not a strict sign flip.
        sign_flip=(naive_net > 0 and net < 0) or (naive_net < 0 and net > 0),
        naive_net_incremental=naive_net,
    )


def break_even_extra_yield(case: SeedCase, max_extra: int = 10_000) -> int | None:
    """First break-even extra quantity within the inclusive supplied horizon.

    One quote per extra unit; committed revenue is irrelevant to incremental
    break-even. The exact binary-float sum avoids a cumulative-rounding change
    at the crossing compared with revenue()'s correctly rounded fsum.
    This is a quantity calculation, not proof that the yield is achievable.
    """
    if not isinstance(case, SeedCase):
        raise ValueError("case must be a SeedCase")
    _count(max_extra, "max_extra")
    purchase = _purchase_cost(case)
    if purchase == 0.0:
        return 0
    running = Fraction(0)
    for extra in range(1, max_extra + 1):
        price = case.book.price_after(case.committed_output + extra - 1)
        running += Fraction.from_float(price)
        try:
            total = _finite(float(running), "extra revenue")
        except OverflowError as exc:
            raise ValueError("extra revenue must be finite") from exc
        if total >= purchase:
            return extra
    return None


def scenario_pack() -> dict:
    """Reproducible sign-flip and break-even fixtures for the V4 queue."""
    book = MarketBook(quote0=10.0, impact=1.0, floor=0.0)
    flip = SeedCase(
        book=book,
        committed_output=8,
        extra_yield=3,
        owned_seed=0,
        buy_seed=1,
        seed_price=6.0,
    )
    flip_v = evaluate(flip)
    sunk = SeedCase(
        book=book,
        committed_output=8,
        extra_yield=3,
        owned_seed=1,
        buy_seed=0,
        seed_price=6.0,
    )
    sunk_v = evaluate(sunk)
    be_case = SeedCase(
        book=book,
        committed_output=8,
        extra_yield=0,
        owned_seed=0,
        buy_seed=1,
        seed_price=3.0,
    )
    be = break_even_extra_yield(be_case)
    return {
        "claim": CLAIM,
        "interpreter_sha": INTERPRETER_SHA,
        "engine_blob_sha": ENGINE_BLOB_SHA,
        "assumptions": [
            "fixed realized yield",
            "isolated same-item liquidation at a specified inventory",
            "public market changes, opponent trades, and future shop unlocks are scenarios",
            "owned seed is sunk and is not charged as a fresh purchase",
            "research result is not permission to skip authored PLANT/BUY_SEED",
        ],
        "sign_flip": {
            "committed_output": 8,
            "extra_yield": 3,
            "buy_seed": 1,
            "seed_price": 6.0,
            "quote0": 10.0,
            "impact": 1.0,
            "naive_incremental": flip_v.naive_incremental,
            "net_sequential": flip_v.net_sequential,
            "sign_flip": flip_v.sign_flip,
        },
        "sunk_owned_seed": {
            "owned_seed": 1,
            "buy_seed": 0,
            "purchase_cost": sunk_v.purchase_cost,
            "net_sequential": sunk_v.net_sequential,
        },
        "break_even_extra_yield": be,
    }


def main(argv: Iterable[str] | None = None) -> int:
    pack = scenario_pack()
    print(pack)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
