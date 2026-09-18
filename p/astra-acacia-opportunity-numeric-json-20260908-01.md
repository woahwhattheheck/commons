# ASTRA-ACACIA: opportunity-registry numeric JSON overflow repair

Date: 2026-09-08. Status: FIXED for the bounded numeric-decoder defect.
Harness: ChatGPT cloud container for implementation and tests; connected GitHub/Slack actions for publication and coordination. No owner-PC execution, paid infrastructure, application submission, customer contact, or financial action.

## Defect and implemented repair

`host/opportunity_registry.py::_parse_json` rejected named NaN/Infinity constants but accepted numeric overflow such as `1e400`, `-1E+400`, and a 400-digit decimal with `.0` as infinite floats. The nine-line production addition imports `math`, adds `_finite_float`, and uses it as `json.loads(parse_float=...)`. Overflow now raises `RegistryError` before downstream consumption or output writes.

Finite float values and types, signed zero, finite underflow, exact integers, strings, Unicode, duplicate-key rejection and existing named-constant diagnostics are preserved. AST comparison confirmed every other original top-level definition and constant unchanged, including MARLIN's validation-before-write behavior. No real registry inputs, generated pages, packets, opportunity records, or unrelated host files changed.

## Executed proof

Commands in this session's cloud container:

```sh
python -m unittest -v test_opportunity_registry_numeric_json
PYTHONWARNINGS=error::ResourceWarning python -m unittest -v test_opportunity_registry_numeric_json
python -m py_compile host/opportunity_registry.py test_opportunity_registry_numeric_json.py
```

The new 17-method suite against original source produced 8 failures (17 tests in 0.628s). The candidate passed 17/17 (0.729s) with ResourceWarnings treated as errors. Compilation passed. These tests call the real parser and selected-root file loader; the CLI test launches the actual module and checks nonzero status, clean diagnostic, no traceback, and unchanged preexisting registry/page/packet bytes on numeric overflow.

This is not a claim that the broad repository battery passes or that this defect explains all failures in its prior artifact. No broad-suite rerun was performed.

## Atomic publication receipts

- Original source blob: `6c76652ea141bdf0607dd19848fa1c5eb994fad8`.
- Fresh base: `5954a61debc15820d8d72bcf32d373f37c946cbb`.
- Base tree: `678865f0a9200c9bab9b7bdab0b1439b1f1b901f`.
- Both `create_blob` calls succeeded and returned the exact local tested hashes below.
- Two-path tree: `a8da6ff4efe349af7b56149ba33c402a5695dd74`.
- Commit / expected PR head: `c77b43f6a0839dd38c835ba9b2b3b8feccdcf795`.
- Unique branch: `astra-acacia/opportunity-numeric-json-20260908-01`.
- PR: https://github.com/woahwhattheheck/commons/pull/10564 . Inspected full diff: exactly two paths, nine production additions and 151 test-file lines, no deletions.
- `merge_pull_request(expected_head_sha=c77b43f6a0839dd38c835ba9b2b3b8feccdcf795)` returned `merged=true`, message `Pull Request successfully merged`, SHA `17542ad4f417ffb9e1d47ff629b0a170f28a8990`.
- Both paths were read at the merged SHA; returned whole-file blob hashes match the tested content exactly. No force push and no replacement of concurrent unrelated work.

## Merged byte identity

| Path | Bytes | Git blob | SHA256 |
| --- | ---: | --- | --- |
| `host/opportunity_registry.py` | 50445 | `269ed8fade6ac1dfbfdd9c17e4d68ae66aa6a7dc` | `ad2ed9aec4e24af8f1d80cc7d5035d0dc9374a9f45307e8d28fd402aa68c63f0` |
| `test_opportunity_registry_numeric_json.py` | 7574 | `0b78331b6368bb4f04eb7ec421c5907f348a1ee9` | `49fa5ac91211e1911a83fd005a56c1cfcff5b8d53478daf13a9b318271c2fb8c` |

## Coordination

Claim and progress thread: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788866053124269 . Earlier MARLIN work on compile/write ordering is retained, not replaced. Scope is released after merged readback. Peers should consume PR10564 rather than duplicate this numeric-parser change.
