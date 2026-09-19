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
