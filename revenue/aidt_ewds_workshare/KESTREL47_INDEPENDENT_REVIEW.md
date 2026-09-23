# Independent AIDT V2 runtime review

Reviewer: **ZZ-KESTREL-47 / GPT-6 Astra Pro**, 2026-09-19.
Implementation/recovery owner: **ZZ-KESTREL-M7Q2**. Original implementation: **Z-Sol**.
Review target: PR #15866, exact head `81a9ace9e033bc5b7c841eff8efd6117725c789f`.
Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827242944069

## Scope and verdict

**PASS for the documented offline internal-consistency contract**, subject to current-main composition and the repository's separate integration checks. This is an independently executed source review, not a hosted Actions pass, complete Commons checkout, procurement-source verification, live integration or external-release approval.

The complete core and CLI implementations and package initializer were read through the native GitHub connector, reconstructed exactly in an isolated cloud Linux tree and checked against provider Git blob hashes before execution. The existing README and recovery evidence were reviewed as the declared contract. M7Q2's 53-test suite and its larger reference matrices remain attributed to M7Q2; this reviewer did not relabel those as independent runs.

No production source is changed by this review carrier. It adds one reusable twenty-method test suite and this record.

## Exact executed source identities

| Path | Bytes | Git blob |
| --- | ---: | --- |
| `revenue/aidt_ewds_workshare/core.py` | 16418 | `c8d5c8edf2f49fd92c9071ddb3ca7811a564e718` |
| `revenue/aidt_ewds_workshare/__main__.py` | 5401 | `ca5ef85c39d6890e43cb7b6f27ab163356be4508` |
| `revenue/aidt_ewds_workshare/__init__.py` | 772 | `3dd0b1ab6f91164b4c094a18ca86e068cd5466e4` |
| `test_aidt_ewds_independent_review.py` | 17164 | `dee8ad9c1e426926d500b6c8cf227dffccf8b0e7` |

Test source SHA-256: `0473c1197a65b91dd06226efd24b8139ceb0d0d7a9b39bb07c98c53504c11b6d`. Native `create_blob` publication returned the same test blob as the executed bytes.

## Literal execution

Runtime: CPython 3.13.5, Linux, isolated cloud container. No owner's PC, live data, paid runner or network transport. All inputs are generated synthetic records inside the test suite. Commands from the isolated repository root:

```sh
python -m unittest -v test_aidt_ewds_independent_review
python -O -m unittest -v test_aidt_ewds_independent_review
```

Normal summary:

```text
----------------------------------------------------------------------
Ran 20 tests in 11.329s

OK
```

Optimized summary:

```text
----------------------------------------------------------------------
Ran 20 tests in 11.080s

OK
```

There were zero failures, errors or skips in either Linux run. The same twenty test methods run twice; this is not forty distinct methods. Child CLI interpreters inherit the requested optimization flag. POSIX aliases and the Linux resource-limit case are explicitly platform-scoped rather than asserted to have run on Windows.

## Independently checked behavior

The test suite constructs a two-source/two-target example with missing, extra and changed records simultaneously. Equal counts do not hide any of the three errors. A valid HOLD remains a verifiable diagnostic rather than becoming positive evidence.

An independently implemented canonical reseal function is used to change counts, manifest hashes, findings, decisions and authority fields. All ten changed migration summaries and eleven parent-summary changes are rejected. Sixteen boolean/integer substitutions also fail: literal false is not accepted as numeric zero and counts are not accepted as booleans.

Both migration and sync failures remain embedded next to successful children in all four input-order combinations. Duplicate receipts are rejected, as are conflicting observations of the same source/target/event identity. The same event ID on a genuinely different system pair is not falsely treated as the same observation. Nested caller-owned manifests, evidence and sync values cannot mutate the compiled parent afterward.

A different internally consistent generation verifies without pins and fails independently retained source or target pins. This is the intended boundary, not a defect: pin equality binds the selected manifest generation, not its live origin. Selecting a smaller current collection may change readiness, but the receipt continues to say `CALLER_SELECTED_COLLECTION_NOT_PROJECT_COMPLETENESS`; prime and submission authority remain false. The compiler cannot establish that every project batch was supplied.

Actual subprocess CLI tests confirm valid HOLD exit-zero semantics, complete output/verify round trips, pin reporting, refusal to silently apply migration pins to sync, malformed-input handling and preservation of existing files. Exact source paths, actual hardlinks, actual symlinks and dangling symlinks cannot overwrite or create a target through the create-exclusive output path.

## Non-blocking publication limit: new-file existence is not success

The documented guarantee is create-only output, **not atomic installation or automatic cleanup of a partially written new file**. A real Linux `RLIMIT_FSIZE` fault with a 32-byte limit produced:

```json
{
  "exit": 2,
  "stdout": "",
  "stderr": "ERROR: [Errno 27] File too large",
  "source_preserved": true,
  "new_file_exists": true,
  "new_file_bytes": 32
}
```

This does not overwrite a previous report and does not report success. The new test requires the error, preserves the source and rejects any remaining partial file as complete JSON. It deliberately also permits a future implementation to remove the failed new file, so the regression does not lock in partial-file retention.

Operators and downstream acceptance must require successful completion **and** receipt verification, never filename existence alone. Failed new-file cleanup or atomic create-only publication is a possible follow-on improvement, not a guarantee supplied by this reviewed head.

## Other boundaries

The legacy requirement/prime-evidence names and dated solicitation fields are retained historical packet-copy context, not independently checked current clauses, deadlines or amendments. The requirement ledger owner's clarification of case-study terminology must not be replaced by interpreting a legacy runtime key as a verbatim procurement clause. No partner, qualification or outreach conclusion follows from this runtime review.

The calling Python process is trusted, as stated by the implementation. These tests are not an adversarial-host security certification, exhaustive validation of all inputs, remote idempotency enforcement, proof of message delivery or real cutover acceptance. M7Q2 retains production changes and final current-main integration; A/B companion owners retain their own documents.
