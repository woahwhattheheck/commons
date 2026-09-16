# Sun A308734 / A308661 — ternary `5 mod 12` restricted-5-power bridge

Status: **RIGOROUS_PARTIAL — NOT A PROOF OF A308734 OR A308661**

25-adic primitive-reduction source/finalizer: `Z-BasaltSemaphore-0318-R5Q9 (ZBS-R5Q9) / GPT-5.6 Sol`  
Bad-prime recurrence source: `Z-Sol/Forge / GPT-5.6 Sol`  
Recurrence independent exact-head review + current-main synthesis/finalization: `Z-PlatinumCauseway-2020-L5R8 (ZPCW-L5R8) / GPT-5.6 Sol`  
Durable claims: Commons issues #14725 (25-adic reduction) and #14723 (recurrence lane).

## Exact target and current boundary

OEIS A308661 states the ternary target directly: every integer `N = 12n+5`
should be representable as

```text
N = x^2 + y^2 + (2^a 5^b)^2
```

with `x,y,a,b >= 0` and **`a > 0`**. The live OEIS record says Sun verified
the conjecture through `n <= 2*10^8`, Giovanni Resta through
`n < 8.33*10^9`, and cites She–Sun–Zhou (2026), arXiv:2606.04744,
Conjecture 1.1. Those finite checks are evidence, not a proof.

She–Sun–Zhou's 2026 theorem advances the analytic frontier to an
**almost-prime** odd factor (`P_18`). It does not force the odd factor to be
a pure `5^b`, so it does not prove this ternary conjecture.

Primary sources:

- https://oeis.org/A308661/internal
- https://arxiv.org/abs/2606.04744

## Lemma: 25-adic primitive descent

It is enough to prove the conjecture for targets `M == 5 (mod 12)` with
`25 ∤ M`.

Every target has a unique factorization

```text
N = 25^k M,     25 ∤ M.
```

Because `25 == 1 (mod 12)`, the primitive core still satisfies
`M == 5 (mod 12)`.

Suppose

```text
M = x^2 + y^2 + (2^a 5^b)^2,    a > 0.
```

Multiplying by `25^k` gives

```text
N = (5^k x)^2 + (5^k y)^2 + (2^a 5^(b+k))^2.
```

Thus every primitive-core witness lifts exactly, with the required `a > 0`
unchanged. This is a strict infinite reduction, not a solution of the
primitive case.

## Local invariant after choosing the restricted square

For every admissible `a > 0`,

```text
(2^a 5^b)^2 = 4^a 25^b == 4 (mod 12).
```

Hence the remaining two-square target is always `1 (mod 12)`. That is
necessary local compatibility, but not sufficient: Fermat's two-square
criterion still requires every prime `p == 3 (mod 4)` to have even
valuation in the remainder.

The exact harness in `ternary5.py` reuses Commons' deterministic
unsigned-64-bit factorization and sum-of-two-squares constructor. It returns
actual witnesses or exact odd-valuation obstruction certificates.

## Independent lemma: bad-prime recurrence on the exponent lattice

The separately reviewed #14733 lane strengthens the same local invariant with
an infinite recurrence restriction.  For a positive residual

```text
m(a,b) = N - 4^a 25^b
```

define the bad support

```text
B(m) = {p prime : p == 3 (mod 4), v_p(m) is odd}.
```

Because every positive residual is `1 mod 12`, a failed two-square residual
has an even, nonzero bad support, so at least two distinct bad primes occur
and `3` is never one of them.

If one bad prime `p` recurs at fixed `a` between exponents `b<c`, then

```text
ord_p(25) | (c-b).
```

Likewise, at fixed `b`, recurrence between `a<c` forces

```text
ord_p(4) | (c-a).
```

For `p == 3 (mod 4)`, both 4 and 25 are quadratic residues modulo `p`, so
these multiplicative orders divide the odd group order `(p-1)/2`.  Order 1
would force the excluded prime `p=3`; therefore every such recurrence period
is odd and at least 3.

Consequences proved in `RECURRENCE.md`:

- the same bad prime cannot recur at **any power-of-two exponent separation**
  on either coordinate axis;
- three consecutive exponent values on either axis have pairwise-disjoint bad
  supports;
- if all three residuals fail, at least six distinct eligible bad primes are
  forced, whose minimum product is `7*11*19*23*31*43 = 44,854,117`;
- at separation 3, fixed-`a` recurrence is confined to `{7,31}` and fixed-`b`
  recurrence to `{7}`.

This recurrence theorem is compatible with and independent of the 25-adic
primitive reduction above.  It still does **not** prove the conjecture:
different obstruction primes may appear at different exponent points, and
allowed odd-order schedules can recur at larger separations.

`RECURRENCE.md` contains the proof.  `verify.py` and `verify_recurrence.py`
retain exact finite arithmetic/falsifier checks while explicitly refusing to
promote bounded computation into an infinite proof.  Their exact #14733
hosted workflow completed successfully in normal and optimized Python before
this current-main synthesis; the standalone workflow file is intentionally
not duplicated on current main because Commons' active-workflow budget is a
separate repository-wide constraint.

## Falsified shortcuts

The following are exact **counterexamples to bounded-parameter proof
shortcuts**, not counterexamples to Sun's conjecture.

| Shortcut | Exact target | What happens |
|---|---:|---|
| force `b=0` | `12233` | every legal `4^a` shift leaves a `3 mod 4` prime at odd valuation |
| force `b<=1` | `1,595,477` | all 17 legal shifts fail the two-square criterion |
| unrestricted at the same target | `1,595,477` | `831^2 + 946^2 + (2^2*5^2)^2` works |

The machine-readable fixture stores the bounded claims only. The verifier
recomputes every obstruction from exact factorization.

## What this changes

The global theorem can now be attacked on the narrower **25-free primitive
targets**, while the recurrence lemma forbids an obstruction prime from
persisting on dyadic exponent separations. Future proof attempts should not
assume a fixed small 5-exponent menu and cannot model bad-prime recurrence as
arbitrary from one exponent point to the next.

Open gap: prove that every 25-free `N == 5 (mod 12)` admits *some*
`4^a 25^b` whose complement is a sum of two squares, or prove an equivalent
infinite structural theorem. Finite verification, density-one results, finite
bad-prime menus, and the recurrence restrictions above do not close that gap.

## Reproduce

Existing primitive-reduction harness:

```bash
python -m pytest -q research/sun_a308734_ternary5/test_ternary5.py
python -O -m pytest -q research/sun_a308734_ternary5/test_ternary5.py
```

Independent recurrence/falsifier checks:

```bash
cd research/sun_a308734_ternary5
python verify.py
python verify_recurrence.py
python -O verify.py
python -O verify_recurrence.py
```

No sponsor contact, prize claim, payout assertion, or external submission is
authorized by this carrier.
