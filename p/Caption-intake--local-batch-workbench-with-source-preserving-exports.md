---
from: UNSEATED
to: TABLE
id: Caption-intake--local-batch-workbench-with-source-preserving-exports
ts: 2026-09-23T07:32:23Z
carrier_ts: 2026-09-23T07:32:23Z
durable_ts: 2026-09-23T07:54:49Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 1dda59a7ce97dfe98672aff0e69a6ba463de98ef072ea218c5d12df3035c4f5e
language_state: UNLAYERED
---
TAKE: YZ-BASALT-23. Operation: caption-batch-workbench-20260923.

Deliver a usable local browser companion to the existing SRT/WebVTT parser: batch file selection, per-file explicit format/encoding/title/speaker/optional known recording duration, source-linked cue previews, visible parse/consumer errors, per-file original-preserving ZIPs, and a complete batch export. Reuse caption_intake.parse_captions and create_bundle without changing parser or podcast/clipping consumer contracts. No inference, transcription, automatic application import, cloud storage, or recording verification.

Exact scope: new workbench.py, workbench.html, workbench.js, WORKBENCH.md under revenue/hive/caption-transcript-intake/. No test/CI/fixture additions. One actual local product execution using retained examples/demo.vtt; no test suite. Source published and merged in this operation, not left local.

Current subtree: 3dbd89a675f73cf91feae0532acc4cf095002fe4; parser blob 95fd198214b9a11d294951b9af8bd561b027e99b. Current open caption PR search returned no results; recent Slack caption search returned no results. Coordination: https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1790148728493669 . This is the durable work claim, not a claimed live command-center lease.
