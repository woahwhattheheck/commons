# UIOWA-071 package composition repair

Builder: ZZ-KESTREL-47 / GPT-6 Astra Pro. Date: 2026-09-19.
Operation: `uiowa-071-import-repair-kestrel47-20260919`.
Integration owner: ZZ-HELIODORE-67, operation `uiowa-071-main-integration-heliodore67-20260919`.
Original inventory, instrument, fixtures and 43 tests: OP5-KELVIN.
Composition defect identification: OP5-IRONWOOD, with the earlier COPPERFIN-73 cross-lane import finding retained.
Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827502523019

## What changed

Package imports now resolve `schema`, `inventory` and `interview_guide` within this package. Direct-script execution and the original lane-local unittest command remain supported. An explicit `__package__` branch is used instead of catching `ImportError`: a missing package dependency must not silently fall back to an unrelated global module.

Only the import sites in `inventory.py`, `interview_guide.py` and `test_inventory.py` changed. A package initializer has no eager imports. Production writes no `sys.modules` aliases and changes no `sys.path` entries. The schema, fixture contents, interview questions, classifier, validation rules, report rendering and original 43 test bodies are unchanged.

A Python process composing lanes should use fully qualified package imports. Manually adding different lane directories to `sys.path` and importing each as bare `schema` is not a supported composition mechanism; direct scripts remain isolated interpreter entry points.

## Exact source and execution

Original snapshot: `e8602b7ba26d90ad02e4ebbeaabce618d258999b` on `claude/multi-agent-slack-demo-4ikzfs`. This snapshot is provenance, not an instruction to merge that shared branch.

Execution environment: ephemeral cloud Linux container, CPython 3.13.5. Not Bryce's computer, not a GitHub Actions run, and not hosted-green evidence. No network is used by the implementation or tests.

The executed original source and fixtures were reconstructed from native GitHub file reads, then checked against their Git blob hashes before execution. Original sample artifacts were regenerated and checked against the independently retrieved published sample tree hashes; all four matched. No fabricated or substituted fixture was used to make the original suite pass.

| File | Original Git blob | Tested repaired Git blob |
| --- | --- | --- |
| inventory.py | 76d79b9c778356f70a7f284075acba6ea573626e | 63b69064a871e54fc0eda806746eac747088328d |
| interview_guide.py | 0a0b90f4cfcf4421a95dd6669ea3ce3ba50caa82 | 8d29293e2adb6b795dbd9053a796fdf97d5a76c4 |
| test_inventory.py | 9976caef209ca44af25ca5f865612ecf6129babd | ba8235cb22717c3f02aaddc884f8e7334d69d78a |
| schema.py | 0a7dbf5873681a2d9f77199b3aad0ec9fbf2a3a4 | unchanged |
| test_package_imports.py | absent | b81bf1d9d489a3956a19ff93b0de3c5a8f744483 |
| __init__.py | absent | 7492aa62ce7bcb97d7953cf431590c9264407bf6 |
| fixtures/synthetic_ai_use.json | 42347c91fd9b6b3ce3e600487bd9a3d4632a83c9 | unchanged |
| fixtures/synthetic_ai_use_hostile.json | af9e0af5d0cc79abccb01e73e28084c89fe97ac6 | unchanged |

The four repaired executable/test blob hashes were returned unchanged by native `create_blob` publication, binding the executed bytes to the published objects.

### Original baseline, literal terminal summary

Command, from the original lane directory: `python -m unittest -v test_inventory`

```text
----------------------------------------------------------------------
Ran 43 tests in 1.193s

OK
```

Original package behavior with a synthetic unrelated module already in `sys.modules['schema']`:

```text
wrong_module_reused True
AttributeError: module 'schema' has no attribute 'validate_record'
```

The foreign module provides `UNKNOWN = 'FOREIGN-SCHEMA'`, so the package import itself succeeds with the wrong dependency; the actual inventory `build()` then fails. This is not merely a static naming concern.

### New regression suite against original production source

Place the new `test_package_imports.py` beside the original files, with both original fixtures and exact sample artifacts present. From repository root:

```sh
python -m unittest revenue.uiowa_rfq_18649_ai_use_inventory.test_package_imports
```

Literal summary:

```text
----------------------------------------------------------------------
Ran 12 tests in 21.359s

FAILED (failures=27)
```

The 27 are failed checks/subtests across 12 test methods, not 27 independent test methods.

### Repaired source, normal and optimized

From repository root:

```sh
python -m unittest revenue.uiowa_rfq_18649_ai_use_inventory.test_inventory revenue.uiowa_rfq_18649_ai_use_inventory.test_package_imports
python -O -m unittest revenue.uiowa_rfq_18649_ai_use_inventory.test_inventory revenue.uiowa_rfq_18649_ai_use_inventory.test_package_imports
```

Literal normal summary:

```text
.......................................................
----------------------------------------------------------------------
Ran 55 tests in 23.925s

OK
```

Literal optimized summary:

```text
.......................................................
----------------------------------------------------------------------
Ran 55 tests in 24.468s

OK
```

These totals are the 43 retained test methods plus 12 new methods. One new method also launches the original 43-test suite by package name; those nested executions are not added again to the headline 55. The new suite forwards the interpreter's actual optimization flag to its child processes and uses unittest assertions rather than removable `assert` statements. Its inline child probes check `sys.flags.optimize` explicitly. The original test bodies, including their historical subprocess invocation, were preserved.

## Regression coverage

The new suite exercises all six import orders in fresh interpreters, and all six with unrelated cached `schema`, `inventory` and `interview_guide` modules. It verifies dependency object identity, a real inventory build, unchanged foreign module dictionaries, no bare-module aliases and no search-path mutation. The lazy probe CLI is invoked with an unrelated cached inventory whose functions raise if called. Importing the original test module also uses scoped dependencies.

Both supplied fixtures run through both the direct inventory script and `python -m` entry point, comparing the actual four emitted artifact bytes. Both guide/probe entry points, direct scripts from unrelated working directories, malformed JSON and missing files are exercised. A missing package schema must raise rather than borrow a foreign bare schema.

In a separate actual original-versus-repaired execution, both fixtures generated byte-identical results:

```text
UNCHANGED_ORIGINAL_VS_REPAIRED synthetic_ai_use.json 52136 bytes in 4 artifacts
UNCHANGED_ORIGINAL_VS_REPAIRED synthetic_ai_use_hostile.json 53407 bytes in 4 artifacts
```

Total: 8 artifacts, 105,543 bytes. The clean fixture still reports `records=10 active=2 informal=4 planned=2 unsupported=1 unknown=1 gaps=19`. Unknown inputs and unsupported claims retain their original meanings.

## Standalone operator smoke commands

```sh
python revenue/uiowa_rfq_18649_ai_use_inventory/inventory.py --input revenue/uiowa_rfq_18649_ai_use_inventory/fixtures/synthetic_ai_use.json --print
python -m revenue.uiowa_rfq_18649_ai_use_inventory.inventory --input revenue/uiowa_rfq_18649_ai_use_inventory/fixtures/synthetic_ai_use.json --print
python -m revenue.uiowa_rfq_18649_ai_use_inventory.interview_guide --probes revenue/uiowa_rfq_18649_ai_use_inventory/fixtures/synthetic_ai_use_hostile.json
```

## Integration boundary and remaining limits

HELIODORE retains independent source review, actual sibling-lane composition and isolated current-main integration. This carrier changes only this lane; do not merge the entire shared Claude branch. Native PR/main receipts must be reported separately. No hosted workflow success or main merge is inferred from this local execution.

The composition sentinels model unrelated modules; this seat did not execute every sibling lane together. Windows and other Python versions were not run. This scoped import repair does not certify the pre-existing classifier against every malformed input, validate real University adoption, create real findings, or change any procurement or scheduling commitment. Every supplied record remains synthetic.
