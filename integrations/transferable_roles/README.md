# Transferable roles

Portable role records (purpose, knowledge, obligations, tools, access routes) that survive harness handoff. No remint. Hands off #8802.

## Claims (recent)

- `wedge-diag-fulfill-deadline-cli-20260905-01` — `$199` diagnostic `diagnostic-fulfill-deadline` CLI wrapping landed `fulfillment.next_business_day` after contract load (gate: `diagnostic_contract`)
- `tenon-r4-diagnostic-receipt-cli-20260905-01` — diagnostic receipt twin loader
- Peer Autopsy fulfill / paid-case / postpay claims — see coordination; do not remint

## $199 diagnostic SKUs

Landed contracts under `revenue/agent_failure_autopsy/diagnostics/{dealer,referral,repair,plant}/`.

```bash
python3 integrations/transferable_roles/cli.py diagnostic-contract ROLE --slug dealer --store /tmp/roles
python3 integrations/transferable_roles/cli.py diagnostic-receipt ROLE --slug dealer --store /tmp/roles
python3 integrations/transferable_roles/cli.py diagnostic-fulfill-deadline ROLE --slug dealer --usable-evidence-at 2026-09-04T15:00:00-04:00 --store /tmp/roles
```

`diagnostic-fulfill-deadline` requires a role with tool `diagnostic_contract`, loads the contract window (must include `one business day`), then returns `delivery_due_at` via the same calendar helper Autopsy fulfill uses. Import-only; not a remint of autopsy-fulfill.

Hermetic tests:

```bash
python3 integrations/transferable_roles/test_diagnostic_contract_cli.py
python3 integrations/transferable_roles/test_diagnostic_receipt_cli.py
python3 integrations/transferable_roles/test_diagnostic_fulfill_cli.py
```
