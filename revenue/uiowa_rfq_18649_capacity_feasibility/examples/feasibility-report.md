# Capacity-aware roadmap feasibility

> FICTION. Northgate State University does not exist. Every item, estimate and prerequisite below is invented to exercise the dependency and capacity engine. Nothing here is a University of Iowa finding, recommendation, or plan.

> Capacity is stated per ROLE and per relative phase window only. No named individual, no calendar date, and no personal availability commitment appears in this file or in any output. The loader rejects a capacity record that carries a person-like field.

## Dependency checks

| Severity | Rule | Subject | Detail |
|---|---|---|---|
| warning | S002_SAME_PHASE_CHAIN | 0-90 | RM-01, RM-02, RM-05 are proposed in the same window and are dependency-ordered (levels 0, 1, 0); the window is carrying a whole chain |

## Scenario comparison

| Scenario | Estimates | Capacity | Proposed plan | Resequenced | Items moved | Beyond horizon |
|---|---|---|---|---|---|---|
| constrained | high | x0.75 | INFEASIBLE | INFEASIBLE | 3 | 1 |
| expected | likely | x1.0 | INFEASIBLE | UNKNOWN | 1 | 0 |
| invested | low | x1.4 | UNKNOWN | UNKNOWN | 0 | 0 |

### constrained - Constrained - current allocation only

Work is squeezed into existing duties and estimates land at the high end.

| Item | Proposed | Scheduled | Reason |
|---|---|---|---|
| RM-01 | 0-90 | 0-90 | unchanged |
| RM-02 | 0-90 | 90-180 | role capacity |
| RM-03 | 0-90 | 0-90 | unchanged |
| RM-04 | 90-180 | 90-180 | unchanged |
| RM-05 | 0-90 | 0-90 | unchanged |
| RM-06 | 90-180 | 90-180 | unchanged |
| RM-07 | 90-180 | 180+ | role capacity |
| RM-08 | 180+ | 180+ | unchanged |
| RM-09 | 180+ | BEYOND_HORIZON | no phase in the horizon has capacity for every role this item needs |

Unmet capacity on the plan **as proposed**:

| Role | Phase | Capacity | Demand | Short by |
|---|---|---|---|---|
| change_management_lead | 180+ | 120.0 | 142.0 | 22.0 |
| iam_service_owner | 0-90 | 67.5 | 88.0 | 20.5 |
| pipeline_engineer | 0-90 | 105.0 | 184.0 | 79.0 |
| ris_service_owner | 90-180 | 45.0 | 60.0 | 15.0 |

### expected - Expected - planned allocation

The planning case: allocation as assumed, estimates at the likely point.

| Item | Proposed | Scheduled | Reason |
|---|---|---|---|
| RM-01 | 0-90 | 0-90 | unchanged |
| RM-02 | 0-90 | 90-180 | role capacity |
| RM-03 | 0-90 | 0-90 | unchanged |
| RM-04 | 90-180 | 90-180 | unchanged |
| RM-05 | 0-90 | 0-90 | unchanged |
| RM-06 | 90-180 | 90-180 | unchanged |
| RM-07 | 90-180 | 90-180 | unchanged |
| RM-08 | 180+ | 180+ | unchanged |
| RM-09 | 180+ | 180+ | unchanged |

Unmet capacity on the plan **as proposed**:

| Role | Phase | Capacity | Demand | Short by |
|---|---|---|---|---|
| pipeline_engineer | 0-90 | 140.0 | 144.0 | 4.0 |

### invested - Invested - additional allocation approved

Additional time is approved and estimates land at the low end.

| Item | Proposed | Scheduled | Reason |
|---|---|---|---|
| RM-01 | 0-90 | 0-90 | unchanged |
| RM-02 | 0-90 | 0-90 | unchanged |
| RM-03 | 0-90 | 0-90 | unchanged |
| RM-04 | 90-180 | 90-180 | unchanged |
| RM-05 | 0-90 | 0-90 | unchanged |
| RM-06 | 90-180 | 90-180 | unchanged |
| RM-07 | 90-180 | 90-180 | unchanged |
| RM-08 | 180+ | 180+ | unchanged |
| RM-09 | 180+ | 180+ | unchanged |

