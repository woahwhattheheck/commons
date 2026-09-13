# Commons SwarmOps Evidence Dossier

This product turns **owner-curated evidence** about Commons into a deterministic, prospect-safe demo dossier. It exists to sell what Commons can actually demonstrate without collapsing repository activity, queued CI, outbound transport, buyer acceptance, payment, or recognized revenue into the same claim.

## What it proves

Each input row binds one capability to a typed immutable source reference, SHA-256, observed state, observation time/freshness, release class, and bounded factual claim. The compiler separates rows into `DEMONSTRATED`, `LIMITED`, `HELD`, or `UNKNOWN`; required capabilities must have current prospect-safe technical evidence or the dossier is `HOLD`.

Commercial truth is intentionally independent:

- `SENT_NOT_ACCEPTED` requires a provider receipt and never means acceptance.
- `BUYER_ACCEPTED` requires a buyer receipt.
- `PAID` requires a payment receipt.
- `REVENUE_RECOGNIZED` requires a separate accounting receipt.

No state implies another. A merged PR cannot imply payment; a checkout cannot imply payment; a provider send cannot imply buyer acceptance; queued/running CI cannot become green.

## Prospect boundary

`INTERNAL_ONLY` evidence never appears in the prospect projection. `OWNER_APPROVAL_REQUIRED` cannot satisfy a required capability. Prospect-safe text is screened for common credential/private-path shapes. This is a conservative publication boundary, not a claim that hashes authenticate providers.

## Determinism and verification

The output contains canonical JSON, a content-addressed receipt, deterministic Markdown, exact packet/policy digests, and an offline verifier that recompiles from the original packet + policy + trusted `as_of` time. Input JSON rejects duplicate keys and non-finite numbers. CLI input must be a bounded regular file; outputs are create-exclusive and will not overwrite an existing file.

## Run

```bash
python -m revenue.swarmops_dossier.acceptance
python -m unittest revenue.swarmops_dossier.test_engine
python -O -m unittest revenue.swarmops_dossier.test_engine
```

Compile and verify:

```bash
python -m revenue.swarmops_dossier.cli compile packet.json policy.json \
  --as-of 2026-09-13T14:00:00Z --json-out dossier.json --markdown-out dossier.md
python -m revenue.swarmops_dossier.cli verify packet.json policy.json dossier.json \
  --as-of 2026-09-13T14:00:00Z
```

## Authority ceiling

Offline owner-review evidence only. It does **not** authorize email/Slack/customer contact, provider/account access, credentials, deployment, proposals/submissions, pricing/staffing/legal/compliance commitments, signatures/contracts, spend, payment actions, buyer-acceptance claims, cash assertions, or revenue recognition.
