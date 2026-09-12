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

The competition artifact is also pinned independently. Submitted V4 control is
the retained archive SHA256
`4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`.
That is deliberately **not** substituted with the repository's contemporaneous
`CURRENT-ARCHIVE.json` object; they are different artifacts.

`build_submitted_v4_treatment.py` accepts only that exact retained archive and
the exact submitted-V3.1 helper. It emits a deterministic treatment archive and
receipt. Member-set and byte comparison must prove:

- exactly one semantic member changes:
  `reference/titan-current/redundant_hire.py`;
- exactly one metadata member changes: `SOURCE.json`, regenerated so its runtime
  hash/byte record truthfully binds the treatment helper and records the
  experiment authority;
- every other package member, including `main.py`, config and opponent/runtime
  dependencies, remains byte-identical to submitted V4 control.

So the intended paired comparison is:

- **control:** exact retained submitted-V4 archive `4d960155...`;
- **E20-detour-OFF:** output of `build_submitted_v4_treatment.py` from that
  control archive.

Do not compare against V3.1 as the treatment: the point is to ask whether this
one V4-added behavior explains any of the V4 regression while holding every
other V4 gameplay byte fixed.

## Source and package contracts

The focused suites:

- resolve the two exact historical helper objects with `git show` and verify
  their Git blobs;
- prove the ablation preserves the entire V4 prefix byte-for-byte and appends
  the exact V3.1 deletion tail;
- execute a direct productive witness where submitted V4 keeps the HIRE and
  rewrites future route rows to HARVEST/DROP while the ablation deletes the HIRE
  and leaves the route byte-identical;
- prove a no-productive-opportunity predecessor returns identical actions and
  route under control and ablation;
- build a synthetic control package using the exact V4 helper and verify the
  archive builder changes only helper semantics + `SOURCE.json` metadata;
- prove deterministic treatment bytes and fail closed on archive, source or
  manifest-identity drift;
- run under normal Python and `-O`.

For a real execution:

```bash
python build_submitted_v4_treatment.py \
  --control-archive /path/to/exact-submitted-v4.tar.gz \
  --v31-helper /path/to/a90d-redundant_hire.py \
  --output /tmp/v4-e20-detour-off.tar.gz \
  --receipt /tmp/v4-e20-detour-off.json
```

The command refuses a control archive whose SHA256 is not exactly `4d960155...`.

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
