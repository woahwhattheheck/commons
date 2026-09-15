# Commons SwarmOps Evidence Dossier

This product turns **owner-curated evidence** about Commons into a deterministic, prospect-safe demo dossier. It exists to sell what Commons can actually demonstrate without collapsing repository activity, queued CI, outbound transport, buyer acceptance, payment, or recognized revenue into the same claim.

## What it proves

Each input row binds one capability to a typed immutable source reference, SHA-256, observed state, observation time/freshness, release class, and bounded factual claim. The compiler separates rows into `DEMONSTRATED`, `LIMITED`, `HELD`, or `UNKNOWN`; required capabilities must have current prospect-safe technical evidence or the dossier is `HOLD`.

Commercial truth has a separate trust root:

- `SENT_NOT_ACCEPTED` requires a provider receipt and never means acceptance.
- `BUYER_ACCEPTED` requires a buyer-receipt row **and** exact independently retained buyer-acceptance authority.
- `PAID` requires a payment-receipt row **and** exact independently retained payment authority.
- `REVENUE_RECOGNIZED` requires an accounting-receipt row **and** exact independently retained accounting-recognition authority.

A packet cannot authenticate its own commercial receipt. The host-owned authority generation is keyed by trusted `source_id`, but a digest match alone is insufficient: every authority record also binds the exact portfolio and the complete commercial evidence semantics — capability, source kind/reference/SHA-256, commercial state, observation time/freshness, prospect release class, required flag, and claim. The compiler requires an exact match before a commercial row can become `DEMONSTRATED`.

That prevents semantic transplantation. A retained payment receipt cannot be relabelled as buyer acceptance or accounting recognition; it cannot be moved to another portfolio/capability/reference, have its observation time refreshed or freshness window extended, or have an internal receipt re-released as prospect-safe merely because the source digest is unchanged. Malformed, internally inconsistent, or unused authority records fail closed. The output v3 receipt binds `trusted_commercial_receipts_sha256`, so verification under a substituted authority generation fails.

**A file supplied by the same CLI caller is not out-of-band authority.** The public CLI therefore exposes no commercial-trust option and always compiles/verifies with an empty commercial trust map. Commercial truth can be promoted only by a trusted host that has independently authenticated buyer/payment/accounting evidence and calls the engine API with its retained authority generation. `compile_dossier(..., trusted_commercial_receipts=...)` and `verify_dossier(..., trusted_commercial_receipts=...)` are host authority-injection boundaries; this package does not authenticate provider/accounting systems by itself.

No state implies another. A merged PR cannot imply payment; a checkout cannot imply payment; a provider send cannot imply buyer acceptance; queued/running CI cannot become green.

## Host authority record

The privileged engine API accepts a map keyed by trusted source ID. Each value must exactly bind the candidate commercial event. Conceptually:

```json
{
  "payment-source-id": {
    "portfolio_id": "commons-swarmops-public-demo",
    "capability_id": "commercial-event",
    "source_kind": "PAYMENT_RECEIPT",
    "source_ref": "retained:payment-provider-receipt",
    "source_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "observed_state": "PAID",
    "observed_at": "2026-09-13T13:05:00Z",
    "freshness_seconds": 86400,
    "prospect_class": "PROSPECT_SAFE",
    "required": false,
    "claim": "An independently retained commercial receipt exists for one event."
  }
}
```

This is a **trusted-host integration shape, not a CLI input format**. The trusted host is responsible for acquiring/authenticating the underlying external evidence independently before constructing the record. The engine validates structural and semantic consistency; it does not turn a caller-authored copy of this JSON into authority.

## Prospect boundary

`INTERNAL_ONLY` evidence never appears in the prospect projection. `OWNER_APPROVAL_REQUIRED` cannot satisfy a required capability. Prospect-safe text is screened for common credential/private-path shapes. This is a conservative publication boundary.

## Determinism and verification

The output contains canonical JSON, a content-addressed v3 receipt, deterministic Markdown, exact packet/policy digests, and the typed trusted-commercial authority digest. The engine verifier recompiles from the original packet + policy + trusted `as_of` time + the independently supplied authority generation. Input JSON rejects duplicate keys and non-finite numbers. CLI input must be a bounded regular file; outputs are create-exclusive and will not overwrite an existing file.

## Run

```bash
python -m revenue.swarmops_dossier.acceptance
python -m unittest revenue.swarmops_dossier.test_engine
python -O -m unittest revenue.swarmops_dossier.test_engine
```

The CLI is deliberately **unprivileged**: commercial truth remains false even if the packet labels a row `BUYER_ACCEPTED`, `PAID`, or `REVENUE_RECOGNIZED`.

```bash
python -m revenue.swarmops_dossier.cli compile packet.json policy.json \
  --as-of 2026-09-13T14:00:00Z --json-out dossier.json --markdown-out dossier.md
python -m revenue.swarmops_dossier.cli verify packet.json policy.json dossier.json \
  --as-of 2026-09-13T14:00:00Z
```

There is intentionally no `--trusted-commercial-receipts` CLI flag. A validating host that truly owns independently authenticated buyer/payment/accounting readback must inject its retained typed authority through the engine API; merely writing a second JSON file beside the candidate packet is not authentication.

## Authority ceiling

Offline owner-review evidence only. It does **not** authorize email/Slack/customer contact, provider/account access, credentials, deployment, proposals/submissions, pricing/staffing/legal/compliance commitments, signatures/contracts, spend, payment actions, buyer-acceptance claims, cash assertions, or revenue recognition.