# luvak-ssa-lab-analytics-cutover-lims-01 receipt

State: TESTED
Binary: `python3 test_luvak_ssa_lab_analytics_cutover.py`
CLI: `python3 luvak_ssa_lab_analytics_cutover.py`

| check | expected | actual |
|---|---|---|
| input rows | 100 | 100 |
| READY | 80 | 80 |
| HOLD | 20 | 20 |
| HOLD codes | 8 MISSING_ACCEPTED_QUOTE + 4 DUPLICATE_SAMPLE_ID + 4 FORM_PACKAGE_MISMATCH + 4 METHOD_REVISION_MISMATCH | exact |
| held test/report stages | 0 / 0 | exact |
| released reports (autonomous) | 0 | 0 |
| staged reports | 80 pending named APPROVER dean-gaskill | 80 |
| replay added records | 0 | 0 |
| fixture_sha256 | b1160d4d7b27f6f254c263b5d8e4d13204903444a97a98205612c059c456dda2 | match |
| audit_sha256 | c69f62396eab88a5c31a994caf4bcb9c51dc6c86a5473e458eff1fad2744c46f | match |
| lineage_sha256 | 7b608c694273df9eea371a0f945250653f49dc40ff2f9075c3c2f4c178c03df5 | match |
| report_digest | 7db20de0c437719284a9d380c2e2c5b49c00b0bce091decf75bd442cc5db542b | match |

Buyer: Dean Gaskill / Luvak Laboratories. Quote/form/package/CoC SSA cutover. Interfaces simulated. No materials-qualification decision, production write, outreach, or automatic release. HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
