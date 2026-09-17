# Rigorous partial results — Rule 30 Prize Problem 3

Operation: `RULE30-LINEAR-LOWERBOUND-ZRH1546-20260917`

This note records what is actually proved in this carrier. It does **not** prove
the Rule 30 prize theorem.

## Lemma 1 — the published prose and displayed predicate are not equivalent

Let `T(n)` be the running time of an exact predictor.

The surrounding sponsor prose asks whether there is a shortcut taking *less than
linear* effort. The natural asymptotic negation of a linear lower-bound claim is
therefore the existence of an exact predictor with `T(n) = o(n)`.

The displayed formal predicate instead rules out an exact machine satisfying

`limsup_{n -> infinity} T(n)/n < infinity`.

For nonnegative runtimes, finite limsup implies an eventual constant upper bound
`T(n) <= C n`, i.e. an `O(n)`-type upper bound. Hence the displayed predicate
rules out both sublinear and ordinary linear-time exact predictors.

The difference is witnessed by `T(n)=n`:

* `T(n)` is **not** `o(n)`, so it is not a counterexample to an intended
  `Omega(n)` lower bound;
* `limsup T(n)/n = 1 < infinity`, so it **is** a counterexample to the displayed
  `NotExists[...]` predicate.

Therefore a proof must name which target it establishes. They cannot be silently
substituted for one another.

`asymptotic.py` makes this distinction executable for exact power/log families
and includes a non-smooth O(n), non-o(n) witness to prevent accidental
finite-sample smoothing from replacing asymptotic reasoning.

## Lemma 2 — causal-cone size alone cannot prove the desired lower bound

A radius-one elementary cellular automaton has a width `2n+1` backward cone for
the time-n center cell. That does **not** imply that evaluating the center bit
requires work proportional to the cone.

Rule 150 is an exact counterexample. Over `F_2`, encode a row as a Laurent
polynomial. From a lone seed,

`P_n(x) = (x^-1 + 1 + x)^n`.

Write the binary expansion `n = sum_{k in S} 2^k`. Frobenius in characteristic
two gives

`(x^-1 + 1 + x)^(2^k) = x^(-2^k) + 1 + x^(2^k)`,

so

`P_n(x) = product_{k in S} (x^(-2^k) + 1 + x^(2^k))`.

The constant term is obtained by choosing the `1` from every factor. There is no
second way to obtain exponent zero: if a nonempty signed sum of distinct powers
of two were zero, the largest selected power would exceed the sum of all
smaller selected powers. Thus the constant coefficient is exactly one for every
n.

So Rule 150 has the same linearly widening geometric cone, yet its lone-seed
center column is identically black and is computable without evolving the cone.
Any valid Rule 30 lower bound must use structure specific to the center-bit
function, not cone area/width by itself.

`rule30.py` independently simulates elementary rules and checks this closed form
for bounded horizons as a falsifier. The proof above, not the finite check, is
the result.

## Lemma 3 — eventual periodicity gives an O(log n) binary-input predictor

Suppose a binary sequence has a finite prefix of length `N` and thereafter a
period `p`. Both `N` and `p` are constants of the machine.

On binary input `n`, one left-to-right scan can maintain `n mod p` in a
finite-state residue register. A finite-state comparison with the fixed
threshold `N` selects either the prefix table or the periodic table. The scan
takes `Theta(log n)` input-symbol steps.

Therefore, if the Rule 30 center column were eventually periodic, an exact
`O(log n)` predictor would exist in the binary-input Turing-machine model
described by the sponsor. Any genuine lower bound excluding `o(n)` predictors
would consequently imply nonperiodicity. This is a conditional implication,
not a proof that Rule 30 is nonperiodic.

`eventually_periodic_predictor` is a constructive executable model of this
reduction.

## Model boundary

The sponsor explicitly describes putting the **digits of n** on a Turing-machine
tape. The input length is therefore `Theta(log n)`. Reading every digit costs
only `Theta(log n)`, matching the sponsor's own observation. Input-reading
arguments alone cannot bridge the gap to an `Omega(n)` lower bound.

General prediction hardness for arbitrary cellular-automaton initial conditions,
P-completeness of other automata, chaos, statistical randomness, and Rule 30
inversion hardness do not automatically imply a lower bound for this *fixed
lone-seed one-bit function*. Any imported complexity result must provide an
explicit reduction to this exact function.

## What remains open

The hard step remains untouched by these model-cleanup lemmas: prove that every
finite exact machine for the Rule 30 lone-seed center bit uses non-sublinear
effort under the intended model (or prove the stronger displayed predicate), or
exhibit a correct sublinear shortcut.

No finite timing curve, symbolic-expression growth plot, causal-cone count, or
generic CA hardness statement is promoted to that conclusion here.
