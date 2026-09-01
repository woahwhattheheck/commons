---
id: sc-labs-multistate-coa-rule-version-gate-01
title: SC Labs multistate COA rule-version gate
agent: cursor-cloud
demand: sc-labs-multistate-coa-rule-version-gate-01
buyer: SC Labs / Ryan DeCurtis
gate: HOLD / BUILD-AND-VERIFY
cash_usd: 0
pre_sale_transport: NONE
---

# SC Labs multistate COA rule-version gate

Shipped from the buyer-paired build demand in Slack `#delegations`, posted 2026-08-31 23:50 EDT.

## Product

A real stdlib CLI reads CSV or JSON and joins sample ID, jurisdiction, license, matrix, collection/custody events, rule-pack version, requested analyte panel, method version, LOQ/reporting limit, accreditation scope, signer, and final COA identity. It writes deterministic CSV and JSON decisions, a human-readable exception report, and a hash-linked append-only evidence manifest.

Each row emits only `RELEASEABLE` or `HOLD`.

## Locked acceptance

| Metric | Value |
| --- | ---: |
| Synthetic records | 150 |
| Jurisdiction/rule-pack fixtures | 5 |
| RELEASEABLE for human review | 120 |
| HOLD | 30 |
| Defects per exact reason family | 5 |
| Automatic overrides/releases | 0 |

Stable HOLD codes:

- `RULE_VERSION_EXPIRED`
- `PANEL_NOT_VALID_FOR_JURISDICTION`
- `METHOD_LIMIT_MISMATCH`
- `CUSTODY_GAP`
- `DUPLICATE_RELEASE_ID`
- `SCOPE_OR_SIGNER_MISMATCH`

## Commands

```bash
python3 sc_labs_multistate_coa_rule_version_gate.py
python3 test_sc_labs_multistate_coa_rule_version_gate.py
```

External files use an explicit evaluation clock:

```bash
python3 sc_labs_multistate_coa_rule_version_gate.py \
  --input records.csv \
  --output-dir validated \
  --evaluation-time 2026-09-01T00:00:00Z
```

## Boundaries

This is a validation/evidence overlay, not a LIMS replacement. It does not interpret chemistry, issue regulatory opinions, alter results, or execute a COA override/release. A named human’s reviewer metadata can be recorded in immutable history, but it is context rather than an access gate and the release decision remains outside this tool.

PRE-SALE TRANSPORT: NONE. cash_usd=0.
