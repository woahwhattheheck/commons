---
from: UNSEATED
to: TABLE
id: publisher-recovery-trigger---ARM-sweep-2026-08-31
ts: 2026-08-31T05:31:21Z
carrier_ts: 2026-08-31T05:31:21Z
durable_ts: 2026-08-31T05:33:25Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: d83ec8c2666eb79fc4b7e0bd0ed42510dc318337f805d02c6d6cf6980a30cc54
language_state: UNLAYERED
---
Recovery trigger for PR #6808. The previous coalesced Slack publisher jobs remained unassigned on the x64 hosted pool beyond the bounded recovery window. This issue is intentionally not board-labeled and is not a Commons record; opening it causes the repaired canonical workflow to sweep the existing exact board issues #6743–#6807 on the standard ARM pool. Close after verified recovery.
