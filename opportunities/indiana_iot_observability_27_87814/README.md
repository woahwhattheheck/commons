# Indiana IOT RFP 27-87814 - Enterprise Observability Platform

Revenue pursuit carrier for Commons issue #15651.

## Current posture

`HOLD / PARTNER-FIRST RESEARCH / NO OUTBOUND`.

The live Indiana IDOA notice identifies RFP 27-87814 / event 000670000087814, due October 28, 2026 at 3:00 PM ET, and says IOT seeks an Enterprise Observability Platform that preserves coverage, scales toward 500 monitored applications, and improves detection, resolution, and alert-quality outcomes.

The controlling State bid package is linked publicly as a ZIP but is **not retained/authenticated** in this carrier. Therefore qualification, submission mechanics, questions/pre-bid dates, teaming rules, evaluation criteria, security requirements, pricing forms, insurance, and contract terms remain fail-closed `UNKNOWN`.

A current third-party mirror reports a September 30 pre-bid, October 7 question deadline, electronic submission, a 3+1+1 year term, and technical scope hints including APM/DEM/network/infrastructure/application-security monitoring, ServiceNow, OpenTelemetry, and AI-assisted troubleshooting. Those facts remain `DISCOVERY_ONLY` until the State ZIP is independently retained and authenticated.

## Retained-evidence trust root

`source_ledger.json` and `requirements.json` are caller/input packets. Their `retained`, `PROVEN`, digest, path, and evidence-id fields are assertions only and can never authenticate themselves.

Positive qualification is possible only when all of these agree:

1. the source-literal SHA-256 pin for `authority_manifest.json`;
2. the exact authority-manifest opportunity/event/generation identity;
3. exact retained source bytes read through descriptor-anchored, no-follow traversal;
4. each retained file's SHA-256;
5. a closed retained-source inventory matching the source ledger;
6. exact evidence bindings to source, requirement, subject, scope, and generation.

The committed authority manifest is intentionally empty because this carrier does not retain the controlling State ZIP or owner qualification evidence. Its raw-byte SHA-256 is:

`4fd50658996cf65e3303d679293dd68857d1d84cf9305ee22ce02c08878c0814`

Changing the manifest, a retained source, or an evidence binding without also publishing a new reviewed source generation fails closed.

## Commercial lane

Current evidence does not support a solo-platform prime posture. The near-term commercial hypothesis is a paid specialist workshare with a qualified platform vendor or integrator: telemetry inventory/migration, deterministic SLO acceptance, synthetic incident/regression packs, ServiceNow integration evidence, rollout scorecards, and AI/agent observability evaluation if allowed.

`partner_targets.json` contains research targets only. It is not an endorsement, selection, representation, or authorization to contact them.

## Current vs historical evaluation

The default CLI uses a process-owned UTC clock. A caller cannot supply the clock for a current readiness decision:

```bash
python -m opportunities.indiana_iot_observability_27_87814.gate \
  --ledger opportunities/indiana_iot_observability_27_87814/source_ledger.json \
  --requirements opportunities/indiana_iot_observability_27_87814/requirements.json \
  --partners opportunities/indiana_iot_observability_27_87814/partner_targets.json \
  --scope opportunities/indiana_iot_observability_27_87814/paid_specialist_scope.json
```

For deterministic archaeology only, `--historical-now 2026-09-17T19:20:00Z` performs a historical replay. Historical replay is deliberately incapable of emitting `PRIME_REVIEW_READY` or `TEAMING_REVIEW_READY`.

Expected current decision with the committed empty authority root: `HOLD`, with every external-authority bit false.

## Single-writer outbound rule

No buyer/vendor/partner email or other external contact is authorized by this carrier. Before any later touch: fresh all-access Slack census, fresh Gmail all-history census, exact Muse arbitration for the recipient/purpose key, and the repository's then-current outbound collision/relationship guards. Re-census immediately before any owner-authorized send.

This package itself grants no Muse, provider, submission, payment, cash, accounting, or revenue authority.
