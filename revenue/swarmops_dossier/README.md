# Commons SwarmOps Evidence Dossier

This product turns **owner-curated evidence** about Commons into a deterministic, prospect-safe demo dossier. It exists to sell what Commons can actually demonstrate without collapsing repository activity, queued CI, outbound transport, buyer acceptance, payment, or recognized revenue into the same claim.

## What it proves

Each input row binds one capability to a typed immutable source reference, SHA-256, observed state, observation time/freshness, release class, and bounded factual claim. The compiler separates rows into `DEMONSTRATED`, `LIMITED`, `HELD`, or `UNKNOWN`; required capabilities must have current prospect-safe technical evidence or the dossier is `HOLD`.

Commercial truth has a separate trust root:

- `SENT_NOT_ACCEPTED` requires a provider receipt and never means acceptance.
- `BUYER_ACCEPTED` requires a buyer-receipt row **and** an independently retained typed trust record for that source ID.
- `PAID` requires a payment-receipt row **and** an independently retained typed trust record for that source ID.
- `REVENUE_RECOGNIZED` requires an accounting-receipt row **and** an independently retained typed trust record for that source ID.

A packet cannot authenticate its own commercial receipt. The out-of-band trust object binds exact `source_id + source_sha256 + source_kind + observed_state + source_ref`. A correctly hashed receipt cannot be relabeled across buyer/payment/accounting roles. Without an exact typed match, a commercial row is limited and external commercial truth remains false. Wrong digests stay limited; unused or malformed trust entries fail closed. The output v2 receipt binds `trusted_commercial_receipts_sha256`, so verification under a substituted authority map fails.

No state implies another. A merged PR cannot imply payment; a checkout cannot imply payment; a provider send cannot imply buyer acceptance; queued/running CI cannot become green.

## Prospect boundary

`INTERNAL_ONLY` evidence never appears in the prospect projection. `OWNER_APPROVAL_REQUIRED` cannot satisfy a required capability. Prospect-safe text is screened for common credential/private-path shapes. This is a conservative publication boundary.

## Determinism and verification

The output contains canonical JSON, a content-addressed v2 receipt, deterministic Markdown, exact packet/policy digests, and the trusted-commercial authority digest. The offline verifier recompiles from the original packet + policy + trusted `as_of` time + the independently supplied trusted-commercial receipt map. Input JSON rejects duplicate keys and non-finite numbers. CLI input must be a bounded regular file; outputs are create-exclusive and will not overwrite an existing file.

## Run

```bash
python -m revenue.swarmops_dossier.acceptance
python -m unittest revenue.swarmops_dossier.test_engine
python -O -m unittest revenue.swarmops_dossier.test_engine
```

Compile and verify without commercial authority (commercial truth remains false):

```bash
python -m revenue.swarmops_dossier.cli compile packet.json policy.json \
  --as-of 2026-09-13T14:00:00Z --json-out dossier.json --markdown-out dossier.md
python -m revenue.swarmops_dossier.cli verify packet.json policy.json dossier.json \
  --as-of 2026-09-13T14:00:00Z
```

To permit a commercial state to become demonstrated, supply a **separate** strict JSON object from the validation host on both compile and verify. Each source ID maps to a typed record, not a bare digest:

```json
{"payment-1":{"source_sha256":"<sha256>","source_kind":"PAYMENT_RECEIPT","observed_state":"PAID","source_ref":"retained:receipt1"}}
```

```bash
python -m revenue.swarmops_dossier.cli compile packet.json policy.json \
  --as-of 2026-09-13T14:00:00Z --trusted-commercial-receipts trusted.json \
  --json-out dossier.json --markdown-out dossier.md
python -m revenue.swarmops_dossier.cli verify packet.json policy.json dossier.json \
  --as-of 2026-09-13T14:00:00Z --trusted-commercial-receipts trusted.json
```

## Authority ceiling

Offline owner-review evidence only. It does **not** authorize email/Slack/customer contact, provider/account access, credentials, deployment, proposals/submissions, pricing/staffing/legal/compliance commitments, signatures/contracts, spend, payment actions, buyer-acceptance claims, cash assertions, or revenue recognition.
