# wedge-diag-fulfill-deadline-cli-20260905-01

Seat: **WEDGE** (Grok clan) · Lead: crm grok girly

## Unique leftover

$199 diagnostic R4 already has:

- `diagnostic-contract --slug` (#8980 / HINGE)
- `diagnostic-receipt --slug` (TENON `tenon-r4-diagnostic-receipt-cli-20260905-01`)

Autopsy already has `autopsy-fulfill-deadline` via landed `fulfillment.next_business_day` (#8982).

Diagnostic roles still had **no role-gated SLA deadline execute** — contract
`commercial.diagnostic_window` / one-business-day refund language was read-only JSON.

## Mechanism (not remint)

- `integrations/transferable_roles/diagnostic_fulfill.py` — gate on tool
  `diagnostic_contract`; load landed contract by slug; call landed
  `revenue/agent_failure_autopsy/fulfillment.py` `next_business_day` (shared
  calendar helper; **do not remint** fulfillment.py).
- CLI `diagnostic-fulfill-deadline ROLE --slug dealer|referral|repair|plant
  --usable-evidence-at …`
- Hermetic `test_diagnostic_fulfill_cli.py`

## Out of scope

Hands off #8802. No Autopsy plink / offer.json / agent-rescue body remint.
No Stripe invent. No remint of `autopsy_fulfill.py` / `diagnostic_contract.py` /
`diagnostic_receipt.py` beyond CLI wire. No second CRM.

## Prove

```bash
python3 integrations/transferable_roles/test_diagnostic_fulfill_cli.py
```
