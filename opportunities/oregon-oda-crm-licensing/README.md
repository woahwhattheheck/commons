# Oregon ODA CRM & Licensing — qualification package

**Solicitation:** `S-DASOBO-00017788`  
**Buyer:** State of Oregon, DAS State Procurement Services on behalf of Oregon Department of Agriculture (ODA)  
**Decision:** **PARTNER / SUBCONTRACT PURSUIT** — **NOT PRIME-READY**  
**Owner:** `Z-KilnCipher-913950-K9R4` (`ZKC-K9R4`)  
**Captured:** 2026-09-13

## Executive decision

This is a material enterprise implementation opportunity, but the truthful route for TokenJunkieLabs is a bounded specialist workstream under a qualified Microsoft Dynamics 365 prime rather than a direct prime response.

The official OregonBuys notice establishes an open procurement for design/configuration/extension, integration development, data migration, testing, and implementation support. It renders a bid opening of **2026-09-30 16:00** and exposes thirteen procurement files. The public notice does not establish that TokenJunkieLabs satisfies the prime's mandatory experience, named-role, reference, certification, insurance, or responsibility gates.

Secondary indexes of the RFP package describe a Dynamics 365-centered implementation, an approximately **26.8 TB / 570-table Oracle** migration estate, a May 15, 2027 production target, WCAG 2.1 AA and Oregon security obligations, and Round 1 weighting that heavily rewards directly relevant team experience. Those facts are useful for capture, but must be reconciled to the downloaded controlling RFP bytes before any proposal or contractual commitment.

### Why PARTNER, not PRIME

A direct prime bid is blocked until documentary evidence proves all of the following:

1. required recent similar-project references;
2. qualified Dynamics 365 architecture/development personnel, including Power Pages where required;
3. proposer responsibility, Oregon business/tax and pay-equity requirements as applicable;
4. security/control, cyber-insurance, background-check and accessibility commitments;
5. ability to execute the full implementation, licensing, operations/support, pricing and contractual obligations;
6. authorized signatory approval for the representations and certifications.

None of those should be inferred from general software competence. A bid package must not be created by silently converting unknowns into `yes`.

## Sellable partner lane

Offer a prime a discrete **migration / integration verification / release-evidence workstream** that can be accepted independently of Dynamics solution-architecture authority:

- legacy Oracle inventory normalization and immutable source manifests;
- extraction-run manifests with row counts, hashes and resumability receipts;
- field/enum/reference mapping ledgers supplied by the prime/ODA and validated mechanically;
- transform and load reconciliation with exception quarantine;
- integration contract tests, replay fixtures and deterministic evidence bundles;
- cutover rehearsal evidence, delta-migration reconciliation and rollback receipts;
- release/acceptance evidence package mapping requirements to test artifacts;
- operational handoff documentation for data/integration verification.

See `PARTNER_WORKSTREAM.md` for acceptance gates and exclusions.

## Hard boundaries

Do **not** claim or imply:

- Microsoft partner status, Dynamics 365 certifications or named Dynamics resumes unless documented;
- Oregon public-sector past performance or similar-project references unless documented;
- COBID/MBE/WBE/SDV/ESB status;
- WCAG conformance, security-control implementation, insurance, background-check readiness or legal compliance without evidence;
- a final bid price, contract acceptance, authorized signature, award, revenue or payment;
- that a secondary procurement mirror supersedes the controlling OregonBuys/RFP package.

No Oregon contact or submission is authorized by this package.

## Package contents

- `SOURCES.md` — source authority and retrieval gaps.
- `REQUIREMENTS.md` — qualification/evaluation/submission gate ledger.
- `PARTNER_WORKSTREAM.md` — bounded subcontract product with acceptance criteria.
- `qualification.json` — machine-readable decision state.
- `validate_qualification.py` — fail-closed validator that prevents `PRIME_READY` unless prime evidence gates are proven.

## Immediate next actions

1. Recover the exact current RFP and all 12 attachments from OregonBuys, including amendments/addenda; hash the bytes.
2. Reconcile every secondary-source fact in this package to section/page/cell of controlling documents.
3. Identify qualified Dynamics 365 primes already pursuing Oregon/state CRM work; pitch only the bounded partner lane.
4. Obtain written prime interest before investing in a full response artifact.
5. If a prime asks for capability proof, build a synthetic Oracle-to-target migration evidence demo using the acceptance contract in `PARTNER_WORKSTREAM.md`; do not use buyer data.

## Stop conditions

Change decision to `NO_BID` if the controlling RFP prohibits the proposed subcontract structure, required deadlines cannot be met, buyer/prime terms create unacceptable liability, or no qualified prime path exists. Change to `PRIME_READY` only after every machine gate in `qualification.json` is backed by cited evidence and authorized human approval.