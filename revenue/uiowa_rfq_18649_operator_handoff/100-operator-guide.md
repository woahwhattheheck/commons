# UIOWA-100 — Engagement-ready operator handoff

**Snapshot basis:** Commons `main` at `f3d68f9799a8c70300ff93bada956186c0c9ba1c`, captured 2026-09-19.  
**Purpose:** give a new operator one safe route through the RFQ 18649 preparation assets that had actually landed at the snapshot.  
**Boundary:** the checked-in examples are synthetic preparation material. They are not University of Iowa findings, accepted contract terms, bid authority, or permission to access a University system.

## Start here

From the Commons repository root:

```bash
python revenue/uiowa_rfq_18649_operator_handoff/preflight.py
python revenue/uiowa_rfq_18649_operator_handoff/sample_run.py \
  --out /tmp/uiowa-100-sample \
  --dry-run
```

The first command verifies that every non-pending catalog path and every executable sample entry point is still present in the checkout. The second resolves the complete synthetic run plan without executing it.

To execute the checked-in synthetic sample:

```bash
python revenue/uiowa_rfq_18649_operator_handoff/sample_run.py \
  --out /tmp/uiowa-100-sample
```

The runner uses `sys.executable` with argv arrays and never invokes a shell. It records each return code, elapsed time, stdout/stderr digest, and generated output digest in `sample-run-receipt.json`.

## Snapshot and refresh rule

This guide freezes a known operator map at one main SHA so its statements are auditable. The repository is moving quickly.

Before a live engagement or demo:

1. run `preflight.py`;
2. compare current `main` to the manifest's `snapshot_main_sha`;
3. inspect newly landed UIOWA assets instead of silently assuming they existed at the snapshot;
4. update a catalog row only after checking the real file and command;
5. keep `pending_at_snapshot` distinct from working assets until verified.

At this snapshot, the UIOWA-088 optional readout architecture is deliberately marked pending. A later merge may supersede that state; preflight emits a warning if a pending path is subsequently populated.

## Lifecycle map

### 1. Kickoff

Primary operator references:

- `revenue/uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` — proposed scope, responsibilities, artifact acceptance, and commercial boundaries.
- `revenue/uiowa_rfq_18649_workbench/11-ais-context.md` — public AIS/ESS/RIS/IAM context and unresolved questions.
- `revenue/uiowa_rfq_18649_workbench/12-policy-reference-memo.md` — policy clauses translated into discovery questions.

Operator objective: agree what will actually be assessed, who will participate, which sources can be requested, how review works, and which statements remain proposed rather than accepted.

Do **not** turn public institutional information into an internal-practice finding.

### 2. Evidence collection

Use:

- `workshare/methodology/23-evidence-confidence.md` for evidence IDs, directness, recency, representativeness, and corroboration.
- `document_extraction/` when locator-preserving extraction is needed. DOCX/TXT paths use the standard library; PDF extraction declares `pypdf` as an optional dependency.

Preserve the source version, locator, date/period, population, and limitations. Missing evidence remains unknown unless there is positive evidence of absence.

### 3. Analysis

#### 12-cell compiler

```bash
cd revenue/uiowa_rfq_18649_workshare
python compiler.py compile \
  fixtures/synthetic_packet.json \
  fixtures/synthetic_authority.json \
  /tmp/uiowa-report.json
python compiler.py verify /tmp/uiowa-report.json
python compiler.py render /tmp/uiowa-report.json /tmp/uiowa-report.md
```

The public CLI is intentionally non-authorizing. Its synthetic inspection cannot mint trusted current maturity/confidence. A trusted integration requires an independent host-controlled authority root.

#### Analyst workbench

```bash
cd revenue/uiowa_rfq_18649_workbench
python3 server.py --port 8765
```

Open `http://127.0.0.1:8765/`. The workbench exposes the 12 ESS/RIS/IAM × assessment-area cells and keeps analyst notes/dispositions separate from immutable compiler output.

#### Framework reference

Use `workbench/framework_crosswalk/20-framework-crosswalk.csv` to trace NIST SSDF, CSF 2.0, and AI RMF concepts. Framework references structure questions; they never replace University evidence or create certification/compliance conclusions.

#### Rating composition

```bash
cd revenue/uiowa_rfq_18649_rating_model
python rating_model.py synthetic_case_critical_gap.json \
  --json-out /tmp/rating.json \
  --markdown-out /tmp/rating.md
```

The model keeps ordinal maturity, evidence coverage, confidence, applicability, and material gaps separate. It deliberately emits no arithmetic maturity average.

#### Practice-specific working examples

The sample runner also exercises already-merged, offline examples for:

- security-event review (`UIOWA-060`);
- service observability (`UIOWA-065`).

These help an operator learn the evidence-state semantics without accessing any live University system.

### 4. Draft review

Use:

- `revenue/uiowa_rfq_18649_handoff/` to validate/render a development-to-operations handoff without declaring release approval;
- `revenue/uiowa_rfq_18649_prioritization/` to inspect recommendation priorities and sensitivity. Missing required estimates become HOLD, not zero;
- `revenue/uiowa_rfq_18649_outcome_measurement/` to link recommended improvements to baseline/follow-up measures while keeping adoption activity separate from outcomes.

Clark's professional judgment and consolidated factual review remain necessary. Formula output is decision support, not a substitute for review.

### 5. Final delivery

Use the UIOWA-093 synthetic traceability rehearsal as the reference chain:

```bash
cd revenue/uiowa_rfq_18649_traceability_rehearsal
python validate_trace.py .
```

Its checked-in synthetic bundle demonstrates:

```text
evidence -> finding -> recommendation -> report statement
```

Every substantive final statement should remain reconstructable to exact supporting material. Reconcile the final artifact list against the **actually accepted** scope, not merely the repository's proposed exhibit.

### 6. Optional readout

At the frozen snapshot, UIOWA-088 was not present in the inspected merged tree, so the manifest marks it `pending_at_snapshot`.

Before preparing an optional leadership/group readout, refresh current main. If a later UIOWA-088 carrier has merged, inspect it and update the operator map. The optional readout remains separately proposed and should agree with the accepted final report.

## Synthetic sample run

The manifest currently contains eight executable sample assets and multiple commands. The runner exercises only checked-in preparation fixtures:

1. workshare compile → verify → render;
2. rating critical-gap composition;
3. security-event review export;
4. observability analysis;
5. handoff validation/render;
6. recommendation prioritization + sensitivity output;
7. outcome-measurement validation/report;
8. finding-to-final-report traceability validation.

Outputs are written only beneath the operator-provided `--out` directory unless a source tool is explicitly read-only/stdout-only.

The runner does **not**:

- connect to University systems;
- use credentials;
- send Slack/email;
- submit a bid;
- accept contract terms;
- schedule meetings;
- buy products/services;
- run a browser or install PDF dependencies.

Those exclusions keep the portable sample deterministic and safe.

## What is working versus what is not asserted

| Status | Meaning |
| --- | --- |
| `working` | Executable entry point exists in the captured checkout. |
| `working_reference` | Usable authored material exists; it is not itself executable. |
| `working_interactive` | Operator-facing local UI exists and has its own acceptance commands. |
| `working_optional_dependency` | Asset is usable but needs its declared optional dependency for some formats. |
| `working_synthetic_rehearsal` | End-to-end rehearsal exists using fictional records. |
| `pending_at_snapshot` | The requested lane was not verified as merged at the snapshot and must not be implied complete. |

"Working" means the artifact/entry point exists at the frozen repository state. It does not mean a real University assessment has been performed.

## University inputs still required

The machine-readable manifest keeps the full list. The high-value unresolved inputs are:

- kickoff/review calendar and participant availability;
- actual ESS/RIS/IAM participants and responsibility boundaries;
- authorized evidence sources and access path;
- actual process documents, system/service records, exports, and interviews;
- agreed maturity-anchor calibration and evidence-confidence conventions;
- consolidated corrections and disputed interpretations;
- accepted priorities, owners, dependencies, and sequencing constraints;
- final audience, accessibility/branding expectations, and optional-readout format.

## Three-minute demo route

If time is short, demonstrate the evidence chain rather than every utility:

1. Open `workshare/methodology/23-synthetic-evidence-register.csv` and show a contradictory/limited synthetic evidence case.
2. Open `workbench/12-policy-reference-memo.md` and show how a public policy becomes a discovery question rather than a finding.
3. Run the UIOWA-022 critical-gap sample and show why strong observations do not hide a critical weakness.
4. Open `traceability_rehearsal/trace-map.csv` and show the path back from report language to exact evidence.
5. Close on `workshare/ACCEPTANCE_EXHIBIT.md`: TJLabs prepares traceable evidence/artifacts; Clark's retains the prime relationship, professional judgment, and final recommendations.

## Files in this handoff

- `operator_manifest.json` — machine-readable lifecycle/asset/command map.
- `asset_catalog.csv` — editable table for operators and reviewers.
- `preflight.py` — fail-closed checkout/path/command validator.
- `sample_run.py` — controlled synthetic execution and receipt generator.
- `test_operator_handoff.py` — regression coverage for the handoff contract.
- `100-operator-guide.md` — this guide.

The handoff is deliberately small: it points to source-of-truth assets rather than copying and forking them.
