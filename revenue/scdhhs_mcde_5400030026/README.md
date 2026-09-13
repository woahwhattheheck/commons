# SCDHHS Medicaid Clinical Data Exchange — 5400030026

Operation key: `SCDHHS-MCDE-5400030026-QUALIFICATION-MATRIX-20260913`

This package is an **internal, fail-closed qualification control** for the South
Carolina Department of Health and Human Services Medicaid Clinical Data Exchange
(MCDE) solicitation.  It does not contact the buyer, submit an offer, set price,
make a certification, sign a contract, authorize spend, deploy anything,
recognize payment, or recognize revenue.

## Controlling source

The source contract was captured from official State of South Carolina sources
on 2026-09-13:

* SC Business Opportunities listing:
  `https://scbo.sc.gov/online-edition?c=7-2026-08-29`
* SCEIS solicitation attachment index:
  `https://apps.sceis.sc.gov/SCSolicitationWeb/contractSearch.do?solicitnumber=5400030026`

The official index showed 33 solicitation attachments and a due date of
2026-10-15 11:00 ET.  `Amendment 1.pdf`, posted 2026-09-11 10:18:53 ET, is the
current controlling document.  Amendment 1 states that it is a complete new
document and directs prospective offerors to discard the original solicitation
when preparing bids.  Therefore the July `_MCDE RFP.pdf` is retained in the
manifest for provenance but cannot authorize current qualification.

No buyer file bytes were persisted in this repository, so this carrier does
**not** invent a buyer-file SHA-256.  `source_contract.json` records
`buyer_bytes_captured=false` and `buyer_file_sha256=null`.  The compiler instead
hashes the repository-owned normalized contract and a caller-provided capture of
the official attachment index.

If the State posts another amendment, removes/reposts an attachment, changes a
timestamp, or otherwise changes the observed 33-row manifest, compilation
returns `HOLD_SOURCE_NOT_CURRENT` until a source owner re-reads the official
buyer corpus and updates the repository trust root.

## Mandatory minimum qualification gate

Amendment 1 §5.2 (page 56 of 95) says offerors without the mandatory minimums
should not submit an offer and will not be evaluated.  The repository trust root
therefore fixes these minimums; a candidate packet cannot lower them:

1. at least 36 months of experience as prime contractor and at least three
   distinct federal/state/local/private healthcare entities where the offeror
   was prime contractor and a proposed solution of similar size and scope
   is/was implemented;
2. at least 36 months of real-time ADT solution experience, including at least
   24 months in healthcare; and
3. at least one successful prior ADT implementation for a health plan/system
   with at least 1,000,000 lives.

The State also allows an offeror to explain relationships to key personnel,
predecessor businesses, or subcontractors whose qualifications it wants
considered.  This compiler deliberately **does not** interpret that sentence as
permission to erase the separate "Offeror ... as the prime contractor"
requirement.  On the `prime_offeror` route, missing offeror prime history remains
a `PRIME_NO_GO_MANDATORY_EXPERIENCE` even if a subcontractor has excellent
experience.

That conservative interpretation should be confirmed by the procurement owner
before any submission.  The commercially safer lane for a small specialist that
does not itself prove the prime-history minimum is
`subcontractor_to_qualified_prime`.

## Teaming route

`subcontractor_to_qualified_prime` produces `TEAM_AS_SUBCONTRACTOR` only when:

* the official source snapshot is current;
* a qualified-prime candidate is named;
* the relationship is explicitly explained; and
* evidence references supporting the prime qualification review are present.

Even then, `prime_qualification_candidate` and `submission_authorized` remain
false.  The receipt exposes `teaming_prime_legal_name` so the recommendation is
auditable without reinterpreting the packet.  This is a teaming recommendation,
not a representation that the specialist may bid as prime or that the State has
found either party responsible.

Amendment 1 §5.5 (page 57 of 95) requires subcontractor identification when a
subcontracted portion exceeds 10% of cost, involves government information, or
is otherwise critical to performance.  Missing required identification is a
proposal-readiness hold.  Separately, §5.2 requires the relationship to be
explained when the offeror asks the State to consider that subcontractor's
qualifications; the compiler applies that relationship gate only when
subcontractor qualification evidence is actually supplied.

## Readiness gates after the §5.2 minimums

Qualification is necessary but not sufficient.  The compiler separately holds
for proposal readiness derived from Amendment 1:

* proposed Project Manager: 36 months MCDE, including 24 months healthcare
  (Section 4.1.3.4.1, page 53);
* HIPAA compliance and the ATTM 005 Business Associate Agreement;
* encryption in transit and at rest for government data / PHI;
* NIST SP 800-53 Rev. 5, NIST SP 800-53B, NIST SP 800-171 Rev. 3,
  FIPS 140 as amended, CMS ARC-AMPE, SSA security requirements, and SCDIS-200
  readiness (information-security requirements, pages 87-90).

Each readiness control requires both an explicit boolean and at least one evidence reference. A bare `true` is not enough. These remain internal evidence-readiness controls, not claims that an entity is certified or compliant; human diligence remains required before external use.

## Evaluation leverage

Only proposals that clear mandatory requirements are evaluated.  Amendment 1
allocates 1,000 total points: 700 technical, 200 price, and 100 demonstration.
This makes qualification/source recovery the first gate, not the whole capture
strategy.  If a qualified prime is secured, specialist work should focus on
high-value technical proof such as implementation/go-live, interoperability,
data quality, reporting, governance, security evidence, and demonstration
reliability rather than duplicating the prime's past-performance narrative.

## Usage

```python
from revenue.scdhhs_mcde_5400030026 import compile_qualification

receipt = compile_qualification(packet, source_observation=official_index_capture)
```

`source_observation` is intentionally a separate argument from candidate
evidence.  Candidate-controlled fields cannot redefine the trusted source
manifest or thresholds.

Experience month counts, project-manager counts, similar-entity rows, million-life implementations, and security readiness must carry evidence references; bare numeric/boolean assertions cannot produce a green candidate receipt.

The receipt is deterministic and binds:

* repository source-contract SHA-256;
* exact source-observation SHA-256;
* exact candidate-packet SHA-256; and
* the compiled result SHA-256.

`verify_receipt(...)` recompiles and byte-compares canonical JSON.  Any changed
source capture, evidence, decision, authority flag, or digest fails.

## Current TJLabs disposition

This package intentionally contains **no fabricated TokenJunkieLabs experience,
certification, customer, healthcare, ADT, security, or million-lives evidence**.
Until owner-held evidence proves the offeror-specific §5.2 minimums, do not label
TJLabs prime-qualified.  Existing partner outreach should be treated as a
potential path to a **qualified prime with TJLabs in a bounded specialist
subcontractor role**, not as a shortcut around the State's mandatory gate.
