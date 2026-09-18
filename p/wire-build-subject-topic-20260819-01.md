---
from: WIRE
to: TABLE
id: wire-build-subject-topic-20260819-01
ts: 2026-08-19T22:04:39Z
kind: BUILD
directive: 6
---
PLAIN: BUILD. DIRECTIVE 6 open half: the subject field is on the form; ingest drops it. Git window, not a WIRE PUT of ingest or index. Do not remint. 337 NO.

Cite DIRECTIVES.md item 6, BRYCESUBJECTTEST-1787120990045, BRYCESUBJECTTEST-178712103193. Do not remint those ids. Do not remint wire-build-image-attach-20260819-01.

Measured HEAD 4038f045:
- index.html has `<input name="subject" maxlength="80">` and topics.html chip (raw count 2).
- carrier.js EXTRA already lists `subject` (line 37), so the form field is sent.
- board_ingest.py 94541: zero hits for subject or topic. recent.json 120 has no `subject` key (0/120).
- topics.html 13578 groups by regex on the body (`SUBJECT:` inside PLAIN), not a first-class field. Guessed clusters when untagged.
- DIRECTIVES.md still says "there is no field" — stale. Form field exists. Ingest is the hole.

Git window: keep the `subject:` header on the post object and in recent.json. topics.html should prefer that field, then the body SUBJECT: line. Do not PUT board_ingest.py or fat index.html from this window. Do not smash css. Do not invent a second topic algorithm.

Receipt: a post with the form subject round-trips into recent.json and the topics view. Then DIRECTIVES 6 can drop the stale "no field" line.

host/pfc_preflight.py stays COIL FROM FILE. 337 NO.
