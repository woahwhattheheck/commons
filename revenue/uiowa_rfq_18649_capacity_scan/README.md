# OPS-PERF-SCAN — delivery-kit performance hotspot scan

A read-only AST scanner that looks across every delivered UIOWA lane for the two
performance defects **measured** under UIOWA-095, plus two related shapes.

Built by seat **OP5-OBSIDIAN** (Claude Opus 5) for RFQ 18649. Companion to
`revenue/uiowa_rfq_18649_capacity_benchmark/`.

## Why this exists

UIOWA-095 measured two real defects in already-shipped lane tools — an
accidental quadratic in `validate_trace.py` (22.55x) and a whole-file read to
inspect 500 characters in `validate_collection.py` (4.15x). Fleet rules kept
that lane from editing files it does not own, so the finding was **one lane
deep**: nobody had looked for the same shapes anywhere else in a kit that is now
55 lanes. A bottleneck found once and never looked for again is a bottleneck you
ship everywhere else.

## The headline result

**Outside the two lanes where these defects were already known and measured, the
scan found no new instance of either one.** The kit does not have the quadratic
scattered through it. That is the actual finding, and it is a good one — this
scan was built expecting to find more and did not.

What it *did* surface is a third, lower-magnitude shape: **15 instances of
order-preserving dedup written as `seen = []` + `if x not in seen`**, which is
O(n²) in the list length. Real, cheap to fix (keep a set alongside the list),
and **magnitude UNKNOWN** — it depends on list sizes this scanner cannot see.

Full results: `results/KIT_SCAN_REPORT.md` and `results/kit_scan_results.json`,
from a real scan of the live kit at the timestamp recorded in them.

## How to run it

Python 3 standard library only. No pip installs, no network.

```bash
cd revenue/uiowa_rfq_18649_capacity_scan

python3 -m unittest discover -v                          # tests

python3 scan_kit.py --revenue ../ --out results          # every UIOWA lane
python3 scan_hotspots.py <any-directory>                 # one tree
```

`--revenue` points at the repo's `revenue/` directory. Output goes only to
`--out`.

## What a finding means — and what it does not

Every finding carries a `confidence` and a `measured_cost`.

| Confidence | Meaning |
|---|---|
| `CONFIRMED_SHAPE` | The AST match is unambiguous — the code really does do the thing described. Whether it **matters here** depends on input sizes the scanner cannot see. |
| `CANDIDATE` | Suggestive, but the scanner cannot establish it from source alone. Needs a human look. |

`measured_cost` is a real figure **only** for the two patterns UIOWA-095
actually measured, and it cites the report those numbers came from. For every
other pattern it is the string `UNKNOWN`. A pattern match is not a measurement,
and converting one into the other is the same move as turning a missing input
into a zero.

## Precision: why this scanner was rewritten twice

The first version flagged any in-loop membership test whose container was not
visibly a set. Against the delivered kit it produced **131 matches, nearly all
of them ordinary `if key in some_dict` lookups** — code that is already O(1) and
entirely correct. A detector that is ~92% noise is worse than no detector: it
buries the real findings, and it reads as an accusation against three dozen
lanes that did nothing wrong.

It also had two outright bugs, both found by calibrating against real code
rather than against test snippets:

- **`for line in path.read_text().splitlines()`** was reported as a read on
  every iteration. A loop's iterable is evaluated *once*, before the body; the
  visitor was walking it inside the loop frame.
- **`with open(p) as fh: fh.read()`** inside a loop was reported as re-reading
  one file. Reading a *different* file each pass is the normal, correct way to
  do that; the visitor was not tracking names bound inside the loop body.

Measured effect of the rewrites on the same kit:

| Version | Matches | Comment |
|---|---:|---|
| v1 — any non-set membership | 174 | unusable; 131 of them O(1) dict lookups |
| v2 — narrowed to string/list containers, loop bugs fixed | 63 → 28 | P3 fell from 40 to 2 |
| v3 — substring scan restricted to file-derived text | **25** | shipped |

The v3 narrowing came from reading the eight remaining substring matches in
their real source. Every one was a test against a *short, bounded* string — a
filename, a CSV token, one joined spreadsheet row. The measured defect needs a
**large** string, and the only strings a source-only scanner can be confident
are large are the ones that came off disk. So `STR_CALLS` is deliberately narrow
and the scanner accepts a false negative rather than a false accusation.

Each of those false positives now has a named regression test in
`TestPrecision`.

## Known limits

- **Source-only.** It cannot see input sizes, so a `CONFIRMED_SHAPE` hit is not
  automatically a problem, and it will miss a real defect whose string arrives
  across a function boundary (an annotated `str` parameter is reported, but only
  at `CANDIDATE`).
- **`P3_same_file_reread_in_loop` found nothing real.** Its 2 remaining matches
  are both correct chunked-read loops (`while` reading successive blocks). It is
  reported at `CANDIDATE`, it is **not** evidence of anything on its own, and it
  is kept only because withdrawing a check silently is worse than stating that
  it scored zero.
- **Point-in-time.** The kit is still growing; the lane count and timestamp in
  the results say what was actually scanned.

## Guardrails

- **Read-only.** It reads other seats' lanes and writes nothing into them.
  There is a test (`test_scanner_never_writes_into_the_tree_it_scans`) that
  snapshots mtimes before and after and fails if anything changed.
- **Not a score.** Findings are listed by file so an owner can act on their own
  code. No lane, seat, or person is ranked; no quality metric is computed; the
  rendered report says so, and a test asserts that it says so.
- **Unscannable ≠ clean.** A file that cannot be read or parsed is reported with
  the reason and is never counted as passing. "We could not look" and "we looked
  and it was fine" are different claims.
- No certification, compliance, or peer-percentile claim. No individual scoring.
- No network at runtime; stdlib only.

## What's real vs. draft

**Real:** the scanner, the tests, and the committed scan results — those came
from an actual run over the live kit.

**Draft:** the remediation advice in each finding's `detail` is a suggestion to
the owning seat, not a change. **This lane edits nothing outside itself.** The
two measured defects live in lanes owned by other seats and are left alone; the
finding is reported for them to take or leave.

## University inputs still UNKNOWN

- The **real input sizes** every flagged site will see in the engagement. Without
  those, a structural match cannot be turned into a cost.
- Whether any flagged site is on a **hot path** at all.
- The **magnitude** of the 15 list-membership findings — list lengths were not
  measured, so their cost stays UNKNOWN rather than being guessed.
