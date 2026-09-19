# OEIS A304081 exact search

This directory contains a dependency-free finite verifier/search tool for
[OEIS A304081](https://oeis.org/A304081).

The sequence counts representations

`n = p + 2^k + (1 + (n mod 2)) * 5^m`

where `p` is an odd prime and the non-prime offset is squarefree. OEIS states
the conjecture `a(n) > 0` for every `n > 7`, reports verification through
`2*10^10`, and records a $2,500 prize for the first proof and $250 for the
first explicit counterexample.

## Build

```bash
g++ -O3 -std=c++20 -Wall -Wextra -pedantic a304081_search.cpp -o a304081_search
./a304081_search self-test
```

## Modes

```bash
./a304081_search count N
./a304081_search scan LO HI
./a304081_search random TRIALS LO HI SEED [SKIP]
./a304081_search sample TRIALS LO HI SEED [SKIP]
```

- `count` enumerates every admissible `(k,m)` representation for one `n`.
- `scan` exhaustively counts every integer in an inclusive interval.
- `random` uses deterministic SplitMix64 samples (with replacement) and stops
  at the first exact zero; it short-circuits after the first representation.
- `sample` computes full representation counts for deterministic samples and
  reports a count histogram.
- `SKIP` advances to a disjoint deterministic suffix of the same SplitMix64
  stream without replaying the prefix.

Primality is deterministic Miller-Rabin for unsigned 64-bit integers. The
squarefree offset table is exact: it sieves primes through the square root of
the maximum search value and rejects any offset divisible by a prime square.

The current implementation intentionally caps the squarefree sieve root at
20,000,000 to keep accidental searches from consuming unbounded memory. That
supports maximum `n` values up to roughly `4e14`.

## Correctness note: k = 0

The OEIS definition allows nonnegative `k`, but `k=0` cannot yield an odd
prime `p`:

- if `n` is even, `1 + 5^m` is even, so `p = n - offset` is even;
- if `n` is odd, `1 + 2*5^m` is odd, so `p` is again even.

Since the required prime is odd, the implementation starts at `k=1`.
The self-test checks OEIS examples including `a(6)=1`, `a(91)=1`, and
`a(6447154629)=2`.

## Research boundary

Finite searches are evidence only. A null search does not prove the conjecture.
A candidate counterexample is valid only if `count N` exhaustively returns
zero and an independent implementation/reviewer confirms the arithmetic.
