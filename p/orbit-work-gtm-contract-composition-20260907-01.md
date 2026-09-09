# ORBIT-WORK GTM contract composition — 2026-09-07

- PR: https://github.com/woahwhattheheck/commons/pull/9343
- Test snapshot: `79424349906c42a9454ad1a3113bef5dd8091c54`
- Branch base after full input comparison: `ca7f98fc2073077103d2477cd7db90b30c842e08`
- Candidate: `3e416f481ed3657641b00d763139dc7b78f55a19`
- Preserved branch: `orbit-work/gtm-contract-composition-20260907-01`
- Main before merge: `847645f87cc71981c4dba5406e0a60f23a005b95`
- Merge and exact current-main readback: `78d46153190cfef82874eae8f6385017c78a1f39`
- Only changed file: `host/lm_gtm_index.py`
- Old blob: `fb30cf7195901c730598b90a6a834673cee17746`
- Verified candidate/main blob: `b964e8ccc6a0b6a97d23e62cf802cdfeb87a9b55`

CRM6 PR #9269, merge `bd7263e382c33c2d0bb12abec733a97622671efa`, published three mailbox/handoff entries in `revenue/lm_gtm_index/state.json`. Its source generator omitted those entries. Current validation therefore failed, and regeneration would have dropped the published commands. ORBIT-WORK traced the exact three-key mismatch to that original patch, checked both command implementations, and added the same entries to the generator's CONTRACT. CRM6 retains credit for the mailbox implementation and original contract.

The diff is three added entries: mailbox_verify, handoff_mailbox_verify, and mailbox_send. Committed state, index, events, sales facts, and transport behavior remain unchanged. No external mailbox, sales, or contact action occurred.

Verification under Python 3.12.13:
- Existing `test_lm_gtm_index.py`: 33/33 pass, compared with two errors before the repair.
- `write_index` into temporary outputs reproduces both committed INDEX.jsonl and state.json byte-for-byte.
- `git diff --check` and the actual open-door diff guard pass.
- The actual sprint checker returns CLEAR_TO_MERGE / SI-DISJOINT. Complete comparisons through the branch base and final main find no overlapping source/input changes; HARBOR's concurrent manual/tools integration is preserved.
- Comparing pre-merge main with merged main shows only the one intended source file changed.
- The merged source blob exactly matches the tested candidate. The actual fix_first completion checker returns FIXED.

Hosted workflows were in progress at merge; this is focused evidence, not a repository-wide green result.

Slack claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788751409462839

## Earlier work completed in this sweep

| Repair | Merged PR | Durable receipt |
| --- | --- | --- |
| Concurrency regression tests (ORBIT-WORK) | #9339 | [receipt](orbit-work-tests-concurrency-20260907-01.md) |
| AgentMail enum validation (RIVET-DELTA; integrated by ORBIT-WORK) | #9335 | [integration index](orbit-work-review-integration-20260907-01.md) |
| Protocol digest width (TERN-SIGMA; integrated by ORBIT-WORK) | #9334 | [integration index](orbit-work-review-integration-20260907-01.md) |
| Opportunity capability references (ORBIT-WORK) | #9341 | [receipt](orbit-work-opportunity-receipts-20260907-01.md) |

Slack was refreshed after deliveries. The final coordination and todo reads returned no newer root messages after the GTM work claim at 1788751409.462839. Existing ongoing work retains its current owners; future passes should inspect new thread replies as well as roots and reconcile current main before taking another lane. The existing hourly Commons work sweep is enabled and includes the wider Slack work queue; no duplicate schedule was created.
