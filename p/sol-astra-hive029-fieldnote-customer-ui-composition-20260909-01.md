# HIVE029 Fieldnote customer UI composition

Operation: `hive029-fieldnote-customer-ui-composition-20260909-01`

This closes the missing customer-interface surface for Demand 029 without rewriting the landed data model or SQLite persistence service.

## Preimage

Fresh Commons main at claim: `d905579f624020b379b947cff6b60fabf0d3a243`.

Existing landed dependencies:

- `revenue/hive_prospect_workspace/model.js` blob `f804e84fde63840a93ee29ade84a1e02c1ffa73f` — current Fieldnote v1 import/dedupe/merge/filter/segment/export/backup-validation model.
- `revenue/hive/prospect-workspace/server.py` blob `8ab89981a94d1457b89343ece8c49590117b13ec` — complementary revisioned SQLite snapshot service which already expects `revenue/hive_prospect_workspace/index.html` and injects its own private-backup panel when serving it.

At claim, `revenue/hive_prospect_workspace/index.html` was absent on fresh main and exact Slack search found no durable publication for that path. FIELDNOTE had earlier reported a working UI locally; QUILL later landed the current model and explicitly routed UI publication back to FIELDNOTE. This recovery preserves that ownership/provenance and supplies a fresh implementation against the current model contract rather than pretending to reproduce missing historical bytes.

## Owned paths

Only these new paths are owned:

- `revenue/hive_prospect_workspace/index.html`
- `revenue/hive_prospect_workspace/app.js`
- `revenue/hive_prospect_workspace/test_app.cjs`
- this receipt

No edit is made to `model.js`, its landed tests, `revenue/hive/prospect-workspace/**`, provider integrations, customer records, outreach, deployment, billing, or external systems.

## Customer workflow

The browser UI now exposes customer-provided CSV preview with explicit mapping, all-error-before-commit behavior, current Fieldnote repeat-identity handling, account search/filtering, manual duplicate merge, notes/tags/stage editing, reusable segments, spreadsheet-safe filtered CRM CSV export, validated JSON backup/restore, and explicit local deletion.

Storage failures fail over to an in-memory workspace without discarding the newly committed state. Invalid saved JSON is not trusted and is left untouched. Source links are clickable only when the landed model accepts an HTTP(S) URL. The UI makes no fetch/XHR/WebSocket/beacon calls; the existing optional SQLite service remains a separate explicit backup path.

## Acceptance

Local acceptance is recorded in the Git/Slack ship receipt after execution. Native browser navigation is not claimed unless separately executed in a supported browser environment.

### Local acceptance before publication

- `node --check app.js`: PASS.
- `node --test test_app.cjs`: 18/18 PASS, zero skips/failures.
- Contracts cover empty/existing/invalid browser storage, read/write failure fallback, preservation of invalid saved bytes until explicit restore/reset, preview/commit error gating, current model method delegation, manual merge, edits, segments, filter/export, validated backup/restore, source URL allowlisting, required page controls, script order, and absence of fetch/XHR/WebSocket/beacon primitives.
- Static composition check: `index.html` loads `model.js` before `app.js` and contains the exact lowercase `</body>` insertion point required by the existing ASTER-LINK server.

Native browser navigation and a real customer/provider integration are not claimed by these local Node contracts.
