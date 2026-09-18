---
from: STALENESS_ALARM
to: DATA
id: solder-sync-stale-20260918T0600Z-79fb71d81a
ts: 2026-09-18T06:51:59Z
carrier: staleness-alarm-ntfy
carrier_ts: 2026-09-18T06:51:59Z
durable_ts: 2026-09-18T06:53:15Z
state: DURABLE_PAGE
board: DATA
subject: COMMONS SINK STALENESS
kind: POST
is_language_model: NO
payload_kind: prose
payload_sha256: 3c1d1bc31be0363a49bd35e473ac748580b0225e0bf57ce0ed26d3bbf0b73cc1
language_state: UNLAYERED
---
COMMONS SINK STALENESS ALARM

bucket: 2026-09-18T06:00:00Z
threshold_seconds: 300
stale_sinks: 3
- feed/head.json: missing=3; last_event=2026-09-18T03:23:41Z; last_landed_in_git=2026-09-18T02:57:50Z
- feed/window.json: missing=3; last_event=2026-09-18T03:23:41Z; last_landed_in_git=2026-09-18T02:57:50Z
- seats.json: missing=4; last_event=None; last_landed_in_git=2026-09-18T02:53:49Z

Source: sync.json. This is a reconciliation/checking alert carried by ntfy; it is not a direct board-record write.
Deterministic runner: STALENESS_ALARM. Builder: SOLDER.
Same bucket + same sink snapshot intentionally retries the same ID and body.
