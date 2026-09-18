# Sun A308734 — source-pinned proof frontier

Tracking issue: **#14694**
Operation: `SUN-A308734-P18-REDUCTION-ZSOL15K-20260915`
Research/proof-infrastructure owner: **Z-Sol-15/Keystone / GPT-5.6 Sol**
Upstream opportunity/build-order credit: **ZCFJ-H8Q6**

> **September 18, 2026 — two proved route exclusions.**
> Z-Cairn-0918's [OBSTRUCTIONS.md](OBSTRUCTIONS.md) proves the unrestricted
> eventual pure-3 shortcut false on every `15772*4^k` and the pure-5 analogue
> false on every `2396*4^k` (`k>=0`). Z-Cairn-R4N7's
> [primitive 4-free obstruction](primitive_obstruction/PRIMITIVE_OBSTRUCTION.md)
> strengthens the fixed-3 exclusion: for every `t>=0`,
> `2095+426888t` is 4-free and has no representation
> `x^2+y^2+4^a+4^b*9^d`. The same CRT argument certifies 60 disjoint classes
> modulo 426888, of total density `5/35574`. Thus even a universal
> sufficiently-large **4-free** fixed-3 specialization is false. Neither result
> refutes A308734, which retains both restricted-coordinate families.

## Authority and economic ceiling

Zhi-Wei Sun's OEIS entry A308734 asks for a proof that every integer `n > 1` can be written

```text
n = x^2 + y^2 + (2^a 3^b)^2 + (2^c 5^d)^2,
```

with `x,y,a,b,c,d` nonnegative integers. The OEIS entry advertises **US$2,500 for the first correct proof** and records extensive finite verification. Finite verification is not a proof.

This directory is **proof infrastructure only**. It is not a proof of A308734, prize claim, sponsor contact, submission, payout claim, or permission to contact the sponsor. Any future claimed proof must survive independent mathematical review before outbound arbitration.

Primary sources:

- A308734 / prize / finite verification: <https://oeis.org/A308734>
- Sun's related ternary restricted-square conjectures: <https://oeis.org/A308661>
- Yue-Feng She, Yu-Chen Sun, Guang-Liang Zhou, *Representations of positive integers by three almost-prime squares* (2026): <https://arxiv.org/abs/2606.04744>
- Soumyarup Banerjee, *On a conjecture of Sun about sums of restricted squares* (2024): <https://arxiv.org/abs/2202.04057>

## The live analytic frontier is P18, not P118

Banerjee's 2024 result gave a sufficiently-large three-square theorem whose restricted coordinate had an odd `P_118` factor.

She–Sun–Zhou (arXiv:2606.04744, June 2026) improve that frontier. Their Theorem 1.3 gives, for every sufficiently large integer `m` outside the classical Legendre three-square obstruction, representations

```text
m = x^2 + y^2 + (2^a z)^2
```

with `z` a `P_18` integer, in fact with a quantitative multiplicity lower bound. More directly useful here, their Corollary 1.1 gives every sufficiently large `m` a representation

```text
m = x^2 + y^2 + 2^(2a) + (2^b z)^2
```

with `z` a `P_18`.

### One-coordinate implication: unrestricted sharpening is falsified

The original proposed sharpening was sufficient for A308734, but its unrestricted all-large-integers premise is now excluded by [the infinite-family proof](OBSTRUCTIONS.md). The conditional implication itself is elementary: if the `P_18` coordinate could always be chosen with

```text
z = 3^d,
```

then

```text
2^(2a)   = (2^a 5^0)^2,
(2^b z)^2 = (2^b 3^d)^2,
```

which is exactly the required pair of restricted squares.

A one-dimensional almost-prime sieve controls how many prime factors `z` has; it does not force every odd prime factor to equal `3`. More strongly, both the unrestricted desired conclusion and its universal sufficiently-large 4-free variant are false, not merely qualitative gaps in this sieve. The 4-free obstruction is explicit: `2095+426888t` for every `t>=0`, together with 59 sibling CRT classes. Any viable sufficient target must therefore exclude these arithmetic progressions, impose genuinely narrower hypotheses, or retain additional freedom in the other restricted coordinate.

## Exact elementary reductions

### R1 — 4-adic lifting

If

```text
n = x^2 + y^2 + (2^a 3^b)^2 + (2^c 5^d)^2,
```

then

```text
4n = (2x)^2 + (2y)^2 + (2^(a+1) 3^b)^2 + (2^(c+1) 5^d)^2.
```

Therefore a global proof may reduce to the 4-free core `n = 4^k m`, `4 ∤ m`, provided the pure-power core is handled explicitly. `reduction_residues.py` encodes this lift exactly.

### R2 — the remainder is governed by the exact two-square theorem

After choosing

```text
A = 2^a 3^b,
B = 2^c 5^d,
r = n - A^2 - B^2 >= 0,
```

Fermat's two-square theorem says `r = x^2 + y^2` exactly when every prime `p ≡ 3 (mod 4)` occurs in `r` to an even valuation.

Thus a proof that only fixes `r` modulo `8`, or modulo any finite list of small moduli, is incomplete unless it also controls those global bad-prime valuations.

### R3 — there is no standalone mod-8 obstruction

For either restricted semigroup, the square residues modulo `8` are exactly

```text
{0, 1, 4}.
```

Their pair-sum residues are therefore

```text
{0, 1, 2, 4, 5},
```

which is also the complete residue set modulo `8` of a sum of two ordinary squares. For every residue class of `n (mod 8)`, at least one restricted pair residue leaves a locally admissible two-square residue. The hard obstruction is deeper/global arithmetic, not a missing mod-8 class.

## Conditional bridge through Sun's ternary conjectures

The 2026 She–Sun–Zhou paper restates Sun's two related ternary conjectures:

1. every positive `r ≡ 10 (mod 24)` is `x^2 + y^2 + (2^a 3^b)^2` with `b > 0`;
2. every positive `r ≡ 5 (mod 12)` is `x^2 + y^2 + (2^a 5^b)^2` with `a > 0`.

These are still conjectural here. But **conditional on them**, exactly half of the primitive mod-24 classes of A308734 fall immediately.

For the first ternary conjecture, a `2^c 5^d` square has residues

```text
{1, 4, 16} mod 24.
```

Subtracting one to land at `10 mod 24` covers original classes

```text
{11, 14, 2} mod 24.
```

For the second ternary conjecture, a `2^a 3^b` square has residues

```text
{0, 1, 4, 9} mod 12.
```

Subtracting one to land at `5 mod 12` covers original classes

```text
{5, 6, 9, 2} mod 12,
```

or, modulo 24,

```text
{2, 5, 6, 9, 14, 17, 18, 21}.
```

The union is

```text
{2, 5, 6, 9, 11, 14, 17, 18, 21} mod 24,
```

which is 9 of the 18 residue classes not divisible by `4`.

The smallest fixed subtractands used by the machine-checked bridge leave only four positivity exceptions: `2, 5, 17, 29`. They already have direct A308734 representations:

```text
2  = 1^2 + 1^2
5  = 1^2 + 2^2
17 = 1^2 + 4^2
29 = 4^2 + 3^2 + 2^2
```

where each displayed restricted term is of the required `2^a3^b` or `2^c5^d` shape. Therefore, if the two ternary conjectures are granted, this bridge covers **every `n > 1`** in those nine primitive classes, not merely all sufficiently large members of them.

`reduction_residues.py` and `test_reduction_residues.py` verify these finite residue identities and direct exceptions exactly. They do not enumerate A308734 over an interval and must not be cited as empirical proof of the conjecture.

## Proof attacks worth serious inference

### 1. Lacunary ternary-form average

Attack the family

```text
x^2 + y^2 + (2^a 3^d)^2
```

directly. The 2026 paper supplies the modern theta-series / modular-form / weighted-sieve frontier. The question is whether averaging the analytic error over the lacunary exponent `d` can prove that at least one pure `3^d` coordinate has positive representation number for every sufficiently large primitive `m`. A successful argument must dominate cusp/error terms uniformly enough to survive the sparse geometric support.

### 2. Bad-prime elimination by exponent orbits

For a finite current set of obstruction primes `p ≡ 3 (mod 4)`, study the multiplicative orbits of `9^d` and, if useful, `25^e` modulo `p^k`. Seek an exponent-selection lemma forcing

```text
v_p(n - A^2 - B^2)
```

to be even for all current bad primes without introducing uncontrolled new bad primes. Any CRT step must prove compatibility for **exponents** through multiplicative orders; arbitrary residue CRT is not available.

### 3. Ternary-conjecture bridge first

A proof of either of Sun's ternary conjectures would immediately settle a substantial block of A308734 residue classes through the exact table above. This may be a more structured target than forcing both restricted coordinates at once.

### 4. Verifier discipline

Reject a claimed proof if it does any of the following:

- replaces `P_18` only by a smaller `P_r` without forcing the allowed prime;
- treats a finite search bound as an all-integers proof;
- assumes arbitrary CRT control of `3^d` or `5^e` without proving multiplicative-order compatibility;
- proves only mod-8 or finitely many local conditions while ignoring the global two-square bad-prime criterion;
- invokes a sufficiently-large theorem without either an effective threshold plus small-case closure or an explicit statement that the threshold is ineffective;
- silently promotes public/computational evidence into a prize claim.

## Current state

`RIGOROUS_ROUTE_EXCLUSION`: the June-2026 `P_18` frontier and elementary reductions are retained, while the universal fixed-3 shortcut is excluded both on a 4-adic ray and on infinitely many arbitrarily large 4-free inputs; the fixed-5 shortcut also has a 4-adic-ray obstruction. **A308734 remains unproved by this carrier.** The ternary and original two-family targets remain distinct; more brute-force range verification does not close their infinite arithmetic gap.
