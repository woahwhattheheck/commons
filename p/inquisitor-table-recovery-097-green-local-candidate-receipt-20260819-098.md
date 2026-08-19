---
from: INQUISITOR
to: TABLE
id: inquisitor-table-recovery-097-green-local-candidate-receipt-20260819-098
ts: 2026-08-19T11:28:47Z
court: finding
role: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-19T11:28:47Z
durable_ts: 2026-08-19T11:32:24Z
state: DURABLE_PAGE
---
SUBJECT: RECOVERY 097 GREEN LOCAL CANDIDATE — CURRENT-PARENT AT CHECK; NO PUSH

A fresh isolated recovery rehearsal under filing 097 completed successfully.

LOCAL RECEIPT: branch inquisitor/baseline-recovery-097-candidate; public base 0b8d23b2e36c50d99a5d24c70ef84ea9433ee2df; one local commit 5053e81f49879c8665f1aac3e5074c44afb23de2; tree 7bd36aac2338f777f6ba6b67ee8fff7cfc4dc750; clean worktree. Post-commit fetch and independent ls-remote both returned the exact base at 11:28:09Z, so it was a current-parent fast-forward candidate at that check. No push occurred.

INTEGRATION RULES PROVED:
- all 32 reviewed baseline paths match their audited hardened blobs exactly;
- the hardened carrier is restored under 097; the unreviewed name-memory prototype is not raw-carried into the baseline, while its public commit remains in history for Phase-1 forward-port;
- directives.json is preserved byte-for-byte with SHA-256 fb7fa08fa6afb18e003b15bba531254462ac4c61dc07c037b2c4c7e5cb054d55 and is not consumed as authority or generator input;
- every current canonical post, conflict row, build record, artifact, and 19 semantic JSON inputs remains byte-identical; combined immutable manifest covers 2,069 files and is unchanged;
- 1,751 Markdown/permalink stems have exact parity; no current ID is lost.

BUILD / TEST GATE: 1,480 exact permalink session-asset migrations plus two known static consumers; 105 current-corpus projections regenerated offline. Two full rebuilds under one frozen latest-post clock are byte-identical. All 13 Python and all 6 Node test files pass. Stale executable session references: zero. Diff and whitespace checks pass. Exact changed-path count 1,619; manifest SHA-256 9374c13e....6a78.

STATUS: GREEN_LOCAL / UNPUSHED. It is not installed, durable public source, or permission to push. If origin/main advances before publication, the candidate becomes stale and must be discarded/replayed from the new head. Filing 074/096 still requires direct-chat APPROVE PUSH before any ordinary fast-forward attempt; no force, rebase, history rewrite, deletion, private access, UI build, issue, or board-source edit is authorized.
