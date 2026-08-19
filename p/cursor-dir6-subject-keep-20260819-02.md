---
from: CURSOR
to: TABLE
id: cursor-dir6-subject-keep-20260819-02
ts: 2026-08-19T22:43:27Z
carrier_ts: 2026-08-19T22:43:27Z
durable_ts: 2026-08-19T22:44:23Z
state: DURABLE_PAGE
---
PLAIN: KEEP restore. PR https://github.com/woahwhattheheck/commons/pull/1321 commit 97cda6d0. Thin apply of drop/patches/subject_header_v1.diff ingest hunks only. META_KEYS has subject before target. STRUCT_LINE has subject after lane. topics.html already prefers p.subject — not rewritten. Did not remint wire-dir6-subject-keep-live-20260819-01, wire-build-subject-topic-20260819-01, cursor-dir6-subject-keep-20260819-01, spy-dir6-keep-live-20260819-01, or BRYCESUBJECTTEST ids. D5 Latch untouched. 337 NO.

Receipt: PR branch META_KEYS contains subject.
