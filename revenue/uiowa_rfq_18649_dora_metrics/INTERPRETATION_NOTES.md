# UIOWA-064 — Interpretation notes

## Current DORA source

Primary guide: https://dora.dev/guides/dora-metrics/ — last updated 2026-01-05.

DORA's 2026 history explains the evolution from the earlier four-key model to the current five-metric model, including the 2023 shift from generic MTTR/time-to-restore language to **failed deployment recovery time** and the 2024 addition of **deployment rework rate**: https://dora.dev/insights/dora-metrics-history/

The current guide describes three throughput metrics (change lead time, deployment frequency, failed deployment recovery time) and two instability metrics (change fail rate, deployment rework rate). The guide also stresses application/service context and warns that blending or comparing materially different applications can mislead.

## What this calculator does

- computes the five event-derived measures per service;
- exposes numerator/denominator and coverage counts;
- preserves explicit observation windows;
- excludes non-production rows while reporting the exclusion count;
- reports missing change linkage instead of imputing it;
- distinguishes “no failed deployment observed” from “zero recovery time”;
- produces machine-readable JSON and a flat CSV summary.

## What it deliberately does not do

1. **No cross-service rollup.** ESS registration, research submission, and sign-in examples have different operating contexts. The tool refuses to manufacture one portfolio metric from them.
2. **No individual or team ranking.** DORA's metrics describe software delivery performance for an application/service and are intended to support improvement, not a developer leaderboard.
3. **No invented peer percentile.** The event calculator does not translate values into a DORA Quick Check score or industry percentile. The Quick Check is a separate survey/benchmark surface with its own model and current benchmark data.
4. **No universal target.** The tool does not declare “good” deployment frequency, recovery time, or fail/rework rate. Service criticality, release model, regulatory obligations, batch size, architecture, demand, and evidence quality matter.
5. **No silent equivalence between incident recovery and failed-deployment recovery.** Only impairments caused by a deployment and explicitly marked as requiring intervention enter the failed-deployment recovery-time population.
6. **No rework inference from commit messages.** A deployment counts as rework only when the input explicitly identifies it as unplanned rework and records the cause.
7. **No DORA-mandated median claim.** Median/min/max are transparent local summaries for event logs; DORA's public guide defines the metrics but does not require this exact aggregation method.

## Synthetic fixture interpretation

The checked-in two-week fixture is fictional. Expected headline values are:

| Service | Deployments/week | Median change lead time | Change fail rate | Median failed-deployment recovery | Deployment rework rate | Evidence note |
|---|---:|---:|---:|---:|---:|---|
| `ess-registration` | 4.0 | 6.5 h | 25.0% | 1.5 h | 25.0% | all six eligible successful changes linked |
| `ris-submission` | 3.0 | 26.5 h | 16.667% | 4.0 h | 16.667% | one of five eligible successful changes lacks commit linkage, so lead-time status is `measured_partial` |
| `iam-signin` | 2.5 | 3.0 h | 0.0% | not observed | 0.0% | no failed deployment in window; recovery is not reported as zero |

These values are test oracles, not claims about the University of Iowa.

## Assessment use

For an actual engagement, first agree the application/service boundary and observation window. Then inspect the source systems that can substantiate commits, successful production state, deployment events, incidents/remediation, and unplanned rework. Record data-source coverage and known blind spots before interpreting the values.

Use the metrics primarily for within-service trend and improvement conversations. If any peer/industry comparison is later proposed, preserve DORA's measurement definitions, the benchmark population/time period, and the local context rather than treating raw values as a maturity score.
