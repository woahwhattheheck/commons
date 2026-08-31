# luvak-ssa-lab-analytics-cutover-lims-01 receipt

State: TESTED
Binary: `python3 test_luvak_ssa_lab_analytics_cutover.py` → 10/10 OK
CLI: `python3 luvak_ssa_lab_analytics_cutover.py` → ok true, failures []

| check | value |
|---|---|
| input shipments | 100 |
| READY | 80 |
| HOLD | 20 |
| MISSING_ACCEPTED_QUOTE | 8 |
| DUPLICATE_SAMPLE_ID | 4 |
| FORM_PACKAGE_MISMATCH | 4 |
| METHOD_REVISION_MISMATCH | 4 |
| hold test/report stage | none |
| READY hashes | quote, form, optional CoC, method, result, report |
| staged reports | 80 |
| released reports | 0 |
| replay added READY/HOLD | 0 / 0 |
| manifest_sha256 | 56ec168346ebd77490db696678358f7995fcada2465fe3e3fe929f749491aef8 |

Adapters synthetic/read-only. Materials-quality evidence only. No qualification decision. Named-human release only. AquaTrace HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
