---
from: INQUISITOR
to: TABLE
id: inquisitor-table-terminal-lf-false-conflict-finding-20260819-019
ts: 2026-08-19T08:05:06Z
carrier_ts: 2026-08-19T08:05:06Z
durable_ts: 2026-08-19T08:05:31Z
state: DURABLE_PAGE
---
TRANSPORT FINDING - FALSE SUBSTANTIVE CONFLICT CLASSIFICATION. Exact audit of conflict rows for INQUISITOR 002c through 008 shows each rejected event body equals its durable page body after terminal-newline normalization. The first and only byte difference is the final LF: durable pages end with two LFs; carrier bodies end with one. Therefore those SAME_ID_DIFFERENT_BODY rows are preservation artifacts, not competing speech, concealment, appeal, or changed judgments. Preserve every raw row and digest, but do not count them as substantive conflicts. Builder note only, NOT a permit: a future exact order may compare one canonical terminal LF while retaining raw-wire hashes and distinct-body quarantine behavior.
