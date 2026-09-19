# UIOWA-064 — DORA five-metric data dictionary

**Reference baseline:** DORA, “DORA’s software delivery performance metrics,” last updated 2026-01-05: https://dora.dev/guides/dora-metrics/

The calculator keeps DORA's current five software-delivery metrics separate and computes them **per application/service**. It does not create a blended score, an individual score, a maturity level, or an industry percentile.

## Metric definitions and local operationalization

| Metric | DORA concept | Local calculation in this carrier | Important boundary |
|---|---|---|---|
| Change lead time | Time for a change to go from committed to version control to deployed/running successfully in production. | Per eligible successfully running change, `successful_change_at - committed_at`; report median/min/max and linkage coverage. | Median/min/max are a transparent local summary, not a DORA-mandated aggregation formula. Missing commit linkage stays missing. |
| Deployment frequency | Number of deployments over a period, or time between deployments. | Count production deployment events inside an explicit half-open observation window; report deployments/day and deployments/week. | Do not infer a rate from first/last observed deployment; the window is explicit. |
| Failed deployment recovery time | Time to recover from a deployment that fails and requires immediate intervention. | For failed deployments, `recovery_completed_at - failure_detected_at`; report median/min/max. | A service with no failed deployment is `not_observed`, not “0 hours.” |
| Change fail rate | Ratio of deployments requiring immediate intervention after deployment. | `failed deployments / production deployments * 100`. | Failure means the explicit event flag is true; do not infer it from incident text. |
| Deployment rework rate | Ratio of deployments that are unplanned and happen because of a production incident/user-facing bug. | `is_unplanned_rework deployments / production deployments * 100`. | Rework must be explicitly identified and carry a cause. |

DORA groups change lead time, deployment frequency, and failed-deployment recovery time as throughput measures, and change fail rate plus deployment rework rate as instability measures. This carrier reports the five source metrics rather than manufacturing a local composite.

## CSV fields

| Field | Required | Meaning |
|---|---|---|
| `deployment_id` | yes | Unique event identifier within the input. |
| `service` | yes | Application/service boundary. Metrics are calculated separately for each value. |
| `window_start` | yes | Inclusive ISO-8601 timestamp for the observation window. All production rows for a service must agree. |
| `window_end` | yes | Exclusive ISO-8601 timestamp for the observation window. |
| `environment` | yes | Only `production` rows contribute to metrics. Other rows are counted as excluded. |
| `deployed_at` | yes | When the deployment reached the named environment; must lie inside the window. |
| `commit_id` | for measured lead time | Stable change/commit identifier. Blank means change linkage is unavailable. |
| `committed_at` | for measured lead time | Time the change was committed to version control. |
| `successful_change_at` | for eligible lead time | Time the change was successfully running in production. Blank for a failed/rolled-back change that did not become the successful change. |
| `requires_immediate_intervention` | yes | Boolean marking a deployment that degraded service and required rollback/hotfix/fix-forward/patch or equivalent immediate intervention. |
| `failure_detected_at` | when failed | Detection/recognition timestamp for the deployment-caused impairment. |
| `recovery_completed_at` | when failed | Timestamp when recovery from that failed deployment completed. |
| `is_unplanned_rework` | yes | Boolean marking an unplanned deployment performed because of a production problem. |
| `rework_cause` | when rework | Cause such as `production_incident` or `user_facing_bug`. |
| `notes` | yes column, optional text | Human context; never parsed to infer metric truth. |

## Evidence statuses

- `measured`: all evidence required for the metric population is present.
- `measured_partial`: some eligible observations are measurable and some required linkage is missing.
- `insufficient_evidence`: eligible observations exist but none has enough evidence.
- `not_observed`: the relevant event type did not occur in the observation window; this is not numerically equivalent to a zero-duration event.

The calculator fails closed on duplicate deployment IDs, naive timestamps, inconsistent observation windows, deployment timestamps outside their windows, impossible timestamp order, failed deployments without recovery timestamps, or unplanned rework without a cause.
