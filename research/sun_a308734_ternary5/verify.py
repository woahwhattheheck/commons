#!/usr/bin/env python3
"""Exact finite checks for the A308661 / A308734 ternary-5 research lane.

This module certifies only the finite falsifiers and arithmetic support used in
README.md. It does not claim to prove the infinite conjecture.
"""
from __future__ import annotations

from math import isqrt


def factorint(n: int) -> dict[int, int]:
    if n < 1:
        raise ValueError("factorint expects a positive integer")
    out: dict[int, int] = {}
    while n % 2 == 0:
        out[2] = out.get(2, 0) + 1
        n //= 2
    p = 3
    while p * p <= n:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
        p += 2
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def bad_support(n: int) -> tuple[int, ...]:
    """Odd-valuation p == 3 (mod 4) primes obstructing two-square status."""
    if n < 1:
        raise ValueError("bad_support expects a positive integer")
    return tuple(
        p
        for p, exponent in factorint(n).items()
        if p % 4 == 3 and exponent % 2 == 1
    )


def is_sum_of_two_squares(n: int) -> bool:
    if n < 0:
        return False
    if n == 0:
        return True
    return not bad_support(n)


def two_square_representation(n: int) -> tuple[int, int] | None:
    if n < 0:
        return None
    for x in range(isqrt(n) + 1):
        y2 = n - x * x
        y = isqrt(y2)
        if y * y == y2:
            return x, y
    return None


def residual(N: int, a: int, b: int) -> int:
    if a < 1 or b < 0:
        raise ValueError("requires a >= 1, b >= 0")
    return N - (4**a) * (25**b)


def bounded_b_falsifier(
    N: int, max_b: int
) -> list[tuple[int, int, int, tuple[int, ...]]]:
    """Return every positive residual at b <= max_b, requiring all to fail."""
    if N % 12 != 5:
        raise ValueError("N must be 5 mod 12")
    rows: list[tuple[int, int, int, tuple[int, ...]]] = []
    a = 1
    while 4**a < N:
        for b in range(max_b + 1):
            m = residual(N, a, b)
            if m <= 0:
                continue
            support = bad_support(m)
            if not support:
                raise AssertionError(
                    f"{N} is not a falsifier for b <= {max_b}: "
                    f"a={a}, b={b}, residual={m}"
                )
            rows.append((a, b, m, support))
        a += 1
    return rows


def theorem_support_checks() -> None:
    # A shared bad prime in fixed-a residuals b distance 1 or 2 would divide
    # 25^d-1. Apart from 3, those constants have no 3 mod 4 prime.
    for d in (1, 2):
        support = tuple(p for p in factorint(25**d - 1) if p % 4 == 3)
        if support != (3,):
            raise AssertionError((d, support))

    # The analogous fixed-b / consecutive-a constants are 4^d-1.
    for d in (1, 2):
        support = tuple(p for p in factorint(4**d - 1) if p % 4 == 3)
        if support != (3,):
            raise AssertionError((d, support))

    six = (7, 11, 19, 23, 31, 43)
    product = 1
    for p in six:
        product *= p
    if product != 44_854_117:
        raise AssertionError(product)


def finite_regression_checks() -> None:
    # "b = 0 always suffices" is false.
    rows = bounded_b_falsifier(12_233, 0)
    if len(rows) != 6:
        raise AssertionError(len(rows))
    if two_square_representation(residual(12_233, 1, 2)) != (18, 97):
        raise AssertionError("expected higher-b witness missing")

    # Even allowing b in {0,1} does not suffice uniformly.
    rows = bounded_b_falsifier(1_595_477, 1)
    if len(rows) != 17:
        raise AssertionError(len(rows))
    rep = two_square_representation(residual(1_595_477, 2, 2))
    if rep != (831, 946):
        raise AssertionError(rep)


def sampled_disjointness_checks(limit: int = 100_000) -> None:
    """Finite regression for the exact symbolic disjointness lemmas."""
    for N in range(5, limit + 1, 12):
        # fixed a, three consecutive b
        a = 1
        while 4**a < N:
            b = 0
            while True:
                ms = [residual(N, a, b + j) for j in range(3)]
                if ms[-1] <= 0:
                    break
                supports = [set(bad_support(m)) for m in ms]
                if any(
                    supports[i] & supports[j]
                    for i in range(3)
                    for j in range(i + 1, 3)
                ):
                    raise AssertionError(("b", N, a, b, supports))
                b += 1
            a += 1

        # fixed b, three consecutive a
        b = 0
        while 25**b < N:
            a = 1
            while True:
                ms = [residual(N, a + j, b) for j in range(3)]
                if ms[-1] <= 0:
                    break
                supports = [set(bad_support(m)) for m in ms]
                if any(
                    supports[i] & supports[j]
                    for i in range(3)
                    for j in range(i + 1, 3)
                ):
                    raise AssertionError(("a", N, a, b, supports))
                a += 1
            b += 1


def main() -> int:
    theorem_support_checks()
    finite_regression_checks()
    sampled_disjointness_checks()
    print("PASS: exact finite checks; no infinite proof claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
