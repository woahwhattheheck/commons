# Sources and evidence ledger

This ledger distinguishes public discovery evidence from controlling procurement evidence. **No external submission should rely on a mirror when the buyer's controlling package is available.**

| ID | Source | What it currently supports | Confidence / limitation | Required action |
|---|---|---|---|---|
| S0 | Official Nova Scotia Procurement Portal tender `IT2026-01` — https://procurement-portal.novascotia.ca/tenders/IT2026-01 | Canonical tender identity/route. The public mirror's original-source link resolves here. | Highest-authority route, but this browser session receives `Request Rejected`, so the tender body/attachments are not yet available as C0 bytes. | Recover the portal record and every attachment/addendum through an authorized browser/session; hash the downloaded bytes. |
| S1 | CanadaBuys tender-opportunity index — https://canadabuys.canada.ca/en/tender-opportunities | St. Francis Xavier University has an open `Certificate Lifecycle Management` services opportunity; index renders a 2026-09-25 close. | High for existence/title/indexed date; index is not the full solicitation and may normalize timezone/date. | Reconcile against S0 controlling metadata. |
| S2 | Updated Nova Scotia procurement mirror record — https://techbids.ca/bids/96820/ | Buyer St. Francis Xavier University; originally posted 2026-08-25; record says the issuing organization later modified the listing; latest mirror renders due 2026-09-24 23:00 ET and links S0 as original source. | Medium/high discovery evidence; still not controlling. The earlier public date discrepancy is now safety-relevant. | Use 2026-09-24 23:00 ET as the conservative internal planning deadline until S0 is readable. |
| S3 | Public scope mirror — https://rfpplanet.com/sys-6673/certificate-lifecycle-management | Detailed functional themes: discovery/inventory, lifecycle automation, CA integrations, RBAC/workflows, APIs, audit/compliance, implementation/KT and support. | Medium. Useful for capture, **not controlling**. It reports publish/close metadata that differs from S2. | Reconcile every row in `REQUIREMENTS.md` to controlling RFP section/page before response use. |
| S4 | Commons issue #13892 | Internal custody, scope and boundaries. | High internal authority. | Keep durable retrieval/decision receipts attached to this lane. |

## Deadline discrepancy and safety rule

The public sources render two dates for what appears to be the same deadline:

- CanadaBuys / other indexing: `2026-09-25`.
- Updated Nova Scotia procurement mirror: `2026-09-24 23:00 ET`.

The mirror explicitly says the listing was modified after original posting. The one-hour/date-boundary pattern may be timezone normalization, but that is **not proven** without the controlling portal record. Therefore:

- treat **2026-09-24 23:00 ET** as the conservative internal planning deadline;
- do not submit based on a mirror timestamp;
- S0 must establish the exact date, local timezone, portal close behavior and any amendment before submission authority can be granted.

Do not infer the question deadline, mandatory meeting, submission method, contract term, award basis, budget, Canadian-vendor preference, insurance, security certification, data residency, or accessibility requirements from discovery mirrors.

## Controlling-package retrieval checklist

Capture all of the following as immutable evidence before bid/no-bid approval:

- S0 portal record, tender identifier `IT2026-01`, and canonical URL;
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
