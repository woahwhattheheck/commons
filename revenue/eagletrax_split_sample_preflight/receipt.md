# eagletrax-split-sample-preflight-lims-01 receipt

State: TESTED
Binary: `python3 test_eagletrax_split_sample_preflight.py` → 10/10 OK
CLI: `python3 eagletrax_split_sample_preflight.py` → ok true, failures []

| check | value |
|---|---|
| input rows | 240 |
| valid parents | 200 |
| children | 280 |
| held | 40 |
| ABSENT_WORKBOOK | 8 |
| INSUFFICIENT_CONTAINER | 8 |
| UNSPLIT_CONTAINER | 8 |
| MISSING_HANDLING | 8 |
| STALE_CLIENT | 4 |
| FORM_CONTAINER_MISMATCH | 4 |
| wrong-child attachments | 0 |
| reports released | 0 |
| replay added parents/children/holds | 0 / 0 / 0 |
| audit_sha256 | 4713d639759868af9475cdddfeed2ff335f004041f55602a2fa36877418d4e4c |

Interfaces simulated and read-only. No production writes. No autonomous certification or release. HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
