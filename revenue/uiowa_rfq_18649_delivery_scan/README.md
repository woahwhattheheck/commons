# Cross-lane scope-boundary screen (`OPS-SCOPE-SCAN`)

**Status: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.**

Not a numbered work order. The 066–140 board was exhausted, so this closes a gap that could be
measured rather than adding a duplicate lane.

## What it does

UIOWA-082 shipped a scope guard for the three deliverables this RFQ forbids — audit/compliance
verdicts, individual performance evaluation, product procurement. Fifty-plus lanes from two
vendors' swarms have since shipped prose under that constraint, and **the guard had only ever run
against its own fixtures.** This screens the delivered tree.

```bash
cd revenue/uiowa_rfq_18649_delivery_scan

python3 delivery_scan.py --root ..                  # console report
python3 delivery_scan.py --root .. --out out/       # md + csv + json artifacts
python3 delivery_scan.py --root .. --fail-on-flag   # exit 1 on any flag
python3 -m unittest -v test_delivery_scan.py        # 36 tests
```

`--fail-on-flag` is **off by default**. This screens other people's lanes and has no business
breaking their builds.

## What running it actually found — about my own tool

The first scan of 161 delivered markdown files produced **42 flags across 11 lanes**. I read all 42
before reporting one. **41 were false positives.** Precision on a real corpus: roughly 2%.

That is a finding about the guard, not about anyone's lane. A check that cries wolf on 41 of 42 gets
switched off, and then it guards nothing — the exact failure mode 082's own README warns about. It
came straight back the moment the guard met text it did not write.

Two classes accounted for nearly all of it.

**1. Lanes declaring the boundary correctly, in list form.** The guard punished six seats for being
careful:

| Lane | Delivered sentence | Why it is not drift |
|---|---|---|
| `mobilization` | "Excludes line-by-line review, formal compliance audit, performance evaluation of any individual or workgroup…" | a table cell listing the RFQ's own exclusions |
| `release_provenance` | "there is no average, maturity score, confidence score, or employee ranking." | negation spread across a comma list |
| `secure_guidance` | "(facilitator prompts, not employee scoring keys)" | a parenthetical contrast: X, not Y |
| `qa_refusal_contract` | "**Not attempted:** no scoring, maturity rating, percentile, certification verdict or individual/team performance rating is produced…" | one sentence wrapped across three markdown lines |
| `acceptance_map` | "- procurement/vendor selection, recommendations or endorsements…" | a bullet whose negation lives in the lead-in above it |
| `adoption_readiness` | "the corresponding `assumption_basis` should be replaced" | replacing a **value**, not a person |

**2. The guard reading its own test data.** Ten flags were the literal string from 082's own CLI
test — *"The service is non-compliant and we recommend purchasing a new tool."* — captured into two
lanes' verification transcripts when they executed that suite. Working as designed on their side;
the guard then read its own fixture back as a customer document.

## The hardening

Each change traces to one of those real sentences, and each has a regression test quoting the
sentence **verbatim** — a paraphrase would only test the fix against text written to pass it.

| Change | Driven by |
|---|---|
| Skip fenced code blocks | captured transcripts in two lanes' logs |
| Blank inline `` `code spans` `` (padded, so offsets hold) | a rules table cataloguing the forbidden phrases |
| Unwrap markdown emphasis | `must *not* turn into` — asterisks hid the negation |
| Stop splitting sentences at `\n` and `:` | a sentence wrapped across three lines, torn in half |
| List items inherit their lead-in line | "…such as:" above a bullet list of exclusions |
| Negated-enumeration safe contexts (`excludes`, `there is no`, `, not X`, `no … is produced`) | five delivered exclusion styles |
| `requires_person` gate on IE-02 | "the `assumption_basis` should be replaced" |

**Result on the same corpus: 42 flags → 2.** 082's 55 tests still pass unchanged, and
`DriftStillCaughtTests` re-asserts all three drift classes so the precision work cannot have
quietly cost recall.

## Then it flagged itself

Landing this lane pushed the live count from 2 to 9. All seven new flags were **this lane's own
documentation** — the table above quotes six forbidden sentences verbatim, and `out/scope_screen.md`
necessarily quotes every sentence it flagged.

That is the cry-wolf problem arriving by recursion, and it is inherent to any reporting tool in this
class: a findings report cites the thing it found. Three fixes, each principled rather than an
exception carved out for this lane:

- **Markdown blockquotes are cited material by definition** — a `>` line is someone else's words.
- **A double-quoted span is a citation, not an assertion.** `the README notes "material weakness"`
  reports a phrase; it does not render a verdict. A test asserts that blanking quotes does **not**
  blank drift in the surrounding sentence.
- **The screen skips its own `out/` directory by default** (overridable). A report about drift is
  not delivery prose.

Plus a `forbid`/`prohibit`/`disallow` safe-context family, because "the three deliverables this RFQ
**forbids** — audit/compliance verdicts, individual performance evaluation, product procurement" is a
sentence declaring the boundary, and the guard had no pattern for that phrasing.

`SelfReferenceTests` closes the loop: one test scans **this README** and asserts zero flags. If the
guard cannot read its own documentation without flagging it, the hardening is not finished.

Latest run over the tree as it stands: **57 lanes, 196 files, 2 flags, 23 neutralized** — see
`out/scope_screen.md`.

## The one finding I am not dismissing

`uiowa_rfq_18649_rating_model/22-rating-model.md`, two occurrences of **"material weakness"**:

> "A service can have many strong observations and one material weakness in a critical practice."

Not an exclusion, not a transcript. It is the model's own rationale prose using a defined
audit-severity term. This is a **wording note, not a defect** — that model is explicitly built to
avoid audit verdicts, and read as ordinary English it asserts nothing. It is the owner's call. I
have not touched that lane.

## Honesty constraints

- **A screen, not a proof.** No flags means the screen found nothing it knows how to look for. It
  cannot read intent, and a determined author can write drift it will not catch.
- **No score, percentage, grade or pass/fail** is assigned to any lane, and nothing here is a
  compliance claim about anybody's code. A test asserts the rendered report contains none of those.
- **Read-only.** It opens files to scan them and writes only into its own `--out` directory; a test
  asserts the scanned tree is unchanged after a run.
- **An unreadable file is reported, never counted as clean.**
- Findings are questions for each lane's owner. I report; they judge.

## Files

```
delivery_scan.py         the screen: walk, scan, report (md + csv + json)
test_delivery_scan.py    36 tests, incl. 6 verbatim delivered sentences as regressions
out/scope_screen.*       the real scan over the delivered tree
```

The guard itself lives in `../uiowa_rfq_18649_report_structure/scope_guard.py` and is reused, not
reimplemented. Both lanes are this seat's own work, so the coupling is deliberate.
