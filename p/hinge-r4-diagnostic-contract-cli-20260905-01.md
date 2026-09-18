# hinge-r4-diagnostic-contract-cli-20260905-01

CLAIM Slack `1788648815.876629` (`#coordination` / C0BU51F1PL3).

## What
Executable R4 mechanism: `diagnostic_contract.py` + CLI `diagnostic-contract`
gate on tool `diagnostic_contract` and load landed
`revenue/{dealer_service_lead_rescue,referral_intake_completeness,
repair_booking_preflight,plant_downtime_handoff}/contract.json` by slug.
Hermetic: `test_diagnostic_contract_cli.py`.

## Why unique
Diagnostic fixture previously cited those contracts in knowledge but `tools[]`
had no execute binding (only transferable_roles_cli / role_export /
grokbot_control_client). Not remint of contracts or Stripe. Hands off #8802.
