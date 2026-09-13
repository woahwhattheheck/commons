# Evidence inventory

The response must remain evidence-first. This file intentionally contains no invented buyer-facing assertions.

| Evidence need | Current repository status | Owner action |
|---|---|---|
| Organization legal name / mission | OWNER_INPUT_REQUIRED | Supply exact current facts |
| Public-health / nonprofit / government-funded engagement | OWNER_INPUT_REQUIRED | Select at least one supportable engagement and evidence reference |
| Two professional references from similar engagements | OWNER_INPUT_REQUIRED | Select two distinct references; keep private contact data out of Git |
| Communications track evidence | NOT ASSERTED | Supply only if selecting the track |
| Research / evaluation evidence | NOT ASSERTED | Supply only if selecting the track |
| Strategy / planning evidence | NOT ASSERTED | Supply only if selecting the track |
| Grant-writing evidence | NOT ASSERTED | Supply only if selecting the track |
| Team availability | OWNER_INPUT_REQUIRED | Confirm staff participation and roles |
| Pricing | OWNER_INPUT_REQUIRED | Owner sets and approves |
| DEI approach | OWNER_INPUT_REQUIRED | Supply actual policy/practice/evidence |
| Boston community knowledge | OWNER_INPUT_REQUIRED / preference | Supply only if supportable |
| Service request portal / tracking | OWNER_INPUT_REQUIRED / preference | Describe only actual capability |
| Living Wage obligation | OWNER_REVIEW_REQUIRED | Review BPHC contract obligation; no legal certification here |
| SAM exclusion requirement | OWNER_REVIEW_REQUIRED | Review/check through appropriate authoritative process |
| RFP source | CAPTURED URL + fact snapshot | Refresh before submission |

## Source custody note

The canonical RFP URL and an extracted fact snapshot are committed. The carrier did **not** obtain the PDF bytes locally, so `rfp_pdf_sha256` is deliberately null. `preflight.py` binds the canonical JSON source snapshot digest rather than inventing a PDF digest.
