# University of Iowa RFQ 18649 — recommendation prioritization worksheet

Work order **UIOWA-084**. A formula-driven ranking tool that compares expected effects on
**quality**, **security** and **delivery** against **implementation complexity**, with every
weight, every input and every arithmetic step printed next to the result — and with missing
estimates held out as explicit UNKNOWNs rather than quietly scored as zero.

Offline, Python 3 standard library only. No network access at runtime, no installs.

---

## Status: what is real and what is draft

| Thing | Status |
|---|---|
| `prioritize.py` — the calculator | **Working code.** 48 tests, all passing. |
| `test_prioritize.py` | **Working tests.** Run them; they are the argument. |
| `fixtures/synthetic-recommendations.json` | **FICTION.** Eleven invented recommendations with invented estimates, written to exercise the calculator. |
| `fixtures/weight-scenarios.json` | **ASSUMPTIONS.** Six weightings nobody has agreed to. The first thing to argue about. |
| `examples/*` | **Generated output** from the fiction above. Not a finding. |

**Nothing in this directory is a University of Iowa finding, assessment, score or commitment.**
Every estimate was invented to make the tool demonstrable. No individual is rated anywhere. No
maturity level, compliance verdict or peer percentile is produced, because none of those are
things this tool is entitled to say.

---

## Run it

```bash
# Print the worksheet for the checked-in synthetic set
python3 prioritize.py

# Write all three outputs
python3 prioritize.py --weights baseline \
  --json-out out.json --csv-out out.csv --markdown-out out.md

# Change the assumption and watch the order change
python3 prioritize.py --weights quality-led
python3 prioritize.py --weights "quality=0.1,security=0.8,delivery=0.1"

# Walk one weight across its whole range and find where the list reorders
python3 prioritize.py --sweep-dimension delivery --sweep-steps 200

# The tests
python3 -m unittest -v test_prioritize.py
python3 -O -m unittest test_prioritize.py       # also passes with asserts stripped
```

`--include-sweep-points` keeps every sampled point of the crossover sweep in the JSON. It is off
by default: the points are intermediate scaffolding, and the crossovers derived from them are the
result.

---

## The formula

```
benefit        = w_quality x quality + w_security x security + w_delivery x delivery
priority_score = benefit / complexity
```

That is the whole model. It is deliberately small enough to check by hand, and the worksheet
prints the substituted arithmetic on every row so that you can:

```
benefit = 0.350x3 + 0.400x5 + 0.250x3 = 3.8; score = 3.8 / 2 = 1.9
```

Weights are normalized to sum to 1.0, and **the normalization is shown** — the worksheet prints
both what was entered and what was used, so a rescale is never something you have to reverse
engineer.

### Scales

| | Range | What the bottom of the scale means |
|---|---|---|
| Expected effect (quality / security / delivery) | 0–5 | **0 is a real estimate**: assessed, and expected to have no effect. |
| Implementation complexity | 1–5 | **There is no 0.** "No effort" is not a real estimate, and accepting one would divide an item straight to the top of the list. A submitted 0 is refused by name. |
| No estimate supplied | — | **UNKNOWN.** Not 0. Not a pass. Not a bottom rank. |

---

## The hard requirement: a missing estimate is never a zero

This is the part worth reviewing, because it is the part that is easy to claim and easy to get
silently wrong. Four mechanisms, each with tests behind it.

**1. UNKNOWN is a sentinel object, not a magic number.** `_Unknown` has no arithmetic. If any
future edit tries to multiply an unestimated value by a weight, Python raises a `TypeError` at
that line instead of contributing a quiet zero. This is not theoretical — it caught a real bug
during development of this file, where a zero-weight dimension was still being read inside the
benefit sum. Had UNKNOWN been `0` or a coerced `None`, that bug would have shipped and scored
unestimated work as though somebody had assessed it.

**2. An item whose ranking depends on an unknown is removed from the ranking.** Not scored 0,
which would bury a potentially urgent recommendation at the bottom. Not scored at the maximum,
which would inflate it. It goes into a separate `NEEDS_ESTIMATE` bucket, **unranked**, with the
blocking field named (`effects.security`, `complexity`, …).

**3. Unranked items carry a bound, not a score.** For each one, the worksheet reports what the
score *could* be if the missing value turned out to sit anywhere in its admissible range, and
uses it to answer the only question that matters about a gap:

- `DECISION_BLOCKING` — the upper bound reaches or exceeds the current top score. This item could
  lead the list. The ranking is **not decidable** until somebody estimates it.
- `NOT_DECISION_BLOCKING` — the upper bound is below the top score. The estimate is still missing
  and the item is still unranked, but filling it in cannot change who goes first.

That distinction is what stops "we have unknowns" from being either ignored or treated as a
blanket excuse. In the synthetic set, two gaps are decision-blocking and one is not.

**4. Materiality is weight-dependent, and the gap is reported either way.** An unknown in a
dimension the active weights give *zero* weight cannot change that ranking, so the item stays
ranked — but the record still carries `non_material_unknowns`, so the gap never disappears from
the output. Give that dimension any weight and the same item moves into the needs-estimate
bucket. The crossover sweep shows this happening at an exact weight:

```
security weight 0.01 -- REC-SYN-RIS-DEP-001 leaves the ranked list
security weight 1.00 -- REC-SYN-ESS-AI-001 enters the ranked list
```

**And in the CSV, where this usually goes wrong.** A blank rank cell sorts as 0 in most
spreadsheet tools, and a blank score reads as nothing-to-see. Both are refused: an unranked row
gets the literal `NOT_RANKED` in the rank column and `UNKNOWN` in the score and benefit columns,
plus a populated `blocked_by`. A test asserts that no unranked row ever carries `""` or `"0"` in
the rank column, and that the row count is preserved — gaps are never dropped to tidy the table.

---

## Sensitivity analysis

Two kinds, both computed rather than asserted.

**Named scenarios.** Re-ranks under each weighting in `fixtures/weight-scenarios.json` and
reports a rank-stability table: best rank, worst rank, spread, and a label — `PINNED` (same rank
everywhere), `MOVES`, `ENTERS_UNKNOWN_BUCKET` (ranked under some weightings, blocked under
others), `NEVER_RANKED`. It also reports whether the leader changes at all. On the synthetic set:

```
top_item_stable = False
baseline / security-led / equal  ->  REC-SYN-IAM-DEP-001 leads
delivery-led / quality-led       ->  REC-SYN-ESS-SD-001 leads
```

with the plain-language reading the tool prints itself: *"this ranking is an argument about
priorities, not a measurement, and the weight vector has to be agreed before the order means
anything."* If the leader had been stable, it would say that instead — there is no false drama,
and a test covers the insensitive case.

**Continuous crossover sweep.** Walks one dimension's weight from 0.0 to 1.0 while holding the
other dimensions in their base proportion, and reports the exact weight at which the order
changes. On the synthetic set, sweeping `security` over 100 steps finds 17 order changes, of
which the headline is:

```
security weight 0.29 -- REC-SYN-ESS-SD-001 gives way to REC-SYN-IAM-DEP-001
```

The baseline weighting uses `security = 0.40`, which sits above that crossover — which is *why*
the security item leads at baseline. Move that single assumption eleven points and the top of
the list is a different recommendation. The test pins this to 0.29 against a hand-solved
crossover (the two benefit lines cross at w = 0.28, so the first step where the new leader is
strictly ahead is 0.29).

---

## Ties

Equal scores **share a rank** — standard competition ranking, so `1, 2, 3, 4, 4, 6`. The
consumed position is skipped rather than quietly reused.

Every tie group is reported with the inputs that produced it, so the tie can be *understood*
rather than just observed. The synthetic set contains a deliberate tie at rank 4 between two
recommendations that arrive at the same score from completely different estimates:

| id | benefit | complexity | Q | S | D |
|---|---:|---:|---:|---:|---:|
| `REC-SYN-ESS-SEC-001` | 3.0 | 3 | 0 | 5 | 4 |
| `REC-SYN-RIS-SD-001` | 3.0 | 3 | 3 | 3 | 3 |

The worksheet then **computes what would separate them** rather than declaring the tie
arbitrary: it probes each single-dimension corner weighting and reports the result, e.g. *"weight
quality alone and they separate (REC-SYN-ESS-SEC-001 0.0, REC-SYN-RIS-SD-001 1.0)."* Where no
corner separates a tie, it says so, and says the tiebreak has to come from something this
worksheet does not carry — sequencing, owner availability, a dependency.

Display order inside a tie group is by `recommendation_id`, purely so the output is byte-stable.
Every tied record is flagged `display_order_is_not_priority = true`, and a test shuffles the
input to prove position never leaks into rank.

---

## What the synthetic set demonstrates

Eleven fictional recommendations, with IDs shaped to match the evidence register in
`../uiowa_rfq_18649_workshare/methodology/23-synthetic-evidence-register.csv`
(`REC-SYN-{GROUP}-{AREA}-{NNN}` citing `FND-SYN-*`) so the two can be read together.

**A strength:** `REC-SYN-ESS-SD-001` is estimated on every dimension and stays in the top two
under five of six weightings — a recommendation you can defend regardless of which priority
argument wins.

**Real gaps, of three different kinds:**
- `REC-SYN-IAM-SD-001` — strong effects, **complexity never estimated** because whether the vendor
  connector supports a scripted release is itself unknown. Unranked, `DECISION_BLOCKING`: its
  ceiling (4.25) is well above the current leader (1.9).
- `REC-SYN-ESS-AI-001` — **quality effect never estimated**, because what assistive code
  generation is doing to ESS code quality is precisely what the recommended inventory would find
  out. Entering a number there would be inventing the answer. `DECISION_BLOCKING`.
- `REC-SYN-RIS-DEP-001` — **security effect never estimated**, `NOT_DECISION_BLOCKING`. Still
  missing, still unranked, but its ceiling (0.7125) cannot reach the top.

**A real zero that must not be confused with a gap:** `REC-SYN-RIS-SEC-001` records
`delivery = 0` with the basis *"the review runs outside the release path."* That is an assessment,
and it is scored. Under the security-only stress weighting, `REC-SYN-ESS-DEP-001` scores exactly
`0.0` and **stays in the ranked list** — visibly a result, not an absence.

**A traceability gap:** `REC-SYN-IAM-AI-001` carries no `finding_ids`. It ranks normally, because
the arithmetic does not depend on provenance, and is reported in its own section — a
recommendation that cannot be traced back to a finding is not defensible in a report whatever it
scores.

---

## University inputs still UNKNOWN

Everything that would make this a real prioritization rather than a working calculator:

- **The weights.** Nobody at the University has set them. The six scenarios are illustrative
  starting points for that conversation, not proposals.
- **The recommendation set itself.** These eleven are fiction. Real ones come out of the
  assessment.
- **Every effect estimate.** Whether a given change would actually help quality, security or
  delivery, and by how much, is a judgment that needs the people who run the systems.
- **Every complexity estimate.** Effort depends on staffing, existing tooling, vendor constraints
  and contention with other work — none of which is known here.
- **Whether the 0–5 scales and the `benefit / complexity` form are the right model at all.** They
  are legible and checkable, which is why they were chosen; they are not the only defensible
  choice. A worked example makes the choice arguable, which is the point.
- **Who decides**, and whether ties get broken at all or are deliberately run in parallel.

---

## Files

```
prioritize.py                              the calculator and CLI
test_prioritize.py                         48 tests
fixtures/synthetic-recommendations.json    11 fictional recommendations
fixtures/weight-scenarios.json             6 weightings (assumptions, editable)
examples/baseline-worksheet.md             generated readable worksheet
examples/baseline-ranked.csv               generated ranked table
examples/baseline-full.json                generated machine-readable bundle
DATA_DICTIONARY.md                         every field and scale, with 0 vs UNKNOWN spelled out
```

---

Built by seat OP5-CINDER (Claude Opus 5) for work order UIOWA-084.
