# South Coast AQMD P2027-03 pursuit recovery carrier

Operation `SCAQMD-P2027-03-RECOVERY-ZMQV5R9-20260916` recovers the unshipped Sep-14 pursuit while preserving original ZMA-K7Q4 opportunity/source/commercial credit.

The official 70-page buyer RFP was re-read on 2026-09-16 and key source pages were visually verified, but raw PDF download failed in this execution environment. `source.discovery.json` therefore states `RAW_BYTES_UNBOUND`, and the discovery assessment must remain `HOLD_SOURCE_BYTES_REQUIRED`. Do not replace that with a guessed hash. When an authorized operator obtains the exact current PDF bytes, update source size/SHA, sign that source generation using an owner-held key, and only then evaluate later gates.

## State ordering

1. `HOLD_SOURCE_BYTES_REQUIRED`
2. `HOLD_DEADLINE_PASSED`
3. `HOLD_CONFERENCE_ATTENDANCE`
4. `HOLD_PAST_PROJECT_QUALIFICATION`
5. `HOLD_CAPABILITY_PLAN`
6. `HOLD_TEAM_QUALIFICATION`
7. `READY_FOR_OWNER_PROPOSAL_REVIEW`

Even the strongest state is owner proposal review, never autonomous submission authority.

## Source boundary

`build_source_authority()` HMAC-binds the retained source record using a key unavailable in the packet. This protects the local retained-generation relationship; it does **not** prove buyer authenticity by cryptography. Buyer authenticity still depends on recovering the official source from the official AQMD route. Candidate packets cannot invent a different URL, page count, digest or raw status and still verify.

## Qualification boundary

The compiler requires at least three distinct comparable projects in the five-year window. Across those projects it requires evidence of a public/regulatory engagement, a >=$100,000 or >=12-month engagement, named core technology, client-verifiable references, and a documented challenge/corrective example. It separately requires mandatory conference attendance evidence and seven prime/team gates. `UNKNOWN` never becomes `PROVEN`.

## CLI

```bash
export SCAQMD_SOURCE_AUTHORITY_KEY_HEX='<64+ hex chars>'
python -m opportunities.scaqmd_p2027_03.cli sign-source source.discovery.json source_authority.json --key-id owner-2026-09
python -m opportunities.scaqmd_p2027_03.cli compile example.discovery.json source_authority.json assessment.json --key-id owner-2026-09
python -m opportunities.scaqmd_p2027_03.cli verify example.discovery.json source_authority.json assessment.json --key-id owner-2026-09
```

Outputs are exclusive-create files. JSON parsing rejects duplicate keys and non-finite constants.

## External authority

The compiler always returns `false` for conference registration, buyer contact, question/proposal submission, signature, certifications, preference claims, price/contract commitment, production access and award/payment/revenue claims.

The prior Sep-14 Varsun Muse clearance is explicitly dead. A later Muse production-correction message identified that exact decision as unsafe because `DO NOT SEND YET` had been converted to `Cleared ... Go`. Any future prime outreach must start with a fresh cross-provider dedupe and a new exact Muse election.
