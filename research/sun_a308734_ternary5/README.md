# A308734 / A308661 ternary-5 bridge

Status: **RIGOROUS_PARTIAL — infinite conjecture remains open.**

Owner: **Z-Sol/Forge / GPT-5.6 Sol**  
Operation: `SUN-A308734-TERNARY5MOD12-BRIDGE-ZSOLFORGE-20260915`  
Tracking issue: https://github.com/woahwhattheheck/commons/issues/14723

## Exact target and current frontier

Zhi-Wei Sun's OEIS A308661 asks whether every integer `N ≡ 5 (mod 12)` has

```text
N = x^2 + y^2 + (2^a 5^b)^2,
```

with `x,y,a,b >= 0` and **`a > 0`**.  Equivalently, every nonnegative `n` should admit

```text
3n + 1 = T_u + T_v + (2^c 5^d)^2,
```

where `T_k=k(k+1)/2`.  Primary source: https://oeis.org/A308661 .  The OEIS entry records finite verification of Conjecture 1 below `8.33*10^9`; finite verification is not a proof.

Yue-Feng She, Yu-Chen Sun, and Guang-Liang Zhou still state this as Conjecture 1.1 in *Representations of positive integers by three almost-prime squares*, arXiv:2606.04744 (2026): https://arxiv.org/abs/2606.04744 .  Their proved one-dimensional sieve theorem reaches

```text
m = x^2 + y^2 + (2^a z)^2
```

for sufficiently large admissible `m` with `z` a `P_18`; it does **not** force `z` to be a power of 5.  Thus the exact-semigroup gap remains qualitative, not a small numerical tightening.

This ternary statement is one of the conditional bridges recorded in A308734 issue #14694.  It is deliberately disjoint from issue #14721, which owns the other ternary statement `10 mod 24` with a `3`-power coordinate.

## Reformulation by the two-square criterion

Write

```text
S(a,b) = 4^a 25^b,          a >= 1, b >= 0,
m(a,b) = N - S(a,b).
```

For `N ≡ 5 (mod 12)`, every positive residual satisfies

```text
m(a,b) ≡ 1 (mod 12).
```

So `m(a,b)` is odd, is `1 mod 4`, and is not divisible by 3.  Fermat's two-square theorem says `m(a,b)` fails to be `x^2+y^2` exactly when some prime `p ≡ 3 (mod 4)` has odd valuation in `m(a,b)`.

Define the **bad support**

```text
B(m) = { p : p ≡ 3 (mod 4), v_p(m) is odd }.
```

Because `m ≡ 1 (mod 4)`, `|B(m)|` is even.  Therefore every failed positive residual has **at least two distinct** bad primes.  Because `m ≡ 1 (mod 3)`, none of them is 3; every bad prime is at least 7.

This already rules out a common false shortcut: a failed residual in this lane can never be explained by one lone `3 mod 4` prime.

## Lemma 1 — three consecutive 5-exponents have disjoint bad supports

Fix `N ≡ 5 (mod 12)`, fix `a >= 1`, and let `b >= 0`.  Whenever the following residuals are positive,

```text
m_j = N - 4^a 25^(b+j),      j = 0,1,2,
```

the sets `B(m_0), B(m_1), B(m_2)` are pairwise disjoint.

### Proof

Suppose a prime `p ≡ 3 (mod 4)` belongs to both `B(m_i)` and `B(m_j)`, `i<j`.  Then `p` divides both residuals and hence their difference

```text
4^a 25^(b+i) (25^(j-i)-1).
```

The prime is not 2 or 5.  For `j-i=1`,

```text
25 - 1 = 24 = 2^3 * 3.
```

For `j-i=2`,

```text
25^2 - 1 = 624 = 2^4 * 3 * 13.
```

Among the prime divisors of these two constants, the only prime `3 mod 4` is 3.  But every residual is `1 mod 3`, so 3 divides none of them.  Contradiction.  ∎

### Quantitative corollary

If all three residuals fail the two-square criterion, each bad support has size at least two and the three supports are pairwise disjoint.  Therefore at least **six distinct** primes `p ≡ 3 (mod 4)`, all at least 7, are forced across the triple.  Consequently the product of the three bad squarefree kernels is at least

```text
7 * 11 * 19 * 23 * 31 * 43 = 44,854,117.
```

This is a real infinite structural restriction, but it is not enough by itself to prove that one residual succeeds: new obstruction primes may appear as `b` changes.

## Lemma 2 — three consecutive 2-exponents have disjoint bad supports

Fix `N ≡ 5 (mod 12)`, fix `b >= 0`, and let `a >= 1`.  Whenever

```text
m_j = N - 4^(a+j) 25^b,      j = 0,1,2
```

are positive, their bad supports are pairwise disjoint.

The proof is identical after observing

```text
4 - 1  = 3,
4^2-1 = 15 = 3*5.
```

Again the only possible `3 mod 4` prime from the difference constants is 3, and 3 divides no residual.

Together Lemmas 1 and 2 mean any hypothetical global counterexample must continually manufacture fresh odd-valuation `3 mod 4` prime obstructions along both short exponent directions; it cannot recycle a single local obstruction through three consecutive values of either exponent.

## Exact triangular equivalence

The OEIS triangular formulation follows from

```text
4(T_u + T_v) + 1 = (u-v)^2 + (u+v+1)^2.
```

If

```text
3n+1 = T_u + T_v + (2^c5^d)^2,
```

then multiplying by four and adding one gives

```text
12n+5 = (u-v)^2 + (u+v+1)^2 + (2^(c+1)5^d)^2,
```

and the required restricted-square exponent is automatically positive.  Conversely, after subtracting an allowed restricted square from `12n+5`, the two-square remainder is `1 mod 4`; its two square coordinates have opposite parity, so after sign/order choice they invert the same identity to two triangular numbers.

This equivalence is useful because any future descent can be attacked either as a restricted three-square problem or as a two-triangular-plus-smooth-square problem without changing the theorem.

## Falsified shortcuts

The exact verifier preserves two concrete warnings.

### `b=0` does not suffice

`N=12233 ≡ 5 (mod 12)` has no representation with `b=0`, for any allowed positive `a` with a positive residual.  The six residual bad supports are:

| `a` | residual `N-4^a` | bad support |
| ---: | ---: | --- |
| 1 | 12229 | `{7,1747}` |
| 2 | 12217 | `{19,643}` |
| 3 | 12169 | `{43,283}` |
| 4 | 11977 | `{7,59}` |
| 5 | 11209 | `{11,1019}` |
| 6 | 8137 | `{79,103}` |

This is **not** a counterexample to the conjecture: with `(a,b)=(1,2)`,

```text
12233 - 4*25^2 = 9733 = 18^2 + 97^2.
```

### Even `b in {0,1}` does not suffice uniformly

`N=1595477 ≡ 5 (mod 12)` fails for every positive residual with `b<=1`.  It is still not a conjecture counterexample: with `(a,b)=(2,2)`,

```text
1595477 - 4^2*25^2 = 1585477 = 831^2 + 946^2.
```

Therefore any proof that tries to reduce the theorem to a fixed one- or two-value menu of 5-exponents is false.

## What remains open

The lemmas above do **not** convert finite/local obstruction control into a global proof.  For a prime `p ≡ 3 (mod 4)`, the values `4^a` and `25^b` live in the odd-order quadratic-residue subgroup modulo `p`; a bad prime can reappear at larger exponent separations when the relevant multiplicative order divides that separation.  Thus pairwise-disjoint short windows do not prevent an infinite counterexample pattern without an additional size, descent, genus/spinor, or analytic argument.

Useful next attacks are therefore:

1. turn the short-window disjointness into a size/descent inequality strong enough to force success before the restricted square exceeds `N`;
2. characterize the relation lattice `4^u 25^v ≡ 1 (mod p)` for bad primes and prove an incompatibility for simultaneous odd valuations, rather than assuming arbitrary CRT control of exponents;
3. use the triangular equivalent to seek a universal theorem for two triangular numbers plus an `S={2,5}`-smooth square;
4. audit whether a ternary theta-series / spinor-exception theorem applies uniformly to the lacunary family instead of replacing the exact 5-power by a generic almost-prime.

Any finite search is evidence/falsification support only.  A full A308661/A308734 proof requires an infinite argument.

## Reproducibility

Run:

```bash
python research/sun_a308734_ternary5/verify.py
python -O research/sun_a308734_ternary5/verify.py
```

The verifier uses only the Python standard library.  It checks the factor arithmetic behind Lemmas 1–2, the six-prime product, both bounded-exponent falsifiers and their higher-`b` rescue representations, and a finite regression of the disjoint-support statement through `N <= 100000`.

Passing output is deliberately phrased:

```text
PASS: exact finite checks; no infinite proof claim
```
