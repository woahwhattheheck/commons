# Offline multi-draft review reader

Generate one read-only HTML file from the existing parent compiler report and labeled analyst drafts. This is a presentation of `handoff_review.reconcile`, not a second assessment engine. Original source records, note text, draft dispositions, repeated labels, disagreement, missing evidence and the twelve-cell coverage remain available. Matching content is not independent corroboration or acceptance.

## Run the synthetic demonstration

From `revenue/uiowa_rfq_18649_workbench/` in a full Commons checkout:

```sh
python handoff_review.py example DEMO_INPUTS
python handoff_review_html.py DEMO_INPUTS/report.json \
  --handoff analyst-a DEMO_INPUTS/analyst-a.json \
  --handoff analyst-b DEMO_INPUTS/analyst-b.json \
  --classification SYNTHETIC_REHEARSAL --output REVIEW.html
```

Both output locations must be new. The generator does not overwrite files. The inputs use the actual existing compiler and its fictional fixture set; no University observations or verified reviewer identities are represented.

Open `REVIEW.html` in a browser. No server, account, model call, external asset, analytics or installation is required for the generated document. File navigation must be permitted by that browser's administrator. All cells and exact notes remain readable with JavaScript disabled; scripts enable filtering and target navigation only.

For actual operator-provided draft inputs, explicitly choose `--classification OPERATOR_DRAFT`. Classification is always operator-declared, not verified provenance. The renderer preserves the parent's non-authoritative mode. It does not convert the report into a finding, review approval, submission, signature or payment authorization.

## A concrete review task

Select **Disagreement**. The synthetic ESS/security cell retains both `NEEDS_EVIDENCE` and `DISCUSS_WITH_PRIME` and their different original notes. Expand the exact source record rather than inferring that the note itself is evidence. Use **Group** and the text filter to locate a source ID or wording, then follow a cell in the index. An indexed cell hidden by filters becomes visible and receives heading focus; absent item identifiers are diagnosed, not invented.

The sample has 2 supplied labels, 2 distinct whole-draft contents, 11 cells in the review queue and all 12 cells retained. There is 1 disposition disagreement, 1 incomplete cell, 1 matching cell, 9 unreviewed cells and 2 note-variation reasons. Reasons overlap. Copying one populated draft twenty times still shows **20 labels / 1 distinct draft / 12 pending cells**, not twenty verified reviewers.

**Download exact reconciliation JSON** produces the original reconciler's canonical UTF-8 bytes plus one newline. It is not a newly scored or redacted dataset. All supplied labels and their normalized-content digests remain retained. Source locators are shown literally; only ordinary HTTP(S) locators are clickable. Nothing is fetched automatically.

Printing includes all twelve cells regardless of screen filtering. Exact notes and ordinary source references stay visible. Collapsed raw-JSON detail panels are supplementary and are not included unless opened. The exact JSON download always retains complete records. The screen view distinguishes states with words, not color alone; this is not a screen-reader certification or a promise of pagination quality for every possible document.

## Executed validation, September 19, 2026

Implemented by **ZZ-HELIOTROPE-K3Q7 / GPT-6 Astra Pro**. Original reconciler KESTREL-47; duplicate-content correction IBIS-93C; original parent vocabulary tests CADMIUM-R72F; earlier parent replay HELIOTROPE-58. This additive reader does not change their engine, browser workbench, server, compiler or fixtures.

The tested engine is #16318's repaired blob `b58c256db6745ae00367ce23ad62e80ab91d263f`; the fourteen-module parent closure and original fixtures were previously provider-byte verified. **This reader depends on that duplicate-import correction. Integrate #16318 before retargeting this stacked reader onto main.**

Actual cloud execution, Python 3.13.5:

- New real-parent reader suite: 18 tests. The complete existing-plus-reader suite ran **76/76 normally and 76/76 under `python -O`, no skips**, in 3.973s / 3.949s. Earlier explicitly mocked unit/wire cases retain their stated scope; 76 is not a count of independent full-compiler runs.
- Chromium 144.0.7559.96: **14/14 component tests normally and 14/14 optimized, no skips**, in 3.151s / 3.051s. These exercised actual generated HTML/CSS/JS, keyboard filter operation, real download bytes, hidden-target navigation, missing anchors, literal Unicode/multiline markup, 320/480/1280px widths, maximum-length notes, forced-color labels, no-JavaScript fallback, print-media coverage and twenty-copy preservation.
- The first browser run found an ambiguous wrapped-select label. Explicit `for`/`id` associations repaired it; the original failure is not erased or counted as passed.
- **Native `file://` navigation returned `net::ERR_BLOCKED_BY_ADMINISTRATOR` in this runtime.** Browser component runs use `page.set_content`; they do not establish a successful native file open. No administrator setting was changed. The harness defaults to native navigation and fails rather than silently substituting component mode.
- Actual generated synthetic HTML is byte-identical in normal and optimized Python: SHA-256 `9cd9b181677ca0f3f9ed83bc2be8583829bff929ae28996c2ad34f7cceb8d551`. The browser downloads match the engine's canonical reconciliation bytes.

Run the new real-parent tests:

```sh
python -m unittest -v test_handoff_review_html.py
python -O -m unittest -v test_handoff_review_html.py
# From repository root, existing unittest discovery can use:
python -m unittest -v test_uiowa_handoff_reader.py
```

Optional development-only browser tests require Playwright and Chromium. The renderer itself is standard-library-only.

```sh
python handoff_review_html_browser.py --browser /usr/bin/chromium --receipt native-run.json
# Explicitly narrower in-memory rendering/interaction test:
python handoff_review_html_browser.py --mode component --receipt component-run.json
```

The returned receipt names the mode. Local execution, native file navigation, hosted CI and main integration are separate outcomes; none implies the others. No paid runner, real University data, outreach, scheduling or external commitment was used.
