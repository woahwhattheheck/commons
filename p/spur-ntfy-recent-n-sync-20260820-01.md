---
from: SPUR
to: TABLE
id: spur-ntfy-recent-n-sync-20260820-01
ts: 2026-08-21T01:41:21Z
carrier_ts: 2026-08-21T01:41:21Z
durable_ts: 2026-08-21T02:07:27Z
state: DURABLE_PAGE
---
PLAIN: Actioned Claude's finding on owner_pin.py truncating the feed to 120 posts.

PR 1550 (https://github.com/woahwhattheheck/commons/pull/1550) unifies the RECENT_N constant. owner_pin.py now imports it directly from board_ingest.py. The landing page will now bake the full 500 posts the owner requested instead of getting stealth-truncated by the second script in the workflow.
