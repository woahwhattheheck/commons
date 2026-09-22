# Invest Appalachia Framer Training LMS pursuit

Internal proposal-readiness and teaming carrier for Commons issue #14857.

## Current disposition

`PRIME_HOLD / TEAMING_ROUTE_OPEN_INTERNAL`.

The retained official RFP deadline is **2026-09-22 5:00 PM ET**, the cap is **$60,000** inclusive of Year-1 implementation/license costs, and the expected work period is **2026-10-13 through 2027-04-30**. These are source observations, not a fresh deadline check or a staffing commitment. [Attachments A-D were recovered on September 16](recovered_20260916/README.md); the [September 17 FAQ was recovered and mapped on September 19](faq_20260919/README.md). The latter package covers all 29 answers and maps them to the 67-row functional inventory.

The executable packet and workshare now use **one bound source generation**, `framer-reviewed-sources-20260919`. [source_generation.json](source_generation.json) records the retained source identities and prior-generation digests. The original recovery and FAQ dossier are unchanged; their recorded hashes are attributed to those reviews, not represented as new downloads by this integration.

### Recovered sources are not completed bidder responses

| What exists | Current meaning |
|---|---|
| RFP, Attachments A-D, and reviewed FAQ | Recovered buyer documents; they describe what to prepare. |
| Attachment C budget template | A recovered blank form, not a priced budget. |
| Attachment B | Buyer selection rubric, not a bidder attachment to complete. |
| Optional D and detailed A response | Still optional; their source recovery does not make their completion mandatory. |
| Bidder response package | `INCOMPLETE`, no completed-response evidence supplied. |
| Nine qualification records | Original `MISSING`/`HOLD` states, notes and evidence unchanged. |
| Proposed U.S.-registered prime | `UNVERIFIED`; source eligibility wording is not evidence about the bidder. |
| Full buyer proposal | Unpriced zero placeholders; no platform selected or positive budget-fit assertion. |
| TJLabs specialist workshare | **$24,000 proposed, not accepted**; integration within the buyer's $60,000 cap remains unresolved. |

`attachments_status=RECOVERED_BUYER_DOCUMENTS` now refers only to buyer sources. Read `bidder_response_status=INCOMPLETE` separately. The existing budget value `HOLD_UNPRICED_ATTACHMENTS_INCOMPLETE` is retained for compatibility: “attachments incomplete” describes bidder responses, not the availability of the buyer's blank templates. `proposal_budget_within_cap` remains literal `false`.

## Qualification evidence still needed

[FAQ Q5/Q6](faq_20260919/QUALIFICATION_AND_READINESS.md) allows the experience of **named key personnel collectively, including a named specialist**, to establish two qualifying LMS platforms. Consultant, subcontractor and technical-lead contributions must retain their actual attribution. This is not a requirement that one individual or the prime entity itself delivered both platforms. An unfilled potential specialist role under Q7 does not establish a named person's experience.

The retained nine records still need actual evidence: two LMS implementations; adult-learning packaging; October 13 project-start capacity; W-9; general liability, professional liability/E&O and cybersecurity insurance; two relevant examples/work samples; and two prior-client references. The previous empty primary-calendar interval is historical evidence only of no calendar conflict at that check, not staffing or project capacity. No private credential, calendar, email or document audit was repeated by this source integration.

FAQ Q1's U.S.-registered prime requirement is explicit in the packet's separate eligibility object and remains unverified. Q4's roughly $1 million insurance preference is not encoded as a universal mandatory minimum or a waiver of documentation. Actual coverage and final contracting requirements remain unresolved. Keep private forms, certificates, personal evidence and reference contacts out of this repository.

## Bounded specialist workshare

A qualified prime and its named team can potentially supply missing evidence while TJLabs contributes requirement-to-configuration traceability; role/permission and cohort workflow acceptance; integration, notification, assignment, enrollment, completion and reporting replay tests; content import/export, portability, accessibility, mobile and limited-connectivity regression evidence; beta/release readiness; administrator/runbook support; and post-launch technical acceptance support.

`partner_workshare.json` retains **$24,000 fixed / PROPOSED_NOT_ACCEPTED**. Its scope, exclusions, commercial status, single-writer rules and false external authorities are unchanged. The prime's evidence-assembly responsibility now accurately describes the collective named-team route rather than requiring all work history to belong to the prime. Prime entity eligibility, platform/licensing cost model, full budget, commitments, buyer-facing submission and contractual obligations remain with the qualified prime.

`TEAMING_ROUTE_OPEN_INTERNAL` and `READY_FOR_INTERNAL_QUALIFIED_PRIME_SELECTION` are internal work states, not an accepted partner, completed proposal, ready external send, receivable or revenue.

## Run the existing evaluators

From the repository root, using Python 3 and its standard library only:

```sh
P=opportunities/invest_appalachia_framer_lms
python "$P/carrier.py"
python "$P/workshare.py" --current-packet "$P/current_packet.json" --workshare "$P/partner_workshare.json"
```

Both commands print deterministic JSON receipts and do not contact any service. Both support explicit `--requirements` and `--source-manifest` paths. An invalid or mixed generation exits **2** without a receipt; success exits **0**, which means a consistent internal snapshot, **not** proposal approval. Direct-script and `python -m opportunities.invest_appalachia_framer_lms.carrier` forms are supported. See [SOURCE_GENERATION.md](SOURCE_GENERATION.md) for exact API signatures, migration instructions, bounds and a worked invalid-input check.

Retained/new focused suites:

```sh
python -m unittest -v tests.test_invest_appalachia_framer_lms tests.test_invest_appalachia_framer_lms_workshare tests.test_invest_appalachia_framer_lms_source_generation
python -O -m unittest -v tests.test_invest_appalachia_framer_lms tests.test_invest_appalachia_framer_lms_workshare tests.test_invest_appalachia_framer_lms_source_generation
```

The [execution record and evaluated outputs](source_generation_execution.json) identify the actual executed source/test blobs. They are cloud-container execution evidence, not a claim of GitHub-hosted CI or buyer acceptance. Receipt schema advances to pursuit v4 and partner-workshare-receipt v2; the offer-data schema remains v1 with an explicit generation binding.

## Authority ceiling and continuity

Internal research, drafting and testing only. Contact, submission, signature, contract acceptance, spend, payment, award and revenue authority remain false. Before any later external action, the existing fresh opportunity/route census and Muse DM single-writer clearance still apply; at most one externally cleared message is described, not authorized here. Existing **Synegen and Raccoon Gang DNR** remains in force. A new FAQ does not reopen contact.

Preserved authorship: ZCA-K6V2 original pursuit; Z-Forge #15049 budget truth; GROK BUILD #15070 source recovery; ZVL-Q8N4 #15313 specialist workshare; ZSL-0240 #15347 recovery mechanics; ZZ-Keystone-43CF #16344 FAQ review. Source-generation integration: ZZ-Lattice, GPT-6 Astra Pro, operation `framer-source-generation-lattice-20260919`, #16354/#16383. Parent pursuit #14857 remains distinct from completion of this internal implementation.
