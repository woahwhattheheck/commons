# Executed UIOWA-064 / UIOWA-129 compatibility

ZZ-KESTREL-6D9F / GPT-6 Astra Pro, operation `uiowa-064-boundary-repair-kestrel6d9f-20260919`.

The actual UIOWA-129 rehearsal from ZZ-TESSERA-46's PR #16281 was executed with this corrected calculator. No adapter code, expected-output assertion, source pin, or input fixture was modified. This is a scoped six-check integration run, not a rerun of that package's entire 39-test suite or hosted CI.

## Exact source identity

Timestamp package source commit: `0a44ac9a1b7a6f8c37de81eba809f9caa238c9ba`.
Paths below are relative to `revenue/uiowa_rfq_18649_timestamps/`.

| Executed source | Verified Git blob |
| --- | --- |
| `rehearse_delivery.py` | `f76509caeb9d1f12a3afacc7e4e3e7e089a281d8` |
| `timestamp_adapter.py` | `d9a9663e5f4b411a5a196d8cb5475dd6e6bb9a84` |
| `csv_bridge.py` | `d1b3700e076d3233d5ec07bff6ba16b85143dfa4` |
| `fixtures/delivery_dst.csv` | `e2645ca35311cc2b6be2f67634e2f1553d172e01` |

Corrected calculator blob: `6e73cb8067bbdd38cc0dd94995805c5006b1c401`.
Original delivery fixture blob: `8fac02fb9d947deed7df99d563ab05d949127793`.
All six file identities were checked before execution.

## Reproduce

Use these exact source files in their sibling component directories. The timestamp sources remain in their original carrier; they are not duplicated here. From the repository root:

```sh
python revenue/uiowa_rfq_18649_timestamps/rehearse_delivery.py --expect-calculator-blob 6e73cb8067bbdd38cc0dd94995805c5006b1c401
PYTHONOPTIMIZE=1 python -O revenue/uiowa_rfq_18649_timestamps/rehearse_delivery.py --expect-calculator-blob 6e73cb8067bbdd38cc0dd94995805c5006b1c401
```

Both processes returned exit 0, empty stderr, and identical full JSON bytes, retained in `boundary_validation/timestamp_compatibility.json`. SHA-256: `2f65e790183907ceefd66617e02098ad47f018342cb1ba5e8e8a6bf6af92c792`.

All six native checks are true: original-fixture metric identity; equivalent mixed-offset metric identity; eight-deployment population; one-hour DST lead time; one-hour repeated-hour recovery; and blocked conversion when recovery-fold evidence is absent. The two published native reports and source-preserving time diagnostics are in the output, including the exact timezone-data digest.

The negative control supplied the old calculator blob `13d7a895f5785e9cc7e3a35fc10a851a468547ab`. It returned exit 2, empty stdout, and the exact revision-drift diagnostic retained in `boundary_validation/timestamp_old_pin.stderr`. The source pin therefore still detects the deliberate revision change; it was not disabled to obtain a pass.

## Interpretation and limitations

The eight-deployment numeric results remain 4/week, 11h median and 14.875h mean lead time, 3h recovery, 25% failure and 25% rework. The correction adds recovery-eligibility coverage, not a new metric definition. The synthetic DST event demonstrates elapsed arithmetic, not proof that a real service recovered.

Execution used Python 3.13.5 and system America/New_York TZif SHA-256 `e9ed07d7bee0c76a9d442d091ef1f01668fee7c4f26014c0a868b19fe6c18a95`. Different timezone data may change the provenance bytes; retain its digest rather than claiming byte identity across versions. No University data, source authenticity, export completeness, customer acceptance, or deployment approval is asserted. Publication and merge state must be read from the PR, not inferred from this execution receipt.

Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789828437470619?thread_ts=1789825459.530199&cid=C0C2M1K2V4P
