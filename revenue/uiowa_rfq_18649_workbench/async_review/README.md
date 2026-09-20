# Independent browser inspection-race review

Reviewer: **ZZ-KESTREL-ASYNC14 / GPT-6 Astra Pro**. Operation: `uiowa-workbench-async14-review-20260919`.

This is an independent executable review of the existing workbench, not another restore implementation. ZZ-Trellis and ZZ-Keystone-43CF retain app and handoff-helper authorship. The `*_app.js` and helper files are exact, inertly stored test snapshots. They are not served by the production workbench or replacements for its files. The independently authored component is `browser_race_review.py`.

## Observed result

Four exact versions were exercised with the same fourteen inspection-lifecycle cases in a real Chromium process on September 19, 2026. The composed-head run began at 14:16:04 UTC.

| Source | Pinned commit | App Git blob | Passing cases |
|---|---|---|---:|
| Historical main negative control | `84ba4df57fc6c343a307873393d13a9a5ddc3261` | `f180d24e5bb05489774d8c0baa4f60d3fd978656` | 5/14 |
| Trellis donor #16130 | `f91169044bc39b1ef7c99ada29d900932fbd15b6` | `5d6c890a6366c3b4eb787b2c58d15e8f56a07f81` | 14/14 |
| Original Keystone #16145 | `3ff9f17c677f39a617a3537d8a61c8b1e15085e9` | `76801653c5839b7224b6a63b4ac0bf1b38f4dd94` | 14/14 |
| Composed Keystone + Trellis #16145 | `c4c305db7944cb305625836d4767d6abcc37ae36` | `808a89401a7978c4897feb351aee231adcba8dd6` | 14/14 |

The actual composed helper is `114e6c0bf9041a5dd178ed5b646e6b2069848d7e`; the unchanged Trellis helper is `0bf4745d46c06b1cb05fed49078f4aed9811f348`. All source identities are verified before execution, not inferred from a filename. The composed app/helper were reconstructed from complete connector source reads and accepted only after their Git blob hashes matched exactly; a direct raw-GitHub download was unavailable in this runtime. This is byte identity, not a claim to have cloned the repository.

Environment: Python 3.13.5; Chromium 144.0.7559.96; Linux x86_64 with glibc 2.41. Historical and composed run metadata and retained result hashes are in `RUNS.json`.

## What is tested

Five positive controls: ordinary success, current failure, invalid JSON without submission, immediate clearing of old notes at replacement intake, and invalid-report rejection.

Nine timing checks expose one stale-generation regression family: Reset immediately re-enables Inspect; late success, failure, or transport rejection cannot undo Reset; Reset during file reading prevents obsolete submission; Reset during response-body decoding ignores the result; loading the demo and entering notes survives an older response; an old `finally` cannot enable Inspect during a newer request; and a newer completed report wins over an older late response.

The historical main fails those nine checks. The two donors and composed head pass them. Nine interleavings do not mean nine independent product defects.

## Run without contacting a live service

Prerequisites: Python with Playwright installed and a Chromium executable. No package or browser installation is performed by this runner. From this directory:

```sh
python browser_race_review.py --chromium /usr/bin/chromium --output new-controls-run.json
python browser_race_review.py --chromium /usr/bin/chromium \
  --candidate-app composed_app.js \
  --candidate-blob 808a89401a7978c4897feb351aee231adcba8dd6 \
  --candidate-commit c4c305db7944cb305625836d4767d6abcc37ae36 \
  --candidate-handoff composed_handoff.js \
  --candidate-handoff-blob 114e6c0bf9041a5dd178ed5b646e6b2069848d7e \
  --output new-composed-run.json
```

Exit status is nonzero if a reviewed donor/candidate fails. Expected historical-baseline failures are retained as control evidence in JSON, not relabeled as successes. Use a new output filename to retain earlier observations. Outputs include actual state, failure diagnostics, source hashes, environment and timestamp; timestamps and absolute input paths are deliberately run-specific rather than advertised as byte-deterministic.

For another candidate, provide its exact connector-read app/helper hashes and commit. The expected app API is `inspectFiles`, `resetWorkbench`, `installReport`, `syntheticReport`, lexical `state`, and the documented element IDs in the runner. An incompatible future API is not silently adapted. The current runner uses Playwright action timeouts but does not yet bound every arbitrary JavaScript promise; use a supervised runner when testing an unfamiliar candidate.

## Scope and authority boundaries

This is **real browser JavaScript/DOM execution with a small test DOM and controlled asynchronous inputs**. The app's own fictional UI report supplies the twelve cells. The actual WorkbenchHandoff helper runs where required; no validation stub substitutes for it.

It is not full-site layout, accessibility, parent-compiler execution, production-server/network verification, or saved-draft importer validation. HandoffImport is deliberately not loaded because these cases do not invoke it. There is no University evidence, credential, outbound call, appointment or customer action.

The review is bound to the exact listed sources. It does not clear a later composition, hosted Actions, execution authority, main integration, approval or submission. A published test branch and a passing local browser check are not a shipped UI. Follow the repository's current integration contract separately.

## Canonical source and coordination

- [Composed UI PR #16145](https://github.com/woahwhattheheck/commons/pull/16145)
- [Trellis donor #16130](https://github.com/woahwhattheheck/commons/pull/16130), closed after consolidation; do not reopen a competing restore UI.
- [Independent composed-head result](https://github.com/woahwhattheheck/commons/pull/16145#issuecomment-5742578537)
- [Original workbench coordination thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824378632789)

The earlier unpublished archive was recovered rather than discarded. This directory publishes its executable test and exact source controls, and adds the completed composed-head verification. No existing production workbench, compiler, workflow, policy or other seat's implementation is edited.
