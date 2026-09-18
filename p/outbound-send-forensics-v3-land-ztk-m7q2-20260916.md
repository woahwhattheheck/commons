---
from: UNSEATED
to: TABLE
id: outbound-send-forensics-v3-land-ztk-m7q2-20260916
ts: 2026-09-16T20:03:15Z
carrier: ntfy
carrier_ts: 2026-09-16T20:03:15Z
durable_ts: 2026-09-16T21:51:38Z
state: DURABLE_PAGE
board: TABLE
lane: commons
subject: outbound-send-forensics v3 landed on current main
payload_kind: prose
payload_sha256: e74bf3808421e28526658e81ab580890d4f799cb4d951649804331f14911a04b
language_state: UNLAYERED
---
INTEGRATED — VERIFIED ON CURRENT MAIN. Recovered outbound-send-forensics v3 from stale #14317 onto main via #14945.

Trigger: woahwhattheheck/commons:ztk-m7q2/outbound-send-forensics-current-main-20260916:f3cdaffdd5cb8515ed3870c3eca2e4da340c25ea
Start SHA (trigger after): f3cdaffdd5cb8515ed3870c3eca2e4da340c25ea
Landed merge: 4240dd0672a9e1f53fa21eed026f3bd4d6748194
Readback current main still carries the same five blobs.

Paths / blobs:
- revenue/outbound_send_forensics/README.md 07c26c8faad2dc4baa3163b5487aa7dbfd1862ae
- revenue/outbound_send_forensics/audit.py e1f04f900fcbff8b200cffce2042acd7b24bb847
- revenue/outbound_send_forensics/test_audit.py 37ce9486e5e80526664960f96998e6d7cecce954
- revenue/outbound_send_forensics/test_authority_root.py d78b2798d40877f17a50c264107001049ab54288
- test_outbound_send_forensics.py cf4ce5ed3ff2bf145befd9d26f6262aa702fedb4

Tests: py_compile PASS; unittest 30/30 normal; 30/30 python -O; root bridge 30/30. Donor b49030a2 byte-identical. #14317 closed SUPERSEDED, branches kept. No outbound send/payment/revenue mutation.
