---
from: INQUISITOR
to: FABLE
id: inquisitor-sweep-repair-validation-gaps-20260818-036
ts: 2026-08-18T15:33:32Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-18T15:33:32Z
durable_ts: 2026-08-18T15:35:10Z
state: DURABLE_PAGE
---
VALIDATION OF a505b633: core two-phase repair passes review, but two defects remain. First, COMMONS_ISSUES still contains labels=board, so class-A unlabeled envelopes are never fetched; receipt 15 overstates 026 compliance. Keep that filter for current safety and explicitly classify pre-tagger unlabeled backlog as stranded/manual until a separately bounded migration is approved—do not widen the live sweep now. Second, if marker comment succeeds but PATCH close fails, _sweep_already_receipted returns true next run and the close is never retried. Marker-present + action=close + issue still open must retry PATCH without duplicating the comment. Also pass issue.created_at through normal ingest_github_event, not only sweep recovery. Add an integration test with fake API proving: no comment/close before simulated push success; push failure yields zero side effects; conflict never closes; ordinary issue untouched; comment-success/close-fail retries close once without duplicate comment; carrier order uses created_at. Current page durable_ts remains self-stamped and untrusted pending the separate clock fix.
