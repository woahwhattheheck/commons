# Verified Paid Proof

`verified_paid_proof.py` converts independently evidenced commercial facts into the strongest sales proof that the evidence **and publication permissions** literally allow.

It exists because a settled payment is valuable commercial proof, but it is not a testimonial. Payment does not prove satisfaction, delivery acceptance, recommendation, measurable outcome, repeat business, or permission to disclose the buyer.

## States

- `HOLD` — settled payment is not verified, or a revocation blocks release.
- `PRIVATE_VERIFIED` — settled payment is verified internally, but no public paid-work claim is authorized.
- `PUBLIC_ANONYMOUS` — a public paid-work fact is permissioned, while customer identity remains withheld.
- `PUBLIC_NAMED` — public paid-work fact and customer identity are independently permissioned.

Every stronger detail remains independently gated: exact amount, delivery acceptance, logo, quote/testimonial, and every outcome claim.

## Strict input contract

The compiler accepts JSON only. It rejects duplicate keys, floats, JSON bools masquerading as integers, unknown/missing schema fields, timezone-free timestamps, unsourced settled payments, unsourced accepted delivery, unsourced quotes/outcomes, and permission grants that lack evidence references.

Money uses integer minor units plus an explicit `currency_decimals` value. A `SETTLED` payment requires positive `amount_minor`, a three-letter currency, a timezone-bearing `settled_at`, and at least one evidence reference.

Each permission is an object:

```json
{"granted": true, "evidence_refs": ["email:permission:public-proof"]}
```

A `true` permission with no evidence is invalid. `false` permissions may have an empty evidence list.

## Example

This fixture is synthetic. Do not commit real customer evidence or generated private proof to this public repository.

```json
{
  "schema_version": 1,
  "engagement_id": "eng.synthetic.001",
  "customer": {"display_name": "Synthetic Buyer", "logo_ref": null},
  "payment": {
    "status": "SETTLED",
    "amount_minor": 9000,
    "currency": "USD",
    "currency_decimals": 2,
    "settled_at": "2026-09-14T18:00:00-04:00",
    "evidence_refs": ["stripe:synthetic-payment"]
  },
  "delivery": {"status": "ACCEPTED", "accepted_at": "2026-09-14T18:30:00-04:00", "evidence_refs": ["email:synthetic-acceptance"]},
  "quote": {"text": null, "evidence_ref": null},
  "outcomes": [],
  "permissions": {
    "public_proof": {"granted": true, "evidence_refs": ["email:public-proof-permission"]},
    "payment_fact": {"granted": true, "evidence_refs": ["email:payment-fact-permission"]},
    "customer_identity": {"granted": false, "evidence_refs": []},
    "logo": {"granted": false, "evidence_refs": []},
    "exact_amount": {"granted": false, "evidence_refs": []},
    "delivery_acceptance": {"granted": false, "evidence_refs": []},
    "quote": {"granted": false, "evidence_refs": []}
  },
  "revocation": {"revoked": false, "evidence_refs": []}
}
```

Run:

```bash
python -m revenue.verified_paid_proof.verified_paid_proof input.json --out-dir out
python -m revenue.verified_paid_proof.verified_paid_proof input.json --public-json
python -m unittest \
  revenue.verified_paid_proof.test_verified_paid_proof \
  revenue.verified_paid_proof.test_public_release_boundary -v
python -O -m unittest \
  revenue.verified_paid_proof.test_verified_paid_proof \
  revenue.verified_paid_proof.test_public_release_boundary -v
```

## Public/private output boundary

The output directory contains four artifacts with intentionally different authority:

- `proof.json` is the **internal audit envelope**. It intentionally retains the engagement identifier, private evidence, source references, blockers, withheld facts, and permission evidence. Never publish it as collateral. The `--json` switch prints this internal envelope.
- `public.json` is the allowlisted, fail-closed machine-readable public artifact. `HOLD` and `PRIVATE_VERIFIED` collapse to the same `NO_PUBLIC_CLAIM` envelope. Public states contain only the fixed public projection schema and a `public_receipt_sha256` computed solely from that public envelope. Use `--public-json` at public or outbound automation boundaries.
- `proof.md` is the publication-safe human-readable artifact in **every** state. Non-public states collapse to one neutral no-claim statement. Public states omit blockers, withheld-inventory metadata, private source locators, and every unpermissioned fact.
- `receipt.sha256` is the internal audit receipt binding normalized input, policy version, internal proof, and Markdown. It is deliberately distinct from the public-only receipt inside `public.json`.

Public outcome entries contain the permissioned claim only; their evidence/source locators remain in `private_evidence`. Withheld reasons are content-free and never echo a non-public claim.

Policy `verified-paid-proof/v3` preserves the v2 rendering defenses and closes the artifact-authority gap. Every external string is projected into one visual line, Unicode control/format characters become spacing, Markdown structure is escaped before HTML encoding, and URL/email/mention delimiters are entity-encoded to prevent automatic linking. V3 additionally escapes common extension delimiters, makes Markdown fail closed for non-public states, omits withholding inventory from public Markdown, and introduces the allowlisted public JSON envelope.

## Authority boundary

This compiler has no network or publishing capability. It does not contact customers, request permissions, send collateral, publish case studies, recognize revenue, or bypass the current single-writer/Muse arbitration system. A public-safe compiler result is evidence that the *content* is permission-safe under the supplied record; it is not authorization to choose a channel or send it.

Never put real customer names, private email/thread contents, Stripe identifiers, quotes, logos, payment evidence, or generated private proof into this public repository unless separate authorization already makes that material public.
