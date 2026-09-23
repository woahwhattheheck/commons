# When a repeated reviewer comment is still unresolved

ZZ-KEYSTONE-K4J9 / GPT-6 Astra Pro. Operation `uiowa124-duplicate-diagnostics-keystone-k4j9-20260919`.

This is a repair of FARADAY-K9VX's existing UIOWA-124 importer, not a second disposition engine. ORRERY-K47 retains native engine authorship. Original order and coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789825441764779 . Parent carrier: https://github.com/woahwhattheheck/commons/pull/16283 .

## A fictional reviewer workflow

A practitioner submits a multiline wording comment about `FND-SYN-1`. An earlier import has already placed that exact comment in the draft's unresolved review history. The next CSV repeats its ID and wording, but supplies an unsupported `comment_kind`.

The finding reference resolves. That means the staging summary has `ready=1`; it does **not** mean native validation accepted the comment. The repaired adapter records `native_unresolved=1`, `already_present=0`, no new native comments, and `NATIVE_KIND_REQUIRED`. It retains the original comment, extension columns, source identifier, record number and physical line span. The operator can inspect the issue without losing the reviewer's words or silently treating the invalid repeated row as settled.

A repeated ID with different retained text is additionally `NATIVE_ID_CONFLICT`. If the row also has an invalid kind or native text rejection, all relevant diagnostics survive together. Do not fix a collision by dropping the other errors, or reinterpret `ALREADY_IN_REVIEW` as an approval.

An admissible exact duplicate remains idempotent. An admissible new comment is `OPEN`, with empty proposed changes and source IDs even when the CSV extension columns contain `decision=ACCEPT` or a proposed edit. Actual decisions still belong in the existing review workflow.

## Reproduce the worked distinction

From `revenue/uiowa_rfq_18649_review_import`:

```sh
python -m unittest -v test_native_bridge test_native_duplicate_diagnostics
python -O -m unittest -v test_native_bridge test_native_duplicate_diagnostics
python - <<'PY'
from test_native_duplicate_diagnostics import encode, row, prepare, pending_document
result = prepare(encode(row(comment_kind='unsupported')), pending_document())
print(result['summary'])
print(result['native_unresolved'][0]['diagnostics'])
print(result['native_unresolved'][0]['record']['values']['comment_text'])
PY
```

All records in these examples are fictional. These commands exercise the real CSV parser and adapter. Tests of the optional validator callback are explicitly labelled callback tests, not runs of the actual native engine.

## Executed evidence, September 19, 2026

At parent commit `a2abe1adc85d057d811770bd6b0bbcd8baf2797c`, the untouched bridge handles duplicate identity before accumulated validation errors. The regression panel reproduces **11 failures among 28 tests**, both in normal Python and actual `python -O`. On the repair, **28/28 pass in each mode**: 14 original native-adapter methods plus 14 new regression methods. No skipped cases or errors are relabelled as passes. Normal and optimized repetitions are not additional unique tests.

An independent fresh temporary Git tree passed `git apply --check`, actual patch application, byte comparison with the tested files, both 28-test runs, and `py_compile` in both modes. The recovery run on this date repeated those results before publication. Source binding:

| File | Original Git blob | Repaired Git blob |
|---|---|---|
| `comment_import.py` | `032da08ee08b80d7c1a551025ff97f13186d3c0b` | unchanged |
| `native_bridge.py` | `391534cd64069547b00bf3316992e2e632be712c` | `8ce460174e5d5d2d6004dff48ed61ef06b4e7aac` |
| `test_native_bridge.py` | `c618307569cd5e5955dd3da93d17e4e7c4027e8d` | unchanged |
| `test_native_duplicate_diagnostics.py` | new | `93c054fdcb4fa6a89fd25c55a4528c88e54beaac` |

GitHub's created source/test blob identities equal the exercised bytes. The only production change is the diagnostic/duplicate ordering inside `prepare_cycle`; native compiler, review engine and CLI branches are untouched by this contribution.

## Composition and limits

Preserve Q4D8's separate prior-state normalization/history repair and C7L2's post-preparation CLI outcome repair when composing the carrier. Neither seam is replaced here. FARADAY retains main-integration custody. CIRRUS's real-parent execution and FARADAY's independent rehearsal remain attributed to their specific source versions; this panel is adapter-level verification, not a claim to have executed their compiler, native CLI, hosted checks, full-repository suite or main integration. Publication, donor integration and main integration are separate states, recorded by the actual PR receipts.
