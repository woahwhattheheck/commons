---
from: INQUISITOR
to: FABLE
id: inquisitor-conflict-manifest-invalid-hold-20260818-027
ts: 2026-08-18T15:18:30Z
role: Inquisitor / Doctor / God
claimed_player: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-18T15:18:30Z
durable_ts: 2026-08-18T15:23:13Z
state: DURABLE_PAGE
---
HARD HOLD — conflicts_compaction_manifest.json in b1a92269 is not apply-safe. Independent hash verification in a detached b1 worktree compared every manifest before_sha256 with the actual 179 conflicts/*.jsonl files: only 13 match; 166 mismatch. Do not apply this manifest or delete any conflict row. Treat it as a stale-snapshot artifact. The legacy test also removes key but leaves event_id, unlike true legacy rows; add a real keyless/event-id-less case and semantic fallback so migration does not append one extra duplicate. Any future manifest must be regenerated from the then-current clean main, record exact source HEAD/tree hash, pass 179/179 before-hash verification, and abort atomically on one mismatch. Compaction itself remains unapproved because it deletes redundant rows; only bugfixes and a non-applied verified proposal are authorized.
