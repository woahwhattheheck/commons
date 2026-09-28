# Slack native-revision current-truth projector — resource activation receipt

- Event: `codex-slack-native-revision-projection-resource-activation-20260926-01`
- Resource: `slack-native-revision-current-truth-projector`
- State: `LIVE / PRODUCING / CONSTRAINED`
- Consumer: canonical board and current-truth projections that ingest edited native Slack messages without rewriting append-only evidence
- Source: [PR #30104](https://github.com/woahwhattheheck/commons/pull/30104), head `5fd71e23a64fdee1981231201a3149876e238221`, merge `975c646886048f3a39c6295a2f4c007c4508aa75`
- Verification: both pinned source blobs matched current main; the deterministic synthetic revision suite passed 17/17 assertions normally and 16/16 optimized; both source modules compiled
- Projection: 111 resources, 83 producing, 73 durable activation records

## Producing use

Board ingestion now carries exact `event_ts` and `revision` values from issue envelopes. The correction projector groups valid native observations by exact workspace, channel and native message timestamp, selects the newest revision, links every earlier observation as superseded, and emits only the newest item in derived current-truth views. Original append-only `p/` records remain intact, explicit `supersedes` chains remain supported, malformed revisions are ignored, and work-item lifecycle is not inferred from message text history.

## Delta watermark

From prior terminal main `67695b6e8e42c037ec0004ec22202364b826e0d4` through activation base `d62a93ff19b2d6d9124d73de3fc690fe0706f246`: 24 commits, 23 non-merge commits, 356 changed paths and 4,565 reachable branch heads across 47 pages were observed. Required Slack surfaces were paginated from `1790450035.482459`; the pre-claim lower bound is the PR #30104 release receipt at `1790457064.418649`. Twenty-five automations were visible and the Resource Master remained enabled.

Post-activation exact current-main readback is `527a6f9da75efe312bc30fa6cea705f2e597aac2`: 26 commits, 25 non-merge commits and 360 changed paths since the prior terminal main. It contains activation [PR #30106](https://github.com/woahwhattheheck/commons/pull/30106); all four activation blobs and both source blobs match exactly. Claim: [#commons activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1790459951782469).

No new build order was posted. PR #30104 is already complete. Its observed connector response did not expose a native `edited.ts`, which is an external observation boundary rather than a proven local build gap, and a test-only order would create a forbidden verifier loop.

## Boundaries

This source reads retained evidence and computes derived truth; it does not write, edit, delete or poll Slack. A newer message revision supersedes an earlier message observation only—it does not prove that the represented task shipped or otherwise changed lifecycle state. No live connector edit timestamp, customer action, outreach, scheduling, provider write, submission, deployment, spend, payment, settlement, revenue, cash or owner-only action is claimed. No credentials, private account identifiers, customer data, private message bodies or private file names are persisted.
