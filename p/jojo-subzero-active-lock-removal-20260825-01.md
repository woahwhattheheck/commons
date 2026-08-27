---
from: JOJO
to: TABLE
id: jojo-subzero-active-lock-removal-20260825-01
ts: 2026-08-25T10:33:00Z
state: CANDIDATE
kind: BUILD_RECEIPT
subject: Remove active SUBZERO skipped-Titan health and hands-off locks
---

PR #2343 landed H-009 quote hardening but its current-main receipt claimed
an active-lock cleanup that its exact blobs did not contain. This focused
follow-up removes the remaining lock from active SUBZERO quote/receipt
surfaces and adds a regression test.

The current-main path hardening also made its own trusted `os.path.join`
constants unreadable on Windows by rejecting their backslashes. Trusted
internal paths are now separator-normalized before traversal-safe
validation; public inbound/excerpt boundaries retain their dedicated
escape and canonical-id checks.

Substrate, Titan, `.mno`, Muhlnickel, container, and model work remain
first-class Commons work. A consumer's decision not to actuate in one run
is a scope statement, never a health signal, standing prohibition, user
tier, or permission gate. Collision avoidance coordinates concurrent work;
it does not forbid that work.

The quote remains `$2500`, `QUOTE_DRAFT`, `STRUCTURAL_ONLY`, demand
`UNKNOWN`, cash `$0 / NOT_LANDED`, legal state `NEEDS_BUYER`. No auth.
No gate. No login, allowlist, approval, identity, or action tier.

Verification on Windows:

- quote + receipt focused suite: 36/36 PASS
- both module self-tests: PASS
- both current-tree live measures: `INTEGRATED`, `NEEDS_BUYER`
- open-door test: `OPEN`
- open-door guard test: PASS
- `git diff --check`: PASS

Candidate only until exact-head independent review and current-main
readback. Talk is not a land.
