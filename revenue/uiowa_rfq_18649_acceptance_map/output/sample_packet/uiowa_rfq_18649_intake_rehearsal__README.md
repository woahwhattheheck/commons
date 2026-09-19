# UIOWA-092 — intake-to-assessment integration rehearsal

**Everything in this directory is fictional.** The three groups, every document, every
number and every quotation were authored for this rehearsal. Nothing here is a
University of Iowa record, measurement, or finding, and nothing here may be presented
as one. That rule is enforced by a test, not just by this paragraph.

Built by seat `OP5-BASALT` (Claude, Opus 5) against work order UIOWA-092.

## What it does

Runs one synthetic engagement's evidence end to end and shows the workflow actually
working, rather than describing it:

```
declared sources ──▶ resolve bytes, digest, keep version + exact locator
                 ──▶ attach interview support (or refuse to)
                 ──▶ derive the twelve (group × area) cells
                 ──▶ export the assessment dataset as JSON + CSV + Markdown
```

The twelve cells are the three fictional groups (**ESS**, **RIS**, **IAM**) against the
RFQ's four assessment areas (**SD** software development, **SEC** security,
**DEP** deployment and operations, **AI** AI readiness).

## How to run it

Python 3 standard library only. No installs, no network, no clock.

```bash
cd revenue/uiowa_rfq_18649_intake_rehearsal

python3 rehearse_intake.py --collection sources --out artifacts     # run the rehearsal
python3 rehearse_intake.py --collection sources --out artifacts --check-digest
python3 -m unittest test_rehearsal                                   # 30 tests
```

Optional: merge an externally supplied collection (read-only; this lane never writes to it):

```bash
python3 rehearse_intake.py --collection sources --out artifacts \
    --extra-collection ../uiowa_rfq_18649_synthetic_collection
```

If that directory has no `evidence_manifest.json`, the run reports
`COLLECTION_UNAVAILABLE` and continues on its own corpus. It never fails silently and
never pretends the external evidence was there.

## Actual execution results

```
SYNTHETIC REHEARSAL OUTPUT - every organization, document, number and quotation below is fictional, authored for the UIOWA-092 integration rehearsal. Nothing here is a University of Iowa record, measurement, or finding.

collection      COLL-SYN-092-A (as of 2026-09-19)
sources         11/12 resolved
observations    16 accepted
interviews      5 excerpts, 4 contributing support
diagnostics     0 REJECT, 2 DEGRADE, 1 NOTE

twelve-cell matrix:
  ESS  SD   DEMONSTRATED_STRENGTH
  ESS  SEC  PARTIAL
  ESS  DEP  MIXED
  ESS  AI   UNKNOWN
  RIS  SD   OBSERVED_GAP
  RIS  SEC  MIXED
  RIS  DEP  OBSERVED_GAP
  RIS  AI   PARTIAL
  IAM  SD   CONFLICT
  IAM  SEC  DEMONSTRATED_STRENGTH
  IAM  DEP  UNKNOWN
  IAM  AI   PARTIAL

state tally: DEMONSTRATED_STRENGTH=2, OBSERVED_GAP=2, MIXED=2, CONFLICT=1, PARTIAL=3, UNKNOWN=2
artifacts written to artifacts/ (6 files + RUN_DIGEST.json)
```

```
REPRODUCIBLE: 6 artifacts match the recorded digests in artifacts/RUN_DIGEST.json
```

```
----------------------------------------------------------------------
Ran 30 tests in 0.083s

OK
```

## The two things this rehearsal is really testing

**1. A missing input never becomes a zero, a pass, or a score.**

Two cells read `UNKNOWN`, and they are not the same `UNKNOWN`:

| Cell | Why |
|---|---|
| `CELL-ESS-AI` | No evidence was supplied for this cell at all. |
| `CELL-IAM-DEP` | Evidence *was* identified — `SRC-SYN-IAM-05`, an IAM deployment log — and it is deliberately absent from disk. The request went unanswered. |

`CELL-IAM-DEP` is the interesting one. The missing file raises `SRC_MISSING`, the
observation citing it degrades to `OBS_UNRESOLVED_SOURCE`, and the cell lands on
`UNKNOWN` — **not** `OBSERVED_GAP`. The interview excerpt attached to it says only
*"we can pull the deployment log, I just have not had a chance to export it yet"*; that
is classified `establishes: availability_only`, contributes **no** support, and raises
`INT_NO_CLAIM`. A promise to send a log is not partial evidence of what the log says.

A test deletes the bytes behind the one `DEMONSTRATED_STRENGTH` cell and asserts it
degrades to `PARTIAL` rather than staying a strength or flipping to a gap.

**2. A second operator gets the same bytes.**

Artifact construction is a pure function of the collection — no clock, no RNG, sorted
traversal, `sort_keys` JSON, explicit `\n` line endings — so `--check-digest` recomputes
every artifact and compares sha256 against the recorded `RUN_DIGEST.json`. Tests prove
the check is real: one asserts a copy of the collection at a different path produces
identical digests, another appends a row to a source file and asserts the check
**fails** (exit 1). A reproducibility check that cannot fail is decoration.

## Observable handling of malformed input

24 reason codes at three severities. `REJECT` excludes the record from the matrix,
`DEGRADE` retains it with reduced evidentiary capability, `NOTE` affects how a reader
should read it. **Nothing is ever discarded silently** — every diagnostic row carries the
record id, the locator and the effect. Covered by tests: dangling source citations,
dangling interview attachments, duplicate ids, missing required fields, unknown
group/area/direction, digest mismatch, path escape outside the collection root,
unparseable manifest, and count assertions whose arithmetic does not hold.

## Internal consistency is executable

Observations may declare a `count_assertion` (`numerator`/`denominator`/`whole`, or
`parts`/`whole`). `check_count_assertion` rejects a numerator above its denominator or
parts that do not sum to the whole; a failing assertion is suppressed and its
observation can no longer demonstrate a strength. One test cross-checks a fixture's
prose against the actual bytes of the file it cites (the IAM recertification campaign:
71 + 19 + 8 + 4 = 102, read back out of the CSV).

## Files

| Path | What it is |
|---|---|
| `rehearse_intake.py` | The pipeline and CLI. |
| `intake_schema.py` | Vocabularies, the 24 diagnostic reason codes, and the cell-state rules. Read this to see *why* a cell says what it says. |
| `test_rehearsal.py` | 30 unittest cases, including the hostile ones. |
| `sources/source-register.json` | Declared sources: id, group, type, path, version, capture date, represented period, locator kind. |
| `sources/{ess,ris,iam}/` | The synthetic evidence artifacts themselves — real bytes on disk, real digests. |
| `sources/analyst/observations.json` | Analyst observation records citing sources by id + locator. |
| `sources/analyst/interview-excerpts.json` | Synthetic interview excerpts. No real person was interviewed. |
| `artifacts/` | Output of the committed run: dataset JSON, three CSVs, the Markdown report, and the digest manifest. |

CSV artifacts carry the synthetic label as a `#` comment on line 1. Consumers should
skip `#` lines — `rehearse_intake.read_csv_artifact()` is the reader contract, and a
test asserts the banner never breaks parsing.

## Working vs. draft

**Working and tested:** the pipeline, the twelve-cell derivation, the diagnostic set,
the count-assertion consistency check, the reproducibility check, all exports, and the
synthetic collection.

**Draft / deliberately narrow:**
- The cell-state rules are a defensible reading of evidence strength, not an agreed
  methodology. They are in one readable module precisely so an assessor can argue with
  them and change them.
- The `--extra-collection` adapter expects `evidence_manifest.json` with
  `sources` / `observations` / `interview_excerpts`. That shape is this lane's guess
  until a collection lands to reconcile against. Field-name reconciliation across lanes
  is UIOWA-098's job, not this one's.
- The corpus is one rehearsal's worth of evidence, sized to exercise the paths — not a
  volume or performance benchmark.

## University inputs still UNKNOWN

- Which real University applications, platforms and shared services are in RFQ scope,
  and who owns each lifecycle stage — **UNKNOWN**.
- Which real records the University can release as evidence, in what form, and under
  what retention constraint — **UNKNOWN**.
- Which roles are available for interview, and in what window — **UNKNOWN**.
- Whether these four assessment areas map onto the University's own internal division
  of work — **UNKNOWN**.
- Every quantity in this package is fictional. No real deployment count, account count,
  finding count or release count has been observed — **UNKNOWN**.

## Out of scope by construction

No maturity score, rating, percentile, certification or compliance verdict is produced
anywhere in this package, and no individual's performance is assessed. A test greps the
exported dataset for scoring language and fails if any appears.
