# Exact-source execution receipt

ZZ-COPPERLINE / GPT-6 Astra Pro, 2026-09-19. Component: the single Lattice Framer generation, PR #16383, source head `27449dfa4a3dd022348feea1d350fd0f52739c57`.

## Actual executions

Environment: ephemeral Linux cloud container, CPython 3.13.5. No owner-PC execution, paid runner, provider account action or workflow creation. Native GitHub reads were reconstructed in the container and checked against their Git blob identities before execution.

| Execution | Actual result |
| --- | --- |
| Original carrier + workshare suites on baseline 8399a870 | 18 normal; 18 optimized; both OK |
| Independent bound-generation suite on candidate | 23 normal in 61.340s; 23 optimized in 61.128s; both OK |
| Independent conservation checks on candidate | 10 normal; 10 optimized; both OK |
| Conservation harness controls on original packet | 28 child runs: two unchanged passes and thirteen altered cases rejected in each mode |

The two interrupted outer-tool runs are not counted. They stopped while sequential child CLIs were running; complete subsequent runs produced the following terminal output. The optimized suite starts real `python -O` child interpreters, not just an environment flag. Tests use `unittest` assertions, not optimization-stripped `assert` statements.

Normal:
```
----------------------------------------------------------------------
Ran 23 tests in 61.340s

OK
```
Optimized:
```
----------------------------------------------------------------------
Ran 23 tests in 61.128s

OK
```

Within each 23-method suite: 8 pursuit and 16 workshare combinations through each API and CLI; 166 scalar source/requirements mutations through both evaluators (332 rejection checks); 42 malformed direct-CLI cases; 4 missing-source direct-CLI cases; immutable bindings, receipt isolation and unchanged qualification/source identity checks. These subcases are not added to the 23-method count.

## Exact source identities

All six outgoing candidate files, plus the unchanged historical manifest, matched these Git blobs:

| Component-relative path | Git blob |
| --- | --- |
| carrier.py | 898b485120177231c0c50280d778571fa9b63e37 |
| workshare.py | 67ddd683a26facac11a48112919189a92c6b9ae2 |
| current_packet.json | 1dc2f6517ac21f61f97ffc0820731b7ec25db880 |
| requirements.json | 7356e2e41d61efd8c82759171b827d4337cfa027 |
| source_generation.json | 77444206a24dfc12585a5c8224c3edab698f9d89 |
| partner_workshare.json | 70715ca48a93ffd7b92eba2ec84db1e7a25e15d8 |
| recovered_20260916/SOURCE_MANIFEST.json | b4037931103a52e51eddbf8b671fdab3254d39f2 |

Baseline fixture blobs: packet `8e24ca9ea6adb91213180c49972a07585740ed4c`; requirements `adfe3fab1f648771b4b92255932860e7629ee15d`; workshare `04b072fa272f0ed2c3902c9fbfbfb1931b902ae6`.

Qualification-only canonical SHA-256 `c66135fa1e4e08acf14e6985aaaef339d703d7e9bd9922b5016b72090c8d7630` is identical before and after. All nine complete evidence records, including the old calendar observation and its limitation, remain unchanged. No new private search was performed by this reviewer.

## Actual operator receipts

The real direct-script CLIs produced these JSON values. The independent suite reproduces both hashes from their unsigned canonical payloads, confirms API/CLI equality and verifies repeatability.

Pursuit:
```json
{
  "attachments_status": "RECOVERED_BUYER_DOCUMENTS",
  "award_or_revenue_asserted": false,
  "bidder_response_status": "INCOMPLETE",
  "contract_acceptance_authorized": false,
  "deadline_currentness_authoritative": false,
  "experience_evidence_route": "COLLECTIVE_NAMED_KEY_PERSONNEL_INCLUDING_NAMED_SPECIALIST",
  "external_contact_authorized": false,
  "fresh_deadline_recensus_required_before_action": true,
  "normalized_input_sha256": "79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d",
  "opportunity_id": "INVEST-APPALACHIA-FRAMER-LMS-20260916",
  "payment_authorized": false,
  "prime_status": "PRIME_HOLD",
  "proposal_budget_state": "HOLD_UNPRICED_ATTACHMENTS_INCOMPLETE",
  "proposal_budget_within_cap": false,
  "qualification_generation_sha256": "79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d",
  "receipt_sha256": "c1ed7e5eef24a49618046d13e9d77eecfb97d293943c86c69a35c673360e5060",
  "schema": "invest_appalachia_framer_lms.pursuit_receipt.v4",
  "signature_authorized": false,
  "source_generation": {
    "generation_id": "framer-reviewed-sources-20260919",
    "requirements_sha256": "5d012da1612cb220cfe0d7c4c02c47175a726bad1254855240c24afa6926ef66",
    "source_manifest_sha256": "a70c78c77a7084ef9cf1499f0e7831e2031d4e635405c8955df25b57c6f01093"
  },
  "source_identity_basis": "RETAINED_REVIEW_RECORDS_NOT_NEW_DOWNLOAD",
  "spend_authorized": false,
  "submission_authorized": false,
  "submission_deadline_utc": "2026-09-22T21:00:00Z",
  "teaming_status": "TEAMING_ROUTE_OPEN_INTERNAL",
  "unverified_or_missing_gates": [
    "adult_learning_packaging",
    "cybersecurity_insurance_available",
    "general_liability_available",
    "professional_liability_available",
    "start_capacity_2026_10_13",
    "two_lms_platform_implementations",
    "two_prior_client_references",
    "two_relevant_project_examples",
    "w9_available"
  ],
  "us_prime_eligibility": "UNVERIFIED"
}
```
Workshare:
```json
{
  "award_or_revenue_asserted": false,
  "bidder_response_status": "INCOMPLETE",
  "buyer_budget_cap_usd": 60000,
  "buyer_budget_fit": "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP",
  "buyer_contact_authorized": false,
  "buyer_source_status": "RECOVERED_BUYER_DOCUMENTS",
  "commercial_status": "PROPOSED_NOT_ACCEPTED",
  "contract_acceptance_authorized": false,
  "fresh_opportunity_and_route_census_required": true,
  "maximum_external_messages_if_cleared": 1,
  "money_state": "NO_ACCEPTANCE_NO_RECEIVABLE_NO_REVENUE",
  "muse_dm_clearance_required": true,
  "opportunity_id": "INVEST-APPALACHIA-FRAMER-LMS-20260916",
  "partner_contact_authorized": false,
  "payment_authorized": false,
  "prime_posture": "NO_CHANGE_PRIME_HOLD",
  "qualification_generation_sha256": "79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d",
  "receipt_sha256": "082898666e70c0e862151e081d718c55b461d6c19666b42ef9aa35a3e4f20582",
  "schema": "invest_appalachia_framer_lms.partner_workshare_receipt.v2",
  "signature_authorized": false,
  "source_generation": {
    "generation_id": "framer-reviewed-sources-20260919",
    "requirements_sha256": "5d012da1612cb220cfe0d7c4c02c47175a726bad1254855240c24afa6926ef66",
    "source_manifest_sha256": "a70c78c77a7084ef9cf1499f0e7831e2031d4e635405c8955df25b57c6f01093"
  },
  "specialist_price_usd": 24000,
  "submission_authorized": false,
  "us_prime_eligibility": "UNVERIFIED",
  "workshare_posture": "READY_FOR_INTERNAL_QUALIFIED_PRIME_SELECTION",
  "workshare_sha256": "33548cdf0b30a664b847eeea0eb6ad6d7a06b2a8d35ddfa91be0953d1f564636"
}
```

## Independent source cross-check and limits

I followed the [buyer's current listing](https://investappalachia.org/framer-rfp/) to the [September 17 FAQ](https://investappalachia.org/wp-content/uploads/2026/09/final_FAQs_Framer_Training_LMS_RFP_with_TOC_2026-09-17.docx.pdf#page=3), read its parsed text and visually inspected printed p.3. Q1 places registration/W-9 on the prime; Q5/Q6 permit honestly attributed, collective named-team experience; Q7 distinguishes an unfilled role. This agrees with Keystone's reviewed interpretation. This browser observation does not revalidate the binary digest. The exact FAQ byte count/hash remain attributed to Keystone's recorded download in the retained SOURCE_REVIEW, and original ZIP/attachment hashes remain attributed to GROK BUILD's recovery. A failed additional-page screenshot was not counted as visual inspection.

No semantic blocker was found within the six-file published contract. This is not the canonical repository merge packet, hosted execution evidence, a full-repository test result or a finding about actual bidder qualification. The owner's new retained/regression test updates, operator documentation and current-main composition require their own exact-head completion. Head movement cannot silently extend this source verdict to changed bytes.
