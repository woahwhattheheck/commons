# Service Change Order Desk

A deterministic, standard-library-only custody rail for proposed changes to an already accepted service baseline.

The desk reconciles exact scope, price, tax/discount, milestone, schedule, evidence, and human-decision state into a canonical JSON receipt and buyer-facing Markdown. It is offline and performs no provider or customer mutation.

## Trust and authority boundary

The caller must provide the accepted baseline's SHA-256 through a separate trusted channel. The desk recomputes the canonical baseline commitment and fails closed when it differs.

The generated receipt is **integrity-only**. Its self-digests prove that the package is internally coherent; they do not prove who authored the baseline, change request, evidence, or decision. Even an operator-recorded `APPROVED` state leaves every authority bit false:

- no send or signature authority;
- no contract-amendment or buyer-acceptance inference;
- no checkout, payment, provider-write, scheduling, dispatch, fulfillment, or deployment authority;
- no cash or recognized-revenue claim.

A self-digested package is not a source-authentication root. Systems needing source authority must bind the input commitments to an independent authenticated evidence channel.

## Contract

Inputs are strict JSON: duplicate keys, floating-point/non-finite numbers, unknown fields, non-canonical Unicode, secret-shaped keys/values, and email/phone-shaped values are rejected. Money is integer cents only and is formatted without binary floating point.

The accepted baseline binds:

- baseline ID/version and three-letter currency;
- accepted timestamp and scope digest;
- exact line-item arithmetic, discount, tax, subtotal, and total;
- dated milestones whose amounts equal the baseline total;
- acceptance evidence plus other content-addressed evidence references.

A change request binds:

- the external baseline commitment and exact baseline ID/version;
- change ID/version and required prior-change commitment for revisions;
- exact price deltas and resulting total;
- schedule delta and resulting end date;
- milestone deltas and nonnegative resulting milestone amounts;
- expiry, scope-delta digest, and evidence references.

The append-only event chain uses optimistic state and change-version fences:

```text
DRAFT --SUBMIT_FOR_REVIEW--> READY_FOR_HUMAN_REVIEW
DRAFT --CANCEL--> CANCELLED
READY_FOR_HUMAN_REVIEW --APPROVE--> APPROVED
READY_FOR_HUMAN_REVIEW --REJECT--> REJECTED
READY_FOR_HUMAN_REVIEW --REQUEST_REVISION--> REVISION_REQUESTED
READY_FOR_HUMAN_REVIEW --CANCEL--> CANCELLED
```

Decision events must cite a content-addressed `buyer_decision` evidence reference. Duplicate event IDs are replay-safe only when the payload is byte-semantically identical; changed-payload reuse fails closed.

## Run the deterministic fixture

From the repository root:

```bash
python -m revenue.service_change_order_desk.cli fixture \
  --output-dir /tmp/service-change-order-fixture
```

The fixture writes strict input JSON, a `READY_FOR_HUMAN_REVIEW` package, an operator-recorded `APPROVED` package, Markdown, verification output, and an acceptance manifest.

Current exact fixture anchors:

- baseline commitment: `efd565fbfb09f9617b8995a1ffbc73beb225a14a89f6d2f8fdc807721bb06d4c`
- ready package SHA-256: `49bd9c0d67a2e015b02519d95151f53fa8be55b5a940ffa21c5968593ea60522`
- acceptance manifest SHA-256: `88f3c34de776af4ec52fc43abf9256afe363028e8d62aadf995f71b768121586`

Two independently generated fixture directories must be byte-identical.

## Build a package

```bash
python -m revenue.service_change_order_desk.cli package \
  --baseline baseline.json \
  --change change.json \
  --events events.json \
  --expected-baseline-sha256 <trusted-sha256> \
  --evaluation-time 2026-09-13T10:00:00Z \
  --output-dir /tmp/change-order
```

`evaluation-time` is a caller-supplied trusted UTC timestamp. The command exits `0` for a structurally valid non-HOLD package and `2` for a HOLD or CLI error. It writes atomically and refuses symlink input/output targets.

Verify a package:

```bash
python -m revenue.service_change_order_desk.cli verify \
  /tmp/change-order/change-order-package.json
```

Verification closes the receipt schema, recomputes receipt/package/Markdown digests, replays the full event chain, rechecks exact arithmetic, and enforces the all-false authority ceiling. Verification remains an internal-integrity result, not source authentication.

## Test

```bash
python -m py_compile revenue/service_change_order_desk/*.py
python -m unittest revenue.service_change_order_desk.test_desk -v
python -O -m unittest revenue.service_change_order_desk.test_desk -v
```

The 35-case hostile suite covers duplicate JSON keys, float/nonfinite input, external baseline drift, exact-cent values near the safe-integer ceiling, money/schedule/milestone mismatch, version supersession, stale/expired changes, secret/PII refusal, event replay and payload conflicts, optimistic state/version fences, decision-evidence binding, event-chain tampering, receipt-schema injection, Markdown/package tampering, and attempted authority escalation.
