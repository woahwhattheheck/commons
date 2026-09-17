# C467704 public recovery pass — 2026-09-16

Operation: `NWLP-SWLP-C467704-CONTROLLING-PACK-RECOVERY-20260916`

This pass re-opened the existing Commons carrier for Imperial College Healthcare NHS Trust's joint NWLP + SWLP Pathology IT LIMS preliminary market engagement, Find a Tender `080252-2026`, OCID `ocds-h6vhtk-06ea51`, Atamis reference `C467704`.

## Result

**Truthful terminal: `HOLD_PORTAL_ATTACHMENT_AUTH_REQUIRED`.**

The opportunity itself is still public and current. Atamis publicly exposes C467704 metadata and reproduces the buyer's instruction that interested suppliers should complete the **attached questionnaire** and respond by **1 October 2026 at 12:00 noon UK time**. The public page does not expose the questionnaire bytes or a public attachment download. Public replicas independently reproduce the same opportunity and Atamis route; the Sell2Wales rendering explicitly reports **Has documents: No**.

No questionnaire bytes were found in public search, public Atamis metadata, D3, OpenTenders, TenderSignal, Stotles or Sell2Wales. This is evidence of the boundary reached by this pass, not proof that the buyer portal has no attachment.

## Controlling-source treatment

Use the buyer's explicit noon instruction as the deadline authority:

- Atamis C467704 text: **1 Oct 2026 12:00 noon UK time**.
- The public notice text replicated by multiple services says the same.
- Sell2Wales separately renders an engagement due date of `23:59`. That later UI rendering must **not** be used to extend the explicit buyer instruction.

Public evidence checked:

1. Atamis public opportunity search/detail — C467704, Imperial College Healthcare NHS Trust, scope, opening date, response deadline, PA23 Open Procedure.
   - `https://atamis-1928.my.salesforce-sites.com/ProSpend__CS_PublicLandingPage`
2. Sell2Wales notice replica — OCID, buyer, contact, full description, and `Has documents: No`.
   - `https://www.gwerthwchigymru.llyw.cymru/search/show/search_view.aspx?ID=AUG651154&catID=`
3. D3 FTS replica — notice identity, £28m value, scope and Atamis route; notice-document list contains the preliminary notice, not the questionnaire.
   - `https://d3tenders.com/contract/?ocid=ocds-h6vhtk-06ea51`

## What remains owner-only

The next useful recovery step requires a supplier-side Atamis session or equivalent owner-authorized portal access. Do **not** replace this with guessed questionnaire fields.

Owner/operator sequence:

1. Enter Atamis and locate exact contract reference `C467704`.
2. Do not accept terms, make declarations or submit anything merely to inspect the record.
3. Download every questionnaire/instruction attachment and all replacement/addendum versions.
4. Preserve original filenames and bytes; record portal version/timestamp metadata.
5. Hash each file SHA-256.
6. Return the bytes + hashes to the existing `questionnaire_recovery.md` / `authority_model.md` flow.
7. If Atamis requires new registration, legal acceptance, a declaration, or a live submission action before download, stop and record that exact gate instead of crossing it implicitly.

Public notice contact `Nigel Weatherhead <nigel.weatherhead1@nhs.net>` is captured only as public procurement metadata. This packet grants **no buyer-contact authority**.

## Commercial path outside the owner gate

The missing questionnaire blocks response-readiness, but it does not require commercial idleness. The existing carrier already defines a bounded `TEAMING_INTEGRATION_SPECIALIST` / `TEAMING_VALIDATION_EVIDENCE` seam.

Clinisys was already contacted for this exact opportunity on 2026-09-13 (`NWLP-SWLP-CLINISYS-TEAMING-ZPLQ7M5-20260913`, Gmail thread `1a09af0c5f357d15`), so it remains hard DNR absent a new event.

A separate collision-clean candidate is **Cirdan**. Its current first-party pages describe ULTRA as a multidisciplinary LIS spanning cellular pathology, transfusion medicine, biochemistry, haematology, microbiology and genetics; support regional/national multi-lab environments; expose FHIR/interoperability; show an NHS testimonial; report 100+ LIS installations / partnerships with 80 national laboratories; and publish `info@cirdan.com`.

This proves plausible prime fit only. It does **not** prove that Cirdan is pursuing C467704, has capacity, wants a subcontractor, or accepts any commercial term.

The active commercial hypothesis is a **paid** `$25,000 fixed / PROPOSED_NOT_ACCEPTED` specialist workshare covering migration reconciliation, interface/replay/idempotency QA, data-lineage/evidence, UAT/acceptance evidence and cutover evidence. Cirdan retains LIMS product/configuration, clinical-safety/regulatory authority, NHS references, prime/submission authority, staffing/pricing and final acceptance.

Exact Muse key: `NWLP-SWLP-CIRDAN-PAID-WORKSHARE-ZSOL-20260916`.

No send is authorized by this repository packet.
