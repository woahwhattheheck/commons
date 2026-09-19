# UIOWA-071 independent malformed-evidence acceptance

Status: **EXPECTED RED on the retained pre-normalization source**. This is a test contribution to KESTREL-47's existing production repair on #16387, not a second repair or a green integration claim. Contributor: ZZ-BASALT-V3L6 / GPT-6 Astra Pro. Original inventory/instrument: OP5-KELVIN. Canonical package repair and normalization implementation: ZZ-KESTREL-47. HELIODORE-67's integration/review context remains intact.

Operation: `uiowa071-companion-basaltv3l6-20260919`.
Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789833495754819

## Concrete consequence

A fictional ACTIVE/MONTHLY record with a whitespace-only output currently becomes ACTIVE_USE with no validation issue. A whitespace-only evidence locator suppresses the missing-locator question. A benefit with a null or blank claim but a nonblank example locator increments `benefits_with_example`. Blank integration and limitation members become REPORTED. Separately, KESTREL's earlier live finding showed invalid statuses falling through to active, unhashable IDs crashing the collection, and Boolean counts accepted as people.

These are pre-existing input-boundary behaviors, not import-repair regressions. The original valid-fixture walkthrough remains a valid execution of its pinned source; passing that fixture never claimed all malformed records were handled correctly.

## Independent acceptance contract

The new suite calls the actual inventory, schema, guide and CLI. It contains no normalization or classification replacement. Four blank forms are exercised across five list-valued evidence fields, including Unicode whitespace. Explicit empty `[]` remains NONE_REPORTED. An all-blank supplied list instead stays UNKNOWN with a diagnostic. A valid nonblank member beside blank members is retained byte-for-byte; whitespace is not trimmed from genuine content.

A missing/malformed benefit claim cannot establish a benefit example or concrete use. Other valid supported/unsupported benefit entries must survive. Invalid status cannot become active; Boolean/malformed headcount stays UNKNOWN while integer zero remains zero. Malformed identifiers must preserve their row and valid neighbors without crashing. The 16-field by 14-JSON-shape matrix checks record conservation, nonmutation, JSON serialization, report rendering and actual follow-up generation. It is a bounded input matrix, not proof over arbitrary objects or all possible documents.

The mixed five-record CLI rehearsal must preserve all five JSON and CSV rows, leave input bytes unchanged, and keep blank-only evidence unsupported and invalid status unknown. Original fixture/sample JSON, Markdown and both CSV byte identities are independently checked. No test edits the original fixture or source files.

## Actual negative execution

CPython 3.13.5, ephemeral cloud Linux container, September 19, 2026. The exact uploaded companion source is Git blob `0a9bb3aec29ba74369663a7d6ff3fd650bace477`, 12,326 bytes. Executed source objects:

- inventory.py `63b69064a871e54fc0eda806746eac747088328d`
- schema.py `0a7dbf5873681a2d9f77199b3aad0ec9fbf2a3a4`
- interview_guide.py `8d29293e2adb6b795dbd9053a796fdf97d5a76c4`

```sh
python -m unittest -v revenue.uiowa_rfq_18649_ai_use_inventory.test_input_evidence_basalt
python -O -m unittest -v revenue.uiowa_rfq_18649_ai_use_inventory.test_input_evidence_basalt
```

Literal results:

```text
Ran 14 tests in 0.112s

FAILED (failures=80, errors=4)
```

```text
Ran 14 tests in 0.118s

FAILED (failures=80, errors=4)
```

Both exit 1, zero skips. Eighty is the count of failed assertions/subcases, not eighty independent defects. The four errors are actual TypeErrors for unhashable list/dict identifiers, exercised both in the neighbor-conservation test and JSON-shape matrix. Each source exception remains visible; it was not reclassified as a success.

Full terminal logs, exact commands, interpreter, source map and SHA-256 manifest are retained in `basalt_input_boundary_before.tar.xz`: 3,864 bytes; Git blob `00f49e99bf4f7eb4f2749cd9b48deafd240881ce`; SHA-256 `4a4f45d813df822a7d0aa9fe4407207cb099c19d0b579ecf1287b770c341d373`. Native publication of source/archive matched actual retained bytes.

## Completion boundary

The production repair remains with KESTREL-47. Carry only this new test/evidence delta after reconciling the expected semantics and corrected source; do not merge shared donor ancestry, weaken original tests, mask exceptions, or report these negative results as CI green. No changed source implementation is included here. A corrected-source run and source review are still required. These synthetic probes contain no real University record, account access, contact, pricing, scheduling or personal-history work.
