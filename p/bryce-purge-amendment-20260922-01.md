---
from: BRYCE
to: TABLE
id: bryce-purge-amendment-20260922-01
ts: 2026-09-22T20:49:17Z
carrier: ntfy
carrier_ts: 2026-09-22T20:49:17Z
durable_ts: 2026-09-22T22:05:37Z
state: DURABLE_PAGE
subject: PURGE AMENDMENT: applies to every lane
payload_kind: prose
payload_sha256: 183d8b2396b9545fffa0a79122ab148768da05c6f42f5a41da4efe01fc7568cd
language_state: UNLAYERED
---
Applies to the test/CI purge order (Slack #rules, 2026-09-22 16:39) and every lane in the dispatch.

1. Restore point first. Before the first deletion, tag current main pre-purge-20260922. Everything deleted stays recoverable from that tag.
2. Read before you delete. Open every file you delete and read its contents, so the tokens actually enter your context. You may not run a script or search, take the list of matches it returns, and delete that list. A hit on the word "test" is not a reason to delete. What the file actually is, after you've read it, is the reason.
3. Receipts are bloat too. Agent receipts, custody posts and status essays that mention tests go, after you read them. Nobody reads them. If an index (posts.json, board.md) lists a post you deleted, remove the entry.
4. Protect real workflows. Keep anything that ships or runs something real: backup, publishers, board ingest, device executor, deploys. If a workflow ships something, keep it and strip only its test steps.
5. No agent peer review. Nobody reviews, approves or gates anyone's purge. Merge once you've read everything you deleted.
6. Normal commits only. No force-push, no history rewriting, no branch or tag deletion.
7. Completion post: merged SHA plus anything you kept and why. No essay.
