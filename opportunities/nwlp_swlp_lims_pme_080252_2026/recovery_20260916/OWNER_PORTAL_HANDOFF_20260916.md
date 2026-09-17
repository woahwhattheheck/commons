# Owner handoff — recover C467704 controlling questionnaire without submitting

Current state: `HOLD_PORTAL_ATTACHMENT_AUTH_REQUIRED`

This handoff exists because the public recovery pass reached the supplier-portal boundary without obtaining the controlling questionnaire bytes.

## Exact target

- Buyer: Imperial College Healthcare NHS Trust
- Programme: NWLP + SWLP Pathology IT LIMS preliminary market engagement
- Find a Tender: `080252-2026`
- OCID: `ocds-h6vhtk-06ea51`
- Atamis contract reference: `C467704`
- Buyer text deadline: **1 October 2026, 12:00 noon UK time**

## Do only the portal step the harness cannot do

1. Open the authorized supplier-side Atamis session.
2. Search exact `C467704`; verify buyer/title before downloading anything.
3. Inspect attachments/addenda without beginning a submission.
4. Download every questionnaire/instruction file plus replacement/addendum versions.
5. Do not edit, normalize, re-save or convert the originals.
6. Record displayed filenames, version labels and portal timestamps.
7. Compute SHA-256 for every exact file.
8. Return the original bytes + hashes to the Commons carrier.

Stop if access requires any new representation or commitment (registration under a new entity, legal acceptance beyond ordinary login, declaration, certification, or submission action). Record the blocking screen/action instead.

## What happens after bytes arrive

Follow existing:

- `questionnaire_recovery.md`
- `authority_model.md`
- `qualify.py`

Required order:

1. bind exact questionnaire digest(s);
2. extract every mandatory field/gate/limit/submission mechanic;
3. prove addenda completeness;
4. independently review and retain questionnaire extraction authority;
5. build/review capability evidence authority;
6. for teaming, bind a real partner-prime authority;
7. run current-readiness qualification.

Even a green current-readiness result is only `READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW`. It is never buyer submission authority.

## Parallel revenue action

The portal gate does not block partner commercialization. Cirdan is in Muse arbitration for one paid fixed-fee specialist workshare inquiry; see `CIRDAN_WORKSHARE_20260916.md`. Do not contact Clinisys again absent a new event.
