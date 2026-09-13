# INPRS RFP 26-04 — Source-Bound Delivery Notes

These notes extract implementation facts from the current INPRS RFP 26-04 packet that materially affect the bounded partner workstream. They are not a substitute for the controlling solicitation or future addenda.

## Controlling public sources

- INPRS procurement page: <https://www.in.gov/inprs/about-us/procurement>
- RFP 26-04 PDF: <https://www.in.gov/inprs/files/rfp-documents/RFP26-04ContractLifecycleManagement(CLM)System.pdf>

Before a proposal or subcontract scope is finalized, re-check the procurement page for amendments/addenda and bind the artifact versions used for the response.

## Current-state facts that drive migration scope

The RFP describes a fragmented current contracting process rather than an existing end-to-end Conga workflow:

- contracts are drafted in Microsoft Word;
- drafts/redlines are exchanged with vendors and internal stakeholders;
- DocuSign is used in the execution flow;
- fully executed PDFs are uploaded to Conga Contracts;
- Conga is used primarily to monitor contract expiration rather than for contract drafting/workflow;
- Conga produces a weekly 90-day expiration report;
- data from that report is copied into an Excel Contract Tracking Log in SharePoint and used by Procurement/Legal to track renewal/termination progress.

This means migration validation should not assume the legacy CLM alone contains every workflow fact needed for the future state. Discovery should identify which authoritative metadata lives in Conga, the SharePoint tracking log, document stores, DocuSign, or other sources.

## Source population

The packet states that approximately **5,000 contracts** are currently in Conga Contracts:

- approximately one third are original/master contracts;
- approximately two thirds are amendments/addenda;
- approximately half are active and approximately half are inactive/expired.

The target system also needs to store vendor documents including:

- certificates of insurance;
- Form W-9s;
- SOC reports.

### Delivery implication

The migration manifest should distinguish master/original agreements from amendments/addenda and preserve their relationships. Volume estimates must also include associated documents and vendor records; “5,000 contracts” should not be treated as the total file/object count.

## Target CLM capabilities relevant to the assurance workstream

The RFP calls for an end-to-end contracting process covering request, drafting/negotiation, execution, storage of executed contracts, and monitoring upcoming renewals. Relevant technical requirements include:

- Microsoft Word use, including redlining;
- document version histories;
- external-user participation in drafting (for example, vendor attorneys);
- messaging during drafting, via Outlook email capability or CLM messaging;
- ad hoc reporting;
- Authorization Letter drafting/signing workflow support;
- transfer of contracts and data from Conga Contracts into the new system.

### Delivery implication

The integration test matrix should validate document/version identity across Word/redline flows and the final executed record, not just API availability. External-user access should be included in authorization and negative-path tests. Migration acceptance should include the records/documents required for renewal monitoring and reporting.

## Public contract portal requirements

The RFP requires a public-facing contract portal. It states that the public must be able to search contracts using multiple attributes/keywords, including examples such as:

- company name;
- service type;
- contract cost;
- effective and expiration dates;
- procurement method;
- RFP number.

Some contract documents require redaction before public access. The packet also distinguishes between redacted public versions and unredacted versions accessible to appropriately permissioned INPRS staff. The pricing questionnaire separately requires pricing for establishing and supporting the public-facing portal/electronic feed and states that public access must not require login credentials.

### Delivery implication

The public-portal assurance lane should test four distinct properties:

1. **discoverability** — expected public records appear under supported search keys;
2. **version parity** — public metadata/document versions correspond to the intended authoritative contract version;
3. **non-disclosure** — confidential test content is absent from pages, files, metadata, indexes, feeds, and cached representations;
4. **anonymous access behavior** — the intended public surface is usable without credentials while privileged/unredacted representations remain permission-gated.

Do not invent redaction rules. The authoritative disclosure/redaction owner must supply or approve the cases that the automation enforces.

## Partner/subcontractor disclosure is contemplated by the RFP

The respondent questionnaire asks whether parts of the proposed services will be provided by a subcontractor/partner and asks the respondent to describe the relationship and role. That supports a truthful bounded-subcontract model when the prime chooses it; it does not waive any respondent responsibility or create a relationship with a potential prime by itself.

The questionnaire also requests at least three recent client references for similar services and asks specifically about public-sector/public-retirement-system CLM clients.

### Delivery implication

TJLabs should not be positioned as supplying the prime's required CLM product history or comparable public-sector references unless evidence actually supports that claim. A prime/SI should retain ownership of those qualification statements while TJLabs' role is described specifically as migration/integration/assurance automation if a subcontract is formed.

## Procurement communication boundary

The solicitation directs respondent inquiries through the RFP's authorized INPRS procurement contact and warns against directing inquiries to INPRS staff or trustees outside that path.

### Delivery implication

Partner discovery, technical scoping, and internal preparation do not authorize agency outreach. Any RFP question or other buyer communication must use the controlling solicitation process and the responsible prime's approved communication path.

## Pre-estimate source checklist

Before turning the partner brief into a fixed estimate, obtain or explicitly mark unavailable:

- current RFP/addenda versions;
- Conga object/field inventory and representative extract;
- SharePoint Contract Tracking Log structure and source-of-truth decisions;
- document/attachment counts and relationship model;
- target CLM import/API constraints;
- Word/redline and e-sign architecture;
- external-user identity/access model;
- public portal/feed/search architecture;
- authoritative redaction/publication rules;
- non-production environment availability;
- security/data-handling restrictions;
- rehearsal and cutover calendar;
- prime-approved acceptance thresholds and RACI.

If those inputs are incomplete, quote discovery/pilot work rather than pretending the full migration and cutover risk is already known.
