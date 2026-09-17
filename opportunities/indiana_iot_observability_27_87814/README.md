# Indiana IOT RFP 27-87814 - Enterprise Observability Platform

Revenue pursuit carrier for Commons issue #15651.

## Current posture

`HOLD / PARTNER-FIRST RESEARCH / NO OUTBOUND`.

The live Indiana IDOA notice identifies RFP 27-87814 / event 000670000087814, due October 28, 2026 at 3:00 PM ET, and says IOT seeks an Enterprise Observability Platform that preserves coverage, scales toward 500 monitored applications, and improves detection, resolution, and alert-quality outcomes.

The controlling State bid package is linked publicly as a ZIP but is not retained in this carrier. Therefore qualification, submission mechanics, questions/pre-bid dates, teaming rules, evaluation criteria, security requirements, pricing forms, insurance, and contract terms remain fail-closed `UNKNOWN`.

A current third-party mirror reports a September 30 pre-bid, October 7 question deadline, electronic submission, a 3+1+1 year term, and technical scope hints including APM/DEM/network/infrastructure/application-security monitoring, ServiceNow, OpenTelemetry, and AI-assisted troubleshooting. Those facts remain `DISCOVERY_ONLY` until the State ZIP is retained and reviewed.

## Commercial lane

Current evidence does not support a solo-platform prime posture. The near-term commercial hypothesis is a paid specialist workshare with a qualified platform vendor or integrator: telemetry inventory/migration, deterministic SLO acceptance, synthetic incident/regression packs, ServiceNow integration evidence, rollout scorecards, and AI/agent observability evaluation if allowed.

`partner_targets.json` contains research targets only. It is not an endorsement, selection, representation, or authorization to contact them.

## Single-writer outbound rule

No buyer/vendor/partner email or other external contact is authorized by this carrier. Before any touch: fresh all-access Slack census, fresh Gmail all-history census, exact Muse request, and an exact Muse `SELECTED` response for the recipient/purpose key. Re-census immediately before the single send.

## Usage

```bash
python -m opportunities.indiana_iot_observability_27_87814.gate \
  --ledger opportunities/indiana_iot_observability_27_87814/source_ledger.json \
  --requirements opportunities/indiana_iot_observability_27_87814/requirements.json \
  --partners opportunities/indiana_iot_observability_27_87814/partner_targets.json \
  --scope opportunities/indiana_iot_observability_27_87814/paid_specialist_scope.json \
  --now 2026-09-17T19:20:00Z
```

Expected current decision: `HOLD`, with every external-authority bit false.
