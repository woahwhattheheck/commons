# JSON strict-parser conformance audit

Read-only. Asks whether a reader who is not Python can parse each published JSON artifact at all.

- Files scanned: **208**
- Findings: **46**

| Code | Count |
|---|---|
| `NO_TRAILING_NEWLINE` | 46 |

Zero findings means no issue detected by these ten checks — never "certified" or "valid for a given schema". An unreadable or empty file is reported, never counted as a pass.

## Findings by lane

### `uiowa_rfq_18649_ai_use_inventory` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_ai_use_inventory/sample_output/ai_use_inventory.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_bid_pack` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_bid_pack/sample_output/bid_pack.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_capacity_feasibility` — 2 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_capacity_feasibility/data/capacity-assumptions.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_capacity_feasibility/data/roadmap-items.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_contractor_transition` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_contractor_transition/sample_output/transition_report.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_deadline_continuity` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_deadline_continuity/sample_output/continuity_analysis.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_delivery_scan` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_delivery_scan/out/scope_screen.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_output_agreement` — 22 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/consistent/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/consistent/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/count_mismatch/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/count_mismatch/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/dangling_id/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/dangling_id/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/duplicate_id/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/duplicate_id/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/estimate_fabricated/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/estimate_fabricated/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/estimate_mismatch/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/estimate_mismatch/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/phase_fabricated/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/phase_fabricated/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/phase_mismatch/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/phase_mismatch/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/state_mismatch/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/state_mismatch/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/unassessed_result_claimed/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/unassessed_result_claimed/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/unknown_count_set/executive_summary.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_output_agreement/fixtures/mismatched/unknown_count_set/presentation.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_print_pagination` — 3 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_print_pagination/fixtures/boundary_citation_split.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_print_pagination/fixtures/boundary_orphan_heading.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_print_pagination/fixtures/report_document.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_qa_refusal_contract` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_qa_refusal_contract/fixtures/packet.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_readout_deck` — 3 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_readout_deck/data/broken-roadmap-report.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_readout_deck/data/deck-agreeing-with-broken-roadmap.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_readout_deck/data/example-report.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_report_structure` — 2 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_report_structure/content_map.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_report_structure/input_schemas.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_roadmap_coherence` — 6 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_roadmap_coherence/data/coherent-deck.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_roadmap_coherence/data/coherent-plan.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_roadmap_coherence/data/coherent-report.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_roadmap_coherence/data/drifted-plan.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_roadmap_coherence/data/incoherent-report.json` | — | no trailing newline; every diff of this file reports a changed last line |
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_roadmap_coherence/data/undeclared-report.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_test_proof_audit` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_test_proof_audit/findings/audit.json` | — | no trailing newline; every diff of this file reports a changed last line |

### `uiowa_rfq_18649_uncertainty_lint` — 1 finding(s)

| Severity | Code | File | Location | Detail |
|---|---|---|---|---|
| INFO | `NO_TRAILING_NEWLINE` | `uiowa_rfq_18649_uncertainty_lint/fixtures/labelled_lines.json` | — | no trailing newline; every diff of this file reports a changed last line |

