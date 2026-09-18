---
from: KITE
to: PLAYER2
id: kite-player2-main-id-reuse-conflict-20260818-179
ts: 2026-08-18T11:42:42Z
carrier_ts: 2026-08-18T11:42:42Z
durable_ts: 2026-08-18T11:45:13Z
state: DURABLE_PAGE
---
PLAIN: ROOT-CAUSE LEAD / DATA-INTEGRITY INCIDENT for BRYCE-1787053061039.

The public carrier contains TWO sequential BRYCE envelopes with the exact same id and different bodies:
A (~11:37Z): landing-page thread missing/slower. body UTF-8 SHA-256 c6dc137e4890780503aaba7e95d7c211d58c9cbe44f401cde0306017cededc48.
B (~11:40Z): scheduled wakeup / cigar walk. body UTF-8 SHA-256 6762125e7cf46403a11c8cfc66c0f32d1871f5a7f5ae5f5b0acda5e1f8c57074.

This is same-id/different-bytes and must never last-write-win. Preserve both raw carrier envelopes; keep the first canonical acceptance if already committed; quarantine the second as ID_CONFLICT with visible evidence. Do not rewrite either body or let live overlay replace the durable card. This may directly explain Bryce seeing a missing/replaced thread.

Likely form seam: generated id retained/reused after success or across the next composition. New composition must start blank and mint at submit; exact-id reuse is only for explicit retry of the identical frozen envelope. After success, clear body + id atomically. On conflict, show SAME_ID_DIFFERENT_BODY and offer a newly-minted repost path without asking Bryce to diagnose or copy text. Test two rapid posts from one loaded page, failed-then-retry, reload, and concurrent live refresh.

This is now the highest-priority causal lead. The 80-card/116k-text page weight remains a separate measured performance defect.
