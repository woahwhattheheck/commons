# UIowa selected-asset operator transfer bundle — resource activation receipt

- Event: `codex-uiowa-operator-transfer-resource-activation-20260926-01`
- Resource: `uiowa-operator-selected-asset-transfer-bundle`
- State: `LIVE / PRODUCING / CONSTRAINED`
- Consumer: the existing UIOWA-100 operator-handoff lane and a second internal operator who needs all eight declared synthetic CLI assets without a full repository checkout
- Source: [PR #30002](https://github.com/woahwhattheheck/commons/pull/30002), head `60b2e7fe204f8dfef91da1d27e70d459ad71f0a5`, merge `b5f271e0522d4856426c84a7cc7bd5702e14d577`; [completion PR #30006](https://github.com/woahwhattheheck/commons/pull/30006), head `ff14509fe8f85c41e61c45c682be4016f7188d32`, merge `21cb81c5f51d8dc958277eed5ba9bc684c8217e0`
- Verification: all seven pinned current-main source blobs matched; the focused handoff suite passed 8/8; a 382,540-byte archive with SHA-256 `2f541989e2d43f93eca906c38de248ae5f0d3e0c23e2da83e9d9e34bc351b8fb` preserved 55 source/input files and all eight selected assets; byte verification passed; the portable run completed 12/12 steps with 18 outputs and `execution_verified=true`; complete 4,843-byte handoff and 4,315-byte outcome reports were retained
- Projection: 110 resources, 82 producing, 72 durable activation records

## Producing use

The offline standard-library bundle creates a deterministic selected-asset ZIP, byte manifest and source-closure record, verifies its extracted bytes, and runs the existing UIOWA-100 synthetic sample from the portable package. It gives the existing operator-handoff lane a reviewable transfer unit without requiring a full checkout or a provider session.

## Delta watermark

From prior terminal main `942de9401f1a92610a9f9926707f8731100c1b75` through activation base `ef0345cd00c801656526ef4a4453dc52dabfdabf`: 236 commits, 170 non-merge commits, 519 changed paths and 4,565 reachable branch heads across 47 connector pages were observed. Required Slack surfaces were paginated from `1790429462.972139`; the pre-claim lower bound is `1790446724.849269`. Twenty-five automations were visible and the Resource Master remained enabled.

Post-activation exact current-main readback is `53f4e8e254411c0124a69c06ddd97632ca694c19`: 237 commits, 171 non-merge commits and 523 changed paths since the prior terminal main. It contains activation [PR #30102](https://github.com/woahwhattheheck/commons/pull/30102); all four activation blobs and all seven source blobs match exactly.

Claim: [#commons activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1790449275735329).

One evidence-backed repair order was posted: [UIOWA-100-RUN-EVIDENCE-CONTRACT-REPAIR-20260926-01](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1790449584110389). The existing hosted `uiowa-100-run-evidence` workflow is red on two stale test expectations after the selected-assets contract landed; the actual current-main eight-asset pack, verify and run operation passed locally. The order is test-contract repair only and excludes the working implementation and activation paths.

## Boundaries

All exercised inputs are synthetic. The checked-in revision label is operator-supplied and source authenticity is not established. A valid portable run is not a University finding, accepted scope, completed engagement, browser/native verification, buyer acceptance or authorization to act. This activation performed no outreach, scheduling, provider write, submission, deployment, spend, payment, settlement, revenue or owner-only action and persisted no credentials, private account identifiers, customer data, private messages or private file names. Hosted source workflow checks remain red on the two named stale tests and are not claimed green.
