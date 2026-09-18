# INPRS CLM migration + public-release evidence gate

This package is a **data-free acceptance harness** derived from Indiana Public Retirement System RFP 26-04. It is intended to help a qualified CLM prime prove a bounded migration/publication workstream; it is not a CLM product, an Icertis implementation, an INPRS submission, or evidence of agency acceptance.

## Why this exists

The September 8, 2026 RFP describes a mostly manual contracting flow backed by Microsoft Word, DocuSign, Conga Contracts, Outlook/email, and a SharePoint/Excel tracking log. It states that roughly 5,000 contracts are in Conga Contracts, with about one third originals/masters and two thirds amendments/addenda, and requires the proposed solution to transfer contracts and data from Conga to the new CLM system. It also requires a no-login public portal for executed contracts, keyword search over contract metadata, and redaction of confidential information before public release. The system must preserve document version history and support vendor-attorney participation in drafting/redlining.

Official source: `https://www.in.gov/inprs/files/rfp-documents/RFP26-04ContractLifecycleManagement(CLM)System.pdf` (Scope of Services, pp. 11–13; milestones p. 7).

The RFP inquiry deadline is September 18, 2026 at 3:00 PM EDT; proposals are due October 16, 2026 at 3:00 PM EDT. Those dates can change only through the official procurement/addendum process, so re-check the INPRS procurement page before relying on them.

## What the gate proves

Given a candidate JSON evidence bundle, `verify_bundle.py` fails closed unless all of these invariants hold:

- the declared source row count reconciles exactly, preventing a silent migration drop;
- legacy IDs are unique;
- every amendment has a resolvable parent chain terminating at a master, with no cycles;
- migrated document hashes equal source document hashes;
- each document has a consecutive version history whose final revision equals the migrated hash;
- public projections are one-to-one with records declared for publication;
- withheld records never appear in the public projection;
- redacted public documents use a distinct declared hash plus a redaction-attestation hash;
- public rows contain only an explicit metadata allowlist;
- search terms are an exact deterministic projection of the required searchable metadata;
- Certificates of Insurance, W-9s, and SOC reports remain internal and byte-preserved;
- the emitted report is canonical JSON, so identical evidence produces byte-identical receipts.

This is deliberately narrower than full CLM acceptance. It does **not** prove Microsoft Word integration, DocuSign behavior, Outlook integration, Icertis configuration, authentication/authorization, production security, availability, agency policy correctness, legal sufficiency of a redaction, or actual Conga connectivity.

## Bundle shape

`fixtures/golden_bundle.json` is a synthetic six-contract fixture with the RFP's stated 1:2 master-to-amendment shape. It includes full publication, redacted publication, an explicit legal-review hold, version histories, and three internal vendor documents. It contains no INPRS or vendor production data.

A real evidence run should be generated from immutable source/export manifests. The `expectations` counts must be populated from that independently frozen manifest rather than calculated from the candidate migration itself; otherwise a dropped row could lower both the data and the expectation together.

## Run

```bash
python revenue/inprs_clm_migration_gate/verify_bundle.py \
  revenue/inprs_clm_migration_gate/fixtures/golden_bundle.json

python -m unittest -v test_inprs_clm_migration_gate.py
```

A passing CLI run exits `0`. Any invariant failure exits `2`. Use `--report PATH` to write the same canonical receipt that is printed to stdout.

## Handoff to a CLM prime

The useful commercial workstream is not “we implement Icertis.” It is independently testable migration/release evidence:

1. freeze source export counts and document hashes;
2. migrate into the prime's candidate CLM environment;
3. export a normalized evidence bundle;
4. run this gate and repair every deterministic failure;
5. separately witness product-specific workflows (Word redlining, approvals, signatures, permissions, integrations);
6. obtain INPRS/prime approval for the actual redaction policy and public-portal acceptance set.

The verifier can be adapted to the prime's export schema without changing these invariants. Any such adapter should preserve the raw source manifest and emit the normalized bundle as a separate derived artifact.
