# Erdős 143(ii): first separation API

This directory is a bounded first-piece carrier for the current Conjectures.io target **Erdős problem 143, part ii**.  The target asks that every `Erdos143.WellSeparatedSet A` have

\[
\sum_{x\in A}\frac1{x\log x}<\infty.
\]

It does **not** claim that summability result.  It isolates elementary consequences of the exact source predicate that later analytic work can reuse, and binds those consequences to deterministic exact controls.

## Sponsor/source pins

At claim time the canonical sponsor page reported a **$4,543** bounty, nobody started, zero published pieces, and zero proof/counterexample attempts.  The exact production target was:

- task: `fc-8432eac9-parts-ii-0703f44156-formalized-v1`
- task commitment: `sha256:fa633be39c4914b8d907e9d1cff77d8cf78eea34632c03fb6a2c03ee9f305ebd`
- source type SHA-256: `sha256:d67e6578eee8f3a70ba0d0b5c0035e56073ee6d2505bee0c99f768e41e21e73d`
- sponsor-derived Formal Conjectures commit: `8432eac998110a563e03df65a28c117e97c8c142`
- source: `FormalConjectures/ErdosProblems/143.lean`

The source predicate is

```text
WellSeparatedSet A :=
  A ⊆ (1,∞) ∧ Infinite A ∧ Countable A ∧
  ∀ x∈A, ∀ y∈A, x≠y → ∀ k≥1, 1 ≤ |k*x-y|.
```

## Reusable deductions

### 1. Unit pairwise separation

Take `k = 1` in the defining inequality.  For distinct `x,y ∈ A`,

\[
1\le |x-y|.
\]

So the floor map is injective on `A`: two distinct points cannot lie in the same half-open integer bin `[m,m+1)`.  Consequently every integer interval `[m,m+L)` contains at most `L` points of `A`.

### 2. Exclusion around every positive multiple

For every `x∈A`, every integer `k≥1`, and every `y∈A\\{x}`,

\[
y\notin(kx-1,kx+1).
\]

This is just the defining inequality in geometric form.  It is the stronger ingredient that later sieve/density arguments must exploit; unit separation by itself only gives an `O(X)` counting bound.

### 3. Integer specialization = primitive sets

If all points are integers greater than one, then `k*x-y` is an integer.  Hence
`|k*x-y| < 1` iff `k*x=y`.  The full multiplicative separation clause is therefore equivalent to saying that **no distinct member divides another** (a primitive set).  This gives a simple exact finite model for regression and a bridge to classical primitive-set combinatorics.

## Exact regression

`separation_api.py` uses `fractions.Fraction` only.  The committed receipt exhausts all **131,072** subsets of `{2,…,18}` and checks the integer-specialization equivalence plus the first consequences above.  It finds:

- **3,896** primitive / integer-well-separated subsets;
- maximum cardinality **9** in this finite window;
- **14** maximizers;
- **0** equivalence mismatches;
- **0** consequence failures;
- status-stream SHA-256 `fec56fc6e3ab926a94bad07372324ede7eb2e44deb5e9351b28807581a64fbba`;
- canonical receipt payload SHA-256 `556c2ef19df9a04d076c53dcd1caf963900cc69e559706e9717b8c92da54ab85`.

The regression also contains exact rational positive and negative controls so it does not reduce every check to integer arithmetic.

Validation commands:

```bash
python -m py_compile separation_api.py test_separation_api.py
python -m unittest -v test_separation_api.py
python -O -m unittest -v test_separation_api.py
```

## Lean handoff / evidence ceiling

`Contribution.lean` contains the smallest sponsor-shaped theorem corresponding to the `k=1` projection.  It is intentionally marked **UNEXECUTED IN THIS RUNTIME** because `lean` and `lake` are not installed here.  It imports only the canonical Formal Conjectures module and contains no `sorry`.

A Lean-enabled continuation should kernel-elaborate that file against the sponsor-pinned environment, then extend it with an interval-cardinality API and the integer/primitive-set specialization.  Only after exact elaboration and the sponsor's current contribution checks should anyone promote or submit it.

This carrier is finite exact evidence plus a mathematical reduction/API.  It is **not** a proof of the summability conjecture, not sponsor acceptance, and not a bounty/payment claim.
