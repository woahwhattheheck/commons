# Multi-framework evidence freshness — fixed diagnostic pilot

Isolated commercial wrapper under this directory. The classifier itself is the merged #13908 engine (`revenue/multi_framework_evidence_freshness`). Commercial credit: Z-CantorSpindle-913946-W7M2 (`ZCS-W7M2`). Engine credit: Z-ApolloniusForge-914000-M7Q2 (`ZAF-M7Q2`).

## Contract

- <=500 sanitized evidence objects per diagnostic
- exact source / packet / projection / receipt binding to the #13908 engine
- buyer-safe JSON plus one-page Markdown
- strict offline CLI and verifier
- offer: **$3,500** diagnostic and optional **$10,000** integration sprint as `PROPOSED_NOT_ACCEPTED`
- no audit, certification, control-effectiveness, customer/provider, payment, or revenue authority

## Run

```bash
python -m revenue.multi_framework_evidence_freshness_pilot.cli compile input.json diagnostic.json page.md
python -m revenue.multi_framework_evidence_freshness_pilot.cli verify diagnostic.json
python -m unittest revenue.multi_framework_evidence_freshness_pilot.test_wrapper revenue.multi_framework_evidence_freshness_pilot.test_wrapper_hostile
python -O -m unittest revenue.multi_framework_evidence_freshness_pilot.test_wrapper revenue.multi_framework_evidence_freshness_pilot.test_wrapper_hostile
```
