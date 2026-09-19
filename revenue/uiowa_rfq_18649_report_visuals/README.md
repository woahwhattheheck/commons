# Accessible visual language for the final report

**UIOWA-090.** Reusable chart and table templates for the four figures the final report needs —
the twelve-cell assessment matrix, cross-group comparison, evidence coverage, and the phased
roadmap — built so a reader understands each one **without relying on colour**, and so an
**unassessed cell never reads as a low rating**.

Python 3 standard library only. No third-party packages, no plotting library, no network at
runtime. SVG is written out by hand so every mark, hatch, label and ARIA attribute in the output
is something this package put there deliberately and can therefore test.

---

## The two rules the whole package exists to enforce

**1. No meaning lives in colour alone.** Every assessment band carries four independent channels:
a fill colour, a drawn **shape**, a fill **texture**, and a written **label**. Take any one away —
a colour-blind reader, a monochrome printer, a projector that flattens fine hatching, a screen
reader that sees only text — and the remaining channels still name the band.

**2. "Not assessed" is not a rating, and must never look like the bottom of the scale.**
`Gap` is a finding about the group. `Not assessed` is a statement about *our* evidence.
`Insufficient evidence` is a third, different thing again. The report is read by people who will
act on it, and quietly converting *our* missing evidence into *their* low score is the single most
damaging thing these visuals could do. So the two not-a-rating states are:

- pulled off the ordinal scale entirely (`rank is None`, so nothing can sort them to the bottom),
- given a dashed border no rating ever uses, plus their own shape and texture,
- kept **at least 3:1 away from every rating fill after the colour is stripped out** — measured,
  not asserted,
- placed **below a solid dividing rule** in the comparison chart, under the heading
  *"Off the rating scale — these are statements about the evidence, not lower ratings"*, so a
  reader scanning downward hits a boundary instead of running out of scale,
- excluded from every count of ratings, rather than counted as zero.

---

## What "accessible" is backed by here

Not a claim — a measurement that runs in the test suite.

`contrast.py` implements WCAG 2.1 relative luminance and contrast ratio from the specification.
It is validated against published reference values (white/black = 21.0; `#767676` on white = 4.54,
the documented 4.5:1 boundary). `palette.audit_palette()` runs every colour pair this package
ships:

```
43 checks, 43 pass, 0 fail        # theme 'print'
43 checks, 43 pass, 0 fail        # theme 'screen'
```

Thresholds: **4.5:1** for text of any size (the large-text exemption is deliberately *not* taken —
report figures get resized, printed and projected), **3:1** for borders, marks, hatch strokes and
rules, **3:1** for two fills a reader must tell apart after colour is removed.

The eight measurements that matter most, from `examples/contrast-audit.txt`:

| pair (colour removed) | ratio |
|---|---|
| Not assessed vs Strength | 7.83:1 |
| Not assessed vs Established | 5.07:1 |
| Not assessed vs Developing | 4.50:1 |
| **Not assessed vs Gap** | **6.38:1** |
| Insufficient evidence vs Strength | 6.32:1 |
| Insufficient evidence vs Established | 4.09:1 |
| Insufficient evidence vs Developing | 3.63:1 |
| Insufficient evidence vs Gap | 5.15:1 |

A test (`test_audit_actually_detects_a_bad_colour`) deliberately breaks a colour and asserts the
audit goes red, because a checker that cannot fail proves nothing.

### Two things the measurement changed

Both of these were caught by running the numbers, not by looking at the chart:

1. The first `Developing` ochre measured 3.47:1 on white and left Not-assessed-vs-Developing at
   exactly 3.00:1 — on the line, no headroom. Darkened to `#8F6510`; that pair is now 4.50:1.

2. **The three group colours are indistinguishable from each other in grayscale** — measured at
   **1.03:1, 1.11:1 and 1.15:1**. Three mid-tone hues at similar luminance always collapse this
   way; picking nicer hues does not fix it. So group identity does **not** ride on colour at all:
   each group gets a distinct **shape** (square / pentagon / hexagon) and its **code printed next
   to every mark**. The colours stay because they help a sighted reader scan, and
   `palette.GROUP_COLOUR_IS_DECORATIVE = True` records the decision so nobody later promotes them
   back to load-bearing. A test asserts every plotted mark has its group code printed beside it.

   This package therefore does **not** claim to be "colour-blind safe" in the sense of having
   three mutually distinguishable group colours. It claims something stronger and testable:
   group colour is never the carrier of meaning.

---

## Honest limits

- **Ordinal ratings are not separable from each other by fill luminance alone.** `Established` vs
  `Developing` is 1.13:1 in grayscale. Six fills cannot all sit 3:1 apart — the luminance range
  does not contain that many steps. That is exactly why shape, texture and the written label are
  mandatory rather than decorative, and why the 3:1 grayscale rule is enforced where it actually
  decides something: between *not-a-rating* and *rating*.
- **Verification here is structural, not visual.** The SVGs are parsed as XML, checked for
  `role="img"`, a real `<title>`/`<desc>`, and that no text or box falls outside the canvas. No
  rasteriser (`rsvg-convert`, `cairosvg`, headless browser) exists in this environment, so
  **nobody has yet looked at these figures rendered as pixels.** They should be opened in a
  browser before use.
- **No testing with actual assistive technology or actual readers has been done.** The ARIA
  structure follows the spec; it has not been driven through a screen reader.
- Long titles are truncated to fit a roadmap card. A title over ~80 characters will clip.

---

## Files

| File | What it is |
|---|---|
| `contrast.py` | WCAG 2.1 luminance / contrast / grayscale, written from the spec |
| `palette.py` | The visual vocabulary + `audit_palette()`; the design contract in comments |
| `svg.py` | Hand-written SVG emitter: marks, hatch patterns, ARIA-labelled documents |
| `model.py` | The assessment data model and the counting rules that keep it honest |
| `figures.py` | The four figure templates |
| `alt_text.py` | Text alternatives + Markdown table templates, generated from the same data |
| `render_report_visuals.py` | CLI: render / `--audit` / `--check-encoding` |
| `fixtures/synthetic_assessment.json` | The fictional example data |
| `examples/` | Rendered output, committed so a reviewer can open it without running anything |
| `test_report_visuals.py` | 60 tests |

## Run it

```bash
cd revenue/uiowa_rfq_18649_report_visuals

python3 render_report_visuals.py                  # render everything into examples/
python3 render_report_visuals.py --audit          # the WCAG contrast report
python3 render_report_visuals.py --check-encoding # verify the redundancy contract
python3 -m unittest test_report_visuals           # 60 tests
```

`--check-encoding` verifies that label, glyph, shape and texture are each unique per band, that
ratings use the solid border and non-ratings the dashed one, that non-ratings carry no rank, and
that every not-a-rating/rating pair clears 3:1 in grayscale. `render` refuses to draw anything if
that contract is broken.

Rendering is **deterministic** — no clock, no randomness, sorted traversal. A second operator
running the same command on the same input gets byte-identical files and a `manifest.json` of
SHA-256 digests, so a diff means the data changed and nothing else. A test renders twice into two
directories and compares bytes.

## Output

Per theme (`print`, `screen`): `matrix`, `cross-group`, `evidence-coverage`, `roadmap` as `.svg`.
Plus `text-alternatives.md` (the exact text embedded in each SVG's `<desc>`), `matrix-table.md`,
`evidence-coverage-table.md`, `roadmap-table.md`, `contrast-audit.txt`, `manifest.json`.

The table templates carry the same redundancy as the charts — a glyph **and** the written band
name in every cell, never a colour swatch on its own:

| Group | Software delivery | Reliability and operations | Security practices | AI readiness |
|---|---|---|---|---|
| **ESS** Enterprise Shared Services | ● **Established** | ▲ **Strength** | ◆ **Developing** | — **Not assessed** |
| **RIS** Research Infrastructure Services | ◆ **Developing** | ● **Established** | ▼ **Gap** | ◎ **Insufficient evidence** |
| **IAM** Identity and Access Management | ● **Established** | ◎ **Insufficient evidence** | ● **Established** | — **Not assessed** |

### Text alternatives cannot drift

Each SVG's `<desc>` is produced by `alt_text.py` from the same `Matrix` object that drew the
picture, and a test asserts `desc == ALT_BUILDERS[key](matrix)` for every figure. A hand-written
caption is correct on the day it is written and wrong the first time the data changes; this one
cannot be.

---

## What is real and what is draft

**Real and working:** the contrast implementation and its audit; the redundant-encoding contract
and its checker; all four figure templates; the text-alternative and table generators; the data
model's rejection rules; deterministic rendering; the 60-test suite. All of it runs on stdlib
Python 3 and is exercised by the committed example.

**Draft / not yet done:** visual review of the rendered pixels (see *Honest limits*); screen-reader
testing; a dark theme; pagination for a matrix wider than four areas or taller than about six
groups; the exact typeface the report will use (the SVG names a generic sans stack).

**Fiction is labelled fiction.** Everything in `fixtures/synthetic_assessment.json` and everything
under `examples/` is invented to exercise the templates. Every figure, table and text alternative
carries the line *"SYNTHETIC EXAMPLE — fictional groups and fictional evidence. Not a University of
Iowa finding."*, and a test asserts that string is present in every output. The example is built to
show both a genuine strength (`ESS / Reliability`) and a real gap (`RIS / Security` — the written
procedure requires two approvals, seven of twelve sampled changes record one), plus two
insufficient-evidence cells and two unassessed cells, because a template that has only ever been
run against tidy data has not been tested.

## University inputs that remain UNKNOWN

Nothing below has been supplied, and none of it is guessed at anywhere in this package:

- The real group names, count and structure, and which are in scope. The three fictional groups
  are placeholders; the templates take any number of groups and areas.
- The agreed assessment areas and the agreed band vocabulary. The six bands here are a working
  proposal and are expected to be renamed.
- Which cells are in scope — i.e. which cells are legitimately `UNASSESSED` rather than pending.
- All actual evidence: documents, interviews, system records, observed artifacts, and their counts.
- The real recommendations, their identifiers, and the real roadmap items, efforts and sequence.
- The report's typeface, page size, column width and print process (these set minimum type size
  and hatch stroke weight; the current values assume roughly a 7-inch text column).
- Whether the client needs a specific conformance target (e.g. WCAG 2.1 AA as a contractual
  obligation) — this package measures against AA thresholds but **makes no certification or
  compliance claim**, here or anywhere in its output.
