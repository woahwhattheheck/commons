# Municipal website acceptance workbench

A buyer-neutral, offline QA/evidence package for municipal website migration and release programs. The commercial trigger is a bounded QA/subcontract teaming inquiry around City of Exeter CA RFP 2026-05, but the code contains no City or Revize data and is intended to be reusable across municipal CMS programs.

## Evidence domains

The workbench binds immutable source references, freshness, and snapshot digests to seven control families:

- content migration identity/digest reconciliation;
- legacy-to-new redirect target, status, and hop count;
- internal/document link availability and document digest custody;
- accessibility scan evidence with explicit standard/tool/age and issue counts;
- forms/calendar/agenda or similar integration fixtures;
- role/permission assertions;
- backup/restore content and item-count reconciliation.

Outputs are canonical JSON plus deterministic buyer-neutral Markdown, with an append-only SHA-256 record chain, artifact checksums, and an offline verifier. A clean set can reach `PACKET_READY_FOR_HUMAN_UAT`; any defect yields `HOLD`.

This is **not** an automated WCAG or legal compliance certification. Accessibility evidence is one bounded input to human review. Human owners retain design, hosting, security/compliance interpretation, production release, customer acceptance, contract, and payment authority.

## Exact synthetic acceptance

`fixture.py` produces exactly **168** source-bound evidence checks:

- **140** clean checks PASS;
- **28** planted defects HOLD;
- exactly **4** each of `MIGRATION_DIGEST_MISMATCH`, `REDIRECT_CHAIN_INVALID`, `LINK_OR_DOCUMENT_FAILURE`, `ACCESSIBILITY_EVIDENCE_FAILURE`, `INTEGRATION_FIXTURE_MISMATCH`, `ROLE_PERMISSION_DRIFT`, and `RESTORE_EVIDENCE_INVALID`;
- zero planted defects PASS;
- reruns and reversed input iteration are byte-identical.

Run:

```bash
python -m unittest -v revenue.municipal_website_acceptance_workbench.test_gate
python -O -m unittest -v revenue.municipal_website_acceptance_workbench.test_gate
python -m revenue.municipal_website_acceptance_workbench.cli --out /tmp/municipal-uat
```

The parser refuses unknown fields, future evidence, secret-shaped values, email/PII-shaped strings, malformed hashes/paths/timestamps, conflicting duplicate IDs, and non-canonical permissions.
