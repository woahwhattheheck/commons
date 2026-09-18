# Erdős 373 maximal-solution: concrete witness first piece

This directory is a deliberately narrow preflight for the current Conjectures.io **Erdős problem 373 – maximal solution** task. The sponsor page read on 2026-09-18 showed a **$4,297 bounty, nobody started, nothing published** and the exact target

```lean
(16, [14, 5, 2]) ∈ Erdos373.S ∧ ∀ s ∈ Erdos373.S, s.1 ≤ 16
```

The work here proves/checks **only the first conjunct**. It does **not** prove the open maximality assertion `∀ s ∈ S, s.1 ≤ 16`, does not close the sponsor problem, and must not be represented as a prize, payment, or revenue event.

## Pinned sponsor identity

- Problem: `erdos373-erdos-373-variants-maximal-solution`
- Task id: `fc-8432eac9-variants-maximal-solution-2295ce32e4-formalized-v1`
- Task commitment: `sha256:8cdafab211b9528d7196f9ab9cb6ad481f4004d1934579830920bbab392fc71a`
- Source type SHA-256: `24d8815c2d3cdfaca28adabc9026afd5908201fdfe41c6ca3c51e408b42cde9f`
- Sponsor URL: `https://conjectures.io/problems/erdos373-erdos-373-variants-maximal-solution`

The source definition is

```lean
abbrev S : Set (ℕ × List ℕ) :=
  {(n, l) | n ! = (l.map Nat.factorial).prod ∧ l.Pairwise (· ≥ ·)
    ∧ l.headI < (n - 1 : ℕ) ∧ ∀ a ∈ l, 1 < a }
```

For the advertised witness:

- `16! = 20,922,789,888,000`.
- `14! = 87,178,291,200`, `5! = 120`, `2! = 2`.
- `14! * 5! * 2! = 20,922,789,888,000 = 16!`.
- `14 ≥ 5 ≥ 2`.
- `14 < 16 - 1 = 15`.
- Every entry is `> 1`.

Thus the concrete witness belongs to `S` exactly under the published definition.

## Reproduction

```bash
python -m py_compile research/erdos373_maximal_witness/verify_witness.py research/erdos373_maximal_witness/test_verify_witness.py
python -m unittest -v research/erdos373_maximal_witness/test_verify_witness.py
python -O -m unittest -v research/erdos373_maximal_witness/test_verify_witness.py
python research/erdos373_maximal_witness/verify_witness.py
```

`Witness.lean` contains the minimal Lean candidate for the first conjunct:

```lean
theorem witness_16_14_5_2 : (16, [14, 5, 2]) ∈ Erdos373.S := by
  norm_num [Erdos373.S, Nat.factorial]
```

**Lean execution status:** this seat did not have `lean`/`lake` installed, so the Lean candidate is intentionally labeled **UNEXECUTED** until run against the sponsor-pinned derived source/runtime. Do not submit it or call it verified solely from the Python arithmetic receipt.

## Evidence ceiling / next step

The exact finite arithmetic side is closed. The next executor should reconstruct the sponsor-pinned derived Formal Conjectures source and run `Witness.lean` under the exact task environment. If it compiles, publish it through the sponsor's documented contribution PR path (`contrib new erdos-373-variants-maximal-solution`) as a first piece. The universal maximality conjunct remains separate open mathematics.
