from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from itertools import combinations
from typing import Iterable, Sequence

ONE = Fraction(1, 1)


def _canon(points: Iterable[Fraction]) -> tuple[Fraction, ...]:
    pts = tuple(sorted(points))
    if len(set(pts)) != len(pts):
        raise ValueError("points must be distinct")
    if any(x <= ONE for x in pts):
        raise ValueError("all points must be > 1")
    return pts


def finite_well_separated(points: Iterable[Fraction]) -> bool:
    """Exact finite analogue of Erdos143.WellSeparatedSet's separation clause.

    For fixed x,y>1, once k*x-y >= 1, all larger k are automatically safe,
    so only finitely many k need checking. Fraction keeps the check exact.
    """
    pts = _canon(points)
    for x in pts:
        for y in pts:
            if x == y:
                continue
            kmax = int((y + ONE) // x) + 2
            for k in range(1, max(2, kmax + 1)):
                delta = Fraction(k, 1) * x - y
                if abs(delta) < ONE:
                    return False
    return True


def pairwise_unit_separated(points: Iterable[Fraction]) -> bool:
    """The k=1 consequence: distinct points are at least distance one apart."""
    pts = _canon(points)
    return all(abs(x - y) >= ONE for x, y in combinations(pts, 2))


def unit_bin_occupancy(points: Iterable[Fraction]) -> dict[int, int]:
    """Occupancy of half-open integer bins [m,m+1)."""
    pts = _canon(points)
    bins: dict[int, int] = {}
    for x in pts:
        m = x.numerator // x.denominator
        bins[m] = bins.get(m, 0) + 1
    return bins


def unit_bin_injective(points: Iterable[Fraction]) -> bool:
    return all(v <= 1 for v in unit_bin_occupancy(points).values())


def integer_interval_occupancy_bound(points: Iterable[Fraction], start: int, length: int) -> bool:
    """If points are unit-separated, [start,start+length) contains <= length points."""
    if length < 0:
        raise ValueError("length must be nonnegative")
    pts = _canon(points)
    lo, hi = Fraction(start), Fraction(start + length)
    count = sum(lo <= x < hi for x in pts)
    return count <= length


def multiple_exclusion(points: Iterable[Fraction]) -> bool:
    """No other point lies in the open radius-one interval about k*x, k>=1."""
    pts = _canon(points)
    for x in pts:
        for y in pts:
            if x == y:
                continue
            kmax = int((y + ONE) // x) + 2
            for k in range(1, max(2, kmax + 1)):
                if abs(Fraction(k) * x - y) < ONE:
                    return False
    return True


def primitive_integer_subset(values: Sequence[int]) -> bool:
    """No distinct member divides another."""
    vals = tuple(sorted(values))
    if len(set(vals)) != len(vals) or any(v <= 1 for v in vals):
        raise ValueError("integer values must be distinct and > 1")
    return all(b % a != 0 for i, a in enumerate(vals) for b in vals[i + 1 :])


def integer_wss_via_divisibility(values: Sequence[int]) -> bool:
    """For integer points, the full k>=1 separation clause iff the set is primitive.

    k*x-y is an integer. Its absolute value is <1 exactly when it is zero,
    which happens for distinct positive x,y exactly when one divides the other.
    """
    return primitive_integer_subset(values)


def _status_stream(limit: int) -> tuple[list[str], dict[str, object]]:
    if limit < 2:
        raise ValueError("limit must be >= 2")
    universe = tuple(range(2, limit + 1))
    records: list[str] = []
    total = 0
    primitive_count = 0
    max_card = -1
    max_count = 0
    equivalence_mismatches = 0
    consequence_failures = 0

    for mask in range(1 << len(universe)):
        values = tuple(universe[i] for i in range(len(universe)) if (mask >> i) & 1)
        total += 1
        primitive = primitive_integer_subset(values) if values else True
        points = tuple(Fraction(v) for v in values)
        finite_clause = finite_well_separated(points) if points else True
        if primitive != finite_clause:
            equivalence_mismatches += 1
        if primitive:
            primitive_count += 1
            if values:
                good = pairwise_unit_separated(points) and unit_bin_injective(points) and multiple_exclusion(points)
                for start in range(2, limit + 1):
                    for length in range(0, limit + 2 - start):
                        good = good and integer_interval_occupancy_bound(points, start, length)
                if not good:
                    consequence_failures += 1
            card = len(values)
            if card > max_card:
                max_card = card
                max_count = 1
            elif card == max_card:
                max_count += 1
        records.append(f"{mask:0{len(universe)}b}|{int(primitive)}|{len(values)}")

    payload = {
        "limit": limit,
        "universe_first": 2,
        "universe_last": limit,
        "total_subsets": total,
        "primitive_or_integer_wss_subsets": primitive_count,
        "max_primitive_cardinality": max_card,
        "maximizer_count": max_count,
        "equivalence_mismatches": equivalence_mismatches,
        "consequence_failures": consequence_failures,
    }
    return records, payload


def build_receipt(limit: int = 18) -> dict[str, object]:
    records, scan = _status_stream(limit)
    rational_controls = [
        (Fraction(13, 6), Fraction(19, 6), Fraction(16, 3)),
        (Fraction(13, 6), Fraction(16, 5), Fraction(27, 5)),
        (Fraction(9, 4), Fraction(13, 4), Fraction(10, 3)),
    ]
    control_rows = []
    for pts in rational_controls:
        control_rows.append(
            {
                "points": [f"{x.numerator}/{x.denominator}" for x in pts],
                "well_separated": finite_well_separated(pts),
                "pairwise_unit_separated": pairwise_unit_separated(pts),
                "unit_bin_injective": unit_bin_injective(pts),
                "multiple_exclusion": multiple_exclusion(pts),
            }
        )
    records_sha = sha256(("\n".join(records) + "\n").encode()).hexdigest()
    body = {
        "schema": "erdos143-separation-api-receipt-v1",
        "claim": "finite exact regression for first consequences of WellSeparatedSet; not a proof of summability",
        "sponsor": {
            "task_id": "fc-8432eac9-parts-ii-0703f44156-formalized-v1",
            "task_commitment": "sha256:fa633be39c4914b8d907e9d1cff77d8cf78eea34632c03fb6a2c03ee9f305ebd",
            "source_type_sha256": "sha256:d67e6578eee8f3a70ba0d0b5c0035e56073ee6d2505bee0c99f768e41e21e73d",
            "formal_conjectures_commit": "8432eac998110a563e03df65a28c117e97c8c142",
        },
        "scan": scan,
        "records_sha256": records_sha,
        "rational_controls": control_rows,
    }
    body_bytes = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return {**body, "payload_sha256": sha256(body_bytes).hexdigest()}


def main() -> None:
    print(json.dumps(build_receipt(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
