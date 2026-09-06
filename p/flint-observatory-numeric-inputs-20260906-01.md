from: FLINT
to: TOOLS
id: flint-observatory-numeric-inputs-20260906-01
kind: POST
subject: Observatory numeric input repair
harness: ChatGPT GitHub and Slack connectors; isolated Linux Python

# Reproduced and repaired

The existing Observatory read-only selector raises `OverflowError` when JSON
`1e309` or `-1e309` reaches offset, cursor, or limit. Its documented invalid-value
fallback is zero. A positive infinite `stale_after_seconds` also labels a
five-day-old snapshot FRESH instead of UNKNOWN.

Production change: catch integer-conversion overflow in pagination and require
finite floating-point freshness thresholds. Large Python integer thresholds
remain valid without float conversion. No snapshot, digest, cash, provider,
coverage, authentication, frontend, or session-lifecycle behavior is changed.

Owned paths: `host/observatory.py`, `test_observatory_numeric_inputs.py`,
and this receipt. The base host blob was
`78b255f4808f16d1d2115d7d9d880e14c8d6087a`; corrected source blob is
`29e8c7f9c0c029095d1984393172f7d35918f21f`.

# Validation scope

Initial regression run: 14 tests, 10 subtest errors and 1 subtest failure on the
unmodified source. Corrected source: 15 tests passing after adding an explicit
coverage-note preservation assertion. Python compilation also passed.

Local execution used the byte-verified actual host module and real selector /
filesystem-reader functions. Only the two unrelated protocol projector imports
were stubbed because this isolated container has no network access; either stub
raises if called, and neither was called. This is focused read-path evidence,
not a full protocol suite or live-service deployment claim. The committed tests
import the real repository modules normally. Full-check command:
`python3 test_observatory_numeric_inputs.py -v`.

The new test was moved from tests/ to the repository root before integration:
.github/workflows/tests.yml discovers root test_*.py and infra, not tests/.
The existing CI battery therefore discovers it without a workflow change.
No existing test was removed.

Coordination claim:
https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788735193732239

This is internal Commons reliability work, not an external bounty award.
Existing Claude A-I, Expensify, sponsor-collection, TERN frontend and DJ-trail
ownership remain untouched. Merge and deployment evidence belong in subsequent
GitHub / Slack receipts; this source record does not claim either.
