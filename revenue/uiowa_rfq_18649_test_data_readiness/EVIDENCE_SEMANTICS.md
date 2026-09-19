# UIOWA-047: evidence-time and coverage operator rehearsal

**FICTIONAL REHEARSAL — NOT UNIVERSITY FINDINGS.** This is an internal, source-bound
worked result for the existing test-data readiness kit. It does not inspect a
University system, establish compliance, certify a dataset or authorize a change.

The executable repair is published in [PR #16397](https://github.com/woahwhattheheck/commons/pull/16397),
source commit [`650d258693f0d479bf17d12fc0eb2abb31631dd8`](https://github.com/woahwhattheheck/commons/commit/650d258693f0d479bf17d12fc0eb2abb31631dd8).
**Publication of this document is not a claim that that executable PR has merged.**
Its current integration state belongs to the PR. The results below describe those
exact source bytes, not whatever a later `main` happens to contain.

Original instrument: ZZ-Sol / [#16122](https://github.com/woahwhattheheck/commons/pull/16122).
Repair and execution: ZZ-KESTREL-R9C4 / GPT-6 Astra Pro.
Earlier cleanup, catalog-input and ASTRA-FORGE discovery work is retained unchanged.
Operation: `uiowa047-evidence-semantics-kestrelr9c4-20260919`.
Defect and implementation record: [#16367](https://github.com/woahwhattheheck/commons/issues/16367).

## What the operator needs to distinguish

A date after the assessment does not establish that an activity was completed at
the assessment date. A September 20 refresh cannot establish September 19
freshness. The record may describe a plan, an incorrect date or later work; this
kit does not choose which explanation is true. It returns **UNKNOWN**, preserves
the chronology in the explanation, and asks for a contemporaneous source or a
source-supported correction. It does not turn that uncertainty into an assertion
that the underlying practice failed.

Likewise, an absent covered-case inventory and an explicitly supplied empty
inventory are different observations. With a documented requirement for case
`empty`, no supplied inventory leaves coverage **UNKNOWN**. An explicit `[]`
records no covered cases and exposes an **OBSERVED_GAP** against that requirement.
Neither input is silently rewritten into the other.

Coverage must be documented as lists of nonblank string identities. A string is
not a list of observed cases, a dictionary's keys are not observed coverage, and
integer `1` is not string `"1"`. Malformed evidence remains **UNKNOWN** rather than
being coerced into a favorable result or crashing the report. Valid duplicate
identities count once. Case, spacing within an identity and Unicode representation
are not silently normalized to make two different identifiers agree.

These are rules for interpreting the supplied catalog, not authentication of its
claims. An `EVIDENCED` result still means that the supplied record supports the
particular check under the declared field contract.

## Twelve-record worked result

All dates and records in this section are fictional. Assessment date:
**September 19, 2026**. The fixture is
[`fixtures/evidence_semantics.synthetic.json`](https://github.com/woahwhattheheck/commons/blob/650d258693f0d479bf17d12fc0eb2abb31631dd8/revenue/uiowa_rfq_18649_test_data_readiness/fixtures/evidence_semantics.synthetic.json).

The before column is from separate single-record executions of original assessor
blob `f9361019d8e5522663a3b229bdd985c86e4e5ab6`. It is not a fabricated successful
whole-catalog baseline: the nested-entry record makes the original full catalog
raise `TypeError`. The repaired full catalog completes and retains all twelve
records. Each row below is checked against its actual executed result.

| Dataset | Check | Before | Repaired | What the reviewer should do |
| --- | --- | --- | --- | --- |
| SYN-FUTURE | refresh_freshness | EVIDENCED | UNKNOWN | Obtain refresh evidence on or before September 19, or resolve the September 20 date from its source. |
| SYN-FUTURE | cleanup | EVIDENCED | UNKNOWN | Obtain contemporaneous verification; a later date is not an earlier completion. |
| SYN-OMITTED | representativeness | OBSERVED_GAP | UNKNOWN | Request the missing covered-case inventory; do not assume it was empty. |
| SYN-NULL | representativeness | OBSERVED_GAP | UNKNOWN | Resolve the unknown inventory; null does not mean no cases covered. |
| SYN-EMPTY | representativeness | OBSERVED_GAP | OBSERVED_GAP | The explicitly empty inventory lacks documented case `empty`; review or add that case. |
| SYN-STRING | representativeness | EVIDENCED | UNKNOWN | Correct the string-shaped inventory; the character `a` is not a case record. |
| SYN-MAPPING | representativeness | EVIDENCED | UNKNOWN | Correct the mapping-shaped inventory; a key with value false is not proof of coverage. |
| SYN-NONSTRING | representativeness | EVIDENCED | UNKNOWN | Resolve integer-versus-string case identity without silent conversion. |
| SYN-NESTED | representativeness | TypeError | UNKNOWN | Correct the nested object in the covered list; the record remains visible in the repaired report. |
| SYN-CURRENT | refresh_freshness | EVIDENCED | EVIDENCED | Same-day refresh is valid evidence for this calendar-date check. |
| SYN-CURRENT | cleanup | EVIDENCED | EVIDENCED | Explicitly required cleanup has a same-day verification record. |
| SYN-CURRENT | representativeness | EVIDENCED | EVIDENCED | Both unique cases are covered; the repeated `a` does not inflate the count. |
| SYN-CADENCE | refresh_freshness | EVIDENCED | EVIDENCED | Age one day equals the declared one-day cadence; it is not overdue. |
| SYN-STALE | refresh_freshness | OBSERVED_GAP | OBSERVED_GAP | Age two days exceeds the declared one-day cadence; investigate representativeness. |
| SYN-NOT-REQUIRED | cleanup | EVIDENCED | EVIDENCED | Explicit false declares non-applicability; an irrelevant date does not invent a cleanup requirement. |

The complete repaired output has **84 checks: 17 EVIDENCED, 2 OBSERVED_GAP and
65 UNKNOWN**. These are counts of fixture checks, not a maturity score, success
rate, risk ranking or an estimate of any University population. Many fields are
intentionally omitted so their uncertainty remains visible.

Example rendered explanations from the actual repaired report:

> Last refresh 2026-09-20 is after assessment date 2026-09-19; it does not evidence refresh as of that date.

> No valid covered boundary-case inventory is supplied.

> Missing boundary cases: empty

The last two explanations belong to different records and require different
follow-up. Do not replace either with a generic failure marker.

## Reproduce the workflow

Use an isolated checkout of source commit `650d258693f0d479bf17d12fc0eb2abb31631dd8`,
not a mutable branch inferred to contain it. The following commands were exercised
from `revenue/uiowa_rfq_18649_test_data_readiness/`; substitute `python` for
`python3` where that is the installed Python command.

```sh
python3 -B -m unittest discover -v
python3 -O -B -m unittest discover -v
python3 -B test_data_assessor.py fixtures/evidence_semantics.synthetic.json --format json
python3 -B test_data_assessor.py fixtures/evidence_semantics.synthetic.json --format markdown
```

For a file result, add `--output` with a new, deliberately chosen destination.
The existing CLI writes that destination; do not aim it at a retained input or
unrelated existing file. Exit code 0 means a report was generated, not that every
check was evidenced. Invalid catalog structures still produce the existing
readable exit-code-2 error before report emission.

The source/fixture references above are internal engineering evidence links, not
a customer delivery or commercial destination. No command contacts a University
system or schedules an activity. The assessment date is an input, not a clock
claim or appointment.

## Executed verification and boundaries

Execution used the existing cloud CPython **3.13.5** sandbox. Because that sandbox
had no outbound DNS, the component was assembled from native GitHub reads and
verified with Git's blob identity calculation before execution. This was a sparse
component reconstruction, not a full repository checkout or hosted Actions run.

The original retained suite passed **40 tests** before the change. The new suite
was then executed against the original assessor:

```text
Ran 24 tests in 1.414s
FAILED (failures=1504, errors=6)
```

Those are failed assertions/subtests across the bounded input grids, not 1,504
independent product defects. The retained negative controls distinguish real
regressions from a check that merely accepts everything.

After the repair, component-root discovery executed the retained 40 plus the new
24 tests, with no skips:

```text
python -B -m unittest discover -v
Ran 64 tests in 11.895s
OK

python -O -B -m unittest discover -v
Ran 64 tests in 31.041s
OK
```

The date grids cover **2,932 cases**: all integer ages from -366 through +366 at
cadences 1, 30 and 365, plus the corresponding cleanup-date grid. Other tests cover
missing/null/empty/non-list inventories, invalid elements, exact identity,
duplicate/order stability, cleanup applicability, input immutability and actual
CLI JSON/Markdown results. The twelve-record expected-state map is authored in
the test, not regenerated from the output it checks.

The first optimized invocation hit the outer tool's 25-second timeout and is not
counted as a pass. The complete retry above finished. Nonfatal sandbox terminal
cleanup noise (`TERM environment variable not set`) appeared outside the suite
conclusion. The timings are observations, not performance guarantees.

Both real CLI formats were executed normally and with `-O`. Repeated stdout and
file results matched byte-for-byte, and the input stayed unchanged. Output
SHA-256 identities:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| JSON | 25353 | `5a8e5bb7149c153a6cdff7c7d4d4c6a15607bd52d9b0763cfc54f2a649982055` |
| Markdown | 14945 | `276c0fe3eb8af4a8e80d0f673ba13d2a79e2b2d8e50223f81bf0e8ae2d49dd6d` |

The original ESS/RIS/IAM fixture produces the same structured report before and
after this repair. Existing cleanup-declaration, exact-date, catalog-shape,
boolean-duration and non-vacuous-discovery behavior is preserved.

## Source bindings

All three native published Git blob IDs matched the executed local bytes:

| Changed path | Git blob |
| --- | --- |
| `test_data_assessor.py` | `9def5e7e260d19d11e5fbb85b41d74a655cefcd7` |
| `tests/test_evidence_semantics.py` | `0aad60223a765e63b08478fe5653231d654928cd` |
| `fixtures/evidence_semantics.synthetic.json` | `267ecb0d84a72da67e0bd869ed6636d86e5f18a3` |

Retained execution inputs, unchanged from the read baseline:

| Retained path | Git blob |
| --- | --- |
| `tests/test_assessor.py` | `024a958a6921422509d0afc5153adf0f1d0e2214` |
| `tests/test_catalog_input.py` | `db103d178723db78222dea48992988c664a7ec76` |
| `tests/test_cleanup_evidence.py` | `7e9ad0d7dcdc63f6ed48e31c4b068c9074d1b0b4` |
| `tests/__init__.py` | `cfff474a68b49059957ceb7ce1afe205576d7cd3` |
| `test_discovery.py` | `8531e9d1ee2118e0b4c5b438c2fbcee44b6651f0` |
| `fixtures/catalog.synthetic.json` | `214a0e4b42d13d02a49e9a5a8b0a8c63962e7a1a` |

No full-repository, operating-system matrix, hosted CI, independent-review or
main-integration success is inferred from these component results. A dated
catalog remains supplied evidence, not independently authenticated completeness.
The executable PR retains its own review and integration requirements; this
worked document can be reviewed separately without changing runtime behavior.
