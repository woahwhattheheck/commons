# csanalytical-expansion-crossline-evidence-lims-01 receipt

State: TESTED
Binary: `python3 test_csanalytical_expansion_crossline.py`
CLI: `python3 csanalytical_expansion_crossline.py`

| check | expected | actual |
|---|---|---|
| input rows | 120 | 120 |
| READY | 90 | 90 |
| HOLD | 30 | 30 |
| HOLD codes | 8 DUPLICATE_ID + 7 WRONG_LINE_METHOD + 5 MISSING_STUDY_PACKAGE + 5 INSTRUMENT_QC_FAILURE + 5 SOURCE_HASH_MISMATCH | exact |
| scheduled holds | 0 | 0 |
| held reports staged | 0 | 0 |
| released reports (autonomous) | 0 | 0 |
| staged reports | 90 pending named APPROVER brandon-zurawlow | 90 |
| replay added records | 0 | 0 |
| fixture_sha256 | a15e0d4fdf758b1c6b3aaf953c207050bed39f95282d5fd40bee97376939d6a8 | match |
| audit_sha256 | edb76b5450c40ff2c52027176485c120e99ca5b1bb51ebb76d237dd836c00632 | match |
| lineage_sha256 | 539ec0898544c686cb7bb47c1851326d2cb0d870ef905b86c221b23dcc2b67e6 | match |
| report_digest | 32d53085590c4db83117700ac2bd0efae1245b1942bf6757db2d680723850e6b | match |

Buyer: Brandon Zurawlow / CS Analytical. CCIT / raw-material / gas / micro cross-line evidence spine. Interfaces simulated. No compliance decision, production write, outreach, or automatic release. HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
