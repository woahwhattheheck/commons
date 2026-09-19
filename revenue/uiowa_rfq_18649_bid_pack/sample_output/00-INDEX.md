# Submission folder index

> SYNTHETIC FIXTURE - FICTION. Northgate Assessment Partners LLC does not exist. No content in this pack is a representation about any real bidder, any real University of Iowa requirement, or any real document. It exists to exercise the assembler.

Solicitation: `RFQ-18649`  
Bidder: Northgate Assessment Partners LLC (FICTIONAL)  
Submission status: **DRAFT - NOT SUBMITTED**  
Rendered proposal: `proposal.pdf` (9 pages), `proposal.docx`

## Documents

| # | Section | File | PDF page | Content |
|---|---|---|---|---|
| 1 | Cover Letter | `documents/01-cover-letter.md` | 3 | SUPPLIED |
| 2 | Executive Summary | `documents/02-executive-summary.md` | 4 | SUPPLIED |
| 3 | Firm Qualifications | `documents/03-firm-qualifications.md` | 5 | SUPPLIED |
| 4 | Scope of Work and Methodology | `documents/04-scope-of-work-and-methodology.md` | 6 | SUPPLIED |
| 5 | Staffing and Key Personnel | `documents/05-staffing-and-key-personnel.md` | 7 | SUPPLIED |
| 6 | Price Proposal | `documents/06-price-proposal.md` | 8 | SUPPLIED |
| 7 | Exceptions and Assumptions | `documents/07-exceptions-and-assumptions.md` | 9 | SUPPLIED |

## Attachment index

`UNKNOWN` = no file supplied, so nothing could be measured. Not zero.

| ID | Title | Category | Required | Status | File | Bytes | SHA256 | Index page |
|---|---|---|---|---|---|---|---|---|
| ATT-FIN-01 | Financial Capacity Letter | financial | yes | **SUPPLIED** | `attachments/A01-financial-capacity-letter.txt` | 385 | `110d1deb877bf3b6` | 2 |
| ATT-FIN-02 | Certified Cost Rate Schedule | financial | yes | **PLACEHOLDER-NOT SUPPLIED** | _(none)_ | UNKNOWN | UNKNOWN | 2 |
| ATT-QUAL-01 | Vendor Registration and Taxpayer Identification | qualification | yes | **SUPPLIED** | `attachments/A03-vendor-registration-and-taxpayer-identification.txt` | 316 | `735ea0aa278ac0f7` | 2 |
| ATT-QUAL-02 | Certificate of Insurance | qualification | yes | **PLACEHOLDER-NOT SUPPLIED** | _(none)_ | UNKNOWN | UNKNOWN | 2 |
| ATT-QUAL-03 | Key Personnel Resumes | qualification | yes | **PLACEHOLDER-NOT SUPPLIED** | _(none)_ | UNKNOWN | UNKNOWN | 2 |
| ATT-REF-01 | Client References | qualification | no | **SUPPLIED** | `attachments/A06-client-references.txt` | 286 | `52627cda38b5c84a` | 2 |

## Submission completeness

**SUBMISSION_INCOMPLETE**

- Required attachments declared: 5
- Present: 2
- Not supplied: `ATT-FIN-02`, `ATT-QUAL-02`, `ATT-QUAL-03`

> Counts describe declared-vs-present documents in this pack only. Whether this list of attachments is the list the University actually requires is UNKNOWN.

## Cross-references

- `S-COVER` -> `S-SCOPE` (section) **RESOLVED**
- `S-COVER` -> `S-PRICE` (section) **RESOLVED**
- `S-EXEC` -> `S-SCOPE` (section) **RESOLVED**
- `S-EXEC` -> `S-STAFF` (section) **RESOLVED**
- `S-EXEC` -> `ATT-FIN-01` (attachment) **RESOLVED**
- `S-QUAL` -> `ATT-REF-01` (attachment) **RESOLVED**
- `S-QUAL` -> `ATT-QUAL-03` (attachment) **RESOLVED**
- `S-SCOPE` -> `S-STAFF` (section) **RESOLVED**
- `S-SCOPE` -> `S-PRICE` (section) **RESOLVED**
- `S-SCOPE` -> `S-APPENDIX-C` (unknown) **UNRESOLVED**
- `S-STAFF` -> `ATT-QUAL-03` (attachment) **RESOLVED**
- `S-PRICE` -> `S-SCOPE` (section) **RESOLVED**
- `S-PRICE` -> `ATT-FIN-02` (attachment) **RESOLVED**
- `S-PRICE` -> `ATT-FIN-01` (attachment) **RESOLVED**
- `S-EXCEPT` -> `S-PRICE` (section) **RESOLVED**

## Assembler issues

- **WARN** `ATTACHMENT_NOT_SUPPLIED` required attachment ATT-FIN-02 (Certified Cost Rate Schedule) is declared but no file was supplied; emitted as a placeholder
- **WARN** `ATTACHMENT_NOT_SUPPLIED` required attachment ATT-QUAL-02 (Certificate of Insurance) is declared but no file was supplied; emitted as a placeholder
- **WARN** `ATTACHMENT_NOT_SUPPLIED` required attachment ATT-QUAL-03 (Key Personnel Resumes) is declared but no file was supplied; emitted as a placeholder
- **WARN** `XREF_UNRESOLVED` section S-SCOPE references 'S-APPENDIX-C', which is not a section or an attachment in this pack
