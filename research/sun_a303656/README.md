# Sun A303656 exact research harness

Zhi-Wei Sun's OEIS [A303656](https://oeis.org/A303656) conjectures that every
integer `n > 1` has

```text
n = a² + b² + 3ᶜ + 5ᵈ
```

for nonnegative integers `a,b,c,d`. The current OEIS record advertises a
**$3,500 first-proof prize** and records verification through `2.4×10¹¹`.
DeepMind's `formal-conjectures` repository carries the corresponding open Lean
statement at `FormalConjectures/OEIS/303656.lean`.

This directory is a proof-search instrument. **It is not a proof, a
counterexample, a submission, or a prize claim.** It gives future workers exact,
reproducible arithmetic instead of disconnected exploratory scripts.

## What is exact

`oracle.py` supplies a deterministic unsigned-64-bit pipeline:

- deterministic Miller-Rabin primality testing on `[0,2⁶⁴)`;
- deterministic Pollard-Brent factorization;
- the sum-of-two-squares criterion (every `p ≡ 3 mod 4` has even valuation);
- Cornacchia construction for primes `p ≡ 1 mod 4`;
- Gaussian multiplication to construct `a,b`, not merely decide existence;
- lexicographic search over `(c,d)` with exact witness reconstruction.

Every returned witness is checked by integer equality. Absence of a witness from
a finite search is never treated as a counterexample to the conjecture.

`modular.py` uses cyclic bitsets to compute, without sampling, the full residue
set

```text
{x²+y²+3ᶜ+5ᵈ mod m : x,y,c,d ≥ 0}
```

for a requested modulus. It also runs a deliberately limited CRT-cover
experiment: for each prime `p ≡ 3 mod 4`, select one residue `n mod p` and count
which exponent pairs satisfy `p | n-3ᶜ-5ᵈ`. Divisibility alone does **not** prove
odd valuation, and uncovered exponent pairs prevent a counterexample
certificate. The tool reports both limitations explicitly.

## Current negative evidence

The deterministic receipt in `evidence/negative_evidence_v1.json` records:

- no missing residue for any modulus `2..500`;
- no missing residue for every `2,3,5,7,11`-smooth modulus at most `30,000`;
  together these form **1,151 exact modulus checks**;
- a one-residue-per-prime greedy cover on the `160×110` exponent grid using all
  **338** primes `p ≡ 3 mod 4`, `7 ≤ p < 5000`, which covers `13,226` of `17,600`
  pairs and leaves **4,374** uncovered;
- 250 seeded exact witnesses near each of `10⁹`, `10¹²`, `10¹⁵`, and `10¹⁸`.

Interpretation: the conjecture survives these tests, and neither a small local
obstruction nor this simple finite congruence-cover recipe closes the problem.
That is useful route-pruning, not theorem proof.

## Reproduce

From the repository root:

```bash
python -m compileall -q research/sun_a303656
python -m unittest -q research.sun_a303656.test_oracle
python -O -m unittest -q research.sun_a303656.test_oracle
python -m research.sun_a303656.generate_evidence
sha256sum research/sun_a303656/evidence/negative_evidence_v1.json
```

Find and verify one witness:

```bash
python -m research.sun_a303656.oracle 1000000000000000000
```

## Productive next attacks

1. Replace the ascending-prime greedy cover with an exact multiple-choice
   maximum-coverage or SAT model, including `p²` constraints that force odd
   valuation instead of mere divisibility.
2. Search for a finite covering on exponent *period classes*, not a bounded
   rectangle; only then can CRT produce a global candidate.
3. Seek a descent or induction identity that preserves exactly two unrestricted
   squares and one power of each base. Finite verification cannot substitute for
   this uniform step.
4. Test any claimed analytic route against the word **every**: density-one or
   almost-all representation theorems do not settle A303656.
5. Formalize only complete lemmas with explicit hypotheses; the public Lean file
   is currently a statement with `sorry`, not evidence of a proof.

## Sources

- [OEIS A303656](https://oeis.org/A303656)
- [Sun, *Restricted sums of four squares*](https://arxiv.org/abs/1701.05868)
- [Formal Conjectures statement](https://github.com/google-deepmind/formal-conjectures/blob/main/FormalConjectures/OEIS/303656.lean)
