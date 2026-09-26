# UIOWA-081 — evidence-linked leadership briefing

Render an editable executive briefing from the existing UIOWA-093 source bundle.
The renderer reuses its native structural validator, preserves finding and
recommendation text, and keeps each statement's evidence and limitation visible.
It does not introduce another assessment, rating or prioritization engine.

## Run the published example

From the Commons repository root with Python 3.10+:

```sh
python revenue/uiowa_rfq_18649_executive_summary/render_summary.py \
  > /tmp/uiowa-leadership-briefing.md
python revenue/uiowa_rfq_18649_executive_summary/render_summary.py \
  --format json > /tmp/uiowa-leadership-briefing.json
```

The default source is the actual checked-in
`revenue/uiowa_rfq_18649_traceability_rehearsal/` bundle. Its three findings,
two recommendations, eight evidence rows and five statement mappings are
fictional preparation material. No new findings or example evidence are created.
The output is readable without the source checkout and editable as Markdown or
structured JSON. Links between findings, recommendations and evidence stay inside
the briefing. No network calls or third-party dependencies are used.

The briefing covers:

- Supplied strengths, gaps and mixed findings with confidence labels and limitations.
- Proposed actions, source-linked rationale and practical dependencies.
- Implementation-effort labels kept separate from unestimated cash savings.
- Expected outcomes kept separate from measurements that were not supplied.
- Unresolved owner, priority, schedule, resource and outcome-measurement decisions.
- Original statement IDs, report locations, evidence locators and exact source hashes.

## Reuse the structured inputs

Pass another authorized local bundle directory as the positional argument. Keep
the established UIOWA-093 six-file contract: `evidence.csv`, `findings.csv`,
`recommendations.csv`, `trace-map.csv`, `executive-summary.md` and `final-report.md`.
The native validator must accept all source links and statement declarations
before a briefing is emitted. The renderer also requires the existing register
columns needed for the briefing; omitted columns fail explicitly.

Use the CSV registers as the editable input template. Finding IDs, recommendation
IDs and evidence IDs remain stable; the trace map identifies exact statements and
their original report locations. Amend the source bundle and its trace map when
changing an authoritative statement, then regenerate the briefing. A hand-edited
rendered briefing is a draft and has not been revalidated automatically.

The renderer copies supplied text and classifications without guessing a priority
order. Identifier order is only display order. A missing limitation or other blank
display value is printed as `NOT SUPPLIED`. Effort categories are not converted to
hours, money or benefit, and no desired outcome is treated as achieved. External
source locators are retained as text; the program does not fetch or authenticate
their underlying documents.

## Output and limits

JSON retains all four source tables, source file/physical-line locators, exact
file lengths, Git blob identities and SHA-256 values. A deterministic bundle digest
binds those source file identities. The renderer checks the source files again
after reading them and rejects a moving bundle. These are byte and structure
checks, not an independent evidence trust root or professional judgment.

Exit 0 means the source bundle passed structural checks and a draft was rendered.
Missing inputs, broken references or malformed fields exit 2 without a partial
briefing. Output goes to stdout; redirect to a new path to retain earlier drafts.

Real evidence belongs in the authorized private engagement environment. The public
sample remains fictional, with no University findings, customer communication,
contract acceptance, scheduling, invoice or payment action implied.

Original UIOWA-093 source authorship is retained. This delivers the reusable
rendering and traceability seam requested in Commons #16154 using the existing
published rehearsal rather than a second demonstration corpus.
