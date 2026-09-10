# Strict causal consumer for returned-action differentials

Operation: `TITAN-V3-RETURNED-ACTION-DIFF-STRICT-CAUSAL-SUCCESSOR-20260910-01`

This is an additive successor to Commons PR #12082 at exact parent
`81cb68dddc701ba5c7ed906418c9fb5f485e1b45`.  It consumes the independent
review HOLD without rewriting the parent's capture harness.

## Why the parent report is not causal evidence yet

The parent is useful for capture and exploratory diffs, but review reproduced
four attribution false-passes:

1. any list of uniquely keyed objects can be treated as unordered, so swapping
   execution-bearing market rows can compare equal;
2. saved bundles can self-assert state/request/action hashes and action
   projection without recomputation;
3. missing state proof or unequal request hashes can still produce a normal
   report; and
4. repeat instability is displayed but sample zero is still compared and the
   process can exit successfully.

A lexical first field in one action object is also not a *temporal* first
divergence.

## What `strict_returned_action_diff.py` adds

The strict consumer accepts only parent-format capture bundles and validates
them bottom-up before comparison:

- parse JSON with duplicate-key and non-finite-number rejection;
- recompute the canonical state bytes, state SHA-256, request SHA-256, and
  request length;
- recompute every sample's unwrapped action, unwrap path, and action SHA-256
  from its persisted raw response;
- recompute sample count, unique-action count, determinism, unstable-sample
  index, parent diagnostic, and every top-level sample-zero projection;
- require both validated operands to have the exact same state *and* request
  digest;
- emit `HOLD_UNSTABLE` without comparing sample zero if either arm varies across
  repeated captures;
- compare every list positionally by default, including execution-bearing
  market/order rows;
- permit identity-based unordered alignment only at exact caller-supplied
  `--unordered-path` JSON paths and only when every row has a unique reviewed
  identity;
- retain exact integer comparison at zero tolerance, avoiding binary64 alias at
  and above `2**53`;
- require regular, non-symlink input files; reject input inode aliases and
  input/output/output path or hard-link aliases; and
- write reports with temp-file + `fsync` + atomic replacement and a
  self-excluding report SHA-256.

The parent capture's `http.body_sha256` is a hash of raw network bytes, but only
the parsed response is persisted.  The strict consumer validates that field's
shape but **does not** claim to recompute it or use it for causal attribution.
The trusted action projection is recomputed from the persisted raw response.

This successor intentionally has no endpoint mode, no headers, and no network
code.  Capture remains with the parent; this layer only decides whether saved
evidence is strong enough to compare.

## Temporal ledger

A temporal attribution uses an embedded ledger:

```json
{
  "format": "titan-returned-action-ledger/v1",
  "steps": [
    {"step": 94, "left": {"format": "titan-returned-action-capture/v1"}, "right": {"format": "titan-returned-action-capture/v1"}},
    {"step": 95, "left": {"format": "titan-returned-action-capture/v1"}, "right": {"format": "titan-returned-action-capture/v1"}}
  ]
}
```

(The abbreviated captures above are illustrative; real rows contain complete
parent capture bundles.)

The ledger must be non-empty and contiguous.  Each left/right capture pair is
fully revalidated and must prove equal state/request bytes.  `TEMPORAL_DIVERGENCE`
is emitted only for the first differing row after every earlier row has passed
strict comparison as equal.  Any unstable row terminates the attribution as
`HOLD_UNSTABLE`.

Example:

```bash
python strict_returned_action_diff.py \
  --left captures/v1.capture.json \
  --right captures/v3.capture.json \
  --json-out strict-report.json

python strict_returned_action_diff.py \
  --ledger temporal-ledger.json \
  --json-out temporal-report.json
```

Use `--unordered-path '$.some.reviewed.collection'` only for a path whose order
is known to be semantically irrelevant.  No unordered path is enabled by
default.

Exit status is `0` for valid evidence, `1` for a valid difference when
`--fail-on-diff` is requested, `2` for malformed/insufficient/aliased evidence,
and `3` for repeat instability.

## Contracts

Local source-independent validation before publication:

- `python -B -m unittest -v test_strict_returned_action_diff.py` — **27/27 PASS**
- `python -B -m py_compile strict_returned_action_diff.py test_strict_returned_action_diff.py` — PASS

The exact-head workflow additionally binds the parent commit and the parent
`returned_action_diff.py` Git blob, requires this successor to be one direct
commit with an exact four-path allowlist, runs the inherited parent suite plus
all strict contracts, and requires a clean checkout afterward.

The tests kill the review predecessors directly: reordered keyed market rows,
forged state/request/action/projection claims, missing state, unstable repeats,
duplicate keys, NaN/overflowing floats, `2**53` integer aliasing, non-contiguous
temporal evidence, symlink/hard-link input aliases, and output-over-input
clobbering.

## Boundary

This is evidence/control-plane code only.  It changes no TITAN policy,
scheduler, runtime, configuration, archive, release pointer, game/seed bank,
provider state, Kaggle state, promotion state, or submission.  A strict
`DIFFERENT` report localizes a validated returned-action seam; it does not by
itself prove downstream score causality or authorize promotion.