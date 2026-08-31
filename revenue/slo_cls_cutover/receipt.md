# slo-cls-cutover-evidence-lims-01 receipt

State: TESTED
Binary: `python3 test_slo_cls_cutover_evidence.py`
CLI: `python3 slo_cls_cutover_evidence.py`

| check | expected | actual |
|---|---|---|
| input rows | 1000 | 1000 |
| READY | 850 | 850 |
| HOLD | 150 | 150 |
| HOLD codes | 50 DUPLICATE_ID + 40 BROKEN_SAMPLE_TEST_REF + 30 METHOD_VERSION_CONFLICT + 30 REPORT_RESULT_HASH_MISMATCH | exact |
| mapped once | 850 unique incumbent→CLS | exact |
| orphans / duplicate mappings | 0 / 0 | exact |
| released reports (autonomous) | 0 | 0 |
| staged reports | 850 pending named APPROVER glen-m-miller | 850 |
| replay added records | 0 | 0 |
| rollback restored | exact baseline | exact |
| fixture_sha256 | 156ce11a5dd46c0b081eff9b9da3dba1bfdd5264b53db6bc6a9d1c76cd641ef4 | match |
| audit_sha256 | 92c29637e02a6eda62707c87bf0e1a5be816f5f6a910cf577fd985fbf1f57dea | match |
| lineage_sha256 | e3ab31e345104a78eb97d2301923aed660b712837517ca2666ca8b427de97d68 | match |
| baseline_sha256 | 4bdef9e897246f67333bd22f1c2035510db25754d3acf8de606780448af38a56 | match |

Buyer: Glen M. Miller / San Luis Obispo County Public Health Laboratory. Incumbent→CliniSys cutover verifier. Interfaces simulated. No public-health interpretation, production write, outreach, or automatic release. HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
