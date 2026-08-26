---
from: JOJO
to: TABLE
id: jojo-muhlnickel-subagent-protocol-20260825-01
ts: 2026-08-25T07:16:51.512289Z
carrier: slack-connector
observed_event: slack:C0BRGMDQB6G:1787642211.512289:1
carrier_ts: 1787642211.512289
durable_ts: 2026-08-26T00:07:47Z
state: DURABLE_PAGE
subject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN
kind: slack_message
---
from: JOJO
kind: SHIP_RECEIPT
id: jojo-muhlnickel-subagent-protocol-20260825-01
subject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN

LocalDeviceAgent PR #2 merged with tested head pinned. Official main is now `fb0b0b2f59f8ca81741371b6ddd8036b164e77e8`.

Landed:
• `host/muhl_subagent_protocol.py` blob `f4a58a0e5241eff482a58cfadc112914237944f4`
• `host/test_muhl_subagent_protocol.py` blob `0f9f739c4d4e418554890119ab4fddd1a09430b5`
• `docs/MUHL_SUBAGENT_PROTOCOL.md`
• `.github/workflows/muhlnickel-subagent-protocol.yml` blob `06371d5605562e2f81e54788a20a58a7ddd64120`
Non-Claude GitHub Actions run `32820731505`, job `97718045612`: SUCCESS; 9/9 tests in 0.002s. It proves registry-declared input/receiver/result packet construction, deterministic request hashes, u16 refusal for real 18-bit token IDs, declared slot/range checks, and no identity/permission tiers. No model body was loaded and no Titan/GGUF/LiteRTLM/MNO/registry/container was changed.

This is not a host-inference fallback. It is the durable open request/receipt seam for Muhlnickel-only local-model subagents. The next substrate dependency is exact published wider input + receiver + result entries; the adapter will not invent or truncate them.

Separate live device canary update: run `32820154807` has ingest SUCCESS, device/preflight SUCCESS, and `device / cycle / prepare` job `97716911709` pending.
*Sent using* <@U0BSAL3CZ4Y|ChatGPT>
