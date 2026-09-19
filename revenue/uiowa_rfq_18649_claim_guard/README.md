# OPS-CLAIM-GUARD — cross-lane prohibited-claim and fiction-labelling guard

Reads every landed `uiowa_rfq_18649_*` lane and asks one question: does any
delivered file make a claim this engagement said it would not make?

**Python 3 standard library only. No network. Read-only. Deterministic.**

## Run it

```bash
cd revenue/uiowa_rfq_18649_claim_guard
python3 claim_guard.py --root ..                  # scan all sibling lanes
python3 claim_guard.py --root .. --out /tmp/out
python3 -m unittest test_claim_guard -v           # 37 tests
```

Real output from a scan of the landed tree:

```
scanned 65 lanes / 873 files under /home/user/commons/revenue
ASSERTION=50  REFUSAL=389  AMBIGUOUS=194
scanned tree unmodified: True
```

## The rules

| ID | Name | Catches |
|---|---|---|
| `CG-01` | `CERTIFICATION_CLAIM` | certified / compliant with / conformance / accredited |
| `CG-02` | `MATURITY_LEVEL` | maturity or readiness level, score, tier |
| `CG-03` | `PEER_COMPARISON` | percentile, benchmarked against peers, industry average |
| `CG-04` | `INDIVIDUAL_SCORING` | scoring or ranking a person rather than a role |
| `CG-05` | `REAL_UNIVERSITY_FINDING` | a statement about the real University as an observed finding |
| `CG-06` | `UNLABELLED_FICTION` | a lane carrying data fixtures with no file saying the data is invented |

`CG-06` is structural rather than textual. UNKNOWN-propagation is deliberately
not attempted here — another lane (`OPS-UNKNOWN-PROPAGATION`) covers it.

## Why this is not a word search

A lane that **refuses** a claim contains the same words as a lane that **makes**
one. `no maturity level, readiness level, or tier is computed` contains every
word a naive scanner looks for and is the opposite of a violation.

So every match gets one of three outcomes:

| Outcome | Meaning |
|---|---|
| `ASSERTION` | The clause reads as a statement of fact containing the prohibited concept. A **candidate finding for a person to confirm — not a proven violation.** |
| `REFUSAL` | The text names the rule in order to decline it. Positive evidence, not silence. |
| `AMBIGUOUS` | The classifier cannot tell. **UNKNOWN.** Listed for a person. Never auto-cleared. |

The third bucket is the point. A guard that resolves its own uncertainty in the
favourable direction manufactures confidence it does not have.

### How a negation is decided

A negation clears a claim only if it **governs** it:

- before the match — `no certification is claimed` → `REFUSAL`
- a verbal negation just after — `certification is not claimed` → `REFUSAL`
- a negation attached to a **different noun** — `the University of Iowa has no
  retention schedule` → **`ASSERTION`**, because the `no` negates the schedule,
  not the claim about the University

Markdown emphasis is stripped before matching. `**not** as a certification
checklist` is a refusal, but the marker `not ` never matches the literal text
`not**`.

Prose is joined into paragraphs before clause-splitting. A sentence wrapped
across two source lines would otherwise be cut in half and the half carrying
the negation lost.

A standalone number next to the match reads as a claim (`maturity level 4 of
5`) — but a digit inside an identifier does not, or the heading `## CG-01
certification` would read as a quantified claim.

## What this tool refuses to do

- **No lane is scored, graded, ranked or rated.** No compliance percentage, no
  per-lane verdict. Findings carry an exact `file:line` and the clause. A test
  asserts the summary contains no per-lane entry and no float.
- **AMBIGUOUS is never resolved automatically** toward clean.
- **Nothing in a scanned lane is modified.** Read-only, proved rather than
  promised: a test hashes the whole scanned tree before and after a full scan
  and asserts it is byte-identical, plus a test proving the digest can move.
- **Its own source and tests are excluded from pattern matching** — a rule
  table necessarily contains every prohibited phrase. The exclusion is printed
  in every output rather than left implicit, and a test asserts it is reported.

## `ASSERTION` is a candidate, not a verdict

The scan cannot tell a claim about the assessed organization from the same word
used as:

- a document name — `certified cost rate schedule`
- a contract mechanism — `conformance/cure protocol`
- an identifier — `check_conformance(port, POLICY)`
- a deliberately planted negative-control fixture in another lane's tests

So each finding carries a `context` field (`prose` / `code` / `data` / `test`)
and the summary breaks assertions down by it. Context is **reported, not
filtered** — nothing is dropped. It exists so a reader starts with `prose`
instead of abandoning the report.

In the scan above, of 50 `ASSERTION` findings: 25 `prose`, 11 `data`, 9 `test`,
5 `code`.

## The fixtures are a negative control

`fixtures/planted_assertions/` and `fixtures/planted_refusals/` use the **same
vocabulary** and mean the opposite in every case. A test asserts the shared
vocabulary, then asserts:

- every rule fires as `ASSERTION` in the assertion fixture
- zero `ASSERTION` findings appear in the refusal fixture
- no planted violation is wrongly cleared as `REFUSAL`

`fixtures/planted_unlabelled/` carries data with no fiction marker and must be
flagged by `CG-06` as `AMBIGUOUS`.

A zero-assertion scan means nothing on its own, so the summary says so
explicitly whenever the assertion count is zero.

## What the tests found

The test `test_no_per_lane_aggregate_exists` originally scanned the serialized
summary for the word `grade` and matched this tool's own refusal sentence,
*"no lane is scored, graded, ranked or rated."* That is exactly the failure
this module exists to catch — a refusal reading as a violation — and it has now
fired on the author's own tests in three consecutive lanes. It is checked
structurally now: field names and value shapes, never prose.

The scan's first run against the landed tree classified this author's own
UIOWA-074 line *"used as a reference, **not** as a certification checklist"* as
an `ASSERTION`. That is what produced the emphasis-stripping fix above. After
it, that lane reports zero assertions.

## UNKNOWN

- **Every `ASSERTION` and every `AMBIGUOUS` finding is unresolved.** 50 and 194
  respectively on the scan above. None has been confirmed or dismissed by a
  person. The tool produces candidates; it does not adjudicate them.
- **Whether an unlabelled-data lane is actually passing records off as real**
  cannot be determined from the files. `CG-06` flags, it does not conclude.
- **Rule coverage is not complete.** These six rules are the ones that could be
  detected with acceptable precision. Other engagement promises — that missing
  evidence stays UNKNOWN, that estimates are not silently zeroed — are not
  checked here.
- **Findings are not routed.** They are reported for the owning seat to act on.
  This lane edits nobody's files and opens no pull requests.

## Files

```
claim_guard.py                      rules, classifier, scanner, writers, CLI
test_claim_guard.py                 37 unittest cases
fixtures/planted_assertions/        deliberate violations (negative control)
fixtures/planted_refusals/          same words, opposite meaning
fixtures/planted_unlabelled/        data with no fiction label (CG-06)
sample/claim_findings.{csv,md,json} output of a real scan of the landed tree
```
