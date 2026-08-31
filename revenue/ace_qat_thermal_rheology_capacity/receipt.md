# ACE/QAT thermal-rheology capacity LIMS — TESTED

Demand: `ace-qat-thermal-rheology-capacity-lims-01`
Buyer: Erick Sharp / ACE Laboratories + Quick Accurate Testing

Binary: `python3 test_ace_qat_thermal_rheology_capacity.py` → 10/10 OK
CLI: `python3 ace_qat_thermal_rheology_capacity.py`

- 120 synthetic orders
- 90 READY
- 30 HOLD: 10 DUPLICATE_ID, 10 CAPABILITY_MISMATCH, 10 QC_FAIL
- 100 jobs; replay added 0
- instrument / method / source hashes match
- released_reports = 0 without named approval
- fixture_sha256 `019eed67be05ac57b8af5e454390eebd688aedac0e4e0466775672db84c25ab9`
- audit_sha256 `63a72dea4306203e2da870a0e9cc657146896965b54943ea096c9a592d29620e`
- report_digest `cfc145784c1e22cc619433d6d0aa541bbb34087e4f186aafde3c8e4a11ec7c22`

AquaTrace HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
