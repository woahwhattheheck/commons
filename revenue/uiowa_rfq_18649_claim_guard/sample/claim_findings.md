# Cross-lane claim guard

Scanned `/home/user/commons/revenue` — **67 lanes, 892 files**.

Read-only. Nothing in any scanned lane was modified.

## Three outcomes, not two

| Outcome | Meaning |
|---|---|
| `ASSERTION` | The prohibited claim is being made. A finding. |
| `REFUSAL` | The text names the rule in order to decline it. Positive evidence, not silence. |
| `AMBIGUOUS` | The classifier cannot tell. **UNKNOWN** — needs a person. Never auto-cleared. |

A lane that refuses a claim contains the same words as a lane that makes one. That is why classification exists and why a word search would be worse than useless here.

## Totals

| Outcome | Count |
|---|---|
| `ASSERTION` | 50 |
| `REFUSAL` | 390 |
| `AMBIGUOUS` | 195 |

Raw counts. No lane is scored, graded or ranked.

### ASSERTION findings by source context

| Context | Count |
|---|---|
| `code` | 5 |
| `data` | 11 |
| `prose` | 25 |
| `test` | 9 |

Context is reported, not filtered. A match in a `test` file is frequently a planted negative-control fixture; a match in `code` is frequently an identifier. Start with `prose`.

### Read before quoting the totals

- ASSERTION means the clause READS AS a statement of fact containing the prohibited concept. It is a candidate finding for a person to confirm, not a proven violation. The scan cannot tell a claim about the assessed organization from the same word used as a document name ('certified cost rate schedule'), an identifier ('check_conformance'), or a deliberately planted test fixture.
- 195 matches could not be classified and are listed as AMBIGUOUS. They are NOT cleared. Each needs a person to read the clause and decide. Treating them as clean would manufacture confidence the scan does not have.
- 390 REFUSAL matches were found. These are positive evidence: lanes naming a prohibited claim in order to decline it.

## By rule

| Rule | Name | ASSERTION | REFUSAL | AMBIGUOUS | What it catches |
|---|---|---|---|---|---|
| `CG-01` | CERTIFICATION_CLAIM | **36** | 156 | 132 | Asserting that the assessed organization is certified, compliant or conformant with a standard. |
| `CG-02` | MATURITY_LEVEL | **1** | 94 | 17 | Reducing the organization to a maturity or readiness number. |
| `CG-03` | PEER_COMPARISON | **9** | 70 | 40 | Placing the organization against peers or an industry norm. |
| `CG-04` | INDIVIDUAL_SCORING | **0** | 9 | 2 | Scoring or ranking a named person rather than a role or a capability. |
| `CG-05` | REAL_UNIVERSITY_FINDING | **4** | 61 | 4 | Stating something about the real University as though it were an observed finding. |
| `CG-06` | UNLABELLED_FICTION | **0** | 0 | 0 | — |
| `CG-00` | UNREADABLE_FILE | **0** | 0 | 0 | — |

## ASSERTION (50)

| File | Line | Rule | Context | Matched | Clause |
|---|---|---|---|---|---|
| `uiowa_rfq_18649_acceptance_map/README.md` | 3 | `CG-01` | `prose` | `conformance` | Artifact conformance evidence only. The workshare these criteria come from is PROPOSED / NOT ACCEPTED. |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/uiowa_rfq_18649_workshare__ACCEPTANCE_EXHIBIT.md` | 40 | `CG-01` | `prose` | `conformance` | The artifact acceptance criteria below are a deliverable-conformance and cure mechanism; |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/uiowa_rfq_18649_workshare__ACCEPTANCE_EXHIBIT.md` | 79 | `CG-01` | `prose` | `conformance` | Section 5.2 provides an objective conformance/cure frame for the delivered draft; |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/uiowa_rfq_18649_workshare__ACCEPTANCE_EXHIBIT.md` | 208 | `CG-01` | `prose` | `conformance` | This conformance/cure protocol is distinct from the proposed payment schedule: kickoff remains triggered by written authorization, draft remains triggered by delivery, and only the final base-workshare milestone is accep |
| `uiowa_rfq_18649_ai_integration/demo_swap.py` | 38 | `CG-01` | `code` | `conformance` | conformance = checkconformance(port, POLICY) if failmode is None else \ |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_ranking.csv` | 7 | `CG-01` | `data` | `certification` | UNKNOWN,UNRANKED - DO-NOT-PURSUE,OPP-RIS-02,RIS,Generate effort-certification reminder narratives,DO-NOT-PURSUE,-346.0,-122.2,-11.0,40.0,70.0,120.0,0.02,0.04,0.08,UNKNOWN,LOW,HIGH,HIGH,none,none,"task suitability is LOW: |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 107 | `CG-01` | `prose` | `certification` | - Certifications completed by the period deadline: certifications on time / certifications due, per certification period, baseline 0.88 |
| `uiowa_rfq_18649_bid_pack/README.md` | 140 | `CG-01` | `prose` | `conformance` | Accessibility requirements. Whether PDF/UA tagging or a specific WCAG conformance level is required is UNKNOWN; |
| `uiowa_rfq_18649_bid_pack/fixtures/sections/price.md` | 1 | `CG-01` | `prose` | `certified` | Pricing is fixed-fee by phase, with the rate basis carried in the certified cost rate schedule rather than restated in the body. |
| `uiowa_rfq_18649_bid_pack/fixtures/sections/price.md` | 8 | `CG-01` | `prose` | `certified` | The certified cost rate schedule is [[ATT-FIN-02]]. |
| `uiowa_rfq_18649_bid_pack/sample_output/00-INDEX.md` | 65 | `CG-01` | `prose` | `Certified` | - WARN ATTACHMENTNOTSUPPLIED required attachment ATT-FIN-02 (Certified Cost Rate Schedule) is declared but no file was supplied; |
| `uiowa_rfq_18649_bid_pack/sample_output/bid_pack.json` | 206 | `CG-01` | `data` | `Certified` | "detail": "required attachment ATT-FIN-02 (Certified Cost Rate Schedule) is declared but no file was supplied; |
| `uiowa_rfq_18649_bid_pack/sample_output/documents/06-price-proposal.md` | 4 | `CG-01` | `prose` | `certified` | Pricing is fixed-fee by phase, with the rate basis carried in the certified cost rate schedule rather than restated in the body. |
| `uiowa_rfq_18649_bid_pack/sample_output/documents/06-price-proposal.md` | 11 | `CG-01` | `prose` | `certified` | The certified cost rate schedule is [[ATT-FIN-02]]. |
| `uiowa_rfq_18649_build_board/13-ai-context.md` | 57 | `CG-05` | `prose` | `the University of Iowa` | For example, the University of Iowa ChatGPT Edu enterprise license is listed for Public and University-Internal data, with Restricted/Critical use requiring consultation with Research Services or ITS-ISPO. |
| `uiowa_rfq_18649_capability_appendix/observed_runs.json` | 72 | `CG-01` | `data` | `compliance determination` | "outputverbatim": "..........................................SCOPE GUARD - UIOWA RFQ 18649 final report\n==============================================================\nflagged: 2 neutralized: 0\n auditverdict 1\n indivi |
| `uiowa_rfq_18649_capability_appendix/out/capability_appendix.json` | 200 | `CG-01` | `data` | `compliance determination` | "outputverbatim": "..........................................SCOPE GUARD - UIOWA RFQ 18649 final report\n==============================================================\nflagged: 2 neutralized: 0\n auditverdict 1\n indivi |
| `uiowa_rfq_18649_capability_appendix/out/rejection_demo/capability_claims.csv` | 3 | `CG-01` | `data` | `certification` | BAD-02,language: certification and guarantee,no,.,1,python3 capabilityappendix.py,2026-09-19,0,wording rejected (prohibited certification or guarantee language: 'certified'; |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 61 | `CG-01` | `test` | `certification` | "certification verdict or individual/team performance rating is produced by any path in\n" |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 188 | `CG-01` | `test` | `compliant with` | classes("Finding 3: the RIS group is non-compliant with the standard, " |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 205 | `CG-01` | `test` | `compliant with` | classes("The group is non-compliant with IT-18. |
| `uiowa_rfq_18649_economics_resource_adapters/README.md` | 135 | `CG-01` | `prose` | `conformance` | Real and working: the five typed ledgers, all three adapters, the merge with conflict detection, the three-view accounting, the UNKNOWN handling, all four output writers, and the 122-test suite (45 integration, 33 confor |
| `uiowa_rfq_18649_economics_resource_adapters/sample_output/integration_report.md` | 54 | `CG-01` | `prose` | `certification` | - WI-FROM-OPP-RIS-02 Generate effort-certification reminder narratives — no crosswalk entry: this candidate is not yet tied to a recommendation, and the join is not guessed from the title |
| `uiowa_rfq_18649_intake_rehearsal/test_rehearsal.py` | 206 | `CG-01` | `test` | `certified` | "overall score", "grade:", "level 1 of", "certified"): |
| `uiowa_rfq_18649_observability/examples.json` | 77 | `CG-03` | `data` | `percentile` | "target": {"operator": "<=", "valuems": 1200, "percentile": 95}, |
| `uiowa_rfq_18649_operator_handoff/fixtures/minikit/README.md` | 14 | `CG-01` | `prose` | `certify` | It is the strength/gap pair the fixture is required to demonstrate: alpha shows the verifier can certify a passing component, bravo shows it refuses to certify a broken one even though bravo's own README claims it works. |
| `uiowa_rfq_18649_operator_handoff/sample/command_index.json` | 1057 | `CG-05` | `data` | `the University of Iowa` | "outputtail": "usage: server.py [-h] [--port PORT]\n\nLoopback-only analyst workbench for the University of Iowa RFQ 18649 carrier.\nThis server deliberately exposes only the existing compiler's untrusted\ninspection pat |
| `uiowa_rfq_18649_operator_handoff/sample/component_status.json` | 1561 | `CG-01` | `data` | `compliance determination` | "outputtail": "atched : \"non-compliant\"\n in : The service is non-compliant and we recommend purchasing a new tool.\n why : States a compliance determination. |
| `uiowa_rfq_18649_qa_refusal_contract/README.md` | 121 | `CG-03` | `prose` | `percentile` | Coverage is absolute: if a question asks about "peer percentile ranking" and the candidate contains none of {peer, percentile, rank}, it does not matter that it outscored the corpus. |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 324 | `CG-03` | `data` | `percentile` | "What percentile are we in compared to other universities?", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet_defective.json` | 156 | `CG-03` | `data` | `percentile` | "text": "ESS is compliant and would be ranked against peers in the top percentile.", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet_defective.json` | 169 | `CG-03` | `data` | `percentile` | "questionvariants": ["What percentile are we in?"], |
| `uiowa_rfq_18649_qa_refusal_contract/qa.py` | 57 | `CG-03` | `code` | `percentile` | # question class is identifiable from one word ("percentile", "auditor", |
| `uiowa_rfq_18649_qa_refusal_contract/test_qa.py` | 155 | `CG-03` | `test` | `percentile` | "What percentile are we in compared to other " |
| `uiowa_rfq_18649_qa_refusal_contract/test_qa.py` | 270 | `CG-01` | `test` | `compliant with` | for bad in ("ESS is compliant with the framework.", |
| `uiowa_rfq_18649_release_recovery_case/release_recovery_case.py` | 1268 | `CG-01` | `code` | `certification` | "release approval, a recovery certification, or a statement that the release was " |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 108 | `CG-01` | `code` | `compliance determination` | "Asserts a policy violation, which is a compliance determination.", |
| `uiowa_rfq_18649_report_structure/test_report_structure.py` | 357 | `CG-01` | `test` | `compliant with` | text = ("Finding 3: the RIS group is non-compliant with the access-review standard. |
| `uiowa_rfq_18649_report_structure/test_report_structure.py` | 383 | `CG-01` | `test` | `compliant with` | text = ("The group is non-compliant with IT-18. |
| `uiowa_rfq_18649_report_visuals/test_report_visuals.py` | 362 | `CG-03` | `test` | `percentile` | "percentile", "/5", "/10"): |
| `uiowa_rfq_18649_scope_change/README.md` | 128 | `CG-01` | `prose` | `certification` | Specific product/vendor recommendations and legal/audit/certification opinions are a controlling RFQ scope boundary, not a change-control item: |
| `uiowa_rfq_18649_secure_guidance/README.md` | 3 | `CG-05` | `prose` | `the University of Iowa` | Offline assessment kit for the University of Iowa RFQ 18649 preparation work order on guidance usability, reusable secure-development patterns, onboarding, and specialist access. |
| `uiowa_rfq_18649_vocabulary_crosswalk/README.md` | 195 | `CG-01` | `prose` | `certified` | The judgemental-language guard scanned the whole report for "certified" and hit the banner's own promise that no lane is certified. |
| `uiowa_rfq_18649_workbench/12-policy-reference-memo.md` | 20 | `CG-02` | `prose` | `maturity level` | - a group has a particular maturity level; |
| `uiowa_rfq_18649_workbench/framework_crosswalk/20-adaptation-memo.md` | 190 | `CG-01` | `prose` | `certified` | - any service is compliant, certified, secure, mature, immature, or benchmarked at a peer percentile; |
| `uiowa_rfq_18649_workbench/framework_crosswalk/20-adaptation-memo.md` | 190 | `CG-03` | `prose` | `percentile` | - any service is compliant, certified, secure, mature, immature, or benchmarked at a peer percentile; |
| `uiowa_rfq_18649_workbench/server.py` | 2 | `CG-05` | `code` | `the University of Iowa` | """Loopback-only analyst workbench for the University of Iowa RFQ 18649 carrier. |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | 40 | `CG-01` | `prose` | `conformance` | The artifact acceptance criteria below are a deliverable-conformance and cure mechanism; |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | 79 | `CG-01` | `prose` | `conformance` | Section 5.2 provides an objective conformance/cure frame for the delivered draft; |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | 208 | `CG-01` | `prose` | `conformance` | This conformance/cure protocol is distinct from the proposed payment schedule: kickoff remains triggered by written authorization, draft remains triggered by delivery, and only the final base-workshare milestone is accep |

## AMBIGUOUS (195)

| File | Line | Rule | Context | Matched | Clause |
|---|---|---|---|---|---|
| `uiowa_rfq_18649_acceptance_map/README.md` | 55 | `CG-01` | `prose` | `CONFORMANCE` | ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/acceptance_map.json` | 340 | `CG-01` | `data` | `certified` | "certified compliant", |
| `uiowa_rfq_18649_acceptance_map/build_index.py` | 35 | `CG-01` | `code` | `CONFORMANCE` | "ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/build_index.py` | 320 | `CG-01` | `code` | `certification` | "score, a rating, a certification, or a professional judgement.") |
| `uiowa_rfq_18649_acceptance_map/output/ACCEPTANCE_INDEX.md` | 3 | `CG-01` | `prose` | `CONFORMANCE` | > ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/output/acceptance_index.csv` | 1 | `CG-01` | `data` | `CONFORMANCE` | # ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/output/acceptance_index.json` | 2 | `CG-01` | `data` | `CONFORMANCE` | "banner": "ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/output/needs_engagement_evidence.csv` | 1 | `CG-01` | `data` | `CONFORMANCE` | # ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/MANIFEST.json` | 2 | `CG-01` | `data` | `CONFORMANCE` | "banner": "ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/uiowa_rfq_18649_workshare__ACCEPTANCE_EXHIBIT.md` | 44 | `CG-01` | `prose` | `conformance` | Acceptance in this exhibit means conformance of TJLabs-delivered artifacts to stated criteria. |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/uiowa_rfq_18649_workshare__ACCEPTANCE_EXHIBIT.md` | 105 | `CG-01` | `prose` | `conformance` | These criteria define artifact conformance, review, and cure. |
| `uiowa_rfq_18649_acceptance_map/output/sample_packet/uiowa_rfq_18649_workshare__ACCEPTANCE_EXHIBIT.md` | 166 | `CG-01` | `prose` | `certification` | - procurement/vendor selection, recommendations or endorsements for specific commercial products/vendors, legal, audit, certification, insurance, or regulatory opinions; |
| `uiowa_rfq_18649_acceptance_map/test_acceptance_map.py` | 439 | `CG-02` | `test` | `maturity score` | for banned in ("maturity score", "percentile", "peer rank", "overall score", |
| `uiowa_rfq_18649_acceptance_map/test_acceptance_map.py` | 439 | `CG-03` | `test` | `percentile` | for banned in ("maturity score", "percentile", "peer rank", "overall score", |
| `uiowa_rfq_18649_acceptance_map/test_acceptance_map.py` | 440 | `CG-01` | `test` | `certified` | "certified compliant", "conformance percentage"): |
| `uiowa_rfq_18649_adoption_readiness/readiness.py` | 17 | `CG-03` | `code` | `percentile` | percentile and no certification claim anywhere in the output. |
| `uiowa_rfq_18649_adoption_readiness/readiness.py` | 79 | `CG-01` | `code` | `certification` | "percentile", "peerpercentile", "grade", "rank", "certification", |
| `uiowa_rfq_18649_adoption_readiness/readiness.py` | 79 | `CG-03` | `code` | `percentile` | "percentile", "peerpercentile", "grade", "rank", "certification", |
| `uiowa_rfq_18649_adoption_readiness/readiness.py` | 679 | `CG-02` | `code` | `maturity level` | "produce a composite score, a maturity level, a peer percentile, a " |
| `uiowa_rfq_18649_adoption_readiness/readiness.py` | 679 | `CG-03` | `code` | `percentile` | "produce a composite score, a maturity level, a peer percentile, a " |
| `uiowa_rfq_18649_adoption_readiness/readiness.py` | 680 | `CG-01` | `code` | `certification` | "certification or compliance claim, or any assessment of an " |
| `uiowa_rfq_18649_adoption_readiness/test_readiness.py` | 416 | `CG-02` | `test` | `maturity level` | for phrase in ("composite score", "maturity level", "peer percentile", |
| `uiowa_rfq_18649_adoption_readiness/test_readiness.py` | 416 | `CG-03` | `test` | `percentile` | for phrase in ("composite score", "maturity level", "peer percentile", |
| `uiowa_rfq_18649_ai_eval_kit/README.md` | 128 | `CG-03` | `prose` | `percentile` | compliance, maturity or peer-percentile claim appears anywhere. |
| `uiowa_rfq_18649_ai_eval_kit/eval_kit.py` | 528 | `CG-02` | `code` | `maturity rating` | "a pass, or a maturity rating.\n\n") |
| `uiowa_rfq_18649_ai_integration/README.md` | 208 | `CG-01` | `prose` | `conformance` | - The port, both fictional adapters, conformance checking, and all three degraded paths. |
| `uiowa_rfq_18649_ai_integration/demo_swap.py` | 46 | `CG-01` | `code` | `conformance` | "conformance": conformance, |
| `uiowa_rfq_18649_ai_integration/demo_swap.py` | 134 | `CG-01` | `code` | `conformance` | print(f" conformance : {run['conformance']['conformant']}") |
| `uiowa_rfq_18649_ai_integration/out/swap_receipt.json` | 46 | `CG-01` | `data` | `conformance` | "conformance": { |
| `uiowa_rfq_18649_ai_integration/out/swap_receipt.json` | 104 | `CG-01` | `data` | `conformance` | "conformance": { |
| `uiowa_rfq_18649_ai_integration/out/swap_receipt.json` | 162 | `CG-01` | `data` | `conformance` | "conformance": { |
| `uiowa_rfq_18649_ai_integration/out/swap_receipt.json` | 220 | `CG-01` | `data` | `conformance` | "conformance": { |
| `uiowa_rfq_18649_ai_integration/out/swap_receipt.json` | 278 | `CG-01` | `data` | `conformance` | "conformance": { |
| `uiowa_rfq_18649_ai_integration/portlib/port.py` | 108 | `CG-01` | `code` | `conformance` | # ------------------------------------------------- contract conformance check |
| `uiowa_rfq_18649_ai_opportunity_portfolio/README.md` | 95 | `CG-01` | `prose` | `certification` | OPP-RIS-02 effort-certification reminders |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 154 | `CG-01` | `data` | `certification` | "title": "Generate effort-certification reminder narratives", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 155 | `CG-01` | `data` | `certification` | "usecase": "Certifiers receive a reminder naming the periods and projects awaiting certification. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 186 | `CG-01` | `data` | `certification` | "numerator": "certifications on time", "denominator": "certifications due", "cadence": "per certification period", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 241 | `CG-01` | `data` | `certify` | "usecase": "Application owners certify entitlements each quarter. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 241 | `CG-01` | `data` | `certification` | A drafted summary of what changed since the last review would shorten the certification. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 268 | `CG-01` | `data` | `certified` | {"name": "Access reviews certified by the quarter deadline", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 269 | `CG-01` | `data` | `certified` | "numerator": "reviews certified on time", "denominator": "reviews due", "cadence": "quarterly", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/candidates.json` | 275 | `CG-01` | `data` | `certify` | "How many application owners certify each quarter, and how long does a certification take today?" |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 221 | `CG-01` | `data` | `certify` | "How many application owners certify each quarter, and how long does a certification take today?" |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 235 | `CG-01` | `data` | `certified` | "name": "Access reviews certified by the quarter deadline", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 236 | `CG-01` | `data` | `certified` | "numerator": "reviews certified on time" |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 265 | `CG-01` | `data` | `certify` | "usecase": "Application owners certify entitlements each quarter. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 265 | `CG-01` | `data` | `certification` | A drafted summary of what changed since the last review would shorten the certification. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 365 | `CG-01` | `data` | `certification` | "cadence": "per certification period", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 393 | `CG-01` | `data` | `certification` | "title": "Generate effort-certification reminder narratives", |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | 395 | `CG-01` | `data` | `certification` | "usecase": "Certifiers receive a reminder naming the periods and projects awaiting certification. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 86 | `CG-01` | `prose` | `certify` | Application owners certify entitlements each quarter. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 86 | `CG-01` | `prose` | `certification` | A drafted summary of what changed since the last review would shorten the certification. |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 93 | `CG-01` | `prose` | `certified` | - Access reviews certified by the quarter deadline: reviews certified on time / reviews due, quarterly, baseline required - not yet measurable, and not recorded as 0 |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 96 | `CG-01` | `prose` | `certify` | - How many application owners certify each quarter, and how long does a certification take today? |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 98 | `CG-01` | `prose` | `certification` | ### OPP-RIS-02 - Generate effort-certification reminder narratives (RIS) |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio_report.md` | 100 | `CG-01` | `prose` | `certification` | Certifiers receive a reminder naming the periods and projects awaiting certification. |
| `uiowa_rfq_18649_ai_policy_to_workflow/README.md` | 113 | `CG-01` | `prose` | `conformance` | A conformance-shaped tool marks this red. |
| `uiowa_rfq_18649_ai_policy_to_workflow/SOURCE_NOTES.md` | 21 | `CG-02` | `prose` | `maturity tier` | Any maturity tier or readiness level |
| `uiowa_rfq_18649_ai_policy_to_workflow/policy_matrix.py` | 49 | `CG-01` | `code` | `certification` | claim, a certification, or a peer comparison. |
| `uiowa_rfq_18649_ai_policy_to_workflow/policy_matrix.py` | 49 | `CG-03` | `code` | `peer comparison` | claim, a certification, or a peer comparison. |
| `uiowa_rfq_18649_ai_policy_to_workflow/test_policy_matrix.py` | 230 | `CG-01` | `test` | `certification` | for term in ("maturity", "certification", "percentage", "individual", |
| `uiowa_rfq_18649_ai_policy_to_workflow/test_policy_matrix.py` | 231 | `CG-03` | `test` | `percentile` | "percentile", "subcategory"): |
| `uiowa_rfq_18649_ai_use_inventory/interview_guide.py` | 15 | `CG-02` | `code` | `maturity score` | a maturity score, or a comparison against another institution, because |
| `uiowa_rfq_18649_ai_use_inventory/schema.py` | 43 | `CG-02` | `code` | `maturity score` | # collapsed into an adoption percentage or a maturity score. |
| `uiowa_rfq_18649_ai_use_inventory/test_inventory.py` | 168 | `CG-03` | `test` | `percentile` | for banned in ("maturity", "percentile", "benchmark", "certif", "score"): |
| `uiowa_rfq_18649_bid_pack/fixtures/manifest.json` | 23 | `CG-01` | `data` | `Certified` | {"id": "ATT-FIN-02", "title": "Certified Cost Rate Schedule", "category": "financial", |
| `uiowa_rfq_18649_bid_pack/packcheck.py` | 22 | `CG-01` | `code` | `conformance` | WCAG or any other conformance statement. |
| `uiowa_rfq_18649_bid_pack/sample_output/00-INDEX.md` | 29 | `CG-01` | `prose` | `Certified` | Certified Cost Rate Schedule |
| `uiowa_rfq_18649_bid_pack/sample_output/attachment_index.csv` | 3 | `CG-01` | `data` | `Certified` | ATT-FIN-02,Certified Cost Rate Schedule,financial,yes,PLACEHOLDER-NOT SUPPLIED,UNKNOWN,UNKNOWN,UNKNOWN,2 |
| `uiowa_rfq_18649_bid_pack/sample_output/attachments/A02-certified-cost-rate-schedule.PLACEHOLDER.txt` | 3 | `CG-01` | `prose` | `Certified` | Attachment id: ATT-FIN-02 Title: Certified Cost Rate Schedule Category: financial Required: yes |
| `uiowa_rfq_18649_bid_pack/sample_output/bid_pack.json` | 31 | `CG-01` | `data` | `Certified` | "title": "Certified Cost Rate Schedule" |
| `uiowa_rfq_18649_bid_pack/sample_output/bid_pack.json` | 183 | `CG-01` | `data` | `Certified` | "label": "Certified Cost Rate Schedule", |
| `uiowa_rfq_18649_capability_appendix/README.md` | 53 | `CG-01` | `prose` | `Certification` | - Certification and guarantee language — certified, compliant, |
| `uiowa_rfq_18649_capability_appendix/README.md` | 54 | `CG-01` | `prose` | `accredited` | accredited, guaranteed. |
| `uiowa_rfq_18649_capability_appendix/capability_appendix.py` | 88 | `CG-01` | `code` | `certified` | "certified", "certification", "compliant", "compliance-ready", |
| `uiowa_rfq_18649_capability_appendix/capability_appendix.py` | 89 | `CG-01` | `code` | `accredited` | "audit-proof", "accredited", "guarantee", "guaranteed", "guarantees", |
| `uiowa_rfq_18649_capability_appendix/fixtures/rejection_demo_register.json` | 19 | `CG-01` | `data` | `certification` | "capabilityarea": "language: certification and guarantee", |
| `uiowa_rfq_18649_capability_appendix/fixtures/rejection_demo_register.json` | 20 | `CG-01` | `data` | `certified` | "statement": "Delivers a certified, compliant record set with guaranteed retention.", |
| `uiowa_rfq_18649_capability_appendix/out/capability_evidence_index.md` | 151 | `CG-01` | `prose` | `compliance determination` | why : States a compliance determination. |
| `uiowa_rfq_18649_capability_appendix/out/rejection_demo/capability_appendix.json` | 51 | `CG-01` | `data` | `certification` | "capabilityarea": "language: certification and guarantee", |
| `uiowa_rfq_18649_capability_appendix/out/rejection_demo/capability_appendix.json` | 52 | `CG-01` | `data` | `certified` | "statement": "Delivers a certified, compliant record set with guaranteed retention.", |
| `uiowa_rfq_18649_capability_appendix/out/rejection_demo/capability_appendix.md` | 10 | `CG-01` | `prose` | `certification` | - BAD-02 (language: certification and guarantee) - wording rejected (prohibited certification or guarantee language: 'certified'; |
| `uiowa_rfq_18649_capability_appendix/out/rejection_demo/capability_evidence_index.md` | 31 | `CG-01` | `prose` | `certification` | ## BAD-02 - language: certification and guarantee |
| `uiowa_rfq_18649_capability_appendix/test_capability_appendix.py` | 67 | `CG-01` | `test` | `certified` | self.assertIn("certified", blockers) |
| `uiowa_rfq_18649_claim_audit/rules.py` | 78 | `CG-02` | `code` | `maturity level` | "mature": "asserts a maturity level without stating what measured it", |
| `uiowa_rfq_18649_closeout/SOURCE_NOTES.md` | 25 | `CG-05` | `prose` | `The University of Iowa` | The University of Iowa Standard Terms and Conditions attached to the solicitation include Section 12, “University records,” stating that the contractor shall not remove University records from the University. |
| `uiowa_rfq_18649_contractor_transition/sample_output/transition_report.json` | 106 | `CG-01` | `data` | `certification` | "compliance or certification conclusion", |
| `uiowa_rfq_18649_contractor_transition/transition.py` | 182 | `CG-01` | `code` | `certification` | "compliance or certification conclusion", |
| `uiowa_rfq_18649_deadline_continuity/test_continuity.py` | 240 | `CG-03` | `test` | `percentile` | "maturity", "score", "percentile"): |
| `uiowa_rfq_18649_delivery_scan/delivery_scan.py` | 26 | `CG-02` | `code` | `maturity score` | average, maturity score, confidence score, or employee ranking", |
| `uiowa_rfq_18649_delivery_scan/delivery_scan.py` | 26 | `CG-04` | `code` | `employee ranking` | average, maturity score, confidence score, or employee ranking", |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 94 | `CG-01` | `test` | `certification` | "commercial products/vendors, legal, audit, certification, insurance, or regulatory " |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 101 | `CG-01` | `test` | `compliance verdict` | "into: an audit/compliance verdict, an individual performance evaluation, a " |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 108 | `CG-01` | `test` | `certifies` | "certifies, failed the audit, in violation of.\n" |
| `uiowa_rfq_18649_delivery_scan/test_delivery_scan.py` | 367 | `CG-01` | `test` | `compliance verdict` | "a compliance verdict about a lane"), |
| `uiowa_rfq_18649_economics_resource_adapters/check_contract.py` | 2 | `CG-01` | `code` | `conformance` | """Contract conformance checker for the UIOWA-105 adapters. |
| `uiowa_rfq_18649_economics_resource_adapters/sample_output/integrated.json` | 1209 | `CG-01` | `data` | `certification` | "label": "Generate effort-certification reminder narratives", |
| `uiowa_rfq_18649_economics_resource_adapters/sample_output/integrated.json` | 1560 | `CG-01` | `data` | `certification` | "label": "Generate effort-certification reminder narratives", |
| `uiowa_rfq_18649_economics_resource_adapters/test_check_contract.py` | 2 | `CG-01` | `test` | `conformance` | """Tests for the UIOWA-105 contract conformance checker. |
| `uiowa_rfq_18649_export_safety/examples/findings.csv` | 2 | `CG-01` | `data` | `CONFORMANCE` | Consider a sidecar notice file, or accept it and say so in the lane's README",# ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_export_safety/examples/findings.csv` | 3 | `CG-01` | `data` | `CONFORMANCE` | Consider a sidecar notice file, or accept it and say so in the lane's README",# ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_export_safety/examples/findings.json` | 183 | `CG-01` | `data` | `CONFORMANCE` | "sample": "# ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_export_safety/examples/findings.json` | 194 | `CG-01` | `data` | `CONFORMANCE` | "sample": "# ARTIFACT CONFORMANCE EVIDENCE ONLY. |
| `uiowa_rfq_18649_export_safety/export_safety.py` | 354 | `CG-01` | `code` | `certified` | "\"certified\", \"compliant\" or \"safe\". |
| `uiowa_rfq_18649_filesystem_safety/test_fsaudit.py` | 304 | `CG-01` | `test` | `CERTIFIED` | for verdict in ("CERTIFIED", "COMPLIANT", "SAFETY SCORE", "% SAFE", "GUARANTEE"): |
| `uiowa_rfq_18649_import_safety/test_import_safety.py` | 254 | `CG-03` | `test` | `percentile` | for banned in ("score", "rating", "percentile", "rank", "grade", |
| `uiowa_rfq_18649_intake_rehearsal/test_rehearsal.py` | 205 | `CG-02` | `test` | `maturity score` | for banned in ("maturityscore", "maturity score", "percentile", "peer rank", |
| `uiowa_rfq_18649_intake_rehearsal/test_rehearsal.py` | 205 | `CG-03` | `test` | `percentile` | for banned in ("maturityscore", "maturity score", "percentile", "peer rank", |
| `uiowa_rfq_18649_labeling_integrity/examples/live_snapshot/screen.json` | 986 | `CG-01` | `data` | `certified` | "path": "uiowarfq18649bidpack/sampleoutput/attachments/A02-certified-cost-rate-schedule.PLACEHOLDER.txt", |
| `uiowa_rfq_18649_labeling_integrity/test_labelcheck.py` | 266 | `CG-01` | `test` | `CERTIFIED` | for verdict in ("CERTIFIED", "COMPLIANT", "LABELING SCORE", "% LABELED"): |
| `uiowa_rfq_18649_mobilization/README.md` | 50 | `CG-03` | `prose` | `peer comparison` | Select a defensible peer comparison approach and record comparability limits. |
| `uiowa_rfq_18649_operator_handoff/sample/verification_log.md` | 963 | `CG-01` | `prose` | `compliance determination` | why : States a compliance determination. |
| `uiowa_rfq_18649_operator_handoff/test_verify_kit.py` | 458 | `CG-03` | `test` | `percentile` | for banned in ("score", "rating", "maturity", "percentile", "grade"): |
| `uiowa_rfq_18649_prioritization/prioritize.py` | 39 | `CG-01` | `code` | `compliance verdict` | compliance verdict, peer percentile or individual performance rating. |
| `uiowa_rfq_18649_prioritization/prioritize.py` | 39 | `CG-03` | `code` | `percentile` | compliance verdict, peer percentile or individual performance rating. |
| `uiowa_rfq_18649_prioritization/prioritize.py` | 39 | `CG-04` | `code` | `individual performance rating` | compliance verdict, peer percentile or individual performance rating. |
| `uiowa_rfq_18649_prioritization/prioritize.py` | 1398 | `CG-01` | `code` | `compliance verdict` | "maturity score, a compliance verdict, a peer comparison or an assessment " |
| `uiowa_rfq_18649_prioritization/prioritize.py` | 1398 | `CG-02` | `code` | `maturity score` | "maturity score, a compliance verdict, a peer comparison or an assessment " |
| `uiowa_rfq_18649_prioritization/prioritize.py` | 1398 | `CG-03` | `code` | `peer comparison` | "maturity score, a compliance verdict, a peer comparison or an assessment " |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 307 | `CG-03` | `data` | `percentile` | "subject": "Peer comparison and percentile ranking", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 311 | `CG-03` | `data` | `percentile` | "percentile", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 326 | `CG-03` | `data` | `industry average` | "Are we above or below the industry average?" |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 366 | `CG-01` | `data` | `certification` | "subject": "Compliance verdicts, audit outcomes and certification", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 373 | `CG-01` | `data` | `certified` | "certified", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 374 | `CG-01` | `data` | `certification` | "certification", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 387 | `CG-01` | `data` | `compliant with` | "Are we compliant with the NIST framework?", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 388 | `CG-01` | `data` | `certification` | "Can we use this as evidence of certification?", |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | 392 | `CG-01` | `data` | `compliance determination` | "requires": "A compliance determination would require an audit against a named control framework: defined control objectives, a complete population rather than a sample, tested evidence for each control, and an auditor w |
| `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet_defective.json` | 168 | `CG-03` | `data` | `percentile` | "triggerterms": ["percentile"], |
| `uiowa_rfq_18649_qa_refusal_contract/index.py` | 23 | `CG-03` | `code` | `percentile` | "peer percentile ranking" and the candidate record contains none of |
| `uiowa_rfq_18649_qa_refusal_contract/index.py` | 172 | `CG-03` | `code` | `percentile` | # ("percentile") costs far more than missing a common one |
| `uiowa_rfq_18649_qa_refusal_contract/qa.py` | 6 | `CG-01` | `code` | `compliance verdict` | peer percentile, a team ranking, a compliance verdict. |
| `uiowa_rfq_18649_qa_refusal_contract/qa.py` | 6 | `CG-03` | `code` | `percentile` | peer percentile, a team ranking, a compliance verdict. |
| `uiowa_rfq_18649_qa_refusal_contract/test_qa.py` | 171 | `CG-01` | `test` | `compliant with` | "Are we compliant with the NIST framework?"): |
| `uiowa_rfq_18649_qa_refusal_contract/test_qa.py` | 271 | `CG-03` | `test` | `percentile` | "This would place us in the top percentile.", |
| `uiowa_rfq_18649_qa_refusal_contract/uncertainty.py` | 145 | `CG-01` | `code` | `certify` | ication)\b", "certify/certified"), |
| `uiowa_rfq_18649_qa_refusal_contract/uncertainty.py` | 148 | `CG-03` | `code` | `percentile` | (r"\bpercentile\b", "percentile"), |
| `uiowa_rfq_18649_recovery_evidence/README-OP5-IRONWOOD-second-implementation.md` | 186 | `CG-02` | `prose` | `maturity score` | pass, or a maturity score. |
| `uiowa_rfq_18649_recovery_evidence/recovery_evidence.py` | 50 | `CG-02` | `code` | `maturity score` | pass, or a maturity score. |
| `uiowa_rfq_18649_recovery_evidence/recovery_evidence.py` | 1156 | `CG-03` | `code` | `peer institution` | "determination, or a comparison against any peer institution.") |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 319 | `CG-01` | `test` | `certification` | # maturity score, a certification, or a peer comparison. |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 319 | `CG-02` | `test` | `maturity score` | # maturity score, a certification, or a peer comparison. |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 319 | `CG-03` | `test` | `peer comparison` | # maturity score, a certification, or a peer comparison. |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 321 | `CG-01` | `test` | `certified` | for banned in ("maturity level", "compliant", "certified", "percentile", |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 321 | `CG-02` | `test` | `maturity level` | for banned in ("maturity level", "compliant", "certified", "percentile", |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 321 | `CG-03` | `test` | `percentile` | for banned in ("maturity level", "compliant", "certified", "percentile", |
| `uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | 322 | `CG-03` | `test` | `peer average` | "peer average", "grade of"): |
| `uiowa_rfq_18649_release_recovery_case/make_fixtures.py` | 17 | `CG-05` | `code` | `the University of Iowa` | describes the University of Iowa or any real release or incident. |
| `uiowa_rfq_18649_release_recovery_case/make_fixtures.py` | 31 | `CG-05` | `code` | `the University of Iowa` | "the University of Iowa, any real service, any real release, or any real incident. |
| `uiowa_rfq_18649_release_recovery_case/test_release_recovery_case.py` | 269 | `CG-03` | `test` | `percentile` | for banned in ("maturity", "percentile", "peerrank", "scoreoutof", |
| `uiowa_rfq_18649_release_recovery_case/test_release_recovery_case.py` | 270 | `CG-01` | `test` | `certified` | "grade", "certified", "compliant"): |
| `uiowa_rfq_18649_report_structure/README.md` | 99 | `CG-01` | `prose` | `certifies` | - auditverdict — non-compliant, audit finding, material weakness, certifies, |
| `uiowa_rfq_18649_report_structure/report_structure.py` | 289 | `CG-02` | `code` | `maturity score` | "zero, a pass, or a maturity score.\n" |
| `uiowa_rfq_18649_report_structure/report_structure.py` | 325 | `CG-01` | `code` | `certification` | "determination, certification or attestation. |
| `uiowa_rfq_18649_report_structure/report_structure.py` | 407 | `CG-01` | `code` | `certification` | "certification or attestation. |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 84 | `CG-01` | `code` | `compliance determination` | "States a compliance determination. |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 100 | `CG-01` | `code` | `certification` | "Issues a certification or attestation.", |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 194 | `CG-01` | `code` | `certification` | certification |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 209 | `CG-01` | `code` | `certification` | r"certification |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 213 | `CG-01` | `code` | `certification` | certification |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 215 | `CG-01` | `code` | `certification` | certification |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 232 | `CG-01` | `code` | `certification` | # rating, percentile, certification verdict or individual/team |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 232 | `CG-03` | `code` | `percentile` | # rating, percentile, certification verdict or individual/team |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 264 | `CG-01` | `code` | `certification` | # percentile, certification verdict or individual/team performance rating is |
| `uiowa_rfq_18649_report_structure/scope_guard.py` | 264 | `CG-03` | `code` | `percentile` | # percentile, certification verdict or individual/team performance rating is |
| `uiowa_rfq_18649_report_structure/test_report_structure.py` | 392 | `CG-01` | `test` | `certification` | "certification or attestation. |
| `uiowa_rfq_18649_report_visuals/README.md` | 256 | `CG-01` | `prose` | `conformance` | - Whether the client needs a specific conformance target (e.g. |
| `uiowa_rfq_18649_scope_change/examples/worksheet.json` | 54 | `CG-01` | `data` | `certification` | "legal, audit, certification, insurance or regulatory opinions", |
| `uiowa_rfq_18649_scope_change/fixtures/baseline.json` | 64 | `CG-01` | `data` | `certification` | "legal, audit, certification, insurance or regulatory opinions", |
| `uiowa_rfq_18649_security_event_review/assess_security_events.py` | 5 | `CG-01` | `code` | `compliance verdict` | credentials, or turns missing evidence into a security/compliance verdict. |
| `uiowa_rfq_18649_synthetic_collection/evidence_manifest.json` | 10 | `CG-01` | `data` | `certification` | "compliance or certification conclusion", |
| `uiowa_rfq_18649_test_proof_audit/test_testproof.py` | 241 | `CG-03` | `test` | `percentile` | for banned in ("rank", "leaderboard", "worst", "grade", "percentile", "score"): |
| `uiowa_rfq_18649_test_proof_audit/test_testproof.py` | 248 | `CG-03` | `test` | `percentile` | self.assertNotIn("percentile", m) |
| `uiowa_rfq_18649_uncertainty_lint/test_lint.py` | 176 | `CG-03` | `test` | `percentile` | # field may carry a score, a rating, a percentile or a per-author |
| `uiowa_rfq_18649_uncertainty_lint/test_lint.py` | 180 | `CG-03` | `test` | `percentile` | for banned in ("score", "rating", "percentile", "rank", "grade", |
| `uiowa_rfq_18649_unknown_propagation/scan_unknowns.py` | 944 | `CG-05` | `code` | `the University of Iowa` | "finding about the University of Iowa, and not a judgement of any lane or " |
| `uiowa_rfq_18649_vocabulary_crosswalk/test_vocabulary.py` | 238 | `CG-01` | `test` | `certified` | ranked or certified"), so a scan of the whole report flags its own promise. |
| `uiowa_rfq_18649_vocabulary_crosswalk/test_vocabulary.py` | 250 | `CG-01` | `test` | `certified` | for banned in ("maturity score", "percentile", "compliant", "certified", |
| `uiowa_rfq_18649_vocabulary_crosswalk/test_vocabulary.py` | 250 | `CG-02` | `test` | `maturity score` | for banned in ("maturity score", "percentile", "compliant", "certified", |
| `uiowa_rfq_18649_vocabulary_crosswalk/test_vocabulary.py` | 250 | `CG-03` | `test` | `percentile` | for banned in ("maturity score", "percentile", "compliant", "certified", |
| `uiowa_rfq_18649_workbench/12-policy-reference-memo.md` | 131 | `CG-01` | `prose` | `conformance` | - actual accessibility conformance or open accessibility defects; |
| `uiowa_rfq_18649_workbench/12-policy-reference-memo.md` | 136 | `CG-01` | `prose` | `certification` | - compliance, certification, maturity, or comparative performance. |
| `uiowa_rfq_18649_workbench/12-policy-reference-memo.md` | 162 | `CG-01` | `prose` | `compliance verdict` | This structure prevents the assessment from turning a policy reference into an unsupported compliance verdict and preserves a constructive, evidence-based scope. |
| `uiowa_rfq_18649_workbench/19-reliability-peer-pack.md` | 20 | `CG-03` | `prose` | `peer comparison` | Cross-peer comparison without matching definitions, periods, denominators, exclusions, and service boundaries |
| `uiowa_rfq_18649_workbench/19-reliability-peer-pack.md` | 190 | `CG-03` | `prose` | `percentile` | statistic type (count, %, mean, median, percentile); |
| `uiowa_rfq_18649_workbench/framework_crosswalk/20-adaptation-memo.md` | 191 | `CG-01` | `prose` | `certification` | - the RFQ requires NIST certification; |
| `uiowa_rfq_18649_workbench/framework_crosswalk/validate_framework_crosswalk.py` | 45 | `CG-01` | `code` | `certified` | "nist certified", |
| `uiowa_rfq_18649_workbench/framework_crosswalk/validate_framework_crosswalk.py` | 48 | `CG-01` | `code` | `certification` | "certification level", |
| `uiowa_rfq_18649_workbench/framework_crosswalk/validate_framework_crosswalk.py` | 49 | `CG-03` | `code` | `percentile` | "percentile rank", |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_CHANGELOG.md` | 13 | `CG-01` | `prose` | `conformance` | Five base production packages, optional readout, responsibility split, consolidated comments, artifact conformance/cure. |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | 44 | `CG-01` | `prose` | `conformance` | Acceptance in this exhibit means conformance of TJLabs-delivered artifacts to stated criteria. |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | 105 | `CG-01` | `prose` | `conformance` | These criteria define artifact conformance, review, and cure. |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | 166 | `CG-01` | `prose` | `certification` | - procurement/vendor selection, recommendations or endorsements for specific commercial products/vendors, legal, audit, certification, insurance, or regulatory opinions; |
| `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT_REDLINE.md` | 33 | `CG-01` | `prose` | `conformance` | The clean exhibit now fails scope conformance if a TJLabs artifact claims authority to recommend or endorse a specific commercial product/vendor. |

## What this tool refuses to do

- No lane is scored, graded, ranked or rated. Findings carry an exact file and line; a human reads them.
- No compliance percentage or pass/fail verdict per lane is produced.
- AMBIGUOUS is never resolved automatically in the clean direction.
- Nothing in a scanned lane is modified. The scan is read-only and a test proves it by hashing the tree before and after.
- UNKNOWN-propagation checking is deliberately not attempted here; another lane (OPS-UNKNOWN-PROPAGATION) covers it.

## Files excluded from pattern matching

This tool's own rule table necessarily contains every prohibited phrase, so its source and tests are excluded from pattern matching. The exclusion is listed here rather than left implicit.

