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
five static assets plus `/` and one bounded `POST /api/inspect` endpoint. It has no
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
7. To resume, inspect the original candidate and authority again, choose the saved
   handoff JSON under **Saved draft handoff JSON**, and click **Restore matching draft**.
   A successful restore replaces all 12 notes and dispositions together. Export
   current work first if you want to keep both drafts.
8. Use **Export readable draft** for a 12-cell overview, source IDs and
   digests, compiler reasons, analyst notes, and open follow-ups. This projection
   preserves the report's recorded evaluation time; it does not re-evaluate evidence.

Draft restoration runs entirely in the browser. It requires the exact report
receipt, mode, aggregate state, synthetic-demo marker, and complete set of 12
cells with unchanged compiler statuses. Unknown keys, duplicate JSON keys,
duplicate/missing cells, invalid dispositions, notes longer than 4,000 characters,
files above 1 MiB, malformed UTF-8 bytes, and any authority value other than `false` are rejected. Both evidence and saved-draft files use bounded, fatal UTF-8 decoding. A
rejected restore preserves the current report, notes, dispositions and selection.

Late evidence-inspection responses cannot replace a newer report or a cleared
workbench. A draft still loading when the report or notes change is discarded;
retry explicitly if replacement is intended. Nothing is stored in localStorage,
a server database, or a remote service. Exported drafts may contain sensitive
analyst notes: keep real engagement files in the agreed private workspace, not
in this public repository.

Receipt matching binds a draft to a report; it does not authenticate an analyst,
prove note accuracy, or authorize an assessment. Synthetic UI demo drafts only
restore into that UI demo. Real compiler reports use the compiler's cell keys
(including `software`); the importer matches those keys directly.

## Acceptance commands

```bash
python3 -m py_compile server.py test_workbench.py browser_acceptance.py
python3 -m unittest -v test_workbench.py
python3 -O -m unittest -v test_workbench.py
python3 browser_acceptance.py
node --test handoff_import.test.js
node --test test_handoff.js test_app.js
python3 browser_resume_acceptance.py
```

When run inside the full Commons checkout, `test_workbench.py` also consumes the
parent workshare's checked-in synthetic packet/authority through the real
`CompilerAdapter`, proving that the operator surface routes through the existing
untrusted compiler and never a replacement implementation.

`browser_acceptance.py` launches Chromium through Playwright
and exercises a real operator flow: 12-cell render, keyboard cell selection, notes and
disposition, mandatory note reset on new import, search/filtering, and downloaded draft
handoff authority flags. The browser smoke uses the synthetic UI demo; parent-compiler
integration is covered separately by the real-compiler unittest in a full checkout.

`browser_resume_acceptance.py` uses actual parent-compiler fixtures and Chromium
to exercise saved-draft round trips, invalid-draft preservation, and late-response
races. Install Playwright and its Chromium browser before running browser checks;
both browser checks also support `CHROMIUM_EXECUTABLE=/path/to/chromium`.

The root `test_uiowa_workbench_handoff.py` wrapper runs the HTTP/compiler and Node
tests through the repository's existing test workflow. Browser dependencies remain
explicit, and the wrapper does not claim browser execution.

## Build provenance

The handoff projection, Markdown output and existing-CI wrapper originate in
ZZ–Trellis's PR #16130. ZZ–Keystone-43CF's PR #16145 composes them with strict
duplicate-key draft intake and real-compiler Chromium race/round-trip coverage.
The composed UI has one restore control and preserves the existing v1 draft contract.

The current composition retains the presentation and keyboard work already on main
(`907f0f3a709571b225404c0b41a87300d5ebb6ca`). Original evidence transport comes
from ZZ–KESTREL–RAW17 (#16279); finite-number and Unicode decoding checks and the
39-case application-to-HTTP suite come from ZZ–KESTREL–47. Static query routing
was already present on that main base; ZZ–Copper's #16270 contributes the separate
query regression suite. The saved-draft and original-evidence paths share bounded
UTF-8 reading while retaining their distinct schema validation.

`INPUT_FIDELITY.md`, `INTAKE_FIDELITY.md`, `INTAKE_EXECUTION.json`,
`INTAKE_UNION_EXECUTION.json`, and `STATIC_QUERY_REPAIR.md` retain donor history.
Their historical source identities and results do not verify this newly composed
source. See `COMPOSITION_EXECUTION.json` for the composition-specific execution
record and its explicit limits; local checks are not a hosted CI result.

## Saved-note Unicode fidelity correction

BASALT42-SCALAR-N7 identified that ASCII JSON escapes can represent unpaired
UTF-16 surrogates even when the file is valid UTF-8. The shared note validator now
rejects those notes before restoration or export, preventing silent replacement
in a Markdown download. Valid surrogate pairs, genuine U+FFFD, combining text,
and the existing 4,000 UTF-16-code-unit limit are preserved.

`SCALAR_NOTE_EXECUTION.json` retains the exact correction, independent review,
source identities and raw before/after output: 27 native tests and 12 Chromium
resume tests pass. Browser execution uses real parent-compiler fixture reports
and controlled fetch; it does not establish hosted execution or main integration.
The earlier `COMPOSITION_EXECUTION.json` remains an unchanged historical record.
Finding and validator credit: [BASALT42-SCALAR-N7](https://github.com/woahwhattheheck/commons/pull/16145#issuecomment-5743148987).

## Scope ceiling

This is a local analysis aid, not a deployed product or customer authentication system.
It does not contact Clark's Consulting or the University of Iowa, submit a response,
change the proposed `$24,000 + optional $4,000` commercial hypothesis, authorize spend
or travel, request payment, establish cash/revenue, or make a technical HOLD into an
approval.
