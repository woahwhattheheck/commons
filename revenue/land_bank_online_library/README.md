# Land Bank T12-09-26 non-authorizing teaming carrier

This package supports a **teaming-first** response to Land and Agricultural
Development Bank of South Africa solicitation `T12-09-26`. It is deliberately
incapable of granting procurement or submission authority.

## What changed after independent RED review

PR #14877 review `5223940323` found two real authority bugs in V1: a caller
could type any 64-hex digest and mint `SOURCE_BYTES_READY`, and the same public
JSON could set four booleans and mint `SUBMISSION_READY`/rc0.

V2 removes both transitions:

1. a caller-supplied digest or URL is never source custody. The process must
   open a retained, regular, non-symlink file, read its bytes through the
   retained descriptor, and compute SHA-256 itself. An optional expected digest
   can only make the check stricter. Even then the result is named
   `RETAINED_SOURCE_CANDIDATE_HASHED`: it proves byte custody, **not buyer
   authorship or procurement authority**;
2. there is **no submission-authority input**. `submission_status` is always
   `HOLD_EXTERNAL_PRIME_AUTHORITY_REQUIRED`, and all external authority facts
   are emitted hard-false. The CLI always returns rc2 so its exit code cannot be
   repurposed as bid/submission permission.

Prime evidence references are likewise only an inventory for external review.
They never establish prime qualification.

## Public discovery snapshot

Public listings captured on 2026-09-16 described an online legal-library
implementation plus licensing, maintenance/support, legal-content management,
secure access, search/retrieval, comparison/citation/export, cloud/security/DR,
and training/handover. The listing showed a 2026-10-08 11:00 SAST close and a
2026-09-17 11:00 SAST virtual briefing marked non-compulsory.

Those are **working discovery facts only** until buyer-authored files are
retained and independently reviewed.

Discovery listing:
`https://easytenders.co.za/tenders/t12-09-26-centurion-online-library-system`

Durable pursuit carrier:
`https://github.com/woahwhattheheck/commons/issues/14872`

## Paid TJLabs seam

The accepted commercial state is only `PAID_SCOPE_TO_BE_AGREED`. The bounded
workshare is migration/metadata acceptance, RBAC/entitlement acceptance,
search/retrieval regression, integration QA, security/DR evidence matrix,
training/handover acceptance, and requirements traceability.

This does not make TJLabs the legal-content supplier, OEM/OSM, registered
bidder, penetration-testing certifier, prime, signatory, or submitter.

## Run

```bash
python -S -m unittest -v test_land_bank_online_library
python -S -O -m unittest -v test_land_bank_online_library
python -S -m revenue.land_bank_online_library.cli \
  revenue/land_bank_online_library/example_hold.json
```

The CLI intentionally exits `2`, including when an internal teaming review
packet is complete. Machine consumers must inspect the JSON states; this tool
never emits submission authority.
