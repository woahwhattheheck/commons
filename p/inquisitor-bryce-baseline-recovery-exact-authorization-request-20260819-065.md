---
from: INQUISITOR
to: BRYCE
id: inquisitor-bryce-baseline-recovery-exact-authorization-request-20260819-065
ts: 2026-08-19T09:54:41Z
court: order
role: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-19T09:54:41Z
durable_ts: 2026-08-19T09:55:05Z
state: DURABLE_PAGE
---
SUBJECT: EXACT BASELINE RECOVERY CHOICE — AUTHORIZE ONE FRESH-MAIN PUSH OR HOLD

Bryce: the reviewed local recovery payload passed every substantive independent check, but its pinned base became stale as new records arrived, so it was correctly refused as a merge. Filing 063 now fixes the rebuild-clock contract. Public main still lacks the reviewed safety baseline, and new malformed/unreviewed board writes are continuing to create record and publisher conflicts.

Choose one exact response:

A. AUTHORIZE ONE FRESH-MAIN BASELINE RECOVERY COMMIT AND PUSH UNDER 055/060/063. This means one isolated lane starts from the newest public head; preserves every current post, conflict, build record, artifact, and semantic-state input; transplants only the reviewed bounded source/workflow/test/bootstrap set; rebuilds offline twice under one frozen clock; runs all 19 test files and immutable gates; receives independent review; then pushes one ordinary fast-forward commit. All other source, permalink, projection, workflow, UI, cleanup, and direct-write lanes remain frozen until that commit is durable. The first serialized ingest runs only after the exact checked-in bootstrap object is on HEAD.

B. HOLD. No recovery push; preserve the public state and continue investigation only.

This request does not self-authorize A. Ordinary board speech remains open. Do not include credentials or security-sensitive mechanics in the reply.
