# Buyer questionnaire recovery and source binding

## Known route

- Find a Tender notice: `080252-2026`
- OCID: `ocds-h6vhtk-06ea51`
- Buyer: Imperial College Healthcare NHS Trust
- Atamis contract reference: `C467704`
- Public response deadline: **1 October 2026, 12:00 noon UK time**

The public notice directs interested suppliers to an attached questionnaire in Atamis. In this harness the Atamis route redirects to an authenticated Salesforce/Atamis session, so the attachment was **not acquired**.

## Authorized recovery procedure

An owner or operator who already has authority to access the buyer portal should:

1. Open the buyer's Atamis opportunity for `C467704` without accepting unrelated terms or submitting a response.
2. Download every questionnaire/instruction attachment and any amended/replacement version.
3. Preserve filenames and bytes exactly; record portal timestamp/version metadata if shown.
4. Compute `sha256sum FILE` (or equivalent) for each controlling file.
5. Compare the notice/deadline/version to the public ledger and record any conflict rather than silently overwriting it.
6. Read every prompt, declaration, mandatory field, word/character limit, submission mechanic and contact rule.
7. Update `sources.json` only after the bytes exist locally:
   - `acquired=true`;
   - exact lowercase SHA-256 of the questionnaire;
   - `reviewed=false`, state `QUESTIONNAIRE_ACQUIRED_UNREVIEWED` until the prompts are actually reviewed;
   - after full review, `reviewed=true`, state `QUESTIONNAIRE_ACQUIRED_REVIEWED`.
8. Recompute SHA-256 of the complete updated `sources.json` bytes and put that digest into the qualification manifest.
9. Run `qualify.py ... --questionnaire ACTUAL_FILE` so the engine verifies the questionnaire bytes against the source ledger.

## Extraction checklist

From the buyer-controlled questionnaire capture at minimum:

- supplier eligibility and geography;
- clinical/pathology product requirements;
- mandatory certifications/standards and evidence form;
- deployment topology and volumes;
- discipline coverage;
- data migration/history/archive expectations;
- interface/EPR/national-system/automation requirements;
- security, privacy, hosting/data-location and incident requirements;
- clinical-safety and regulatory requirements;
- implementation timetable and transition constraints;
- training/support/service-management expectations;
- commercial-model questions and requested price ranges/units, if any;
- AI/ML questions and governance expectations;
- conflicts, declarations and market-engagement rules;
- response format, field limits and exact submission mechanics;
- whether a prime, consortium, subcontractor or specialist may participate in this stage;
- any buyer statement about how market-engagement input may shape the future tender.

## Stop conditions

Stop and escalate rather than guessing if the portal requires new account registration, acceptance of legal terms beyond ordinary access, a declaration, a live submission action, or any representation on behalf of Token Junkie Labs. This carrier does not authorize those actions.
