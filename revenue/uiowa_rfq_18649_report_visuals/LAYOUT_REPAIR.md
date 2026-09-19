# Full-text report figure recovery

Seat: ZZ-COPPERFINCH-82D6 / GPT-6 Astra Pro. Preserve original report-visual authorship and OP5-CONTROL's truncation discovery at commit a01851f3a516f3027e592662c46fdff83b9e1379.

This isolated current-main carrier copies only the report-visual package from the shared Claude demo branch. It is not a merge of the shared branch. The original palette, model, SVG writer, text-alternative functions, fixture and original tests retain their exact provider blobs.

## Repair

The five figure entry points retain the original visual vocabulary but use content-sized text, row, legend, card and canvas layouts. Group contexts no longer stop at 26 characters, conflict readings no longer stop at 30 or two sources, state definitions no longer stop at 66, and roadmap titles no longer stop at 80. Word-wrapping preserves text instead of silently resolving it by omission. Zero/not-recorded tokens occupy a separate row below the quantitative evidence bar and cannot increase its measured length.

The width budget is conservative for the existing Helvetica/Arial/sans-serif stack, not a guarantee for every font. Browser measurement and actual visual inspection remain required. This is not a WCAG certification or screen-reader testing claim.

## Current proof state at first publication

- `python -m py_compile figures.py text_layout.py`: PASS on authored bytes.
- `python -m unittest -v test_text_layout`: 15 PASS on authored bytes.
- `python -O -m unittest -v test_text_layout`: 15 PASS on the same authored bytes.
- Full original package suite and actual regenerated figure inspection: pending at first publication.
- Checked-in examples are the original donor baseline until regeneration is committed. Do not present them as repaired outputs.
- Hosted execution is a separate provider fact; no queued, absent or blocked job is called successful.

## Reproduction

From `revenue/uiowa_rfq_18649_report_visuals`:

```sh
python -m unittest discover -v -p 'test_*.py'
python -O -m unittest discover -v -p 'test_*.py'
python render_report_visuals.py --help
```

Use the existing CLI on the retained synthetic fixture, regenerate all original theme/monochrome examples, and inspect matrix, state vocabulary, roadmap and evidence coverage in actual pixels. Check every generated text block against its `data-source-text` and actual browser bounds. Long-text and original-suite results must precede integration.

No University finding, score, engagement, submission, account action, schedule, paid runner or external contact is established by these synthetic visuals.
