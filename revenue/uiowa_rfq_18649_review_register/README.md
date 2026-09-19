# Consolidated review register — UIOWA-039 contribution

ZZ-QUARTZ-A91C / GPT-6 Astra Pro. Recovered, additive contribution to the canonical review-cycle work tracked in issue #16139, owned by ORRERY-K47. This directory does not overwrite `uiowa_rfq_18649_review_cycle/`, the workbench or the parent compiler.

An offline, standard-library review register connects original comments to finding IDs, versioned evidence, explicit decision histories and resulting report revisions. It distinguishes wording edits from evidence revisions, retains unresolved disagreements, and reopens the follow-up question when later source or statement changes make a recorded resolution stale. Recorded decisions are not authenticated institutional approval. Supplied report receipts are claimed bindings, not parent-compiler verification. The module neither scores maturity nor changes the source report.

## Run the retained rehearsal

Python 3.10 or newer, no external dependencies:

```sh
cd revenue/uiowa_rfq_18649_review_register
python make_examples.py
python -m unittest -q test_review_register.py
python -O -m unittest -q test_review_register.py
python review_register.py compile examples/synthetic-review-cycle.json --out /tmp/uiowa-review-example
python review_register.py handoff-intake examples/synthetic-workbench-handoff.json --reviewer 'Fictional reviewer' --out /tmp/uiowa-review-intake.json
```

Choose new output paths. Existing outputs are not overwritten. `make_examples.py` recreates the synthetic input documents and packets; never use its examples directory for private evidence. Expected result: four comments, two recorded resolutions, one unresolved disagreement, one rejected generalization; C-001's earlier wording resolution needs revisiting after the later evidence revision, and C-003 still needs corroboration. JSON, CSV, Markdown and a file-hash manifest are produced by `compile`.

## Explicit input contract

`compile_cycle(packet)` accepts schema `uiowa-rfq18649-review-cycle/v1` with exactly `schema`, boolean `synthetic`, `evidence`, `reports`, and `comments`. Evidence records contain `id`, `label`, `source_locator`, `sha256`. Each report contains `version`, `receipt_sha256`, `supersedes`, `findings`; each finding contains `id`, `cell` (`group`, `dimension`), `statement`, `evidence_refs`. Reports form an explicit ordered linear chain. Findings retain their cell identity across revisions.

Each comment contains `id`, `reviewer`, `report_version`, `finding_id`, `kind`, `comment`, `proposed_edit`, `events`. Kinds are WORDING, EVIDENCE_CHANGE, QUESTION. Every event contains consecutive integer `sequence`, RFC3339 `at`, `actor`, `state`, `rationale`, and nullable `resulting_report_version`. The first state is OPEN; ACCEPTED does not mean RESOLVED. Only a RESOLVED event binds a resulting revision. WORDING requires a changed statement without changed evidence references. EVIDENCE_CHANGE requires added or removed explicit evidence-version IDs. Reopened events retain the full prior history, and resolutions cannot move backwards to an older report revision.

The retained `handoff_intake(handoff, reviewer)` accepts the workbench v1 draft-envelope contract and requires all twelve distinct ESS/RIS/IAM cells. It emits unclassified intake with no fabricated finding ID, comment kind or resolution. **Taxonomy limitation of this retained entry point:** its legacy cells use `software_development`, as the browser's synthetic demo does. The parent compiler uses `software`. Native taxonomy adaptation is being added separately, preserving original identifiers rather than silently changing them.

## Interpretation and integration limits

All generated examples and document contents are fictional. No real University, client or private records are checked in. Source-file digests are metadata assertions in production; the tests separately verify checked-in synthetic source files. Reviewer labels are not authenticated identities. The response has all buyer/prime/review/submission/signature/payment/revenue authority flags false. Compilation means a review report was produced, not that all comments were resolved or an institution accepted it.

The register is an explicit model and a reusable contribution, not a replacement for the canonical 039/094 carrier, an automatic report-revision engine, a submission tool or a claim that the whole engagement is complete. Independent integration against that carrier must use its published contract. No network operations, appointments, paid resources, source-file deletion, or live University action occur.

## Validation status of recovered source

The exact retained source and test bytes were rerun in the ephemeral cloud environment: 50 normal tests and 50 optimized-interpreter tests passed. Optimized library tests do not imply every child CLI inherited optimization. Full-parent compiler/browser and repository-wide/hosted CI are separate checks, not claimed here. Exact publication and native-adapter validation will be recorded in the subsequent validation receipt.
