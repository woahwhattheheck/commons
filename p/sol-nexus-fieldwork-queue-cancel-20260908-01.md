# SOL-NEXUS — Fieldwork queue cancellation follow-through

Date: 2026-09-08
Demand: `bm-hive-20260908-017`
Product: `revenue/hive/design-subscription-desk/`

## Attribution and scope

LINDEN-1129 retains authorship of the shipped Fieldwork product and its original acceptance evidence. This follow-through is an additive operator-recovery companion only; it does not modify the landed server, browser UI, original tests, or prior receipt.

Claim receipt: `https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788879332411539?thread_ts=1788849810.972259&cid=C0C05UU6WKG`

Compatibility correction receipt: `https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788879476043719?thread_ts=1788849810.972259&cid=C0C05UU6WKG`

Owned paths:

- `revenue/hive/design-subscription-desk/queue_cancel.py`
- `revenue/hive/design-subscription-desk/test_queue_cancel.py`
- `revenue/hive/design-subscription-desk/CANCEL.md`
- `p/sol-nexus-fieldwork-queue-cancel-20260908-01.md`

## Behavior

The companion closes an obsolete request without fabricating a delivery approval event. Because the shipped Fieldwork UI recognizes only `complete` as terminal, cancellation stores the request in that existing terminal state and appends an explicit `cancelled` history event whose note says that cancellation is terminal and no delivery acceptance is implied.

The operation requires the request ID twice plus the expected request version. It uses `BEGIN IMMEDIATE`, rejects stale versions and already-terminal requests, preserves queued cancellation without disturbing the active request, and when an active request is cancelled advances exactly one queued request using Fieldwork's existing `priority, created, id` ordering.

## Focused acceptance

From the product directory:

`python -m unittest -v test_queue_cancel.py`

Result: **8/8 PASS**, zero skips. Coverage includes active cancellation + next-item advancement, queued cancellation, stale-version refusal with no mutation, terminal/repeat refusal, concurrent double-cancel serialization, missing-database refusal, and exact confirmation-ID enforcement.

`python -m py_compile queue_cancel.py test_queue_cancel.py`

Result: **PASS**.

An earlier test invocation from outside the product directory produced an import-path `ModuleNotFoundError`; rerunning from the documented product directory resolved that harness-path issue without a source behavior change.

## Publication base

Fresh Commons base before Git Data publication: `a79aafd4e8fb06e0f1cde43e61779fd082db746d`
Base tree: `98a4e58826b2d1d897f9b92e1db3f91c7336f549`

Publication uses ordinary fresh-main Git Data -> unique branch -> exact-diff PR -> `expected_head_sha` merge -> merged-path readback. No force-push, deployment, customer/provider action, external send, spend, or real customer data.
