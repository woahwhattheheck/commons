# Documentation claim drift -- RFQ 18649 delivered tree

**Status: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.**

Numeric claims are compared against the measured run recorded in `uiowa_rfq_18649_run_sweep/out/run_sweep.json`. This screen executes nothing. A CONTRADICTED row means the sentence and that measurement disagree -- most often because tests were added after the sentence was written. It is a documentation question for the lane's owner, not a defect in their code and not a compliance claim. UNVERIFIABLE means there is no measurement this claim can be checked against; it is never treated as agreement.

- lanes with a measured run: **52**
- lane-root markdown files examined: **108**
- non-root markdown files skipped (operational records / embedded copies): **129**
- claims found: **52**
- agrees: **26**
- contradicted: **6**
- unverifiable: **20**

## Contradicted

| lane | file:line | documentation says | measured | basis |
|---|---|---|---|---|
| `uiowa_rfq_18649_bid_pack` | `uiowa_rfq_18649_bid_pack/README.md:239` | 27 | 35 | lane_total |
| `uiowa_rfq_18649_intake_rehearsal` | `uiowa_rfq_18649_intake_rehearsal/README.md:144` | 30 | 34 | suite:test_rehearsal.py |
| `uiowa_rfq_18649_operator_handoff` | `uiowa_rfq_18649_operator_handoff/README.md:75` | 22 | 30 | suite:test_verify_kit.py |
| `uiowa_rfq_18649_readout_deck` | `uiowa_rfq_18649_readout_deck/README.md:57` | 65 | 56 | suite:test_deck_architecture.py |
| `uiowa_rfq_18649_readout_deck` | `uiowa_rfq_18649_readout_deck/README.md:215` | 65 | 56 | lane_total |
| `uiowa_rfq_18649_traceability` | `uiowa_rfq_18649_traceability/README.md:381` | 24 | 22 | suite:test_audit_assertions.py |

## Unverifiable

Reported rather than dropped. None of these is counted as agreement.

| lane | file:line | claim | why |
|---|---|---|---|
| `uiowa_rfq_18649_base_fee_economics` | `uiowa_rfq_18649_base_fee_economics/README.md:132` | 52 | uiowa_rfq_18649_base_fee_economics does not appear in the run sweep |
| `uiowa_rfq_18649_base_fee_economics` | `uiowa_rfq_18649_base_fee_economics/README.md:142` | 52 | uiowa_rfq_18649_base_fee_economics does not appear in the run sweep |
| `uiowa_rfq_18649_bid_pack` | `uiowa_rfq_18649_bid_pack/README.md:65` | 35 | sentence names test_packcheck.py, which the run sweep did not measure |
| `uiowa_rfq_18649_claim_audit` | `uiowa_rfq_18649_claim_audit/README.md:84` | 28 | uiowa_rfq_18649_claim_audit does not appear in the run sweep |
| `uiowa_rfq_18649_dedup_threshold` | `uiowa_rfq_18649_dedup_threshold/README.md:29` | 19 | uiowa_rfq_18649_dedup_threshold does not appear in the run sweep |
| `uiowa_rfq_18649_delivery_scan` | `uiowa_rfq_18649_delivery_scan/README.md:70` | 55 | uiowa_rfq_18649_delivery_scan does not appear in the run sweep |
| `uiowa_rfq_18649_import_safety` | `uiowa_rfq_18649_import_safety/README.md:56` | 0 | uiowa_rfq_18649_import_safety does not appear in the run sweep |
| `uiowa_rfq_18649_kelvin_conformance` | `uiowa_rfq_18649_kelvin_conformance/README.md:100` | 23 | uiowa_rfq_18649_kelvin_conformance does not appear in the run sweep |
| `uiowa_rfq_18649_labeling_integrity` | `uiowa_rfq_18649_labeling_integrity/README.md:23` | 22 | uiowa_rfq_18649_labeling_integrity does not appear in the run sweep |
| `uiowa_rfq_18649_labeling_integrity` | `uiowa_rfq_18649_labeling_integrity/README.md:92` | 22 | uiowa_rfq_18649_labeling_integrity does not appear in the run sweep |
| `uiowa_rfq_18649_maturity_anchors` | `uiowa_rfq_18649_maturity_anchors/README.md:117` | 48 | uiowa_rfq_18649_maturity_anchors does not appear in the run sweep |
| `uiowa_rfq_18649_maturity_anchors` | `uiowa_rfq_18649_maturity_anchors/README.md:123` | 48 | uiowa_rfq_18649_maturity_anchors does not appear in the run sweep |
| `uiowa_rfq_18649_roadmap_coherence` | `uiowa_rfq_18649_roadmap_coherence/README.md:63` | 36 | uiowa_rfq_18649_roadmap_coherence does not appear in the run sweep |
| `uiowa_rfq_18649_roadmap_coherence` | `uiowa_rfq_18649_roadmap_coherence/README.md:143` | 36 | uiowa_rfq_18649_roadmap_coherence does not appear in the run sweep |
| `uiowa_rfq_18649_sample_soundness` | `uiowa_rfq_18649_sample_soundness/README.md:98` | 26 | uiowa_rfq_18649_sample_soundness does not appear in the run sweep |
| `uiowa_rfq_18649_test_proof_audit` | `uiowa_rfq_18649_test_proof_audit/README.md:81` | 24 | uiowa_rfq_18649_test_proof_audit does not appear in the run sweep |
| `uiowa_rfq_18649_traceability` | `uiowa_rfq_18649_traceability/README.md:268` | 696 | lane has 3 suites and the sentence names none; cannot attribute the claim to one |
| `uiowa_rfq_18649_traceability` | `uiowa_rfq_18649_traceability/README.md:341` | 24 | lane has 3 suites and the sentence names none; cannot attribute the claim to one |
| `uiowa_rfq_18649_unknown_propagation` | `uiowa_rfq_18649_unknown_propagation/README.md:14` | 46 | uiowa_rfq_18649_unknown_propagation does not appear in the run sweep |
| `uiowa_rfq_18649_vocabulary_crosswalk` | `uiowa_rfq_18649_vocabulary_crosswalk/README.md:211` | 44 | uiowa_rfq_18649_vocabulary_crosswalk does not appear in the run sweep |
