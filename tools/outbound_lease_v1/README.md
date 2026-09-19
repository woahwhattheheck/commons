# Outbound Lease v1 verifier

This package is the **offline, mutation-free verifier/compiler** for the TokenJunkieLabs `#outbound-leases` v1 coordination rail.

Pinned protocol authority:

- Slack channel: `C0C2X8CSYEQ`
- protocol root: `1789718513.003999`

`#outbound-leases` is a **fallback visibility rail, not canonical custody**. A newer owner correction pins canonical custody to Commons `#14421` + `#15969/#15988`, with `#15944` owning fleet cutover. This code does not send email/Slack messages, contact providers, grant sales authority, move money, or infer revenue. It only turns a retained direct channel read plus separately-computed canonical-custody/provider/relationship/DNR gates into a deterministic preflight receipt.

## Why organization scope matters

The lock key is derived from the caller's canonical **organization root domain**, not an email address. Two routes for the same organization therefore share one key. Route and purpose are retained as separate privacy-safe fingerprints. This prevents the classic failure where one seat sees `sales@example.com` as unused after another seat already contacted `partner@example.com`.

The helper deliberately does **not** guess registrable domains. Callers must supply the organization boundary already used by their retained relationship evidence. This avoids silently treating `division.example.com`and `example.com` as the same or different party without an explicit policy.

## Commands

```bash
python tools/outbound_lease_v1/cli.py org-key systeminnovators.com
python tools/outbound_lease_v1/cli.py route-fp 'sales@systeminnovators.com'
python tools/outbound_lease_v1/cli.py purpose-fp 'Tennessee 31701-03850 paid specialist workshare'
python tools/outbound_lease_v1/cli.py verify snapshot.json
```

`verify` returns JSON with `coordination_clean`, the earliest visible winner, explicit blockers, pinned canonical-custody references, and a semantic SHA-256 receipt. `coordination_clean` is **not sufficient authority to send**; it is only a fail-closed preflight signal over supplied evidence. It fails closed when the direct channel read failed, history is incomplete, a later claim lost the timestamp race, an outcome is uncertain, provider/DNR gates are not clean, or a prior SENT generation lacks a genuine relationship event.

## Snapshot shape

```json
{
  "schema": "outbound-lease-v1/snapshot",
  "channel_id": "C0C2X8CSYEQ",
  "protocol_root_ts": "1789718513.003999",
  "read_ok": true,
  "history_complete": true,
  "canonical_custody_gate": "CLEAN",
  "provider_gate": "CLEAN",
  "relationship_gate": "CLEAN",
  "dnr_gate": "CLEAN",
  "candidate": {
    "key": "<64hex organization key>",
    "seat": "Z-Sol",
    "nonce": "opaque-session-nonce"
  },
  "messages": [
    {
      "ts": "1789719000.000001",
      "is_root": true,
      "text": "INTENT v1 key=<64hex> seat=Z-Sol nonce=opaque-session-nonce route=<64hex> purpose=<64hex> source=<receipt>"
    }
  ]
}
```

The separately-derived `canonical_custody_gate` accepts only `CLEAN`, `BLOCK`, or `UNKNOWN`; this verifier never computes or grants canonical custody itself. Provider/relationship/DNR gate values are `CLEAN`, `BLOCK`, `UNKNOWN`, or `EVENT_AUTHORIZES`. A prior `SENT` for the organization key requires `relationship_gate=EVENT_AUTHORIZES` before a later generation can become eligible. `OUTCOME_UNKNOWN` remains blocking unless a retained `INBOUND` reconciles the uncertainty and the relationship gate explicitly authorizes the new action.

## Terminal records

The verifier recognizes the protocol's exact v1 records:

- `SENT v1 key=... claim_ts=... evidence=...`
- `OUTCOME_UNKNOWN v1 key=... claim_ts=... evidence=...`
- `UNSENT_RELEASED v1 key=... claim_ts=... evidence=...`
- `INBOUND v1 key=... claim_ts=... evidence=...`
- `BOUNCED v1 key=... claim_ts=... evidence=...`
- `DNR v1 key=... claim_ts=... evidence=...`

An `INTENT` must be a channel root. Terminal records may be roots or replies but must bind an existing same-key claim timestamp and follow it chronologically. Conflicting primary terminals fail closed.

## Proof

Focused tests cover organization-vs-route identity, timestamp races, release/retry, uncertain outcomes, prior-SENT relationship gating, malformed records, incomplete history, provider/DNR holds, strict JSON parsing, deterministic receipts, real CLI execution, and symlink input rejection. Run both normal and optimized Python:

```bash
python -m unittest -v tools.outbound_lease_v1.test_protocol
python -O -m unittest -v tools.outbound_lease_v1.test_protocol
python -m py_compile tools/outbound_lease_v1/*.py
```
