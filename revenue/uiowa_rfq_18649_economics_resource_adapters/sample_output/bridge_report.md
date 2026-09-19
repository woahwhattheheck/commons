# Ledger bridge report (UIOWA-105C)

> Derived from synthetic component output. Not a University of Iowa finding or plan.

## One-time effort crossing to the roadmap lane

Unit: `staff-hours`. Ledger: `hours (one-time implementation)`.

| Item | Recommendation | Effort (low-likely-high) | Complete |
|---|---|---|---|
| `RM-FROM-REC-SYN-ESS-SD-001` | `REC-SYN-ESS-SD-001` | 45.00 - 80.00 - 130.00 | yes |
| `RM-FROM-REC-SYN-ESS-SEC-001` | `REC-SYN-ESS-SEC-001` | 30.00 - 50.00 - 90.00 | yes |
| `RM-FROM-REC-SYN-IAM-DEP-001` | `REC-SYN-IAM-DEP-001` | 55.00 - 85.00 - 130.00 | yes |
| `RM-FROM-REC-SYN-IAM-SD-001` | `REC-SYN-IAM-SD-001` | 45.00 - 80.00 - 130.00 | yes |
| `RM-FROM-REC-SYN-IAM-SEC-001` | `REC-SYN-IAM-SEC-001` | 130.00 - 220.00 - 360.00 | yes |
| `RM-FROM-REC-SYN-RIS-DEP-001` | `REC-SYN-RIS-DEP-001` | 10.00 - 16.00 - 28.00 | yes |
| `RM-FROM-REC-SYN-RIS-SD-001` | `REC-SYN-RIS-SD-001` | 12.00 - 20.00 - 34.00 | yes |
| `RM-FROM-REC-SYN-RIS-SEC-001` | `REC-SYN-RIS-SEC-001` | 70.00 - 110.00 - 160.00 | yes |

## Recurring load the receiving lane cannot represent

The receiving lane has no recurring field. Recurring load is returned in `recurring_not_representable`, NOT in `items[].effort`.

| Recommendation | Recurring (FTE/yr) |
|---|---|
| `REC-SYN-ESS-DEP-001` | 0.010 - 0.020 - 0.040 |
| `REC-SYN-ESS-SD-001` | 0.010 - 0.020 - 0.050 |
| `REC-SYN-IAM-DEP-001` | 0.020 - 0.030 - 0.060 |
| `REC-SYN-IAM-SD-001` | 0.010 - 0.020 - 0.050 |
| `REC-SYN-IAM-SEC-001` | 0.060 - 0.120 - 0.220 |
| `REC-SYN-RIS-DEP-001` | 0.002 - 0.005 - 0.010 |
| `REC-SYN-RIS-SD-001` | 0.005 - 0.010 - 0.020 |
| `REC-SYN-RIS-SEC-001` | 0.020 - 0.040 - 0.070 |

## Unestimated — the roadmap must not treat these as free

- `REC-SYN-ESS-AI-001`: the roadmap must treat this as UNESTIMATED. It is not zero capacity consumed, and it is not a free item.
- `REC-SYN-ESS-DEP-001`: the roadmap must treat this as UNESTIMATED. It is not zero capacity consumed, and it is not a free item.
- `REC-SYN-IAM-AI-001`: the roadmap must treat this as UNESTIMATED. It is not zero capacity consumed, and it is not a free item.

## Recurring-unit agreement check

- `RES-001`: **UNKNOWN** — deck states 4 staff-hours per month = 0.02308 FTE/yr, but no asserted correspondence links `R-001` to any recommendation in this lane's register, so agreement cannot be established and is not assumed
- `RES-002`: **UNKNOWN** — the deck records this as not assessed; it stays UNKNOWN and is not converted to zero
- `RES-003`: **UNKNOWN** — the deck records this as not assessed; it stays UNKNOWN and is not converted to zero

## Identifier islands

4 identifier conventions observed; components in different islands CANNOT be joined without a human-asserted correspondence. This module reports the split rather than inventing the mapping.

| Convention | Components | Examples |
|---|---|---|
| `OPP-* / WI-*` | uiowa_rfq_18649_economics_resource_adapters | `WI-DEPLOY-APPROVALS-001`, `WI-ESS-RELNOTES-001`, `WI-FROM-OPP-ESS-02` |
| `OTHER` | uiowa_rfq_18649_economics_resource_adapters | `ECON-004` |
| `R-NNN` | uiowa_rfq_18649_readout_deck | `R-001`, `R-002`, `R-003` |
| `REC-SYN-*` | uiowa_rfq_18649_prioritization | `REC-SYN-ESS-AI-001`, `REC-SYN-ESS-DEP-001`, `REC-SYN-ESS-SD-001` |

