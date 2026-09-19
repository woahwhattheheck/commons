# UIOWA-093 — finding-to-final-report traceability, with drift detection

A miniature report bundle plus a checker that walks every substantive statement
back to the bytes it rests on:

```
statement (report prose) -> finding -> citation -> source record on disk
```

It fails loudly on an orphan at any level, **in both directions**, and compares
what the report *asserts* against what the record *says*.

Everything here is fabricated for rehearsal. **No statement in this bundle is a
University of Iowa finding**, and nothing synthetic is presented as one. The
University inputs that would replace these fixtures are listed under
[UNKNOWN](#what-is-still-unknown).

## The failure this exists to catch

The neighbouring lane `revenue/uiowa_rfq_18649_traceability_rehearsal/`
(Keystone / GPT-5.6 Sol, merged) ships a **link checker**: it verifies that every
id referenced in the bundle resolves. That is the right first layer and its id
graph is clean.

Link integrity and evidentiary agreement are different properties, and only the
first one is covered by an id check. Running the merged checker against its own
merged bundle with one record edited after the fact:

```
# findings.csv, edited weeks after the report was written:
#   F-002,RIS,gap,Propagation evidence remains incomplete
#     -> F-002,RIS,strength,Propagation evidence is complete
# the executive summary is NOT touched and still says the opposite

evidence=8 findings=3 recommendations=2 statements=5
trace validation: PASS
```

The report and the record flatly contradict each other and the bundle passes.
Two further gaps in the same run: appending an unsourced sentence to the
executive summary (*"All three groups demonstrate adequate release discipline
and no further remediation is required this cycle."*) also passes, because the
check walks trace-map → text and never text → trace-map; and no citation
resolves to a source record, because the bundle contains no source files — the
`locator` column is free text with nothing behind it.

In a long engagement the report is edited many times after the findings are
written. **Drift is the realistic failure, not a typo'd id.** This lane is that
missing layer. It is additive: it does not modify the merged lane, and it reuses
its field names (`statement_id`, `finding_id`, `evidence_id`, `locator`,
`evidence_state`, `limitation`, `linked_findings`) so the two compose.

## Run it

```bash
python3 trace_check.py bundle                       # the clean bundle  -> PASS, exit 0
python3 trace_check.py bundle_drifted               # the broken fixture -> FAIL, exit 1
python3 trace_check.py bundle --format markdown     # the trace map (TRACE_MAP.md)
python3 trace_check.py bundle --format json         # machine-readable, deterministic
python3 trace_check.py bundle --rules               # the rule catalogue
python3 -m unittest test_trace_check -v             # 34 tests
```

Clean bundle:

```
bundle: sources=8 evidence=8 findings=3 recommendations=2 statements=6
trace rows (statement -> finding -> citation -> source): 15

TRACE CHECK: PASS - every statement resolves to a finding, every
finding to a citation, every citation to a source record on disk,
and every asserted polarity and quantity matches its record.
```

## The deliberately broken fixture

`bundle_drifted/` is `bundle/` with **one** edit — somebody "resolves" the RIS
gap in the findings sheet and never reopens the report:

```
$ diff -rq bundle bundle_drifted
Files bundle/findings.csv and bundle_drifted/findings.csv differ
```

One file. The report is byte-identical and still reads *"the test inventory lists
0 end-to-end propagation scenarios and no retained example was identified."*
A test (`test_drift_is_confined_to_the_record`) asserts that, so the fixture
cannot quietly become a report rewrite and stop proving anything.

```
ERROR T301 trace-map.csv:S-002       statement asserts 'gap' but finding F-002 is recorded as 'strength'
ERROR T301 trace-map.csv:S-004       statement asserts 'gap' but finding F-002 is recorded as 'strength'
ERROR T306 trace-map.csv:S-002       finding F-002 changed after this statement was registered
                                     (registered ae41cb9edae7f6a2, now f5fd5e86705f0044)
                                     -- re-read the report against it, then re-register deliberately
ERROR T306 trace-map.csv:S-004       finding F-002 changed after this statement was registered ...
ERROR T307 recommendations.csv:R-001 rests only on findings recorded as strengths -- either the
                                     finding moved or the recommendation lost its basis

TRACE CHECK: FAIL - 5 error(s), 0 warning(s)
```

Three **independent** detectors fire, deliberately not one:

| | what it compares | defeated by |
|---|---|---|
| **T301** | the polarity the statement declares vs the finding's recorded `type` | editing the declared polarity too |
| **T306** | a content digest over the fields the statement rests on | a careless `--register` |
| **T307** | whether a recommendation still has a gap or mixed finding under it | deleting the recommendation |

Any one is defeatable by a careless keystroke. All three is a decision, and a
decision leaves a diff a reviewer can see. `test_link_integrity_alone_would_not_catch_it`
asserts that no id-resolution rule fires on this fixture — that is precisely why
the agreement layer has to exist alongside a link checker rather than instead of one.

## Design decisions worth knowing

**The digest covers normalised text over named fields.** `FINDING_DIGEST_FIELDS =
(finding_id, type, statement, limitation, evidence_ids)`, hashed over
whitespace-normalised values. Re-quoting a CSV cell or reflowing a line is not
drift; changing what a finding *says* is. `evidence_ids` is in the set on
purpose — changing which evidence a finding rests on is material even when the
prose is identical. A digest that fires on formatting churn gets switched off.

**Nothing self-heals. Registration and sealing are two separate commands.**

```bash
python3 trace_check.py bundle --register   # rebind statements to findings
python3 trace_check.py bundle --seal       # record source-record sha256s
```

If running the checker silently refreshed a digest, it would pass forever and
the guarantee would be theatre — `test_registering_is_deliberate_and_running_the_check_never_heals_drift`
runs the checker three times over drifted data and asserts T306 still fires.
They are two commands because *"my report changed"* and *"my evidence changed"*
must not be approvable by the same keystroke. Both print exactly what moved.

**An absent input never becomes a number.** `SRC-008` declares
`QUANTITY propagation_outcome_for_remaining_consumers=UNKNOWN`. A statement
asserting a value there raises **T304** (*"an absent input must not become a
number"*). Note what is *not* UNKNOWN: `end_to_end_propagation_scenarios=0` is a
counted zero — the inventory was read in full and contains no such row — and the
source file says so in as many words. A counted zero and an unmeasured quantity
are different things and the bundle keeps them apart.

**The exact check blocks; the heuristic advises.** `T202` (every report paragraph
is either a registered `**S-NNN.**` statement or explicitly `{narrative}`) is
mechanical and carries the error. `T201` scans `{narrative}` paragraphs for
smuggled quantities and universals, and is reported as a **warning** — it is a
lexical tripwire, not a semantic judge. Its first run flagged this bundle's own
disclaimer (*"Every claim paragraph carries the statement id…"*), which is a
statement about the document, not the assessed subject. The rule was narrowed —
a quantifier now only trips next to an assessment subject — and demoted rather
than excepted. A heuristic that blocks the build on prose like that gets silenced
by its users within a week, which is strictly worse than an advisory that still
gets read.

**A statement that appears twice must say the same thing.** S-001/S-002/S-003
appear in both the executive summary and the report body. **T112** compares the
normalised paragraph text across every location, so the summary cannot soften or
sharpen a claim the body makes.

## What is real, what is draft

| | state |
|---|---|
| `trace_check.py`, `schema.py` | **working** — runs, 34 tests, stdlib only, no network |
| `bundle/` (8 sources, 8 citations, 3 findings, 2 recommendations, 6 statements) | **working fixture, fictional content** |
| `bundle_drifted/` | **working fixture** — the deliberately broken case |
| `TRACE_MAP.md` | **generated** from `bundle/`; a test fails if it goes stale |
| Rule catalogue (30 rules) | **working**; T201 is advisory by design |
| The `{narrative}` paragraph contract | **draft convention** — it works, but a real report would need this agreed with whoever writes the prose |

## What is still UNKNOWN

None of these are guessed, defaulted, or scored. They are absent inputs.

- The University's actual evidence taxonomy and whether `source_type` values
  (`requirement`, `test_result`, `acceptance_record`, `test_inventory`,
  `interview_note`, `inventory`, `design_record`) match what AIS keeps.
- Where real source material would live and whether a stable locator exists for
  it — every anchor here resolves because the bundle owns its own files. A real
  engagement citing a ticket system or a wiki needs a resolution rule this lane
  does not have.
- Whether the report is authored in Markdown at all. `T202` assumes a paragraph
  contract; a Word or Google Docs pipeline needs a different extractor for the
  same rule.
- Retention: how long a sealed source record must remain resolvable after
  delivery. The RFQ's 30-day post-completion requirement is handled in
  `uiowa_rfq_18649_closeout/`, not here.
- Real strengths and gaps. Every finding in this bundle is fabricated.

## Not in this lane

No real University findings and nothing synthetic presented as one. No live data,
no network at runtime, no outreach, no scheduling. No maturity scores, no
certification, compliance or peer-percentile claims, no individual performance
scoring. No edits to another seat's lane — the merged rehearsal bundle was read
and re-run, never modified.

## Files

| file | what it is |
|---|---|
| `trace_check.py` | the checker; `--register`, `--seal`, `--rules`, `--format text\|json\|markdown` |
| `schema.py` | field contract, id formats, rule catalogue, digest functions |
| `test_trace_check.py` | 34 tests, including every hostile case above |
| `bundle/` | the clean miniature report bundle, with real source files in `sources/` |
| `bundle_drifted/` | the same bundle with one record edited after the fact |
| `TRACE_MAP.md` | generated statement → finding → citation → source map |
