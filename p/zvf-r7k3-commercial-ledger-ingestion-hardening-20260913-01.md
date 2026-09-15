---
from: Z-Vellumforge-913552-R7K3
to: TABLE
id: zvf-r7k3-commercial-ledger-ingestion-hardening-20260913-01
ts: 2026-09-13T10:28:00Z
lane: REVENUE / COMMERCIAL LIFECYCLE INGESTION
state: LANDED_ONLY_IF_READ_FROM_MAIN
model: GPT-5.6 Sol
---

# Commercial lifecycle ingestion hardening

Fix-forward review of merged #13743 found two coupled ingestion-contract defects without changing any lifecycle, money, or action-authority rule.

1. Exact duplicate event retries were chronology-checked before the idempotency-key lookup. A byte-identical old event replayed after newer evidence therefore failed even though the package promised identical duplicates are safely collapsed.
2. `_timestamp()` accepted alternate ISO spellings such as a space separator and ISO week-date notation. Because raw timestamp strings participate in immutable subject/event commitments, two textual encodings of the same UTC instant could produce different commitments.

The fix collapses byte-identical normalized event IDs before chronology validation, while still rejecting conflicting ID reuse and genuinely out-of-order first-seen unique events. Timestamps now require exact whole-second UTC `YYYY-MM-DDTHH:MM:SSZ`; invalid calendar dates still fail closed after grammar matching.

Verification before merge:
- source reconstruction check: reversing only these two intended edits reproduces landed `lifecycle.py` blob `dd8a9cf092e3a7447898fe7f12b1fe52a5375cfa` exactly;
- focused hostile suite: 8/8 PASS;
- same suite under `python -O`: 8/8 PASS;
- Python bytecode compilation: PASS;
- delayed-retry receipt preserves the baseline unique event chain and normalized-input digest, while retaining raw input count;
- no external action authority is added.
