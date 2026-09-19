# UIOWA-110 — policy-versus-practice disagreement rehearsal

**Status:** fully synthetic integration rehearsal for RFQ 18649 preparation. Nothing in this directory is a University of Iowa finding.

## Why this exists

A written rule can be strong evidence of **documented intent** without being proof of execution. This rehearsal gives the merged evidence-confidence and rating components a controlled disagreement:

- a current fictional procedure says standard production changes require two recorded approvals;
- a fictional participant says that is the normal path but urgent changes can complete with one recorded approval;
- a fictional 12-record sample partly supports the documented rule: 8 records show two approvals, while 4 show one approval and no exception marker.

The correct result is not “policy wins” or “sample wins.” The disagreement remains bounded and unresolved until the exception/effective-scope question is answered.

## Existing components used

| Component | Current-main interface used | Role in this rehearsal |
|---|---|---|
| UIOWA-023 evidence confidence/provenance | `revenue/uiowa_rfq_18649_workshare/methodology/validate_23_evidence_register.py` and §7/§11 of `23-evidence-confidence.md` | Validates the evidence register; contradictory evidence stays `UNRESOLVED`; policy is indirect evidence for execution |
| UIOWA-022 rating composition | `revenue/uiowa_rfq_18649_rating_model/rating_model.py::compose` | Composes the criterion without inventing a maturity score or hiding unassessed coverage |
| Review control | UIOWA-023 §11 review controls | Checks that contradictions, source scope, confidence, and recommendation language survive into the reviewer card |

A separate UIOWA-021 calibrated maturity-anchor component and a standalone consolidated-review executable were **not present on current `main` when this rehearsal was built**. The harness therefore refuses to invent a maturity rank for the unresolved practice and applies the already-merged UIOWA-023 review controls. This is an explicit interface boundary, not a silent substitute.

## Files

- `evidence-register.csv` — three-source controlled disagreement in the UIOWA-023 schema.
- `rating-input.json` — the linked practice remains `unassessed` because the finding is unresolved.
- `run_rehearsal.py` — imports and executes the merged UIOWA-023 validator and UIOWA-022 rating engine, then builds the review result.
- `component-results.json` — checked-in expected output for the synthetic packet.
- `review-discussion-card.md` — facilitator-ready summary of supported strength, uncertainty, and smallest useful follow-up.
- `test_rehearsal.py` — bridge/regression tests, including a guard that prevents unresolved findings from being converted into an assessed maturity observation.

## Run

From the repository root:

```bash
python revenue/uiowa_rfq_18649_policy_practice_rehearsal/run_rehearsal.py \
  --write revenue/uiowa_rfq_18649_policy_practice_rehearsal/component-results.json

python -m unittest -v \
  revenue/uiowa_rfq_18649_policy_practice_rehearsal/test_rehearsal.py
```

Expected semantic result:

- evidence-register validation: pass;
- finding state: `UNRESOLVED`;
- rating composition for `deployment_operations`: `unassessed`, 0% assessed coverage, no maturity distribution;
- review disposition: **targeted follow-up required before definitive practice characterization**.

## Reviewer interpretation

### Supported strength

The synthetic packet supports two narrow statements:

1. a current documented procedure exists; and
2. most records in the bounded synthetic sample (8 of 12) align with that procedure.

Neither statement establishes universal execution.

### Specific uncertainty

Four sampled records show one approval and no exception marker, while the participant says urgent changes may legitimately use a different path. The packet cannot determine whether those four records are:

- legitimate exceptions with incomplete classification;
- a stale/inapplicable procedural rule;
- incomplete recordkeeping; or
- actual variation from the documented practice.

### Smallest useful follow-up

Inspect the exception classification and approval history for the four one-approval records and confirm the procedure’s effective scope/date. If a group-wide statement is needed, compare the resolved interpretation against an authoritative change population rather than extrapolating the 12-record sample.

## Guardrails demonstrated

- policy text is not treated as execution evidence;
- interview testimony is not treated as organization-wide fact;
- a bounded sample is not silently generalized;
- contradictory sources remain visible together;
- unresolved evidence does not receive an invented maturity rank;
- missing classification is not rewritten as misconduct, failure, or absence;
- the review recommendation is to discriminate between plausible explanations, not to choose the most formal source.
