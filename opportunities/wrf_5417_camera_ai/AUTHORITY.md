# WRF 5417 readiness authority v2

This file documents the machine boundary implemented by `validate_readiness.py`. It does not grant submission authority and it does not contain private applicant evidence.

## Why v2 exists

The first landed checker correctly defaulted to `HOLD`, but its hypothetical READY path trusted caller-authored gate names, deadline fields and arbitrary evidence strings. That meant a self-consistent candidate manifest could delete mandatory requirements or label synthetic strings as proof. Version 2 makes the checker useful as an authority boundary rather than a formatting check.

## Fixed contract

The verifier owns the WRF-5417 contract. Candidate bytes cannot change:

- opportunity identity `WRF-5417`;
- the exact 16 required hard-gate names;
- the controlling deadline fields or the conservative expiry instant `2026-09-14T21:00:00Z` (the earlier interpretation of the public Mountain-Time / GMT-07 display discrepancy);
- the $300,000 request ceiling;
- the 33% minimum applicant-contribution rule;
- the 15% reimbursed-indirect ceiling;
- the requirement for budget terms, workbook and narrative authority;
- at least two distinct consenting sites spanning drinking-water and wastewater sectors.

The embedded contract records the reviewed `requirements.json` Git blob `ef4ca5d4a91bea0f03054ad879409fba0083c36d` and emits its own SHA-256 in every result receipt.

## Candidate evidence is not authority

A gate with `status: PROVEN` is still HOLD unless its `evidence` list names an exact record in a separate authority bundle whose **entire canonical SHA-256 root is pinned in reviewed verifier source**. `PINNED_AUTHORITY_ROOTS` is deliberately empty in this public carrier today, so the checked-in carrier cannot reach READY using public/caller-authored data alone.

A future authorized operator can build a private authority bundle without committing tax, financial, credential or utility-consent contents here. Before the public verifier can accept it, a separate reviewed source change must pin that bundle's canonical root. This makes readiness promotion a deliberate code-reviewed authority event rather than a manifest edit.

Each authority record binds:

- opportunity id;
- gate and subject;
- evidence type;
- immutable source id + generation + SHA-256;
- exact candidate claim SHA-256;
- verified time and expiry;
- a deterministic record id derived from the record body.

The verifier rejects stale records, changed claims, wrong subjects/gates/opportunities, missing records, record reuse across claims, and source-evidence identity reuse. Utility consent is bound to the exact utility/site/sector tuple. Third-party contribution commitments are bound to exact contributor/type/value claims.

## Ingress and receipts

CLI JSON input is bounded to 1 MiB, final-path `O_NOFOLLOW` where supported, retained-descriptor regular-file reads, duplicate-key rejection, and non-finite JSON rejection. The verifier emits a deterministic receipt for a fixed evaluation time containing contract, manifest and authority-bundle digests, authority generation, state, reasons and a receipt SHA-256.

Usage remains fail-closed:

```bash
python opportunities/wrf_5417_camera_ai/validate_readiness.py \
  opportunities/wrf_5417_camera_ai/submission_manifest.json
```

The checked-in manifest must return `HOLD` / exit 3. Supplying an unpinned authority bundle must also return HOLD:

```bash
python opportunities/wrf_5417_camera_ai/validate_readiness.py MANIFEST.json AUTHORITY_BUNDLE.json
```

## Non-authority boundary

Even a valid `READY_FOR_AUTHORIZED_SUBMITTER_REVIEW` receipt keeps `carrier_may_submit=false`. The tool cannot sign/certify forms, create portal access, commit cash/in-kind support, represent utility participation, submit the application, accept a contract, spend funds, or claim an award/payment. Those remain authorized-human actions outside this carrier.
