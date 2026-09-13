# Atomic Send Authority

This package closes the last pre-send conjunction gap between two existing controls:

1. the outbound evidence guard, which can say `ALLOW_NEW` but deliberately authorizes no side effect; and
2. the atomic buyer+offer lease, which proves one claimant won the seam but deliberately sets `external_send_authorized=false`.

`authority.py` consumes the **exact bytes** of both receipts plus a PII-minimized authority intent. It returns `SEND_READY` only when the guard is complete and exactly `ALLOW_NEW`, the lease is exactly held by the named claimant/claim, the permanent buyer+offer lease seam recomputes, the lease's `preflight_sha256` equals the guard payload receipt digest, the guard recipient hashes to the intent's `recipient_sha256`, exact receipt-file digests match the intent, and request/preflight/lease times are current.

Every failed or ambiguous binding is `HOLD`. `REPLY_ONLY` is never promoted into net-new authority. Neither prerequisite's own false authority bit may be true. The package performs no Gmail, Slack, provider, payment, or customer mutation and cannot claim that a send happened.

`SEND_READY` is permission for **one immediate provider mutation by the exact claimant/claim**. Provider SENT truth is still the completion receipt. Callers should persist both the authority receipt and the provider message ID; a later sender must start from fresh provider evidence, not replay an old authority receipt.

## Intent

```json
{
  "schema_version": "outbound-send-authority-intent/v1",
  "buyer_scope": "example.com",
  "offer_scope": "lims-migration-validation-pilot",
  "recipient_sha256": "<sha256 of the normalized recipient address>",
  "claimant": "Z-Example-123",
  "claim_id": "example-lims-zexample-20260913",
  "requested_at": "2026-09-13T14:40:00Z",
  "route_kind": "email",
  "guard_receipt_sha256": "<sha256 of exact guard receipt file bytes>",
  "lease_receipt_sha256": "<sha256 of exact lease receipt file bytes>"
}
```

No raw recipient, subject, body, credentials, customer notes, or message content are persisted by the authority intent/output.

## Run

```bash
python -m revenue.outbound_send_authority.authority \
  --intent intent.json \
  --guard-receipt guard.json \
  --lease-receipt lease.json \
  --out authority.json
```

Exit `0` means `SEND_READY`; exit `4` means a valid `HOLD`; exit `2` means invalid/tampered input or publication failure. `--out` is create-exclusive and refuses input aliases, symlinks, and overwrites. Tests run both ordinary and optimized Python.
