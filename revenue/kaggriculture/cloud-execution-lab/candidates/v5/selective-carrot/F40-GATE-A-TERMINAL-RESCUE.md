# TITAN V5 Wave 4 — F40 C11 Gate A terminal-rescue latch

## Scope

F40 is one additive, default-inert component for the held V5 superiority line. It implements the exact public-state Gate-A condition posted in the Wave-4 frontier:

- public step **>= 648**;
- public own-minus-rival cash gap **>= -1500**; and
- rival crop-yield units minus own crop-yield units **>= 7**.

When all three are true, the component latches terminal rescue for the remainder of that game. It does not select a terminal action, derive hidden state, call a producer, remint a candidate, run games, move `CURRENT`, change a default, publish a release, or touch Kaggle.

## Public-scalar contract

The helper accepts exactly four already-derived public scalars:

```text
step
public_cash_gap
own_crop_yield_units
rival_crop_yield_units
```

It deliberately does not guess a package-specific observation path. The exact production archive is source authority for those derivations, while this repository checkout exposes only its member manifest. A later one-tree composer must authenticate that runtime source and supply the four values at the existing terminal-rescue boundary.

Every integer is a plain nonnegative `int`; booleans and coercible aliases are rejected. Cash gap is a finite plain `int` or `float`. Nonzero step rewinds fail closed. Step zero starts a fresh latch generation, and callers must observe step zero or explicitly reset at each new game.

## Fresh-win controls

A healthy late-game state must not arm rescue. The focused suite therefore includes all of these controls:

- own yield lead;
- tied yield;
- rival lead of only six;
- cash gap just below -1500; and
- step 647 with an otherwise qualifying deficit.

The exact thresholds open only at step 648, gap -1500, and yield deficit seven.

## Source custody

`build_f40_gate_a.py` requires the exact production-v3 runtime preimage:

```text
7fefc550cf2b1ee73995616321bf4824755f075125221a03bdc5d83db1ee22ab  titan_runtime.py
```

It fails closed unless there is exactly one `TitanAgent` class seam, inserts one inert module-level bridge, and adds `f40_gate_a.py`. The bridge is behaviorally inert until an authenticated composer explicitly calls it. Inputs are deep-copied; helper collisions, source drift, duplicate anchors, and reapplication are rejected.

## Receipt

Every transition can emit canonical finite JSON under schema `titan-v5-f40-gate-a-decision/v1`, including thresholds, public inputs, current eligibility, latch state, generation, reason, and a SHA-256 seal.

## Verification

```bash
python -B -m unittest -v test_f40_gate_a.py
python -O -B -m unittest -v test_f40_gate_a.py
python -m py_compile f40_gate_a.py build_f40_gate_a.py test_f40_gate_a.py
```

Source-contract success is not a score or promotion claim. Activation still requires exact-current public-scalar derivation, terminal-rescue composition, matched official-engine evaluation, and the root superiority gate.
