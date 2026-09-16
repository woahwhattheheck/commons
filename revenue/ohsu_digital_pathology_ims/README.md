# OHSU Digital Pathology IMS — qualification and synthetic integration evidence

Evidence-only internal tooling for **OHSU RFP-2027-2012, Digital Pathology Image Management System**.

## Why this exists

OHSU's public procurement page lists the opportunity as issued **2026-09-11** and due **2026-10-11**. The public description requires an enterprise digital-pathology IMS with bi-directional Epic Beaker integration, end-to-end clinical pathology workflows, centralized image management/view/share/analyze capability, and scalable native/third-party AI and image-analysis integration across clinical, educational and research missions.

Critically, OHSU's listing also tells respondents to read and confirm **minimum requirements contained in the RFP document**. The public summary therefore is not enough to establish bidder eligibility.

This pack turns that boundary into code:

- `qualification.py` is the deterministic candidate/replay compiler. It binds opportunity identity and public source, requires a captured full-RFP digest, explicit minimum rows, and evidence for every mandatory row.
- The candidate bundle carries a content-addressed `requirements_manifest` and completeness-attestation record. Those hashes prove internal consistency only; because they travel with the candidate, they are **not** the positive trust root for current authority.
- `current_authority.py` is the only current-authority wrapper. It owns the wall clock and compares the candidate completeness-attestation digest with a verifier-retained root read from the fixed sibling path `trusted_completeness.sha256`.
- The candidate cannot name or override that root through JSON or CLI arguments. Missing, malformed, or mismatched retained authority forces `HOLD`.
- The current CLI does not accept a caller-supplied evaluation time. Historical/replay reconstruction may call `qualification.evaluate` directly, but that deterministic compiler is not the current-authority entry point.
- A public-listing-only capture deterministically returns `HOLD`; it can never silently become bidder qualification.
- Receipts are content-addressed and explicitly deny outreach, intent-to-bid, proposal submission, clinical use, payment, and buyer-acceptance authority.
- `integration_contract.py` provides a PHI-free synthetic bidirectional Beaker↔IMS trace model without claiming Epic certification or clinical interoperability.

## Completeness authority boundary

A captured full-RFP bundle is not sufficient by itself. The bundle's manifest records:

- the exact full-RFP SHA-256;
- exact total and mandatory requirement counts;
- a canonical digest over `{id, mandatory, text}` for every captured minimum;
- one non-empty source locator for every requirement ID;
- a completeness-review record containing reviewer identity, artifact reference, manifest-core digest, and deterministic SHA-256.

Those in-bundle bindings detect stale or internally inconsistent rewrites. They do **not** authenticate a freshly reminted replacement universe because the candidate controls them all.

Current `READY_FOR_INTERNAL_BID_REVIEW` therefore additionally requires a separately retained verifier root whose value exactly matches the candidate completeness-attestation SHA-256. The hostile suite proves that replacing the universe with one easy row and then recomputing every candidate-controlled digest still returns `HOLD` against the retained root.

`trusted_completeness.sha256` is intentionally absent until an independent review has approved a concrete completeness artifact. Do not populate it by reading the value back from the candidate being evaluated; that would collapse the authority boundary back into self-attestation.

## Truth / authority boundary

`READY_FOR_INTERNAL_BID_REVIEW` means only that a locally captured minimum-qualification snapshot passed deterministic checks **and** its completeness attestation matches the verifier-retained root. It does **not** mean OHSU has accepted the bidder, Epic has certified an integration, the IMS is clinically validated, or anyone may contact OHSU / submit an intent / submit a proposal.

The synthetic integration fixture contains no patient information and is not connected to Epic, Beaker, an IMS, OHSU, or any clinical system.

## Validation

```bash
cd revenue/ohsu_digital_pathology_ims
python -m py_compile qualification.py current_authority.py integration_contract.py cli.py test_qualification.py test_current_authority.py test_integration_contract.py test_cli.py
python -m unittest -v
python -O -m unittest -v
python cli.py fixtures/public_listing_only.json
```

Expected focused suite: **47 tests**.

The current CLI uses exit `0` only for verifier-root-backed `READY_FOR_INTERNAL_BID_REVIEW`, `3` for a truthful `HOLD`, and `2` for malformed/unreadable evidence or CLI misuse. Receipts can be written atomically with `--output`. There is deliberately no `--evaluated-at` option on the current path.

## Next evidence step

Acquire the official RFP package through the procurement process, hash the exact source package, transcribe the actual minimum qualifications, record source coordinates, obtain an independent completeness review, and preserve its approved attestation digest outside the candidate bundle. Only then provision that approved digest as `trusted_completeness.sha256`, attach content-addressed evidence references, and rerun the current gate. Until that independent root exists, `HOLD` is the correct current result.

No external outreach or submission is performed by this module.
