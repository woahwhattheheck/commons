# Unit vocabulary report (UIOWA-105D)

> Read-only scan of landed lanes. No lane is modified.

## Unit vocabulary across landed lanes

7 quantities observed under 10 spellings; 6 resourcing unit strings name a measure but no period and are listed rather than guessed; 19 strings carry no resourcing measure and are out of scope for this module.

| Quantity | Spellings in use | Components |
|---|---|---|
| `FTE-fraction per year` | `FTE-fraction per year (recurring staff load)`, `FTE-fraction per year (recurring)` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_economics_resource_adapters |
| `currency one-time` | `currency (one-time)` | uiowa_rfq_18649_economics_resource_adapters |
| `currency per year` | `currency per year (recurring)` | uiowa_rfq_18649_economics_resource_adapters |
| `staff-hours one-time` | `hours (one-time implementation)`, `hours (one-time)` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_economics_resource_adapters |
| `staff-hours per month` | `person_hours_per_month`, `staff-hours per month` | uiowa_rfq_18649_adoption_readiness, uiowa_rfq_18649_readout_deck |
| `staff-hours per phase window` | `staff-hours available to this programme per phase window` | uiowa_rfq_18649_capacity_feasibility |
| `staff-hours per year` | `staff-hours released per year (recurring)` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_economics_resource_adapters |

### Unit strings that do not state a period

These are not read as one-time. Each needs its own component's metadata, or an answer from the seat that owns it.

| Component | Unit | Measure | Period |
|---|---|---|---|
| uiowa_rfq_18649_adoption_readiness | `person_hours` | staff-hours | UNSTATED-PERIOD |
| uiowa_rfq_18649_ai_decision_case | `currency_per_hour` | staff-hours | UNSTATED-PERIOD |
| uiowa_rfq_18649_capacity_feasibility | `staff-hours` | staff-hours | UNSTATED-PERIOD |
| uiowa_rfq_18649_deadline_continuity | `hours` | staff-hours | UNSTATED-PERIOD |
| uiowa_rfq_18649_readout_deck | `hours` | staff-hours | UNSTATED-PERIOD |
| uiowa_rfq_18649_readout_deck | `staff-hours` | staff-hours | UNSTATED-PERIOD |

