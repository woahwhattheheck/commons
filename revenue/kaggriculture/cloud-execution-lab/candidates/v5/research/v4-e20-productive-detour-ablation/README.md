# TITAN V5 — submitted V4 E20 productive-detour self-ablation

This is a causal research carrier for the observed **V3.1 > V4** regression.
It changes no current V5 runtime, defaults, config, release archive, pointer, or
Kaggle state.

## Why this delta is isolated

Both submitted packages enable `redundant_hire=true`, but the helper changed:

- submitted V3.1 `a90d888f...` has repository source
  `revenue/kaggriculture/cloud-execution-lab/reference/titan-current/redundant_hire.py`
  at Git blob `4a0bf316...`;
- submitted V4 `4af11131...` has the same repository source at Git blob
  `9ded2a9b...`.

V3.1 proves trailing hired workers physically redundant over the remaining shift
and replaces their current HIRE rows with zero-quantity SELL placeholders. It
does **not** edit future producer route bytes.

V4 retains that certificate but then calls `_productive_detour`. That branch may
protect one otherwise-redundant hire and mutate future route rows to
`spawn -> HARVEST -> DROP -> rejoin` when the harvested deposit's **current
observed quote** exceeds the wage. The helper itself states future-cash
compatibility is not established.

The implementation entered through #11130 as a bounded mechanism screen. That
work explicitly did not complete its requested matched full-game evaluation.

## Exact counterfactual

`ablate_e20_productive_detour.py` authenticates both submitted helper Git blobs.
It keeps every submitted-V4 byte through the completed physical redundancy
certificate, then replaces only the E20 productive-detour tail with the exact
submitted-V3.1 deletion tail. Dormant V4 detour helper definitions remain; only
their call/protection/route-mutation path is removed.

Repository-source identity and package-member identity are intentionally kept
separate. `build_integrated.py` packages that repository source as archive member
`reference/titan-current/redundant_hire.py`. The treatment builder rejects the
repository path if it appears as an archive member, preventing a synthetic test
from validating the wrong namespace.

Submitted V4 control is the retained competition archive SHA256
`4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`.
This is deliberately **not** substituted with the repository's contemporaneous
`CURRENT-ARCHIVE.json` object; they are different artifacts.

`build_submitted_v4_treatment.py` accepts only that exact retained archive plus
the exact V3.1 helper and emits a deterministic treatment archive. It proves:

- exactly one semantic member changes:
  `reference/titan-current/redundant_hire.py`;
- exactly one metadata member changes: `SOURCE.json`, regenerated to truthfully
  bind the treatment helper and source/archive authority;
- every other member remains byte-identical to submitted V4 control.

## Focused contracts

Exact-head CI runs normal and `-O` under Python 3.11/3.12 and covers:

- exact V3.1/V4 helper Git-object authority and the surgical source splice;
- direct productive witness: V4 keeps HIRE + authors HARVEST/DROP; treatment
  deletes the redundant HIRE + leaves future route exact;
- no-op witness: no productive opportunity => control/treatment action and route
  are identical;
- exact report-shape boundary before/after the E20 tail;
- deterministic archive build, source-manifest rebinding and source/member
  namespace separation;
- returned-action trace hashing/divergence/restoration and terminal score logic;
- paired-runner archive safety and summary contracts;
- pycompile and clean worktree.

## One-command matched-game evidence

`paired.py` authenticates the retained control, builds treatment in memory,
authenticates the existing joint-liquidity evaluator/opponent harness by Git
blob, snapshots it, and runs both arms while observing returned candidate
actions without modifying evaluator/agent bytes.

Default screen: 16 distinct seeds × both seats × `apex_v7,arlene_v14`.

```bash
python paired.py \
  --kg-root /path/to/commons/revenue/kaggriculture \
  --engine-dir /path/to/official-engine \
  --baseline /path/to/exact-submitted-v4-4d960155.tar.gz \
  --output /tmp/e20-detour-ablation
```

The runner refuses a baseline whose SHA256 is not exactly `4d960155...` and
records the generated treatment SHA, package-diff receipt, authenticated harness
receipt, engine hashes, per-game scores, returned-action trace hashes, first
control/treatment divergence, and aggregate all/opponent deltas.

First returned-action divergence is the natural E20 engagement witness because
the treatment's only gameplay semantic change is the productive-detour
protection path. If the screen is cold, report it as cold; do not infer economics
from the synthetic source witness.

## Promotion boundary

A directional screen is not promotion authority. Any E20 removal/tightening must
survive opponent-diverse holdout and the shared current-V5 champion/economics
gate, then converge through the one V5 runtime. This carrier never authorizes a
parallel V3.1 runtime or direct release/Kaggle mutation.
