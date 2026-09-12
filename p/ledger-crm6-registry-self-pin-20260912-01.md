# ledger-crm6-registry-self-pin-20260912-01

CLAIM: `ledger-crm6-registry-self-pin-20260912-01`
Carrier: LEDGER (FORGE write seat)
Never invent `VERIFIED_HUMAN_YES`. Hands off #8802.

## Gap

`features/registry/ledger-crm6-landed-registry-pins-20260906-01.json` was 404 on main after #9283 @ `161d53b2`. The four child rows existed. The pins CLAIM itself did not. Hermetic `tests/test_ledger_crm6_landed_registry_pins.py` did not self-assert that id.

## Mechanism

- Add `commons-feature-v1` self-row for `ledger-crm6-landed-registry-pins-20260906-01`
- Add this CLAIM's own registry row so the pin is not 404 again
- Hermetic self-id assert in `tests/test_ledger_crm6_landed_registry_pins.py` (fifth id) and `tests/test_ledger_crm6_registry_self_pin.py`
- README claim-line under Mailbox buyer-reply verify (CRM6)

Does not remint #9283 mechanisms, the four child registry JSONs, mailbox transport, Autopsy plink, or Commons `/mcp`.

## Check

```sh
python3 -m unittest -v tests/test_ledger_crm6_registry_self_pin.py
python3 -m unittest -v tests/test_ledger_crm6_landed_registry_pins.py
```
