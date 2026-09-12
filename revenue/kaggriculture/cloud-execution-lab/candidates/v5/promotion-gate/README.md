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
gate accepts only raw paired cells and recomputes each margin itself.

The v3 economics report is execution-bound. It carries exact control and
candidate `v5c:` identities, the candidate manifest's engine/opponent-pack
identity, and the exact old/new release archive SHA-256 values. Each raw cell
also names the opponent actually played. The release transaction supplies the
build/execution authorities independently and rejects stale or cross-wired
evidence.

A paired-economics PASS requires:

- at least 2 distinct opponents and 4 distinct seeds per opponent;
- every opponent covers the exact same seed set;
- exactly one seat-0 and one seat-1 cell for every `(opponent, seed)` pair;
- unique cells in canonical `(opponent_id, seed, seat)` order;
- exact bounded nonnegative integer own/rival scores for control and candidate;
- no caller-supplied aggregate or claimed delta fields;
- execution authority equal to the promotion manifest and release archive pair;
  and
- nonnegative aggregate paired margin delta.

The receipt records the actual sorted opponent IDs/count, execution identity,
recomputed cell/seed counts, sign counts, margin sums, mean delta, and canonical
panel digest. This proves balanced coverage across the opponents explicitly
present in the evidence. The current candidate identity's `opponent_pack_id` is
opaque, so this gate does **not** independently claim that those opponent IDs are
an exhaustive decode of every member of that opaque pack; it makes the played
membership explicit and transition-bound instead of hiding it behind the label.

```bash
python candidates/v5/promotion-gate/economics_gate.py economics-report.json \
  --output economics-receipt.json
```

## Release transaction

`release_transaction.py` is the pointer-transition authority in this directory.
Version 3 keeps the existing promotion replay, V4 trusted-base replay,
source/archive binding, expected-old transaction, and atomic commit semantics,
and requires `--economics-report`.

The release transaction replays `economics_gate.validate_report()` against the
same candidate/control, engine/opponent-pack, and old/new archive authorities
already authenticated by the transition. It redundantly validates the economics
receipt's sorted unique opponent list/count and serializes both, the raw report
SHA-256, and the canonical panel digest into the `v5tx:` transition identity.
Negative-mean, single-opponent, uneven-seed, missing-seat, duplicate, stale-
archive, wrong-pack, or cross-build panels fail before a release pointer can
move.

Exit status is `0` only for a PASS receipt. Invalid, ambiguous, incomplete,
cross-wired, or economically regressive evidence exits `2`.
