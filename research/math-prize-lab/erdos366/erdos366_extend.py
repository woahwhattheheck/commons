#!/usr/bin/env python3
"""Exact, shardable bounded search for the Erdős 366 orientation.

Target:
    exists n > 0 with n 2-full and n+1 3-full.

This extension enumerates only 3-full successors m=n+1, then proves that a
candidate predecessor is not 2-full by exhibiting a prime p with p || n.
When no such prime exists, the complete factorization is retained as a witness
certificate.  For integers < 2**64 the primality test uses a deterministic
Miller-Rabin basis.  Pollard-Brent is only an accelerator: an exact trial-
division fallback is retained, so failure to find a factor heuristically never
turns into an acceptance.

A negative bounded run is finite computational evidence, not a proof of global
nonexistence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

VERSION = "erdos366-extend-v2"
MAX_EXACT_N = (1 << 64) - 1
MR64_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)


def integer_nth_root(n: int, k: int) -> int:
    if n < 0 or k <= 0:
        raise ValueError("need n >= 0 and k > 0")
    if n < 2:
        return n
    lo, hi = 0, 1
    while pow(hi, k) <= n:
        hi <<= 1
    while lo + 1 < hi:
        mid = (lo + hi) >> 1
        if pow(mid, k) <= n:
            lo = mid
        else:
            hi = mid
    return lo


def primes_upto(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    p = 2
    while p * p <= limit:
        if sieve[p]:
            start = p * p
            sieve[start : limit + 1 : p] = b"\x00" * (((limit - start) // p) + 1)
        p += 1
    return [i for i in range(2, limit + 1) if sieve[i]]


def is_prime64(n: int) -> bool:
    """Deterministic primality for 0 <= n < 2**64."""
    if n < 2:
        return False
    if n > MAX_EXACT_N:
        raise ValueError("is_prime64 supports only n < 2**64")
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in MR64_BASES:
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _trial_factor(n: int) -> int:
    """Exact nontrivial factor fallback. Called only if Brent stalls."""
    if n % 2 == 0:
        return 2
    p = 3
    while p * p <= n:
        if n % p == 0:
            return p
        p += 2
    return n


def brent_factor(n: int) -> int:
    """Deterministic-seed Pollard-Brent factor search with exact fallback."""
    if n % 2 == 0:
        return 2
    if n % 3 == 0:
        return 3
    if is_prime64(n):
        return n

    # Fixed seeds make executions reproducible.  Any failure is not trusted:
    # exact trial division below remains the final fallback.
    for c in (1, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31):
        for seed in (2, 3, 5, 7, 11):
            y = seed % n
            r = 1
            g = 1
            x = y
            ys = y
            while g == 1 and r <= (1 << 20):
                x = y
                for _ in range(r):
                    y = (y * y + c) % n
                k = 0
                while k < r and g == 1:
                    ys = y
                    q = 1
                    span = min(128, r - k)
                    for _ in range(span):
                        y = (y * y + c) % n
                        q = (q * abs(x - y)) % n
                    g = math.gcd(q, n)
                    k += span
                r <<= 1
            if g == n:
                g = 1
                while g == 1:
                    ys = (ys * ys + c) % n
                    g = math.gcd(abs(x - ys), n)
            if 1 < g < n:
                return g
    return _trial_factor(n)


def factor_counts(n: int) -> tuple[tuple[int, int], ...]:
    """Return exact sorted prime factorization for 1 <= n < 2**64."""
    if n <= 0 or n > MAX_EXACT_N:
        raise ValueError("factor_counts supports 1 <= n < 2**64")
    if n == 1:
        return ()
    factors: list[int] = []
    stack = [n]
    while stack:
        x = stack.pop()
        if x == 1:
            continue
        if is_prime64(x):
            factors.append(x)
            continue
        r = math.isqrt(x)
        if r * r == x:
            stack.extend((r, r))
            continue
        d = brent_factor(x)
        if d in (1, x):
            # This should occur only when fallback establishes primality, but
            # keep the branch exact and explicit.
            if is_prime64(x):
                factors.append(x)
                continue
            raise RuntimeError(f"failed to split composite {x}")
        stack.extend((d, x // d))
    counts = Counter(factors)
    return tuple(sorted(counts.items()))


def factors_product(fs: Iterable[tuple[int, int]]) -> int:
    out = 1
    for p, e in fs:
        out *= pow(p, e)
    return out


def factors_text(fs: Iterable[tuple[int, int]]) -> str:
    return "*".join(f"{p}^{e}" for p, e in fs) or "1"


def enumerate_k_full_values(bound: int, k: int) -> list[int]:
    """Enumerate each k-full integer in [2,bound] exactly once."""
    if bound < 2:
        return []
    primes = primes_upto(integer_nth_root(bound, k))
    out: list[int] = []

    def rec(start: int, current: int) -> None:
        for i in range(start, len(primes)):
            p = primes[i]
            pk = pow(p, k)
            if current * pk > bound:
                break
            value = current * pk
            while value <= bound:
                out.append(value)
                rec(i + 1, value)
                value *= p

    rec(0, 1)
    out.sort()
    return out


@dataclass(frozen=True)
class PowerfulCheck:
    is_powerful: bool
    rejecting_prime: int | None
    factors: tuple[tuple[int, int], ...]
    path: str


def check_powerful(n: int, trial_primes: Sequence[int]) -> PowerfulCheck:
    """Exactly decide whether n is 2-full for 1 <= n < 2**64.

    The fast path is the residue certificate p || n.  Any unresolved remainder
    is then decided by deterministic primality / exact factorization.
    """
    if n <= 0 or n > MAX_EXACT_N:
        raise ValueError("check_powerful supports 1 <= n < 2**64")
    if n == 1:
        return PowerfulCheck(True, None, (), "unit")

    x = n
    known: list[tuple[int, int]] = []
    for p in trial_primes:
        if x % p:
            continue
        # This residue condition is already a complete rejection certificate.
        if x % (p * p):
            return PowerfulCheck(False, p, (), "small_residue")
        e = 0
        while x % p == 0:
            x //= p
            e += 1
        if e < 2:
            raise AssertionError("residue/factor inconsistency")
        known.append((p, e))
        if x == 1:
            return PowerfulCheck(True, None, tuple(known), "small_factors")

    if x == 1:
        return PowerfulCheck(True, None, tuple(known), "small_factors")
    if is_prime64(x):
        return PowerfulCheck(False, x, (), "prime_remainder")

    root = math.isqrt(x)
    if root * root == x:
        # A perfect square has only even residual prime exponents.  Factor it
        # only on this (rare) acceptance path so the witness is complete.
        tail = factor_counts(x)
        full = tuple(sorted((*known, *tail)))
        if factors_product(full) != n:
            raise AssertionError("accepted factorization does not reconstruct n")
        return PowerfulCheck(True, None, full, "square_remainder")

    tail = factor_counts(x)
    for p, e in tail:
        if e == 1:
            return PowerfulCheck(False, p, (), "factored_remainder")
        if e < 1:
            raise AssertionError("invalid factor exponent")
    full = tuple(sorted((*known, *tail)))
    if factors_product(full) != n:
        raise AssertionError("accepted factorization does not reconstruct n")
    return PowerfulCheck(True, None, full, "factored_powerful")


def _witness_factorization(m: int) -> tuple[tuple[int, int], ...]:
    fs = factor_counts(m)
    if factors_product(fs) != m or any(e < 3 for _, e in fs):
        raise AssertionError("enumerated successor is not 3-full")
    return fs


def search(
    bound: int,
    *,
    shard_index: int = 0,
    shard_count: int = 1,
    trial_prime_limit: int = 997,
) -> dict:
    if bound < 2 or bound > MAX_EXACT_N:
        raise ValueError(f"bound must be in [2,{MAX_EXACT_N}]")
    if shard_count <= 0 or not (0 <= shard_index < shard_count):
        raise ValueError("require shard_count > 0 and 0 <= shard_index < shard_count")
    trial_primes = primes_upto(trial_prime_limit)
    successors = enumerate_k_full_values(bound, 3)
    h = hashlib.sha256()
    witnesses: list[dict] = []
    path_counts: Counter[str] = Counter()
    selected = 0

    for ordinal, m in enumerate(successors):
        if ordinal % shard_count != shard_index:
            continue
        selected += 1
        n = m - 1
        chk = check_powerful(n, trial_primes)
        path_counts[chk.path] += 1
        if chk.is_powerful:
            m_factors = _witness_factorization(m)
            witness = {
                "ordinal": ordinal,
                "n": n,
                "n_factors": list(chk.factors),
                "n_plus_1": m,
                "n_plus_1_factors": list(m_factors),
            }
            witnesses.append(witness)
            record = (
                f"W|{ordinal}|{n}|{factors_text(chk.factors)}|"
                f"{m}|{factors_text(m_factors)}\n"
            )
        else:
            p = chk.rejecting_prime
            if p is None or n % p != 0 or n % (p * p) == 0:
                raise AssertionError("invalid p||n rejection certificate")
            record = f"R|{ordinal}|{n}|{p}^1|{m}\n"
        h.update(record.encode("ascii"))

    return {
        "schema_version": 2,
        "engine": VERSION,
        "target": "exists n>0: Nat.Full 2 n and Nat.Full 3 (n+1)",
        "successor_bound_inclusive": bound,
        "global_3full_successors": len(successors),
        "shard_index": shard_index,
        "shard_count": shard_count,
        "selected_3full_successors": selected,
        "trial_prime_limit": trial_prime_limit,
        "classification_counts": dict(sorted(path_counts.items())),
        "witness_count": len(witnesses),
        "witnesses": witnesses,
        "record_digest_sha256": h.hexdigest(),
        "interpretation": (
            "Exhaustive only for this deterministic shard of n+1 <= "
            "successor_bound_inclusive; zero witnesses is not a global "
            "nonexistence proof. Union all shard indexes for the same "
            "bound/count/engine to cover the full bounded search."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bound", type=int, default=1_000_000_000_000_000)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--trial-prime-limit", type=int, default=997)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = search(
        args.bound,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        trial_prime_limit=args.trial_prime_limit,
    )
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
