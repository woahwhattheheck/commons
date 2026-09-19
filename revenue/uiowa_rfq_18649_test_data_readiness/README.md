# UIOWA-047 — Test-data readiness and maintenance

Offline, synthetic-only assessment kit for University of Iowa RFQ 18649 preparation.

The kit evaluates whether a supplied test-data catalog contains evidence about:

- accountable ownership;
- refresh timing and staleness;
- interface/schema alignment;
- documented boundary-case coverage;
- cleanup/retirement evidence;
- retention rules; and
- data origin/handling references.

It does **not** inspect live systems, ingest University data, determine regulatory compliance, or convert missing records into defects.

## Evidence states

The evaluator intentionally uses three states:

- **EVIDENCED** — the supplied record contains evidence for the check.
- **OBSERVED_GAP** — supplied evidence conflicts with the catalog's own documented expectation, such as a stale fixture against its declared cadence or a fixture interface version that differs from the recorded current version.
- **UNKNOWN** — evidence is absent or insufficient. Unknown is not treated as failure.

This separation is the core acceptance guardrail for the work order.

Cleanup applicability uses an explicit declaration: `cleanup_required: false`
records that cleanup is not required; `true` requires a recorded verification
date before that check is evidenced. An omitted, null or non-boolean flag is
`UNKNOWN`, not an implicit `false`, including when a verification date is
present. This is an evidence state, not a regulatory or operational verdict.

## Files

- `test_data_assessor.py` — deterministic standard-library CLI and library.
- `catalog_template.csv` — editable catalog starter.
- `schema/catalog.schema.json` — machine-readable field contract.
- `fixtures/catalog.synthetic.json` — explicitly fictional ESS/RIS/IAM rehearsal data.
- `fixture_specifications.md` — boundary-case specifications for the three fictional services.
- `refresh_lifecycle.md` — lifecycle and evidence diagram.
- `interview_guide.md` — discovery prompts tied to the catalog.
- `tests/test_assessor.py` — regression tests for evidence-state behavior.

## Run

From this directory:

```bash
python3 test_data_assessor.py fixtures/catalog.synthetic.json
python3 test_data_assessor.py fixtures/catalog.synthetic.json --format json --output report.json
python3 -m unittest -v tests/test_assessor.py
```

The default output is Markdown. JSON output preserves the same checks and evidence states for later report tooling.

## Test discovery

Run the full component suite from this directory:

```bash
python3 -m unittest discover -v
python3 -O -m unittest discover -v
```

`test_data_assessor.py` is the application, not a test suite, despite its
`test_` prefix. Do not classify the component by executing that module through
`unittest` alone. The behavioral tests live in `tests/test_assessor.py`;
`tests/__init__.py` makes that directory importable for component-root discovery.
The original direct test command above remains supported. To run only the
behavioral suite, use `python3 -m unittest discover -s tests -v`.

`test_discovery.py` stays at the component root and checks, in fresh normal and
optimized Python processes, that every retained behavioral case is collected
exactly once. Its negative control removes the behavioral test file only in a
temporary copy and verifies that the missing suite is detected. The checks use
standard-library `unittest` assertions, which remain active under `python3 -O`.
They neither change assessment behavior nor rewrite the source catalog.

Repair validation on Python 3.13.5: before the package marker, root discovery
collected zero tests while explicit `tests/` discovery passed seven. After this
repair, root discovery passed eleven tests (seven retained behavioral checks
plus four discovery checks) in both normal and optimized Python. This is local
execution evidence, not a hosted CI or whole-repository pass. Original UIOWA-047
implementation credit is unchanged; the discovery repair is by ZZ-ASTRA-FORGE.

## Synthetic rehearsal

The checked-in catalog contains three fictional fixtures:

1. **ESS-REGISTRATION-BOUNDARIES** — current, owned, aligned, and complete for its documented boundary set.
2. **RIS-AWARD-SYNC** — intentionally stale, on an older interface version, and missing two documented boundary cases.
3. **IAM-ROLE-TRANSITION** — current interface alignment but missing owner, refresh, cleanup-verification, and retention evidence; those conditions remain **UNKNOWN**. It also intentionally omits two documented boundary cases, which is an **OBSERVED_GAP** because the catalog itself establishes the expectation.

This lets reviewers see the difference between an evidenced mismatch and missing evidence without using real student, research, or identity data.

## Assessment use

During discovery, populate a copy of the catalog from supplied evidence. For each fixture or dataset:

1. establish purpose and service boundary;
2. record a role accountable for maintenance;
3. record the evidence-backed refresh trigger/cadence and last refresh;
4. bind the fixture to a known interface/schema version;
5. document the boundary cases that matter for the business behavior being tested;
6. capture cleanup and retention evidence; and
7. identify origin/handling context without copying sensitive values into this public repository.

A report writer should use evaluator output as a question/evidence organizer, not as an automatic University finding. Any finding still requires source citations, service context, and reviewer judgment.

## Public-repository boundary

All checked-in examples are fictional. Do not commit private University artifacts, production-derived records, credentials, student/research/identity data, or proprietary source extracts here.
