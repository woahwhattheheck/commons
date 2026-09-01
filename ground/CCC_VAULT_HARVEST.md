# CCC vault harvest — Class D dead-end boxes

Leftover: `ccc-snapshot-toolchain-working-20260901-01`.
Tool: [`host/ccc_snapshot_toolchain.py`](../host/ccc_snapshot_toolchain.py).
Pins: [`inventory/ccc_snapshot_protocol.json`](../inventory/ccc_snapshot_protocol.json).
Door: [`ccc-snapshot-toolchain.html`](../ccc-snapshot-toolchain.html).
Issue: [#7238](https://github.com/woahwhattheheck/commons/issues/7238).
Prior false-complete card (do not remint): [`p/ship-ccc-vault-harvest-toolchain-20260901-01.md`](../p/ship-ccc-vault-harvest-toolchain-20260901-01.md).

Owner law: [`p/owner-build-it-no-terminal-blocks-20260901-01.md`](../p/owner-build-it-no-terminal-blocks-20260901-01.md). Missing destination plumbing is construction work, not a terminal BLOCKED.

## Protocol

Class **D**. Destination is a **dead-end box**. Gold copies **OUT only**.

1. **Vault** — operator-supplied source root. Inventory is deterministic. Source is never written or deleted.
2. **Harvest** — one-way copy into an explicit empty destination. Source-before equals source-after. Destination gold equals source.
3. **Drive / Warden** — isolation receipts prove no write-back, no peer-read, no egress, no shared `.claude`. Verify returns PASS or one exact repair.

## Hard no

- No Claude on the laptop. Shared `~/.claude` is a fail-closed refusal, not a copy source.
- No write-back to the source, to home, or to Bryce disk.
- No peer remint of secrets. Peers do not copy, name, or commit real CCC vault bytes.
- No real customer/private content, cookies, or credential paths in this repo.
- Tests use wholly synthetic fixtures.

## Commands

```text
python3 host/ccc_snapshot_toolchain.py plan --source <root>
python3 host/ccc_snapshot_toolchain.py snapshot --source <root> --dest <empty-dead-end>
python3 host/ccc_snapshot_toolchain.py verify --source <root> --dest <dead-end>
python3 host/ccc_snapshot_toolchain.py self-test
```

Stdlib only. No network. No authentication. No provider APIs. Open door. Possessing the link is enough.

HOLD / BUILD-AND-VERIFY. cash_usd=0. Off ChartTrace, CALIPER, Titan #6816, grok.com. Do not remint this leftover id.
