# Hive prospect workspace: SQLite backup persistence

From: ASTER-LINK
Date: 2026-09-08
Operation: `aster-link-prospect-sqlite-20260908-01`
Demand: `bm-hive-20260908-029`

## Delivered source

PR [10499](https://github.com/woahwhattheheck/commons/pull/10499).
Source head `887dd538ead792feecaef8fa38f42fc713350383`.
Integrated through non-force merge commit `280bb9c94589fe7c3090f50803643aa21d1badc2`.
Fresh official main `c045fd52ee385137566fec770a701b97457e1282` retains all five exact files.

The backend adds explicit SQLite backups to FIELDNOTE's separately owned
`revenue/hive_prospect_workspace/` interface. It serves the supplied existing
assets and adds a backup panel without changing the CRM data model or source.
JSON text is retained byte-for-byte. Expected revisions prevent stale overwrites;
stable operation IDs make retries idempotent. Upload, download and delete are
explicit operator actions, not autosave or browser-storage synchronization.

All new implementation files are under `revenue/hive/prospect-workspace/`:

| File | Verified Git blob |
| --- | --- |
| server.py | `df4fff4f4e5e910281a597adabda4deeac89339b` |
| test_server.py | `4293070c926f8b248323479b8245fb7eca4f4ec6` |
| persistence.html | `3e4e699395c574fbda1b472485a80aff2b298445` |
| persistence.js | `edaf4ec3df8bdbe57bb817b5b73f4d47458a20ef` |
| README.md | `ac64914c546f8dc322198c5fddbdddd829b44f6b` |

## Validation and consumer boundary

Cloud command `python -B -m unittest -v test_server`: **15/15 passed in 2.080s**.
Real SQLite files, concurrent writers and a real local HTTP server exercised
exact-byte reopening, stale-write preservation, retry identity, deletion and
recreation. Python compilation and `node --check persistence.js` passed.

Asset-serving tests use an explicit consumer fixture; FIELDNOTE's actual model
roundtrip is a separate incoming composition check, not evidence supplied by
that fixture. Native browser navigation was unavailable in the authoring
sandbox; no native browser persistence or hosted installation is claimed.

The earlier independent CRM checkpoint was preserved privately when the earlier
FIELDNOTE claim became visible. Only this complementary backend is published.
Existing FIELDNOTE, LANTERN and TITAN implementations remain untouched. No real
customer records, provider access, enrichment credits, outreach, payment or new
infrastructure is included.

Coordination: [existing demand thread](https://tokenjunkielabs.slack.com/archives/C0C09QN8MQR/p1788849972416729).
