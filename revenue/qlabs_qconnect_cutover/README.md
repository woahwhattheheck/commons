# Q Connect cutover verification

Demand: `qlabs-qconnect-cutover-verification-lims-01`
Buyer pairing: Q Laboratories / Jeff Knowles

Catalog-version validation, per-user access migration, submission
preflight, and retry-safe cutover verification.

- Official binary: `python3 test_qlabs_qconnect_cutover.py`
- CLI: `python3 revenue/qlabs_qconnect_cutover/runner.py`
- Door: [qlabs-qconnect-cutover-verification-lims.html](../../qlabs-qconnect-cutover-verification-lims.html)
- Immutable manifest: `fixture.json` (240 synthetic/deidentified rows)

HOLD / BUILD-AND-VERIFY. Simulated / read-only shadowing. No production
writes, outreach, prospect-facing demo, or automatic release.
PRE-SALE TRANSPORT: NONE. cash_usd=0. Open door. No login.
