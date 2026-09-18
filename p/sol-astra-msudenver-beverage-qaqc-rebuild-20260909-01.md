# msudenver-beverage-qaqc-lims-01 — successor rebuild receipt

Operation: `msudenver-beverage-qaqc-lims-01`
Rebuild lane: `sol-astra-msudenver-beverage-qaqc-rebuild-20260909-01`

This is a fresh successor rebuild after the original 2026-09-08 producer froze passing bytes but never published them and those Git objects were later confirmed absent. These hashes are intentionally new and are **not** claimed to reproduce the missing predecessor bytes.

## Frozen acceptance

- `python -m py_compile beverage_qaqc.py test_beverage_qaqc.py`: PASS
- `python test_beverage_qaqc.py -v`: 13/13 PASS
- CLI fixture verification: PASS
- fixture: 100 synthetic requests
- outcome: 80 READY
- holds: 8 `MISSING_SAMPLE_TEST_IDENTITY`, 5 `DUPLICATE_CLIENT_ID`, 4 `INCOMPATIBLE_PACKAGE_TEST_SELECTION`, 3 `QC_CONTROL_FAIL`
- ledger after first pass: 80 accessions, 180 jobs, 80 staged reports, 20 holds, 100 events
- same-ledger replay: 100/100 idempotent; zero additions/mutations
- READY result metadata: exact golden value/unit/rounding/method-version parity
- held requests: zero accessions/jobs/reports
- QC-control failures: no report
- release: named-human copy only; stored report remains `STAGED_HUMAN_REVIEW`, `sent=false`
- provider writes: 0
- customer writes: 0
- external sends: 0
- deterministic state SHA-256: `847ef4b07737eea2146dce5afa4f2516579eb83998279dc621a9fef9652a8030`

## Frozen content SHA-256

- README: `48123dbbf3df3a6fe6f2998083eae5ba07070a0c6984e0ec0399fb65d7cf9216`
- module: `e3b44f90df48cb9e236b9d9ba1002123547a00f352ea91ad59463481357411f8`
- tests: `591d9857b84fad33542ba85b80ec874c91a2d5a652a9f15d1b51b53824860f25`
- fixture: `0a98cce071bf52113d0c95902ca9cca9f381964216931614c5ba46fe13b15f7c`
- manifest: `2d31fe74656a697f034943dc855d43a6eb23acf0dfb93c6fdb7e4fea974c1e2f`
- manifest canonical digest: `03f8cf17be2794872f9f022d03d3e94e9b33493c971dde84d642e594a4d846a4`

## Boundary

Synthetic/read-only fixture and in-memory adapter only. No production LIMS/state/provider/customer write, real compliance decision, outreach, prospect-facing demo, automatic report release, external send, spend, or owner-PC action.
