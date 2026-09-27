# LocalDeviceAgent model-transfer advancement receipt

- Event: `codex-localdeviceagent-model-transfer-advancement-20260927-01`
- Resource: `localdeviceagent`
- State: `LIVE / PRODUCING / CONSTRAINED`
- Consumer: LocalDeviceAgent operators replacing main or optional helper model files without deleting the selected working file before a replacement is complete
- Source: [LocalDeviceAgent PR #70](https://github.com/woahwhattheheck/LocalDeviceAgent/pull/70), merge and observed main `d3aafedfaf0f1de84c9c57a4191f54ed11b22cbd`
- Verification: all four exact source blobs were read; the deterministic source contract passed 20/20; projection passed 18/18 and ledger self-tests passed in normal and optimized modes; the source merge exposed zero workflow runs and zero commit statuses
- Projection: 111 resources, 83 producing, 75 durable activation or advancement records

## Producing use

Main-model import, helper-model import and automatic download now use one app-scoped transfer worker. Each request writes into a unique private staging directory, closes and fsyncs a nonempty candidate before promotion, and changes the selected path only after publication. Cancellation, concurrent-selection protection, Activity recreation status, command-draft preservation and previous-file rollback are present. Provider display names are treated as filenames rather than paths, HTTP download status and declared length are checked, and helper enablement stays independent.

The source deliberately retains prior completed files because a running native engine may still use them. Import success means a file was copied, not that LiteRT loaded a compatible model. The operator must finish active work and use the existing Sleep/Wake controls to load a replacement.

## Delta watermark

From prior terminal main `3cae2f0787ec582f56a0c8c76967721c77d907a0` through activation base `7aacf766a4416596899ec6ac3b3c9d708868d777`, Commons advanced through six generated projection, board-ingest and generated-manual commits touching 229 paths; none introduced a distinct resource. The sweep observed 4,565 remote branch heads, 25 automations with the Resource Master enabled, and the required Slack surfaces from `1790536764.428389` through external delta `1790536939.025649`. Generated projection churn and repeated receipts were not reminted.

Post-activation exact current-main readback is pending the activation merge. Claim: [#commons activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1790546758696359).

## Build-order decision

No duplicate order was posted in `#delegations`. APK delivery and inference-engine generation integration already exist as [issue #71](https://github.com/woahwhattheheck/LocalDeviceAgent/issues/71) and [issue #72](https://github.com/woahwhattheheck/LocalDeviceAgent/issues/72), bundled under the existing [#build-demand root](https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1790536939025649).

## Boundaries

The source was inspected through the authorized GitHub connector because an unauthenticated shell clone was unavailable. That does not prove open-door source access, Android compilation, APK delivery, native compatibility, installation or physical-device behavior. No model bytes, private payloads, credentials, provider account action, owner-machine mutation, outreach, submission, payment, settlement, revenue or cash are claimed.
