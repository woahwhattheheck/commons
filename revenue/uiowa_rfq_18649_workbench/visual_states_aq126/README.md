# Visual states are not performance grades

**UIOWA-126 · ZZ-ASTRA-QUARTZ · GPT-6 Astra Pro**  
Operation: `uiowa-126-astra-quartz-20260919`  
Carrier: [Commons issue 16265](https://github.com/woahwhattheheck/commons/issues/16265)

The actual workbench matrix now carries readable state labels, original source
codes, explanatory text, and separate numeric-availability labels. No score,
percentage, weighted average, maturity finding, or new compiler state is computed.
The same labels survive monochrome, forced colors and printed output. Border
patterns supplement words; a color or symbol alone never supplies the meaning.

## Read the distinction

| Input | Display | Do not infer |
|---|---|---|
| Numeric `0` | Supplied value: 0 (display only) | Missing data, successful practice, or a validated grade. |
| Field absent | Not supplied (field absent) | Explicit null or numeric zero. |
| Explicit `null` | Not determined (null) | A poor result. |
| Null under `UNTRUSTED_EVIDENCE_CONSISTENT` | Not reported in untrusted inspection (null) | Missing evidence; this parent mode deliberately withholds numbers. |
| `HOLD_MISSING_EVIDENCE` | Missing evidence | A demonstrated practice deficiency. |
| `NOT_ASSESSED` | Not assessed | An established assessment outcome. |
| `NOT_APPLICABLE` | Not applicable | A zero, pass, or completed assessment. |
| `HOLD_CONFLICT` | Conflicting evidence | Permission to average differing records into a score. |
| `HOLD_STALE_EVIDENCE` | Stale evidence | A finding about present practice. |
| Unrecognized code | Unrecognized status, plus the original code | A guessed synonym or default success/failure. |
| `false`, `"0"`, empty text or a non-finite number | Non-numeric or invalid value | Numeric zero through coercion. |

A supplied zero and conflicting evidence can coexist in the same display case.
The zero does not resolve the conflict. These axes are not collapsed.

## Runtime boundary

The current parent inspection compiler emits four relevant states:
`UNTRUSTED_EVIDENCE_CONSISTENT`, `HOLD_MISSING_EVIDENCE`, `HOLD_CONFLICT`, and
`HOLD_STALE_EVIDENCE`. Its untrusted-consistent branch deliberately returns null
maturity and confidence. Source inspected: `workshare_assessment.py` blob
`8390cff50054053fa3d9ed032eb3187a46826abf` at main snapshot
`32347167ec22ee93b550adcfb945638b02f42e88`.

**The comparison is UI-only fiction, not compiler output.** `comparison.json`
wraps a marked UI report containing extra named states and numeric sentinels solely
to exercise presentation. This does not expand the candidate/authority intake
schema, establish source authenticity, or assert that the compiler emits those
extra states. Do not use it as an evidence package or a maturity assessment.

The patch changes matrix/detail presentation and scoped styles only. It does not
change import, keyboard listeners, selection state, reset, note contents, parent
verification, or the v1 handoff schema. The original report remains byte-equivalent
under JSON serialization. Draft handoffs retain raw status codes, literal notes,
the synthetic marker, and all seven false authority flags. Display labels are not
inserted into exported cell-note records.

## Run the tests

From repository root, with Node available:

```sh
node --test revenue/uiowa_rfq_18649_workbench/visual_states_aq126/test_visual_states.js
python -m unittest -v test_uiowa_visual_states_aq126.py
python -O -m unittest -v test_uiowa_visual_states_aq126.py
```

The root shim enrolls the Node battery in existing discovery without changing a
workflow. Missing Node is an explicit skip, not executed-runtime evidence. The
Node suite uses a small DOM double and is not browser or print validation.

For actual Chromium and PDF acceptance, use an environment with Playwright,
PyMuPDF, and a Chromium executable. No network or compiler service is invoked:

```sh
python revenue/uiowa_rfq_18649_workbench/visual_states_aq126/browser_rehearsal.py NEW_OUTPUT_DIRECTORY
python -O revenue/uiowa_rfq_18649_workbench/visual_states_aq126/browser_rehearsal.py ANOTHER_NEW_DIRECTORY
```

Use `--chromium PATH` when the executable is not on PATH. Missing dependencies or
changed workbench resource wiring fail explicitly. Output directories must be new.
The harness loads the actual `index.html`, `app.js` and `style.css`, operates the
real DOM, edits a note, downloads the actual handoff, and captures the resulting
matrix as a portable static HTML/PDF comparison. It does not run a second renderer
implementation. Output includes source SHA-256 values, machine-readable checks,
color/monochrome screenshots, and every rendered PDF page for visual inspection.
The static comparison is a readout, not an interactive replacement workbench.

## Executed acceptance

In the ephemeral cloud container, Node 22.16.0 and Chromium 144.0.7559.96:

- 32/32 Node runtime checks passed, zero skipped; the root shim passed normally
  and under Python optimization.
- 42/42 browser/PDF checks passed both normally and under Python optimization.
- All four final PDF pages were visually inspected. Labels, source codes, numeric
  distinctions, page numbers and the fictional-context footer remain readable.
- Normal/optimized runs produced identical comparison HTML and handoff JSON.
  PDF byte determinism is not asserted.

The initial grayscale simulation rasterized PDF text. Grayscale is now used only
for its screenshot; print uses the actual black-on-white rules without the CSS
filter. Acceptance now requires searchable text and fictional context on every
PDF page, plus all critical state labels. This prevents a screenshot-like export
from passing as a text-preserving report.

These are local source-bound execution and visual results, **not hosted CI,
parent-compiler execution, or merge authority**. Current-main reconciliation and
provider execution are recorded separately on the pull request. Other report
chart components, platform-specific screen readers, and unrelated print-template
pagination are outside this narrow repair.
