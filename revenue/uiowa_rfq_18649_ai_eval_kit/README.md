# UIOWA-075 — AI usefulness evaluation kit

Built for work order **UIOWA-075** (University of Iowa RFQ 18649 preparation) by seat
`OP5-FLINT`, Claude Opus 5.

An evaluation kit for **AI-assisted documentation, test drafting, and requirements
summarization**. Synthetic tasks carry a *known answer key*, so correctness and completeness
are **computed against ground truth** rather than judged. The fourth measure — **time required
to repair the output** — is what actually decides whether an assisted workflow is cheaper, so
it is measured separately and never folded into the other three.

> **Everything in `data/` is FICTION.** The tasks, the candidate outputs, the reviewers, the
> source locators, the services (ESS / RIS / IAM) and the timings are invented for this kit.
> None of it is a University of Iowa finding, system, document, person, or measurement.

## Run it

```
cd revenue/uiowa_rfq_18649_ai_eval_kit

python3 eval_kit.py validate       # structural checks on the answer keys
python3 eval_kit.py report         # score both workflows, write examples/
python3 eval_kit.py check-digest   # prove a second operator gets identical bytes
python3 -m unittest -v             # 29 tests
```

Python 3 standard library only (developed on 3.11). No pip install, no network at runtime,
no model is called and none is simulated.

```
eval_kit.py          scoring engine + CLI
interchange.py       lossless, reader-safe CSV/JSON/Markdown export and import
data/tasks.json      12 tasks: 3 families x 4 case classes, each with an answer key
data/runs_*.json     recorded candidate outputs for two fictional workflows
examples/            generated: results.json, results.csv, schema.json, report.md, digests.json
test_eval_kit.py     29 unittest tests, including hostile and missing-data cases
```

## The four measures, and why they stay apart

| Measure | How it is obtained |
|---|---|
| **Correctness** | Of what the output asserted, how much was right — precision against the answer key. |
| **Completeness** | Of what the key requires, how much the output covered. |
| **Repair time** | Minutes to make the output usable. `MEASURED` where an operator timed it, `MODELED` from the key's per-element repair costs otherwise. **The two subtotals are printed side by side and never averaged.** |
| **Usefulness** | Net minutes saved against an explicit stated `from_scratch_minutes` assumption — arithmetic, not an opinion. Absent assumption → `UNKNOWN`. |

**The kit emits no single composite score.** A blended number would hide exactly the trade a
reader has to make, which the result below demonstrates.

## Case classes — all four, and they behave differently

* **ordinary** — one right answer.
* **ambiguous** — more than one defensible answer. Each defensible reading is a separate
  *answer variant*; an output matching any of them scores correct, and the report records
  **which** variant it matched. If an output fails to discriminate, the tie is reported as a
  tie (`tied_variants`) rather than resolved silently by sort order.
* **stale_context** — the supplied source is out of date. The right behavior is to flag it.
  An output that uses the stale fact fluently is penalized *because* it is fluent.
* **missing_information** — the answer is not derivable from the supplied sources. The right
  behavior is to say so.

### The guardrail that matters most

**A confident fabrication must score worse than an honest abstention.** A kit that ranks
fluent invention above "this is not in the sources" will recommend the wrong workflow, and it
will do it convincingly. `test_fabrication_scores_worse_than_abstention` asserts that ordering
on completeness, on correctness, on repair minutes, and on net time.

It is enforced in the data too: per-element repair costs price a **forbidden** element higher
than any **required** one, because a missing statement announces itself and a confident wrong
statement has to be caught first. `validate_dataset` fails a dataset that inverts that.

## Actual result from the shipped fixtures

`python3 eval_kit.py report`, verbatim:

```
assisted-draft-v1: scored 12/12  completeness=0.7292  correctness=0.75  forbidden_fires=3  net_saved_timed=209min  NOT_RUN=none  time_UNKNOWN=['REQ-MIS-12']
manual-draft-v1:   scored 11/12  completeness=0.9242  correctness=1.0   forbidden_fires=0  net_saved_timed=26min   NOT_RUN=['REQ-STA-11']  time_UNKNOWN=['REQ-MIS-12']
paired on 11 tasks; unpaired excluded: ['REQ-STA-11']
```

Paired on the 11 tasks both workflows ran:

| | assisted-draft-v1 | manual-draft-v1 |
|---|---|---|
| Completeness (mean) | 0.7045 | 0.9242 |
| Correctness (mean) | 0.7273 | 1.0 |
| Generation minutes | 25 | 317 |
| Repair minutes used | 140 | 17 |
| **Net minutes saved** | **195** | **26** |
| Wrong / invented / stale assertions | **3** | **0** |

**The strength is real.** The assisted path drafts in 25 minutes what the unassisted path takes
317 to draft, and still nets +195 minutes after repair.

**The gap is real too, and it is not a rounding artifact.** Three assertions were wrong or
invented where the unassisted path produced none, and both missing-information tasks went **net
time-negative**:

* `DOC-MIS-04` — asked for a backup retention period the fictional sources never state. The
  assisted output says "retained for 90 days". Completeness 0.0, correctness 0.0, 34 modeled
  repair minutes, **net −16 minutes**. Generating that draft in two minutes *cost* time.
* `TST-MIS-08` — asked for behavior on duplicate enrollment that is nowhere specified. The
  assisted output asserts `HTTP 409`. **Net −8 minutes.**
* `DOC-STA-03` — a well-written procedure built on a retired endpoint from a 2025 source.
  Correctness 0.0 precisely because it reads as correct.

The honest reading: on this fictional task mix the assisted workflow is clearly worth using for
ordinary and test-drafting work, and is a **net loss** on tasks where the source does not
contain the answer. That is a statement about task mix, not a verdict on a product.

## What this kit refuses to do

* **It does not turn an absent input into a number.** A task with no recorded run is `NOT_RUN`:
  completeness, correctness, repair and time are all `UNKNOWN` and it leaves **every**
  denominator. `manual-draft-v1` never ran `REQ-STA-11`; zero-filling it would have reported
  completeness 0.847 instead of 0.9242 — a fabricated finding. A test asserts the difference.
* **It distinguishes "produced nothing" from "never ran."** An empty recorded output is scored
  0.0 (real evidence about the workflow); a missing record is `UNKNOWN`.
* **It does not average a measurement with an estimate.** `DOC-MIS-04` has no measured repair
  time — the reviewer never caught the invented figure during the timed session — so its basis
  reads `MODELED` and it is named in `repair_not_measured_tasks`.
* **It does not zero-fill a paired comparison.** Tasks only one workflow ran are listed as
  unpaired and excluded.
* **It does not rate individuals.** The unit of measurement is a workflow. No certification,
  compliance, maturity or peer-percentile claim appears anywhere.
* **It does not generalize.** 12 fictional tasks. A different task mix moves the answer.

## Interchange: the results have to survive leaving this environment

`interchange.py` exists because the kit's value depends on a reader opening the results without
the producing environment. Exercised by the shipped `examples/results.csv` and by tests:

* **CSV formula injection is neutralized *and* flagged, never silently mangled.** A reviewer
  note of `=SUM(B2:B13)` (a real fixture — someone pasted a spreadsheet formula into a notes
  field) exports as `'=SUM(B2:B13)`, appears in an export-warnings table in `report.md`, and is
  restored **exactly** on import. Tests assert no exported cell begins `=`, `+` or `@`, and that
  the value round-trips byte-identically.
* **NULL vs empty string vs literal `"NA"` stay three distinct states**, using the Postgres
  `COPY` convention: NULL is the sentinel `\N`, and a leading backslash in real data is escaped
  by doubling. `analyst_followup` carries all three in the shipped fixtures.
* **Dates are ISO-8601 only.** `03/04/2026` raises `AmbiguousDateError` naming *both* readings
  (2026-03-04 and 2026-04-03). The kit does not guess a locale.
* **Unicode, multiline notes, embedded quotes and commas, long locators.** Accented and CJK
  reviewer names round-trip NFC-normalized; a note containing a CRLF inside a quoted field
  round-trips; a 477-character source locator survives intact.
* **Round-trip equality is proved, not asserted** — records are content-hashed before export
  and after import and the hashes compared.

### Format boundary — stated, not faked

This kit writes **CSV, JSON and Markdown** with the standard library. It does **not** write
`.xlsx` or `.pdf`: both need a third-party dependency this kit does not take. Rather than ship
a stub that pretends, the CSV is emitted beside a machine-readable column dictionary
(`examples/schema.json`, naming every column's kind and the null sentinel) so a spreadsheet
import is correct and repeatable, and `report.md` is the document-format deliverable. If a
real `.xlsx`/`.pdf` writer is wanted, that is a scoped follow-on with a dependency decision
attached — not something to claim here.

## Reproducibility

No clock, no RNG, sorted traversal. `python3 eval_kit.py report` writes `examples/digests.json`;
`python3 eval_kit.py check-digest` rebuilds into a temp directory and compares. A second
operator gets byte-identical artifacts or a loud failure. A test builds twice into two
directories and compares all four digests.

## A bug these tests caught, recorded rather than quietly fixed

The first run of the suite failed `test_ambiguous_case_accepts_either_defensible_answer`. The
cause was real and would have produced a wrong published finding: both `REQ-AMB-10` outputs
mention *both* senses of "priority" ("uses queue priority, **not** the business priority
column"), so with plain substring answer keys each output matched **both** variants, and the
`variant_id` tie-break silently credited the unassisted run with the reading it had explicitly
rejected. Fixes: `none_of` negative terms so an ambiguous key can discriminate; keys tightened
to match what the output says it *uses*; and a genuine tie is now reported as
`tied_variants` instead of being resolved by sort order. Regression test:
`test_ambiguous_reading_is_attributed_to_the_right_variant`.

## University inputs still UNKNOWN

This kit is a **method plus a worked fictional example**. Before it says anything about the
University it needs, from the University or from Clark's:

1. **The real task inventory** — which documentation, test-drafting and requirements work is
   actually AI-assisted today, and in what proportion. The headline result above is entirely a
   function of task mix.
2. **Real answer keys**, written by whoever owns the source of truth for each task. This is the
   expensive input and it cannot be synthesized.
3. **Real `from_scratch_minutes` baselines.** Ours are stated assumptions, labeled as such.
4. **Real measured repair times**, taken by an operator with a timer. Everything not measured
   stays `MODELED` and says so.
5. **Which workflows are actually candidates for comparison**, and their versions.
6. **Whether repair cost asymmetry holds in their setting** — we price catching a fabrication
   above noticing an omission. That is a claim about their review process, and they should
   confirm or correct it.

Until those land, every number in `examples/` is fiction demonstrating a method.

## Scope

No real University findings and nothing synthetic presented as one. No live data, no model
calls, no outreach, no scheduling. No certification, compliance, maturity or peer-percentile
claims. No individual performance scoring.
