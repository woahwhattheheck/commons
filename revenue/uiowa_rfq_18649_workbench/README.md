# University of Iowa RFQ 18649 — local analyst workbench

This directory is an additive operator surface over the existing
`../uiowa_rfq_18649_workshare` evidence compiler. It does **not** reimplement scoring,
trusted-root validation, commercial terms, or evidence authority.

## Authority boundary

The HTTP adapter calls only the parent compiler's `compile_untrusted_inspection` and
`verify_report_integrity` surfaces. There is no HTTP field, CLI switch, or browser
control for a trusted authority root. The server fails closed unless the returned
report is `UNTRUSTED_INSPECTION` with `current_evidence_review_authority=false`.
Analyst notes live only in browser memory and are exported separately as
`DRAFT_NON_AUTHORITATIVE`, bound to the immutable report receipt. Exported authority
flags for buyer/prime approval, submission, signature, invoice/payment and recognized
revenue are always false.

Real University, prime, credential, customer or other private evidence must not be
committed to this public repository. The checked-in UI demo is synthetic and is
explicitly labeled as **not compiler output**.

## Run

From this directory:

```bash
python3 server.py --port 8765
```

Open `http://127.0.0.1:8765/`. The server binds IPv4 loopback only. It exposes exactly
four static assets plus `/` and one bounded `POST /api/inspect` endpoint. It has no
file-path API, persistence, database, telemetry, external provider calls, arbitrary
repository serving, trusted-root/current-READY path, or note store. Host, Origin,
content type, strict JSON shape, duplicate keys and body size are fail-closed.

## Operator flow

1. Choose the candidate packet JSON and evidence-authority JSON.
2. Click **Inspect with parent compiler**.
3. Review the 12 ESS/RIS/IAM × software-development/security/deployment/AI-readiness
   cells, using status filter or search.
4. Select a cell with mouse or keyboard and record a non-authoritative disposition/note.
5. Export a draft handoff JSON. Notes are bound to the report receipt and stay separate
   from the immutable compiler report.
6. Any new import clears all notes/dispositions before rendering the new generation.
7. To resume a saved review, inspect the same candidate and authority again, choose
   **Saved draft JSON**, and click **Restore saved draft notes**. Export current notes
   first if needed: a valid restore replaces all twelve note/disposition rows.
8. Use **Export readable review Markdown** to produce a twelve-cell overview,
   source IDs and record/content digests, compiler reasons, analyst notes, disposition
   totals, and open follow-ups. The Markdown file includes the report receipt and
   limitations; share the original evidence package separately through its existing
   authorized delivery path.

`handoff.js` preserves the existing `uiowa-rfq18649-analyst-handoff-draft/v1` JSON
format. A restore must match the inspected receipt, mode, aggregate state, synthetic
marker, exact twelve cells and per-cell compiler statuses. Every authority flag must
remain false. Validation finishes before any notes are replaced, so malformed or
mismatched drafts leave the current review intact. Source evidence and compiler
scores cannot be edited by restoring notes. Notes remain limited to 4,000 characters.

Restoration is explicit even when a receipt repeats. An older asynchronous inspection
or draft read cannot overwrite a newer import or a review cleared by the analyst;
notes edited while a draft is being read are also preserved. Keep the draft JSON for
resumption; Markdown is a readable projection, not an import format or a self-contained
evidence bundle. Synthetic UI drafts remain explicitly labeled and distinct from
actual parent-compiler reports.

## Acceptance commands

```bash
python3 -m py_compile server.py test_workbench.py browser_acceptance.py
python3 -m unittest -v test_workbench.py
python3 -O -m unittest -v test_workbench.py
node --test test_handoff.js test_app.js
python3 browser_acceptance.py
```

When run inside the full Commons checkout, `test_workbench.py` also consumes the
parent workshare's checked-in synthetic packet/authority through the real
`CompilerAdapter`, proving that the operator surface routes through the existing
untrusted compiler and never a replacement implementation.

`browser_acceptance.py` launches the machine's `/usr/bin/chromium` through Playwright
and exercises a real operator flow: 12-cell render, keyboard cell selection, notes and
disposition, mandatory note reset on new import, search/filtering, and downloaded draft
handoff authority flags. The browser smoke uses the synthetic UI demo; parent-compiler
integration is covered separately by the real-compiler unittest in a full checkout.
The browser flow also exercises JSON export/restore, mismatched-draft preservation,
and Markdown download. `test_app.js` exercises the actual application event handlers
with a dependency-free DOM test adapter, including asynchronous import races and a
report from the real parent compiler. It is not a browser layout test. The repository
root `test_uiowa_workbench_handoff.py` includes the HTTP/compiler and Node tests in
the existing CI battery without adding a workflow.

## Scope ceiling

This is a local analysis aid, not a deployed product or customer authentication system.
It does not contact Clark's Consulting or the University of Iowa, submit a response,
change the proposed `$24,000 + optional $4,000` commercial hypothesis, authorize spend
or travel, request payment, establish cash/revenue, or make a technical HOLD into an
approval.
