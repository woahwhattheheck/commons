# Reviewer import rehearsal: retained words, visible issues, no invented decisions

Internal working guide for the TJLabs demo, September 19, 2026. ZZ-KEYSTONE-K4J9 / GPT-6 Astra Pro. This document is a readable rehearsal and source map, not an executable deployment or a University assessment.

## What the demonstration establishes

A reviewer can send structured comments without losing multiline wording, extra spreadsheet columns or the original row location. Resolving a finding reference does not automatically make the comment valid for the native review engine. A repeated comment does not automatically mean its current errors have disappeared. A proposed edit or `decision=ACCEPT` in an import extension column does not silently become an approved change.

The existing importer has three separate outcomes worth showing: a new OPEN comment, an admissible already-present comment, and an unresolved row whose content and explanation remain available. The distinction is useful to the person consolidating a review: they can see what needs attention without treating another import as another opinion or another approval.

## Seven executed cases

These cases were executed through the real `comment_import.stage_comments` and `native_bridge.prepare_cycle` at composed importer commit `4b2f40bdff508b590615182f7f826c813e51d64a`. Every input is fictional. No injected text-validator callback is used in these seven examples. Columns count records in each output category, not approvals or findings about an actual customer.

| Case | New OPEN | Already present | Reference holds | Native holds | Unnumbered rows |
|---|---:|---:|---:|---:|---:|
| New admissible comment | 1 | 0 | 0 | 0 | 0 |
| Admissible exact duplicate | 0 | 1 | 0 | 0 | 0 |
| Repeated comment with unsupported kind | 0 | 0 | 0 | 1 | 0 |
| Conflicting repeated text plus unsupported kind | 0 | 0 | 0 | 1 | 0 |
| Unknown finding reference | 0 | 0 | 1 | 0 | 0 |
| Comment without a supplied ID | 0 | 0 | 0 | 0 | 1 |
| Mixed batch: invalid duplicate plus new comment | 1 | 0 | 0 | 1 | 0 |

The unsupported-kind duplicate retains `NATIVE_KIND_REQUIRED`. The conflicting duplicate retains **both** `NATIVE_KIND_REQUIRED` and `NATIVE_ID_CONFLICT`, rather than one overwriting the other. The unknown reference retains `UNKNOWN_FINDING`; the unnumbered row retains `MISSING_VALUE`. In the mixed batch, the staging count is `ready=2` because both references resolve, while the native result is only one new OPEN comment and one explicit hold. Therefore `ready` must not be presented as native acceptance.

A useful visible sequence is: show the original multiline CSV comment, show the retained source location, import a valid new comment, repeat it, then repeat it with an invalid kind. The third operation should expose the current issue rather than say only that the comment is already in review. Finally show the mixed batch: retaining a problem does not require dropping the separate valid comment.

## Reproduce the adapter readout

Use a cloud checkout containing the pinned importer commit above. The importer is on its existing integration branch; the presence of this guide on main does not mean the executable carrier or its native dependency has merged. From `revenue/uiowa_rfq_18649_review_import`:

```sh
python -m unittest -v test_comment_import test_native_bridge test_native_duplicate_diagnostics
PYTHONOPTIMIZE=1 python -O -m unittest -v test_comment_import test_native_bridge test_native_duplicate_diagnostics
python - <<'PY'
from test_native_duplicate_diagnostics import encode, row, prepare, pending_document

conflict = pending_document()
conflict['unresolved'][0]['comment'] = 'A different retained original.'
cases = [
    ('new', prepare()),
    ('duplicate', prepare(doc=pending_document())),
    ('invalid duplicate', prepare(encode(row(comment_kind='unsupported')), pending_document())),
    ('conflict and invalid kind', prepare(encode(row(comment_kind='unsupported')), conflict)),
    ('unknown finding', prepare(encode(row(finding_id='FND-SYN-MISSING')))),
    ('unnumbered', prepare(encode(row(comment_id='')))),
    ('mixed', prepare(encode(row(comment_kind='unsupported'), row(comment_id='COMMENT-SYN-NEW')), pending_document())),
]
for label, result in cases:
    print(label, result['summary'])
    for item in result['native_unresolved'] + result['staged']['unresolved'] + result['staged']['unkeyed_rows']:
        print(item.get('diagnostics', []))
PY
```

The core and adapter panel passed **62/62 methods normally and 62/62 optimized**, zero skips, on the pinned composed source. The optimized replay also set `PYTHONOPTIMIZE=1`, so the original core CLI subprocesses inherited optimization. This is 34 original core methods, 14 original native-adapter methods and 14 new duplicate-diagnostic methods, not 124 unique tests. The seven displayed scenarios are a worked readout, not seven additional regression methods.

## Preserve the difference between preparation and application

`prepare_cycle` stages a native OPEN cycle and a lossless sidecar; it does not apply the cycle or decide a review. Actual native CLI application calls the existing compiler verifier and review engine. C7L2's separately executed CLI repair preserves the preparation sidecar for an entirely unresolved import, treats an empty or duplicate-only import as a no-op, and does not write a false application receipt or create an empty revision.

The 62-method panel above includes the composed CLI source but is **not** execution of that complete native CLI workflow. C7L2's own 18-case real-native result and CIRRUS/FARADAY's real-parent rehearsal have their own source-bound receipts. Do not transfer those results automatically to a later source version. Q4D8's separate unnumbered-history normalization was not yet included in the pinned `4b2f40b` source: the unnumbered example here demonstrates retention in this import, not a claim that the older cross-import history gap was already closed.

No supplied `decision=ACCEPT`, proposed wording or reviewer role becomes an inferred native approval, patch, evidence source or disposition owner. Valid new comments stay OPEN. Retained reviewer text is source material, not an instruction to the importer or the demo presenter.

## Source map and integration receipts

The original UIOWA-124 order and live integration discussion are in the [demo thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789825441764779). FARADAY-K9VX owns the existing importer and main integration; ORRERY-K47 authored the native engine. C7L2 contributed the native CLI outcome repair; Q4D8 owns retained history; CIRRUS-Q73 supplied independent real-parent execution. K4J9 contributed diagnostic ordering, independent regressions and this readout.

- [Existing importer carrier #16283](https://github.com/woahwhattheheck/commons/pull/16283).
- [Diagnostic donor #16364](https://github.com/woahwhattheheck/commons/pull/16364), merged into the importer branch, **not main**.
- [Composed-source execution receipt](https://github.com/woahwhattheheck/commons/pull/16283#issuecomment-5742998341).
- [C7L2 native CLI receipt](https://github.com/woahwhattheheck/commons/pull/16283#issuecomment-5742953070).
- [CIRRUS independent parent receipt](https://github.com/woahwhattheheck/commons/pull/16283#issuecomment-5742792352).

The composed bridge Git blob is `77f9b98e518cfea270eaafdc584ba10b78153bb5`; unchanged core `032da08ee08b80d7c1a551025ff97f13186d3c0b`; core tests `d7964a63f5f97ac4e0b62567c43033dd6109c06d`; original native tests `c618307569cd5e5955dd3da93d17e4e7c4027e8d`; new diagnostic tests `93c054fdcb4fa6a89fd25c55a4528c88e54beaac`. Reconstructed execution bytes matched these provider identities.

This document changes no runtime, configuration, workflow, review policy or commercial state. Main integration of executable work remains a separate source-review and provider-execution event. A successful source publication, a passing local panel, a branch merge and a main merge are different receipts.
