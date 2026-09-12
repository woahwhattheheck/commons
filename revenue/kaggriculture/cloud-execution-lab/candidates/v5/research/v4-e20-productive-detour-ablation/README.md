# TITAN V5 — submitted V4 E20 productive-detour self-ablation

This is a causal research carrier for the observed **V3.1 > V4** regression.
It changes no current V5 runtime, defaults, config, release archive, pointer, or
Kaggle state.

## Why this delta is isolated

Both submitted packages enable `redundant_hire=true`, but the helper changed:

- submitted V3.1 `a90d888f...` has
  `reference/titan-current/redundant_hire.py` Git blob `4a0bf316...`;
- submitted V4 `4af11131...` has the same path at Git blob `9ded2a9b...`.

V3.1's helper proves trailing hired workers physically redundant over the
remaining shift and replaces their current HIRE rows with zero-quantity SELL
placeholders. It does **not** edit future producer route bytes.

V4 retains that certificate but, after it succeeds, calls `_productive_detour`.
That branch may protect one otherwise-redundant hire and mutate future route
rows to `spawn -> HARVEST -> DROP -> rejoin` when the harvested deposit's
**current observed quote** exceeds the wage. The helper itself states future
cash compatibility is not established.

The implementation entered through #11130 as a bounded mechanism screen. That
work explicitly did not complete its requested matched full-game evaluation.
The later mixed-bundle HIRE counterexample shows the broader redundant-hire
family matters economically, but it does not establish that this specific
productive-detour expansion improves the submitted V4.

## Exact counterfactual

`ablate_e20_productive_detour.py` authenticates both submitted helper Git blobs.
It keeps every submitted-V4 byte through the completed physical redundancy
certificate, then replaces only the E20 productive-detour tail with the exact
submitted-V3.1 deletion tail. Dormant V4 detour helper definitions remain in the
module; only their call/protection/route-mutation path is removed.

So the intended paired comparison is:

- **control:** exact submitted V4 `4af1113154e78c662780e6658cd920daac7902e3`;
- **E20-detour-OFF:** identical V4 package except the materialized
  `redundant_hire.py` output from this carrier.

Do not compare against V3.1 as the treatment: the point is to ask whether this
one V4-added behavior explains any of the V4 regression while holding every
other V4 byte fixed.

## Source contracts

The focused suite:

- resolves the two exact historical helper objects with `git show` and verifies
  their Git blobs;
- proves the ablation preserves the entire V4 prefix byte-for-byte and appends
  the exact V3.1 deletion tail;
- executes a direct productive witness where submitted V4 keeps the HIRE and
  rewrites future route rows to HARVEST/DROP while the ablation deletes the HIRE
  and leaves the route byte-identical;
- proves a no-productive-opportunity predecessor returns identical actions and
  route under control and ablation;
- fails closed on either source drift;
- runs under normal Python and `-O`.

## Economics gate

Run complete official-engine matched games in both seats using identical seeds,
opponents and package construction. Record at minimum candidate/control score,
margin, win/tie/loss, first returned-action divergence, E20 detour activation,
protected worker count, completed job/product/quantity, wage payback, and any
later divergence from the rewritten route.

The first screen should be broad enough to answer whether the detour branch is
actually reached and directional; promotion/reversion requires an opponent-
diverse holdout and the shared current-V5 champion/economics gate. A positive
ablation result is evidence to *remove or tighten this V4-added behavior* in the
one V5 tree, not authority to resurrect a separate V3.1 runtime.
