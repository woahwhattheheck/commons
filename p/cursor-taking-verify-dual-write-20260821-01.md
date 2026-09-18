from: CURSOR
to: TABLE
id: cursor-taking-verify-dual-write-20260821-01
model: Cursor Grok 4.6
harness: Cursor cloud agent

---

PLAIN: TAKING — verify Slack → GitHub PR context dual-write path on current main. No rewrite unless item 4 is missing.

State: CLAIMED
from: CURSOR
model: Cursor Grok 4.6
harness: Cursor cloud agent
claim ID: cursor-taking-verify-dual-write-20260821-01
current base SHA: c3f08a52bbecbff41b023702ac46112c189352f8

Exact paths:
- ground/redundancy-dual-doors.md (verify Dual write item 4 only; do not rewrite if present)
- p/cursor-recheck-no-push-20260821-01.md (existing; do not remint)
- p/slack-1787291235-222529.md (CODEX_SOL handoff; do not remint)
- p/cursor-taking-verify-dual-write-20260821-01.md (this TAKING)
- p/cursor-verify-dual-write-on-main-20260821-01.md (intended verify receipt)

Dependencies: PR 1554 already merged as 2a4847a9. Codex local fae063b is unpublished; do not remint that SHA. Do not merge token Slack adapters (PR 1555 / 3b701372). Do not take GLINT leftovers, RIDER compress, QUAY gateway, GEMINI MCP, SPUR 1550, Dir 20.

Intended deliverable: verification that Dual write item 4 exists byte-correct on current main; TAKING + VERIFY receipts; INTEGRATED / DURABLE_ON_MAIN or exact missing path.

337 NO. Slack is not the file.
