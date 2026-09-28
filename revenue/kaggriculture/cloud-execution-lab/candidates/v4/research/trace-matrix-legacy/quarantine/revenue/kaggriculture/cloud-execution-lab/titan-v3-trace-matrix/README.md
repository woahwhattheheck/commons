# TITAN V3 trace gate and constrained experiment matrix

This directory adds two **additive, evidence-only** tools to the TITAN evaluation lane:

1. `matrix.py` compiles a small, deterministic set of runtime-legal configurations that covers every reachable declared one- and two-feature interaction.
2. `trace_gate.py` compares baseline and candidate step traces on an exact opponent × seed × seat grid, finds the first externally observable divergence, attributes later transaction and cash deltas, and applies an explicit promotion policy.

Neither tool edits `TITAN-CONFIG.json`, runtime source, archives, champion pointers, or leaderboard material. A matrix row is an experiment request, not evidence that a candidate is better. A trace report is paired trajectory evidence, not access to hidden reasoning and not an opponent-independent proof of dominance.

## Why this lane exists

A win/tie/loss summary can remain unchanged while the candidate gives away cash in individual games. One-at-a-time feature toggles can also miss interactions between hooks. This package makes both failure modes visible:

- score-preserving economic regressions are rejected by cash/margin policy;
- opponent-sensitive action edits are grouped only when the action signature, seed, and seat are fixed;
- every reachable declared pair of feature values appears in at least one legal matrix row;
- stale or hand-edited generated matrices fail CI.

## Files

| File | Purpose |
| --- | --- |
| `matrix.py` / `matrix_support.py` | Deterministic constrained t-wise matrix compiler and strict input/constraint helpers. |
| `MATRIX-CONTRACT.json` | Declared factors, runtime constraints, mandatory controls, strength, and row budget. |
| `MATRIX.json` | Generated matrix bound to the exact base-config and contract SHA-256 digests. |
| `trace_gate.py` / `trace_support.py` / `trace_compare.py` / `trace_policy.py` | Fail-closed trace ingestion, first-divergence comparison, exact-grid policy, and CLI. |
| `TRACE-CONTRACT.example.json` | Complete contract shape with placeholder paths and digests. |
| `test_matrix.py` | Matrix legality, determinism, coverage, type-safety, and failure-mode tests. |
| `test_trace_gate.py` | Trace integrity, alignment, attribution, policy, and adversarial-input tests. |

## Current matrix result

Generated from the parent `../TITAN-CONFIG.json` and the committed contract:

- raw Cartesian combinations: **4,096**
- runtime-legal combinations: **2,176**
- rejected combinations: **1,920**
- reachable one- and two-feature interactions: **284**
- covered interactions: **284 / 284**
- selected configurations: **12** within a budget of 24
- verdict: **`COMPLETE`**

`COMPLETE` means only that the declared reachable interaction space is covered. Each selected row still requires official-engine paired evaluation.

## Rebuild and verify the matrix

Run from this directory:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
python matrix.py \
  --base ../TITAN-CONFIG.json \
  --spec MATRIX-CONTRACT.json \
  --output /tmp/titan-v3-matrix.json
cmp MATRIX.json /tmp/titan-v3-matrix.json
```

Exit codes:

- `0`: all reachable declared interactions fit in the budget (`COMPLETE`)
- `2`: malformed base/specification or impossible mandatory assignment (`INVALID`)
- `3`: inputs are valid, but the row budget leaves reachable interactions uncovered (`BLOCKED`)

### Matrix rules

The compiler:

- preserves all undeclared base-config keys in every row;
- treats JSON scalar types distinctly (`true` is not integer `1`);
- evaluates explicit implication and forbid constraints;
- begins with the exact current base configuration;
- resolves each mandatory partial assignment to the nearest legal completion;
- greedily selects the legal row covering the most still-uncovered interactions, with deterministic tie-breaking;
- reports both a primary rejection partition and overlapping constraint-violation incidence.

The compiler does not run games, estimate score, modify production configuration, or promote a candidate.

## Produce and evaluate trace evidence

`benchmark.py` already emits external per-step JSONL records containing the observation, actions for both seats, transactions, post-step cash, shed, market, and terminal flag. Capture baseline and candidate traces on the exact same declared grid, hash the stored bytes, then populate a contract following `TRACE-CONTRACT.example.json`.

```bash
python trace_gate.py \
  --contract /path/to/TRACE-CONTRACT.json \
  --report /path/to/TRACE-REPORT.json
```

Exit codes:

- `0`: evidence is structurally valid and satisfies policy (`PROMOTE`)
- `2`: contract or evidence is invalid (`INVALID`)
- `3`: evidence is valid but fails one or more policy thresholds (`REJECT`)

### Evidence integrity

The trace gate fails closed on, among other cases:

- missing or extra opponent × seed × seat cells;
- duplicate JSON keys, non-finite numbers, or malformed rows;
- a SHA-256 mismatch on any compressed or uncompressed trace file;
- symlinks, non-regular files, oversized input, decompression expansion, or excessive rows;
- non-contiguous steps, changing candidate seat, wrong seat, missing actions, malformed transactions, or nonterminal/truncated traces;
- baseline/candidate row-count mismatch;
- a changed initial observation when the policy requires identical initial state;
- identity candidates with no candidate action change when `require_any_action_change` is enabled.

The contract binds four provenance digests independently of per-trace hashes:

- official engine;
- trace-producing runner;
- baseline archive;
- candidate archive.

### Reported comparison data

For every exact cell the report includes:

- first candidate-action, opponent-action, full-observation, public-observation, cash, market, and shed divergence;
- a structural signature of the first candidate action edit;
- changed-action count;
- per-step own-cash and margin deltas;
- terminal, worst, and first-nonzero cash deltas;
- baseline/candidate transaction totals and typed transaction deltas;
- exact trace path, byte count, row count, compression mode, and SHA-256 digest.

Aggregate policy can set floors or ceilings for mean/median/worst cash, margin, positive/negative cell fractions, per-opponent cash, per-seat cash, required action change, and opponent-contingent first-action signatures.

An action signature is labeled opponent-contingent only when **seed, seat, and first candidate action edit are identical**, at least two declared opponents are present, and terminal own-cash delta changes from positive to negative. This prevents seed- or seat-sensitive behavior from being mislabeled as an opponent response.

## Test suite

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
python -m py_compile trace_gate.py trace_support.py trace_compare.py trace_policy.py matrix.py matrix_support.py test_trace_gate.py test_matrix.py
python -m unittest -v test_trace_gate.py test_matrix.py
```

The committed suite contains 19 adversarial and functional tests. CI additionally rebuilds `MATRIX.json` and requires a byte-identical result plus complete reachable-interaction coverage.

## Integration boundary

This package complements, rather than replaces, the existing game-level paired gate:

1. Compile the bounded interaction matrix.
2. Execute selected rows through the official engine on a declared paired grid.
3. Apply the existing game/provenance gate for canonical W/T/L and archive admission.
4. Apply `trace_gate.py` for first-divergence and economic-regression analysis.
5. Promote only when every required gate passes; never infer a leaderboard gain from local matrix coverage or trace structure alone.
