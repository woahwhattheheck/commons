# TITAN V3 intent-priority `2609097304` causal closure

This directory is an additive, exact-current evidence lane for the live `FrozenSelected.transform` version of the all-shed intent-priority SELL traversal. It does **not** change the canonical runtime, selected archive, configuration, archive pointer, provider state, or Kaggle state.

## Why this exists

The scheduler-only port in PR #11997 is unreachable on the selected archive because `main.py::agent` dispatches through `TitanAgent.transform_selected -> FrozenSelected.transform`. A fresh current-archive panel reported that moving the same factor to the live seam changed only the two mirrored Arlene cells for environment seed `2609097304`; both cells moved own cash `-6`, rival cash `+33`, and margin `-39`. An aggregate table is enough to reject promotion, but not enough to establish where the treatment first entered the official world.

This lane reconstructs those two cells and records the first changed returned action, the identical pre-action world, the unchanged rival action, the immediate official-interpreter transition, and the policy-local order inputs that selected the changed SELL queue. The analyzer publishes only if the exact reported activation topology and terminal deltas reproduce. Otherwise the workflow fails closed and retains the raw reports.

## Byte-bound experiment

`materialize_pair.py` accepts only the selected archive and source closure below:

- archive SHA-256 `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`, 428,158 bytes;
- source-manifest SHA-256 `3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469`;
- 109 runtime files; and
- `frozen_selected.py` Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`.

It rejects links, non-regular members, path aliases, duplicate names, expansion-bound violations, duplicate JSON keys, non-finite JSON, manifest/archive disagreement, and any runtime file identity drift. It writes detached `control/` and `candidate/` roots under the runner temporary directory. The sole treatment delta is this one expression inside `FrozenSelected.transform`:

```python
# control
targets = {p: max(0, int(shed.get(p, 0))) for p in PRODUCTS if shed.get(p, 0) > 0}

# candidate
target_order = {
    p: None for p in [*self.pending, *baseline_q, *PRODUCTS]
    if p in PRODUCTS
}
targets = {
    p: max(0, int(shed.get(p, 0))) for p in target_order
    if shed.get(p, 0) > 0
}
```

Membership and requested stock quantities are unchanged. Only dictionary traversal order may change. Both detached entrypoints apply the same bounded, post-return debug wrapper. The wrapper records the pre-call `pending`/`planned` state, inherited baseline SELL order, positive-shed PRODUCTS order, counterfactual intent order, chosen diagnostics summary, and returned market queue. Its post-unit reconstruction runs **after** the policy returns and on deep-copied inputs.

`materialize_evaluator.py` accepts only evaluator Git blob `077feb2208b6e0c1727835eb4f8089709bf67f3b`. It preserves the two returned actions passed to the official interpreter while adding an observability timeline with:

- pre-world SHA-256 after both agents return and before either action is installed;
- immutable tested and rival actions plus independently recomputed hashes;
- the tested entrypoint's bounded debug snapshot;
- post-world SHA-256 immediately after the official interpreter; and
- both bank balances after that transition.

The child-reported decision time is measured before debug retrieval, so instrumentation is not charged to the policy's reported call time.

## Panel and hard gates

The workflow runs one opponent, eight environment seeds, and both seats for each arm: 16 paired cells per arm, plus the evaluator's deterministic first-cell recheck.

```text
opponent: arlene.py::agent
seeds: 2609097304, 539131249, 1834999074, 2609097301,
       2609097302, 2609097303, 2611092201, 2611092207
seats: 0, 1
agent RNG seed: 20260907
```

`analyze_divergence.py` independently binds the pair receipt, evaluator receipt, generated entry hashes, checked-out Arlene source, loader, and all three official-engine files. It rejects incomplete games, duplicate cells, non-finite values, malformed or discontinuous world timelines, action-hash disagreement, debug/action disagreement, terminal score/bank disagreement, and any untreated world or rival-action drift before the first tested-action change.

Publication requires all of the following:

1. exactly two action-active cells: Arlene × `2609097304` × seats 0 and 1;
2. fourteen action- and score-identical dormant cells;
3. own/rival/margin terminal deltas `-6/+33/-39` in each active cell;
4. aggregate means `-0.75/+4.125/-4.875` for own/rival/margin;
5. an identical pre-world and rival action at each first divergence;
6. a market-only tested-action change inside the executable order prefix; and
7. an immediate official post-world change.

If those gates pass, the output disposition is `RETIRE_FACTOR`. There is no enabling public-state guard to promote from this panel: every observed activation is harmful, and blocking every harmful activation reduces the factor to current control on the measured grid. A broader or differently conditioned policy is a new factor and requires a new claim and panel.

## Run locally

The workflow is the authoritative run because it has the selected archive and pinned official engine in the checked-out repository. Unit contracts are host-independent:

```bash
python -m unittest discover -s . -p 'test_*.py' -v
python -m py_compile *.py
```

Generated evidence is uploaded as a workflow artifact and is not committed. The artifact contains the two full reports, pair and evaluator receipts, first-divergence JSON/Markdown, and pre/post canonical identity receipts.
