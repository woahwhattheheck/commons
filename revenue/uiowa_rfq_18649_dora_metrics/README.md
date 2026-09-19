# UIOWA-064 — Software delivery metrics calculator

Runnable, stdlib-only preparation asset for University of Iowa RFQ 18649. It calculates DORA's **current five** software-delivery performance metrics from explicit deployment-event data while preserving evidence gaps and service context.

**Synthetic only.** Nothing in this directory is University of Iowa evidence or a finding.

## Primary source

DORA, “DORA’s software delivery performance metrics”  
https://dora.dev/guides/dora-metrics/  
Guide last updated: **2026-01-05**

The current five metrics are:

- change lead time;
- deployment frequency;
- failed deployment recovery time;
- change fail rate; and
- deployment rework rate.

DORA's current guide recommends applying the metrics in the context of an application/service and cautions against disparate comparisons. This carrier therefore produces **no cross-service aggregate**, **no individual productivity score**, and **no inferred peer percentile**.

## Run

From this directory:

```bash
python3 dora_metrics.py fixtures/synthetic_deployments.csv
python3 dora_metrics.py fixtures/synthetic_deployments.csv \
  --json-out /tmp/uiowa-dora.json \
  --csv-out /tmp/uiowa-dora.csv
python3 -m unittest -v test_dora_metrics.py
```

No third-party packages, network calls, credentials, or live-system access are required.

## Verified synthetic expectations

The regression fixture covers three fictional services over the same two-week window plus one staging row that must be excluded.

| Service | Deployments/week | Lead-time median | Change fail rate | Recovery median | Rework rate |
|---|---:|---:|---:|---:|---:|
| ess-registration | 4.0 | 6.5 h | 25.0% | 1.5 h | 25.0% |
| ris-submission | 3.0 | 26.5 h | 16.667% | 4.0 h | 16.667% |
| iam-signin | 2.5 | 3.0 h | 0.0% | not observed | 0.0% |

The RIS fixture intentionally omits commit linkage for one otherwise eligible successfully deployed change. The calculator reports lead-time status `measured_partial`, one missing linkage, and 80% coverage; it does not guess the missing lead time.

The IAM fixture intentionally contains no failed deployment. Failed-deployment recovery status is `not_observed` with a null duration; zero hours would be a false claim.

## Files

- `dora_metrics.py` — parser, fail-closed validation, per-service five-metric calculation, JSON/CSV export.
- `fixtures/synthetic_deployments.csv` — fictional ESS/RIS/IAM event history.
- `fixtures/missing_evidence.csv` — focused missing-linkage case.
- `DATA_DICTIONARY.md` — event fields, formulas, evidence statuses, boundaries.
- `INTERPRETATION_NOTES.md` — DORA source/currentness and assessment guardrails.
- `test_dora_metrics.py` — regression and hostile-data tests.

## Local verification performed before publication

The authored source and exact fixtures were executed with the Python standard library before publication:

```text
Ran 4 tests in 0.003s
OK
```

Covered behaviors:

1. expected values for all three synthetic services;
2. missing change linkage remains partial rather than imputed;
3. failed deployment without recovery timestamps fails closed;
4. inconsistent observation windows fail closed.

Runtime timing is environment-specific; the substantive receipt is the four passing assertions and the deterministic values above.
