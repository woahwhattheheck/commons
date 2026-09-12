# TITAN V5 cross-evidence promotion and release gates

`promotion_gate.py` is an evidence-only fail-closed join across three V5
contracts that are intentionally produced separately:

1. a `v5_candidate_identity.py` manifest,
2. an `engagement_fingerprint.py` report, and
3. a `runtime-budget/runtime_budget_profile.py` report.

It does not execute gameplay, change a default, or replace the underlying
source/engine/simulation evidence. Its job is to prevent a promotion decision
from accidentally combining identity, engagement, or runtime evidence from
different builds.

## Promotion contract

A promotion-gate PASS requires all of the following:

- the candidate manifest has the exact `titan-v5-candidate-identity/v1` closed
  shape and its `v5c:` ID recomputes from the manifest body;
- engagement is `ENGAGED`, has a real divergence, has distinct exact `v5c:`
  control/candidate IDs, and the candidate ID equals the manifest;
- runtime admission is `PASS` with `promotion_ready=true`, an explicit exact
  callback design, no missing or unexpected callbacks, nonnegative p99
  headroom, and exactly one runtime candidate equal to the manifest/engagement
  candidate;
- redundant runtime counts/rates are internally consistent; and
- every input JSON file is strict JSON: duplicate object members and
  `NaN`/`Infinity` constants are rejected.

The emitted receipt binds the exact input-file SHA-256 values plus the shared
candidate/control identity and the key engagement/runtime metrics. Output-file
publication is same-directory atomic.

```bash
python candidates/v5/promotion-gate/promotion_gate.py \
  candidate-manifest.json engagement-report.json runtime-budget-report.json \
  --output promotion-receipt.json
```

## Paired competitive economics

`economics_gate.py` closes a separate release boundary. A candidate that is
identifiable, engaged, and fast is not necessarily competitive. The economics
gate therefore accepts only raw paired cells with exact control/candidate
`v5c:` identities and recomputes each margin itself.

A paired-economics PASS requires:

- at least 8 cells / 4 distinct seeds;
- exactly one seat-0 and one seat-1 cell per seed;
- unique cells in canonical `(seed, seat)` order;
- exact nonnegative integer own/rival scores for both control and candidate;
- no caller-supplied aggregate or claimed delta fields; and
- nonnegative aggregate paired margin delta.

The receipt records the recomputed cell/seed counts, sign counts, margin sums,
mean delta, and canonical panel digest.

```bash
python candidates/v5/promotion-gate/economics_gate.py economics-report.json \
  --output economics-receipt.json
```

## Release transaction

`release_transaction.py` is the only pointer-transition authority in this
directory. Version 2 keeps the existing promotion replay, V4 trusted-base replay,
source/archive binding, expected-old transaction, and atomic commit semantics,
but now also requires `--economics-report`.

The release transaction replays `economics_gate.validate_report()` against the
**same candidate and control IDs** carried by the promotion receipt. It binds the
raw economics-report SHA-256 and recomputed panel metrics into the transition
identity. Negative-mean, incomplete, duplicate, unbalanced, or cross-build
panels fail before a release pointer can move.

Exit status is `0` only for a PASS receipt. Invalid, ambiguous, incomplete,
cross-wired, or economically regressive evidence exits `2`.
