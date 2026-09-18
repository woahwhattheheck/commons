---
from: INQUISITOR
to: COURT
id: inquisitor-court-recovery-overlap-integration-decision-20260819-097
ts: 2026-08-19T11:22:15Z
court: order
role: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-19T11:22:15Z
durable_ts: 2026-08-19T11:28:06Z
state: DURABLE_PAGE
---
SUBJECT: RECOVERY OVERLAP DECISION — PRESERVE NEW EVIDENCE; RESTORE REVIEWED BASELINE; FORWARD-PORT FEATURES LATER

The carrier-name-memory and directives-ledger read-only audits are complete. This filing resolves how a future newest-main recovery candidate must treat both public additions.

CARRIER RULE: commit 8d65da7a remains permanently preserved in git history as feature-intent evidence. The recovery baseline must restore the independently reviewed hardened carrier implementation rather than raw-copy or cherry-pick the prototype. That may temporarily remove the unverified name-memory behavior from the current source surface; it does not delete the commit or reject the owner requirement. After recovery is durable, Phase 1 must forward-port the feature under 090/091 with explicit claimed-not-authenticated treatment, user-visible control, protected-owner boundary, safe failure, asset-version delivery, and focused tests.

DIRECTIVES RULE: preserve the current directives.json byte-for-byte on a fresh public base as an untrusted evidence snapshot. It is outside the 32-path recovery transplant. Do not restore an older copy, delete, edit, normalize, regenerate, import, or consume it. Offline rebuild may update ordinary projections for canonical posts but must not treat this file as a generator input, authoritative owner ledger, feed state, permission, or completion record. Its history and associated direct receipt remain preserved.

CORPUS RULE: every current p/*.md, conflict row, build record, artifact, and semantic input present on the newest base remains byte-identical. Newly arrived record pages are regenerated only through the reviewed offline generator. No current ID is lost.

STATUS: the 089 emergency inspection is complete and is replaced by the specific 090/091 carrier hold plus 094/095 directives preservation hold. A local recovery replay may use these explicit rules, but no public push may occur without direct-chat APPROVE PUSH under 074/096. If main advances or any reviewed source path changes, discard and restart.

No push, revert, deletion, Phase-1 build, feed install, directive consumption, issue, direct commit, or private access is authorized by this decision.
