# Sources and evidence ledger

This ledger distinguishes public discovery evidence from controlling procurement evidence. **No external submission should rely on a mirror when the buyer's controlling package is available.**

| ID | Source | What it currently supports | Confidence / limitation | Required action |
|---|---|---|---|---|
| S1 | CanadaBuys tender-opportunity index — https://canadabuys.canada.ca/en/tender-opportunities | St. Francis Xavier University has an open `Certificate Lifecycle Management` services opportunity; public index shows a 2026-09-25 close. | High for existence/title/indexed close; index is not the full solicitation. | Recover exact opportunity detail, attachments and amendments from controlling procurement route. |
| S2 | Nova Scotia procurement mirror/index — https://techbids.ca/bids/source/novascotia/ | Buyer is St. Francis Xavier University; opportunity is active in Nova Scotia procurement ecosystem. | Medium/high discovery evidence; mirror may lag amendments. | Bind official notice ID, portal URL, dates and attachment inventory. |
| S3 | Public scope mirror — https://rfpplanet.com/sys-6673/certificate-lifecycle-management | Detailed functional themes: discovery/inventory, lifecycle automation, CA integrations, RBAC/workflows, APIs, audit/compliance, implementation/KT and support. | Medium. Useful for capture, **not controlling**. It reports publish/close metadata that may differ from other indexes. | Reconcile every row in `REQUIREMENTS.md` to controlling RFP section/page before response use. |
| S4 | Commons issue #13892 | Internal custody, scope and boundaries. | High internal authority. | Keep issue updated with retrieval/decision receipts. |

## Known discrepancy

Public indexes do not provide a single fully reliable controlling metadata record in this package. Observed public dates include a September 25 close, while mirrors can lag or normalize procurement dates. Therefore:

- `2026-09-25` is a **planning date only** until buyer-controlled documents confirm it.
- Do not infer the questions deadline from a mirror.
- Do not infer timezone, mandatory meeting, submission method, contract term, award basis, budget, Canadian-vendor preference, insurance, security certification, data residency, or accessibility requirements.

## Controlling-package retrieval checklist

Capture all of the following as immutable evidence before bid/no-bid approval:

- buyer/portal opportunity identifier and canonical URL;
- RFP/NRFP document and every appendix/schedule;
- pricing form / response workbook;
- legal terms and conditions;
- security/privacy schedule;
- accessibility requirements if present;
- mandatory technical form / rated criteria;
- references/experience form;
- addenda and Q&A, including posting timestamps;
- question deadline, channel and permitted contact;
- proposal deadline with timezone;
- portal registration and upload requirements;
- mandatory declarations/certifications;
- contract start, implementation deadline, initial term and renewals;
- evaluation weights and mandatory pass/fail criteria.

For downloaded files, record filename, source URL, retrieved-at UTC time, byte length and SHA-256.

## Evidence classes

- **C0 — controlling:** buyer-issued solicitation/addendum/portal record.
- **C1 — authoritative external:** government procurement index that identifies the opportunity.
- **C2 — discovery mirror:** third-party RFP index; useful for finding requirements but not controlling.
- **I0 — internal durable:** Commons issue/commit/decision receipt.
- **V0 — vendor evidence:** official product documentation, contract, certification or partner authorization for the exact proposed solution.

A proposal claim about a mandatory requirement should resolve to C0 + V0. A capture hypothesis can begin from C1/C2 but must be visibly marked pending.
