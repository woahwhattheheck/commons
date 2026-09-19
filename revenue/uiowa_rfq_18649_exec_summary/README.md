# UIOWA-081 — Leadership executive-summary template

Work order **UIOWA-081**. Built by seat **OP5-QUARRY** (Claude Opus 5).

The order's bar is *every statement traceable to a finding*. A template with a
"cite your evidence" note in the margin meets that bar on paper and fails it in
practice, because nothing checks. So this is not a template. **It is a compiler.**

A statement is authored as text bound to finding IDs. It reaches the rendered
document only if it survives every check below. A statement that fails is not
silently softened or quietly dropped — it goes to the compile report with the reason
and the specific remedy. The author fixes the sentence; the tool does not fix it for
them.

---

## Run it

Python 3 standard library only. No installs, no network.

```bash
cd revenue/uiowa_rfq_18649_exec_summary

python3 build_summary.py                    # compile the summary into out/
python3 -m unittest -v test_exec_summary    # 42 tests
```

`build_summary.py` is deterministic and **exits non-zero** when an assertable
SIGNIFICANT or CRITICAL finding is cited by no accepted statement. On the shipped
fixtures it exits `1`, on purpose — see *Coverage* below.

### Generated into `out/`

| File | Reader |
|---|---|
| `executive_summary.md` | Leadership. Accepted statements only, each with its finding IDs. |
| `traceability_matrix.csv` | A reviewer challenging a sentence: statement → finding → basis → evidence locator → collection date. |
| `compile_report.md` | The author. Every rejection with its reason and remedy, plus coverage. |
| `compile_result.json` | Machine-readable compile result. |

Three outputs because they have three different readers. Collapsing them is how
traceability dies — the appendix nobody opens.

---

## The seven checks

| Code | Catches |
|---|---|
| `NO_CITATION` | The sentence cites nothing. |
| `UNKNOWN_FINDING` | It cites an ID that is not in the findings store. |
| `ASSERTS_NOT_ESTABLISHED` | Its evidence cannot support an assertion at all. |
| `OVERCLAIM` | Its phrasing claims more than its weakest citation carries. |
| `SCOPE_OVERREACH` | It generalizes past the units the findings were established in. |
| `UNSUPPORTED_NUMBER` | It contains a figure that appears in none of its citations. |
| `INDIVIDUAL_ATTRIBUTION` | It evaluates a person rather than a workflow or a system. |

**`OVERCLAIM` is the one that earns the build.** An unsourced sentence is obvious and
any reviewer catches it. A sentence with a *real* citation that says more than the
citation supports looks like diligence, and reads as settled fact to a reader who
will never open the appendix. That is the failure mode that survives review, and it
is the one an unchecked template cannot touch.

### How strength is derived

`evidence.py` computes a **maximum assertable strength** per finding from four
inputs a reviewer can re-derive by hand — basis, confidence, corroborating sources,
and how many evidence items are actually attached:

| Strength | What phrasing it permits |
|---|---|
| `SETTLED` | Stated as fact, unhedged. |
| `INDICATED` | Must be hedged and scoped: "evidence indicates", "in the units reviewed". |
| `SINGLE_SOURCE` | Must be attributed: "one unit reported". Never generalized. |
| `NOT_ESTABLISHED` | **May not be asserted at all.** May only be named as an open question. |

`summary.py` reads the *claimed* strength off the sentence's own phrasing and compares
it to the *supported* strength. Three rules hold this together:

1. **UNKNOWN confidence and NOT_ESTABLISHED basis both collapse to `NOT_ESTABLISHED`.**
   An unresolved finding does not become a weaker yes. Hedging does not rescue it
   either — there is a test for exactly that attempt.
2. **A finding with no evidence attached is `NOT_ESTABLISHED`,** whatever its declared
   basis and confidence. A basis and a confidence with nothing behind them is an
   assertion wearing a finding's clothes.
3. **A statement is capped by its weakest citation.** Citing a settled finding
   alongside a single-source one does not launder the weak one.

### Scope, made checkable

Each finding records `units_established` of `units_in_scope`. A universal phrasing
("across the institution", "all units") is only permitted when every cited finding was
established across full scope. **An `UNKNOWN` scope is never universal** — "we did not
count" must not read as "we counted all of them".

---

## Real output on the fixtures

The shipped draft is seeded on purpose with the failure modes the compiler exists to
catch. A clean draft would demonstrate nothing.

```
Statements: 4 accepted, 8 rejected, of 12 drafted
  REJECT S-002  OVERCLAIM
  REJECT S-003  SCOPE_OVERREACH
  REJECT S-004  UNKNOWN_FINDING
  REJECT S-005  NO_CITATION
  REJECT S-006  ASSERTS_NOT_ESTABLISHED
  REJECT S-007  UNSUPPORTED_NUMBER
  REJECT S-010  INDIVIDUAL_ATTRIBUTION
  REJECT S-011  OVERCLAIM

Findings rejected at load: F-007-MALFORMED

Coverage: 4/6 findings cited by an accepted statement
  F-003 (CRITICAL) NOT ASSERTABLE - belongs in open questions
  F-005 (CRITICAL) ASSERTABLE BUT UNCITED

FAIL: 1 assertable SIGNIFICANT/CRITICAL finding(s) are missing from the summary: F-005
```

Three pairs in that output are the whole design:

- **`S-002` rejected, `S-008` accepted.** Same subject, same citation. The first states
  it as fact; the second attributes it to the one unit that reported it.
- **`S-003` rejected, `S-009` accepted.** Same subject, same citation, both correctly
  hedged. The first says "all units"; the second says "in the 2 of 5 units reviewed".
- **`S-007` rejected, `S-013` accepted.** Same subject, same citation. The first says
  42%; the finding says 31%.

In each pair the rejected version is the one that would have shipped.

### Coverage — the quiet failure

An executive summary fails in two directions, and reviewers only watch one. The
overstated sentence gets argued about. **The dropped finding gets nothing**, because
nobody reviews an absence.

So the compile report splits uncited findings by *why* they are uncited:

- **`F-005` — assertable but uncited.** A CRITICAL finding (corrective actions
  recorded at closure in 4 of 5 units, with no mechanism tracking whether the action
  was completed) that is fully supported and appears nowhere in the summary. Either a
  deliberate editorial choice or a finding that fell out unnoticed — and the tool
  cannot tell which, so it fails the build and makes a human say.
- **`F-003` — not assertable, correctly absent.** A CRITICAL finding with `UNKNOWN`
  confidence and no evidence. It *cannot* be summarized. It appears in the
  open-questions section instead, which is exactly where it belongs.

Those are two very different facts and a raw "2 findings uncited" count would have
hidden both.

---

## Fictional fixtures

Everything in `data/` is **FICTIONAL**. Cedar Hollow Regional Authority does not
exist. There are **no University of Iowa data, findings, systems or measurements** in
this lane.

The register demonstrates both a strength and a gap: `F-001` and `F-006` are
well-evidenced, corroborated and full-scope, and state cleanly; `F-002` is a real
observation that only one unit supports; `F-003` is carried with `UNKNOWN` confidence
and no evidence *so that the gap stays visible* rather than being summarized away;
`F-007-MALFORMED` is a hostile-input probe whose severity value is outside the
declared vocabulary.

**A malformed finding is rejected at load and named. It is never repaired with
defaults** — a repaired finding becomes citable, and a statement would then rest on a
record the tool invented. There is a test asserting the rejected ID cannot be cited.

---

## What is real vs. draft

**Real and runnable now**

- All seven checks, each exercised by the fixture draft and asserted individually
  (42 passing tests).
- The evidence lattice, including its three collapse rules and its refusal of a
  missing confidence value.
- Load-time rejection of malformed findings, and the proof that a rejected finding
  cannot be cited.
- Coverage reporting split by assertability, wired to the build's exit code.
- Deterministic rendering of all four artifacts.

**Draft / judgement, meant to be argued with**

- The lattice thresholds (what combination reaches `SETTLED`) are a defensible first
  cut. They are deliberately conservative and deliberately simple so a reviewer can
  re-derive any verdict by hand — otherwise the tool becomes the authority instead of
  the evidence.
- The phrasing marker lists (hedges, attributions, universal quantifiers) are
  English-surface heuristics. They catch the common forms; a determined author can
  phrase around them. **This is a check on ordinary drafting, not an adversarial
  filter**, and the README says so rather than implying a guarantee.
- `INDIVIDUAL_ATTRIBUTION` is **narrow by design**. It matches evaluative language
  about people; it does not attempt general name detection, because a broad name
  matcher produces false positives on unit and system names and gets switched off
  within a week — which is worse than a narrow check people trust.

---

## University inputs still UNKNOWN

1. The real assessment areas and their names.
2. How many units are in scope, and their identifiers.
3. The basis and confidence conventions the engagement will actually use — the six
   basis values and four confidence values here are a proposal.
4. Whether leadership wants the open-questions section in the summary itself or in an
   appendix.
5. Severity vocabulary and who assigns it.
6. Whether an assertable SIGNIFICANT/CRITICAL finding may ever be deliberately
   excluded from the summary, and who signs that off.

---

## What this lane does not do

No real University findings, no live data, no network calls, no outreach, no
scheduling. No maturity scores, certification claims, or peer-percentile comparisons.
**No individual performance scoring** — that is not just avoided, it is a check that
rejects the statement. Unresolved evidence stays UNKNOWN and renders as UNKNOWN: a
leadership summary that rounds an unknown into a reassurance is the specific failure
this lane is built against.

## File map

```
evidence.py          basis/confidence lattice -> maximum assertable strength
findings.py          Finding, EvidenceItem, store, loader with load-time rejection
summary.py           Statement, claim detection, the seven checks, compilation
render.py            executive summary, traceability matrix, compile report
build_summary.py     deterministic CLI; non-zero exit on a dropped serious finding
data/findings.json   FICTIONAL findings register (+ one malformed probe)
data/draft_statements.json  FICTIONAL draft, seeded with every failure mode
test_exec_summary.py 42 unittest cases
```

---

## Runner contract

This lane emits a `KIT-STATUS` line and exits by the four-code contract in
`revenue/uiowa_rfq_18649_exit_signals/contract.py`:
`0 CLEAN` / `1 FINDINGS` / `2 INPUT_ERROR` / `3 INDETERMINATE`.

`kit_status.py` here is a six-line local emitter. It does **not** import the other
lane, deliberately: lanes in this kit are independently runnable and a cross-lane
import would break that. The line format is the interface.

Real output from `python3 build_summary.py`:

```
KIT-STATUS: code=1 status=FINDINGS tool=build_summary findings=10 indeterminate=1 note=8 statement(s) rejected, 1 serious finding(s) missing, 1 not-established finding(s)
```

`INDETERMINATE` outranks `CLEAN` in the precedence order, so unresolved evidence can
never be reported as a clean run.
