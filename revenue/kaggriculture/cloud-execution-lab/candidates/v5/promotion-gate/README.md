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

The v4 economics report is execution-bound. It carries exact control and
candidate `v5c:` identities, the candidate manifest's engine/opponent-pack
identity, and the exact old/new release archive SHA-256 values. Each raw cell
also names the opponent actually played. The release transaction supplies the
build/execution authorities independently and rejects stale or cross-wired
evidence.

The release roster is no longer inferred from an opaque pack label. It is
explicitly fixed to:

- `apex_v7`
- `arlene_v14`

and the receipt binds the reviewed `REFERENCE-POLICIES.json` Git blob
`6bce02dad705ccc57656ff2e2139db215f9fcc57`. The registry contains other
recovered names, so using every registry key would be wrong; the two-name roster
is an explicit release authority, not a registry enumeration.

A paired-economics PASS requires:

- the played opponent IDs equal the exact authorized roster (no favorable
  subset, superset, or invented replacement);
- at least 4 distinct seeds per authorized opponent;
- every opponent covers the exact same seed set;
- exactly one seat-0 and one seat-1 cell for every `(opponent, seed)` pair;
- unique cells in canonical `(opponent_id, seed, seat)` order;
- exact bounded nonnegative integer own/rival scores for control and candidate;
- no caller-supplied aggregate or claimed delta fields;
- execution authority equal to the promotion manifest and release archive pair;
- nonnegative aggregate paired margin delta; and
- nonnegative paired margin delta **for each authorized opponent separately**.

The opponent-local floor prevents one favorable opponent from laundering a
regression against another. The receipt serializes each authorized opponent's
cell count, control/candidate margin sums, and delta, plus the global sign/count
metrics and canonical panel digest.

```bash
python candidates/v5/promotion-gate/economics_gate.py economics-report.json \
  --output economics-receipt.json
```

## Release transaction

`release_transaction.py` is the pointer-transition authority in this directory.
Version 4 keeps the existing promotion replay, V4 trusted-base replay,
source/archive binding, expected-old transaction, and atomic commit semantics,
and requires `--economics-report`.

The release transaction replays `economics_gate.validate_report()` against the
same candidate/control, engine/opponent-pack, and old/new archive authorities
already authenticated by the transition. It redundantly requires the exact
Apex+Arlene roster and registry blob, checks the opponent-local arithmetic and
nonregression floors, and binds the roster, registry authority, per-opponent
aggregates, raw report SHA-256, and canonical panel digest into the `v5tx:`
transition identity.

Module custody is source-real: `_load_module()` reads each Python authority once
and executes the **captured authenticated byte buffer** via `compile`/`exec`.
It never authenticates one read and then asks `exec_module(path)` to perform a
second path read. Tests cover both a path swap and deletion after the first read.

Negative-global, negative-per-opponent, unauthorized-roster, uneven-seed,
missing-seat, duplicate, stale-archive, wrong-pack, cross-build, or source-path
race cases fail before a release pointer can move.

This generic firewall is intentionally only the incumbent/control economics
subgate. The separate V3.1 champion-ratchet owns the final champion objective;
no V3.1 floor semantics are duplicated here.

Exit status is `0` only for a PASS receipt. Invalid, ambiguous, incomplete,
cross-wired, or economically regressive evidence exits `2`.
