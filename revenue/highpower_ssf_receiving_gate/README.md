# HIGHPOWER SSF-to-receiving accession + hold/release gate

Demand: `highpower-ssf-receiving-gate-lims-01`

Buyer pairing: HIGHPOWER Validation Testing & Lab Services / Gary Socola

The runner is the product:

```text
python3 highpower_ssf_receiving_gate.py
python3 test_highpower_ssf_receiving_gate.py
```

200 paired synthetic HP-QC-067 Sample Submission Forms and receiving-inspection records. 160 accession once. 40 HOLD under the exact discrepancy code. Zero downstream while held. Source/version provenance on every field. Replay changes nothing. Named human `SYN-HPV-RELEASE-OFFICER` only.

Adapters stay synthetic or simulated and read-only. No live sample or test action. No outreach. cash_usd=0. HOLD / BUILD-AND-VERIFY.
