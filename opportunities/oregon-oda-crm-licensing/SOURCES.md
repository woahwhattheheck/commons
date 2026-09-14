# Source ledger — Oregon ODA CRM & Licensing

The controlling procurement record is OregonBuys. Secondary indexes are discovery aids only and must not override buyer-controlled files.

| ID | Source | Supports | Authority / limitation | Required action |
|---|---|---|---|---|
| S0 | OregonBuys — https://oregonbuys.gov/bso/external/bidDetail.sda?docId=S-DASOBO-00017788&external=true&parentUrl=close | Solicitation ID/title; buyer; OPEN status; official notice scope; rendered opening `09/30/2026 04:00 PM`; electronic quote allowed; attachment inventory. | **Controlling public notice.** The rendered page does not by itself prove timezone or that no addendum changes a file after capture. | Download current RFP + every attachment/addendum; hash bytes; verify timezone and portal close rule. |
| S1 | GovTribe opportunity index — https://govtribe.com/opportunity/state-local-contract-opportunity/request-for-proposal-customer-relationship-management-crm-licensing-solution-sdasobo00017788 | Discovery summary of Dynamics 365 focus; ~26.8 TB / 570 Oracle tables; team roles; Round 1 weights; May 15, 2027 target; reference/security/accessibility themes. | **Secondary, non-controlling.** Its generated summaries can be wrong. One indexed price-file description appears to contain stale/foreign 2022 metadata, so no summary may be treated as contract text without byte reconciliation. | Reconcile each retained fact to RFP section/page or attachment cell. |
| S2 | CLEATUS opportunity index — https://www.cleat.ai/government/contracts/request-for-proposal-customer-relationship-management-crm-licensing-solution-lu54 | Discovery summary of Dynamics 365/OneODA scope; integration/data migration; WCAG 2.1 AA; security/standards themes; document inventory. | Secondary, non-controlling; dates can be normalized and AI summaries are not legal text. | Use only to guide retrieval; bind requirements to S0 package bytes. |
| S3 | OregonBuys file inventory on S0 | Thirteen files exposed with the official notice. | High for filenames present at capture; files may be amended/replaced. | Capture file bytes and cryptographic hashes. |

## Official notice attachment inventory at capture

S0 exposes the following filenames:

1. `S-DASOBO-00017788 CRM and Licensing Solution Request for Proposal.docx`
2. `Attachment A -Sample Contract_S-DASOBO-00017788.docx`
3. `Attachment B - Disclosure Exemption Affidavit S-DASOBO-00017788.docx`
4. `Attachment C - Proposer Information and Certification Sheet S-DASOBO-00017788.docx`
5. `Attachment D - Reference Check Form S-DASOBO-00017788.docx`
6. `Attachment E - Price Proposal S-DASOBO-00017788.xlsx`
7. `Attachment F - Certified Disadvantage Business Outreach Plan S-DASOBO-00017788.docx`
8. `Attachment G - Responsibility Inquiry.docx`
9. `Attachment H - OneODA CRM Licensing High-level Solution Requirements S-DASOBO-00017788.xlsx`
10. `Attachment I - OneODA CRM Licensing System Integrations S-DASOBO-00017788.xlsx`
11. `Attachment J eis-css-oregon-standards-spreadsheet S-DASOBO-00017788.xlsx`
12. `Attachment K- Digital Accessibility Narrative S-DASOBO-00017788.docx`
13. `Attachment L - OneODA CRM Licensing Oracle Tables S-DASOBO-00017788.xlsx`

## Source-safety rules

- The official notice's `09/30/2026 04:00 PM` rendering is stored as the planning deadline; **timezone remains unverified in this carrier** until the controlling RFP is read.
- Do not infer a questions deadline, conference attendance requirement, amendment status, contract term, insurance limits, proposal page limits, exact scoring, or signature method from a search snippet.
- Never copy a secondary-source generated statement into a proposal as if it were buyer language.
- The anomalous stale metadata visible in a secondary price-file summary is a concrete reason this package is fail-closed.
- Before any response is sent, record SHA-256 for every controlling document and addendum and cite section/page/cell for every mandatory gate.

## Retrieval receipt template

For each downloaded buyer file record:

```text
filename:
source_url:
retrieved_utc:
sha256:
size_bytes:
addendum_or_version_marker:
controls_which_requirement_ids:
```

Until that ledger is populated, this package is authorized for **capture/partner discovery only**, not proposal submission.