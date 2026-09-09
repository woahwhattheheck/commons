# ASTRA-BEECH: GTM timestamp error-contract repair

Task: `astra-beech-lm-gtm-timestamps-20260908-01`.

## Scope

The production change is limited to `host/lm_gtm_index.py::parse_time`.
Non-string inputs previously escaped as AttributeError or TypeError before
parsing; timezone conversion at the datetime endpoints could escape as
OverflowError. Both now produce the existing `IndexError_` diagnostic.
Valid offset normalization, microsecond precision, representable endpoints,
and the timezone-required diagnostic are unchanged.

No real CRM, event ledger, saved index, occupancy, transport, provider,
customer, or financial state was changed by testing.

## Reproduction and acceptance

Run from the repository root:

```sh
python -B -m unittest -v test_lm_gtm_index_timestamps
python -m py_compile host/lm_gtm_index.py test_lm_gtm_index_timestamps.py
```

The new suite imports the complete production module and uses real temporary
JSON/JSONL ledgers and subprocess CLI calls, not extracted functions or mocks.
Original source blob `b964e8ccc6a0b6a97d23e62cf802cdfeb87a9b55`:
16 test methods, FAILED (2 failures, 29 errors across subcases).
Candidate: 16 tests passed, no skips. Compilation passed.
ASTs outside `parse_time` were compared and are identical.

Coverage includes JSON non-string values, bytes, invalid text, naive timestamps,
both UTC overflow endpoints, equivalent offsets, microseconds, representable
minimum/maximum dates, rejected append/claim/release with byte-identical file
snapshots, JSONL loading, a valid occupancy round trip, the exact 12-hour freshness
boundary, CLI error diagnostics without tracebacks, and unchanged fresh/stale/send
exit codes.

## Exact tested artifacts

| Path | Git blob SHA | SHA-256 |
| --- | --- | --- |
| `host/lm_gtm_index.py` | `5fdd971ef162d209ffb1bb50e56b791429a39770` | `9cc51f973d28081db28e30c64dbed3d9e5d36014ffaa5dfaaaf403a81b7efac7` |
| `test_lm_gtm_index_timestamps.py` | `e3848bad3826a749cc4415cfbb0d22e6ce1bb9b0` | `824b6d3724ad8b280124ca1d3ac8fa22803482e35a95313872404bfffa502dd4` |

## Evidence boundaries and coordination

The retained hosted battery run `34214634173` identified the GTM-index test
surface as failing. This bounded repair does not establish that its original
native suite or the full repository battery is green; neither is claimed here.

Harness: ChatGPT cloud container plus connected GitHub and Slack actions.
No owner-PC compute, live sends, customer contact, provider changes, or spend.
Publication uses a fresh-main base tree and only these three owned paths,
followed by PR diff inspection, expected-head merge, and blob readback.

Claim and progress thread:
https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788866700669839
