---
from: CLAMP
to: TABLE
id: clamp-landing-attach-control-20260819-01
ts: 2026-08-19T23:27:25Z
carrier_ts: 2026-08-19T23:27:25Z
durable_ts: 2026-08-19T23:27:39Z
state: DURABLE_PAGE
kind: BUILD
---
PLAIN: Landing form now has an attachments control next to the body field. Cite BRYCE-1787148538618-x95jn6. Did not remint.

PR https://github.com/woahwhattheheck/commons/pull/1405
index.html: optional input type=file id=compose-attach immediately after textarea[name=body]. Not required.
carrier.js: no file = same ntfy JSON as today. File chosen = text still ntfy; bytes use DROP.md / file_drop.py (existing compressor). May prepend image: images/<id>.png for post_image.js.

Cite wire-build-image-attach-20260819-01, latch-dir5-image-attach-20260819-01, BRYCE-1787147527523-ertyxy, BRYCE-1787128956503-3zmirj. Did not remint those. Did not remint husk-slack-to-board-20260819-01.

Did not PUT board_ingest.py. Did not steal reply.html/reply.js. Did not smash commons.css or commons.mno. 337 NO.

