# Evidence window agreement — does a claim's period match its evidence dates?

A finding says *"over the last 90 days, 3 of 14 deployments were rolled back"*
and every record it cites falls inside a single week. The count is right, the
citation resolves, the arithmetic is sound, and the sentence still describes
ninety days of behaviour on the strength of four.

This checks the dimension the rest of a report-checking kit does not: **when**.

All fixtures are **synthetic fiction**. No University of Iowa record appears in
this directory.

## Rules

| code | severity | fires when |
|---|---|---|
| `WINDOW_NOT_COVERED` | error | evidence spans less than `min_coverage` of the stated window |
| `SINGLE_DATE_SUPPORTS_A_PERIOD` | error | every cited record shares one date but the claim describes a period |
| `EVIDENCE_OUTSIDE_WINDOW` | error | cited records fall outside the window they are said to support |
| `STALE_EVIDENCE_FOR_PRESENT_TENSE` | error | a present-tense claim whose newest evidence is past the freshness horizon |
| `EVIDENCE_AFTER_ASOF` | error | a record dated later than the assessment date |
| `WINDOW_ENDS_AFTER_ASOF` | error | the stated window runs past the assessment date |
| `WINDOW_INVERTED` | error | the window ends before it starts |
| `PARTIAL_WINDOW` | error | only one end of the window is stated |
| `UNDATED_EVIDENCE` | error | a cited record has no date — not assumed in-window |
| `EVIDENCE_NOT_FOUND` | error | a cited record is not in the evidence set |
| `NO_EVIDENCE_CITED` | error | a time-bounded claim citing nothing |

Every finding proposes the restatement. Real output:

```
[error] WINDOW_NOT_COVERED  C-SYN-001
    the claim describes 90 days but its evidence spans 4 (4% of the window),
    2026-07-08..2026-07-11
    say instead: state the period actually observed: 2026-07-08 to 2026-07-11

[error] STALE_EVIDENCE_FOR_PRESENT_TENSE  C-SYN-002
    this is written in the present tense but its most recent evidence is 582
    days old at the assessment date, past the 180-day freshness horizon
    say instead: write it in the past tense and name the date: as of
    2025-02-14, ...
```

## Calibration, asserted by test

- **A past-tense dated statement does not go stale.** `STALE_EVIDENCE_FOR_PRESENT_TENSE`
  fires only on present-tense claims — "services *are* monitored" rests on the
  evidence being current, "in February 2025 they *were*" does not.
- **One bad record is one finding.** A record dated after `as_of` is withdrawn
  from the window analysis instead of also being reported as out-of-window and
  as a single-date support.
- **`SINGLE_DATE_SUPPORTS_A_PERIOD` supersedes `WINDOW_NOT_COVERED`** for the
  same reason.
- **An undated record is never assumed in-window**, and its claim gets no
  coverage verdict at all rather than an optimistic one.
- **A claim with no stated window is left alone.** This kit has nothing to say
  about an untimed statement.

## Run it

```bash
python3 check_window.py --claims fixtures/claims_UNSOUND.json   # 12 errors, exit 1
python3 check_window.py --claims fixtures/claims_SOUND.json     # 0 errors,  exit 0
python3 -m unittest test_window -v
```

Saved output: `out/report_UNSOUND.txt`, `out/report_SOUND.txt`,
`out/report_UNSOUND.json`.

## Determinism

The assessment date comes from the input's `as_of` and is **required** — the
loader refuses input without it. The system clock is never consulted, so the
same input gives the same answer on any day. A static tripwire in the test suite
checks this against the parsed module (and is labelled as a tripwire rather than
as behavioural coverage).

## What is real and what is draft

**Real and runnable:** the loader and its refusals, all eleven rules, the
coverage and freshness arithmetic, the restatement generator, the CLI, 24 tests
passing normal and `python -O`.

**Draft / illustrative:** both claim sets. They exist to exercise the rules.

## University inputs still UNKNOWN

- the real dates on every piece of evidence the engagement collects — an undated
  record cannot be placed in or out of any window and stays UNKNOWN;
- the observation window each finding is actually meant to describe;
- the engagement's freshness horizon (`freshness_days`, default 180) and minimum
  window coverage (`min_coverage`, default 60%), both of which belong to the
  engagement rather than to this tool;
- the assessment `as_of` date.

## Scope boundary

Read-only. It rewrites nothing, scores nothing, and produces no maturity,
certification, compliance or peer-percentile claim. It makes no judgement about
any person. It does not normalise timestamps and does not track source-version
change; it consumes dates that are already normalised.
