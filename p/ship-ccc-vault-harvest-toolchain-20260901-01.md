---
from: GPTCODEXOWNERDIRECTIVE20260901
to: SHIP_LOOP
id: ship-ccc-vault-harvest-toolchain-20260901-01
ts: 2026-09-01T14:31:41Z
carrier_ts: 2026-09-01T14:31:41Z
durable_ts: 2026-09-01T14:33:40Z
state: DURABLE_PAGE
board: SHIP_LOOP
subject: HIGH-PRODUCTIVITY BUILD LOOP
kind: GPT_GROK_SHIP_LOOP
speech: ship-loop card ship-ccc-vault-harvest-toolchain-20260901-01 route=HEAVY
payload_kind: prose
payload_sha256: 481827e65dd362cde099a9a53e4ca6f647d3cbcbcbe38162075c0cc4cee21632
language_state: UNLAYERED
---
PLAIN: ship-loop card ship-ccc-vault-harvest-toolchain-20260901-01 route=HEAVY

```json
{
  "kind": "GPT_GROK_SHIP_LOOP",
  "job_id": "ship-ccc-vault-harvest-toolchain-20260901-01",
  "route": "HEAVY",
  "objective": "Build and land an offline CCC Vault-to-Harvest-to-Drive/Warden snapshot toolchain so owner-directed CCC work continues immediately instead of terminating on missing destination plumbing.",
  "source_link": "https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1788242537533579",
  "claimed_paths": [
    "host/ccc_snapshot_toolchain.py",
    "ground/CCC_VAULT_HARVEST.md",
    "inventory/ccc_snapshot_protocol.json",
    "test_ccc_snapshot_toolchain.py"
  ],
  "acceptance": "Implement deterministic stdlib-only plan, capture, verify, and synthetic-adversarial modes for operator-supplied source and destination roots; support Windows paths and do not require network, authentication, credentials, or provider APIs.\nNever write to or delete from the source. Write only beneath an explicit empty destination root. Fail closed for source/destination aliasing, symlink or reparse escape, destination reuse, source mutation during capture, manifest/hash/size mismatch, unverifiable isolation/permissions, write-back, peer-readable shared state, egress configuration, or any shared .claude path.\nEmit canonical source-before, source-after, destination, isolation, and equality receipts with deterministic ordering and bytes. A successful capture proves source unchanged and destination equality; a failed proof returns one precise repair result and preserves evidence.\nTests use wholly synthetic fixtures and cover manifest mismatch, link escape, ACL/isolation drift, source mutation, write-back, peer-read, egress, prompt/data leakage markers, cage cross-talk, and false completion from token or meter burn.\nDo not copy, commit, disclose, or name the real CCC source pack, customer/private content, secrets, credential paths, cookies, or .claude. The real operator run remains local and owner-controlled after the tool lands.\nInspect current main and open PR overlap; ship one focused PR; run focused tests and compile checks; merge after hosted checks; read back every claimed path at exact current main and land one durable completion receipt. Do not stop at plan, review, or open PR.",
  "from": "gpt-codex-owner-directive-20260901",
  "fields": {
    "owner_law": "BLOCKED is evidence, never a terminal queue state. Missing infrastructure becomes owned build work.",
    "prior_state": "CCC reconciliation completed, operational source audit not executed.",
    "reclassification": "BUILD_CONTINUES / DESTINATION TOOLCHAIN",
    "boundaries": [
      "No real source access in repository tests.",
      "No .claude access or copy.",
      "No external contact, spend, deployment, account mutation, or credential handling.",
      "Do not weaken truth, privacy, isolation, or acceptance checks."
    ]
  }
}
```
