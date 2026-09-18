# Buyer questionnaire recovery, extraction and authority retention

## Known route

- Find a Tender notice: `080252-2026`
- OCID: `ocds-h6vhtk-06ea51`
- Buyer: Imperial College Healthcare NHS Trust
- Atamis contract reference: `C467704`
- Public response deadline: **1 October 2026, 12:00 noon UK time**

The public notice directs interested suppliers to an attached questionnaire in Atamis. In the original harness the Atamis route redirected to an authenticated Salesforce/Atamis session, so the attachment was **not acquired**.

## Authorized recovery procedure

An owner or operator who already has authority to access the buyer portal should:

1. Open the buyer's Atamis opportunity for `C467704` without accepting unrelated terms or submitting a response.
2. Download every questionnaire/instruction attachment and every amended/replacement version.
3. Preserve filenames and bytes exactly; record portal timestamp/version metadata if shown.
4. Compute SHA-256 for every controlling file.
5. Compare notice/deadline/version against the public ledger; record conflicts rather than silently overwriting them.
6. Read every prompt, declaration, mandatory field, limit, submission mechanic and contact rule.
7. Update `sources.json` only after the bytes exist:
   - `acquired=true`;
   - exact lowercase questionnaire SHA-256;
   - `reviewed=false` and `QUESTIONNAIRE_ACQUIRED_UNREVIEWED` until full review;
   - after full review, `reviewed=true` and `QUESTIONNAIRE_ACQUIRED_REVIEWED`.
8. Recompute SHA-256 of the exact updated `sources.json` bytes and bind the manifest to it.
9. Build a questionnaire extraction-authority packet as specified in `authority_model.md`, including the exact source/questionnaire digests, document version, complete addenda set, and complete required-gate universe.
10. Independently review that extraction, then retain the exact packet SHA-256 in `TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256` through a source review. Supplying an unretained authority packet intentionally fails.
11. Build/review/retain capability-evidence authority and, for a teaming route, partner-prime authority using the same process.
12. Run `qualify.py` with the actual questionnaire plus all applicable retained authorities. A READY result remains owner-review only and never buyer-submission authority.

Example shape after reviewed authorities exist:

```bash
python3 qualify.py MANIFEST.json \
  --questionnaire ACTUAL_QUESTIONNAIRE \
  --questionnaire-authority RETAINED_EXTRACTION_AUTHORITY.json \
  --evidence-authority RETAINED_EVIDENCE_AUTHORITY.json \
  --partner-authority RETAINED_PARTNER_AUTHORITY.json
```

## Extraction checklist

Capture at minimum:

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
- whether a prime, consortium, subcontractor or specialist may participate at this stage;
- any buyer statement about how market-engagement input may shape the future tender;
- all addenda/replacement-document identities needed to show the extracted gate universe is complete.

## Stop conditions

Stop and escalate rather than guessing if the portal requires new account registration, acceptance of legal terms beyond ordinary access, a declaration, a live submission action, or any representation on behalf of Token Junkie Labs. This carrier does not authorize those actions.
