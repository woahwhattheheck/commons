# Sample soundness — can this measure carry the claim made from it?

An assessment samples 12 change records, finds 7 with a single approval, and the
report says **"58.3% of changes receive a single approval."** Every step of that
is arithmetically correct and the sentence is wrong in three separate ways:

1. It implies a resolution of one tenth of a percentage point from data whose
   finest possible step is **8.33** points.
2. It states a rate where the honest statement is a count.
3. It describes the **population** when it measured a **convenience sample**.

None of this is caught by a citation checker (the citation resolves) or by an
arithmetic checker (the arithmetic is right).

All fixtures are **synthetic fiction**. No University of Iowa measurement
appears in this directory.

## Rules

| code | severity | fires when |
|---|---|---|
| `DENOMINATOR_TOO_SMALL` | error | a proportion from fewer than `--min-denominator` observations |
| `FALSE_PRECISION` | error / warning | reported precision finer than half the resolvable step; a decimal place is the error, a whole percent the warning |
| `PERCENTAGE_WITHOUT_DENOMINATOR` | error | a proportion with no denominator recorded |
| `EMPTY_DENOMINATOR` | error | denominator is 0 — no proportion exists |
| `NUMERATOR_UNKNOWN` | error | denominator recorded, numerator never was |
| `ZERO_OBSERVED_AS_ABSENCE` | error | 0 of n reported as absence |
| `SAMPLE_STATED_AS_POPULATION` | error | population phrasing over a convenience / self-selected / unknown sample |
| `MEDIAN_OF_TOO_FEW` | error | a median of fewer than 3 observations |
| `MEDIAN_OF_FEW` | warning | a median of 3–4 observations |
| `MEDIAN_WITHOUT_OBSERVATIONS` | error | a median with no underlying values |
| `COMPONENT_UNKNOWN` | error | a component was never recorded — not summed as zero |
| `COMPONENT_SUM_MISMATCH` | error | components do not reach the stated total |

### Every finding proposes the honest restatement

A checker that says "this is wrong" and stops has moved the work, not done it.
Real output:

```
[error] FALSE_PRECISION  M-SYN-001
    reported to 1 decimal place(s), implying a resolution of 0.1 percentage
    points, but 12 observations can only resolve steps of 8.33 points
    say instead: 7 of 12 (about 58%)

[error] ZERO_OBSERVED_AS_ABSENCE  M-SYN-004
    zero occurrences in 8 observations is not evidence that the rate is zero;
    it is consistent with a rate as high as about 37.5%
    say instead: 0 of 8 observed; consistent with an underlying rate up to
    about 37.5%
```

The 37.5% is the rule of three: with zero events in *n* trials the approximate
95% upper bound on the underlying rate is 3/*n*. It is the standard answer to
"we never saw it happen, so it doesn't happen."

### What the rules do not object to

Calibration matters more than coverage, so several rules are deliberately narrow
and are asserted by test:

- `SAMPLE_STATED_AS_POPULATION` fires on **convenience**, self-selected and
  unknown sampling. A **random** sample or a **census** may be stated about the
  population — the rule objects to unwarranted generalisation, not to all
  generalisation.
- Below `--min-denominator`, `DENOMINATOR_TOO_SMALL` **supersedes**
  `FALSE_PRECISION`. Two findings for one defect makes the counts untrustworthy.
- 58 of 100 at whole percent is clean.

## The before/after pair

```bash
python3 check_soundness.py --measures fixtures/measures_UNSOUND.json   # 10 error, 2 warning, exit 1
python3 check_soundness.py --measures fixtures/measures_SOUND.json     # 0 error,  0 warning, exit 0
python3 -m unittest test_soundness -v
```

Saved output: `out/report_UNSOUND.txt`, `out/report_SOUND.txt`,
`out/report_UNSOUND.json`.

## The thresholds are arguments, not laws

`--min-denominator` (default 8) is a **readability** judgement, not a statistical
one: "3 of 4" is honest and "75%" invites the reader to generalise. An engagement
is expected to set its own, and raising it is a supported operation:

```bash
python3 check_soundness.py --measures fixtures/measures_SOUND.json --min-denominator 200
```

reports measures that pass at the default. A test asserts this, so the threshold
cannot quietly become a law.

## What is real and what is draft

**Real and runnable:** the loader and its refusals, all twelve rules, the
resolvable-step and rule-of-three arithmetic, the restatement generator, the
CLI, 26 tests passing normal and `python -O`.

**Draft / illustrative:** both measure sets. They exist to exercise the rules.

## University inputs still UNKNOWN

- the actual sampling method behind every figure the engagement reports —
  without it, `sampling` defaults to `UNKNOWN`, which is treated as *not*
  licensing a population statement rather than as permission;
- real denominators for any measure the engagement intends to state as a rate;
- the raw observations behind any median;
- the engagement's own `--min-denominator` and whether `MEDIAN_OF_FEW` should be
  an error rather than a warning here.

## Scope boundary

Read-only. It rewrites nothing, scores nothing, and produces no maturity,
certification, compliance or peer-percentile claim. It makes no judgement about
any person. Deterministic: no clock, no RNG, sorted traversal.
