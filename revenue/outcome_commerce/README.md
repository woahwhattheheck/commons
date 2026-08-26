# Commons Outcome Commerce Bridge

This module turns Commons' separate commercial surfaces into one machine-readable
economic layer without changing their canonical terms.

```text
canonical offer -> catalog adapter -> quote
DIO job         -> immutable commercial events -> deterministic state projection
accepted work   -> immutable metering events -> deterministic statement
statement       -> external rail reference -> separately measured cash states
```

Run:

```bash
python3 host/outcome_commerce.py validate
python3 host/outcome_commerce.py catalog
python3 host/outcome_commerce.py quote --listing same-day-agent-survival-proof
python3 host/outcome_commerce.py quote \
  --catalog revenue/outcome_commerce/examples/hybrid_catalog.json \
  --listing synthetic-hybrid-agent \
  --metric platform=1 --metric action_units=1350 --metric outcomes=4
python3 host/outcome_commerce.py statement \
  --catalog revenue/outcome_commerce/examples/hybrid_catalog.json \
  --events revenue/outcome_commerce/examples/hybrid_events.json
python3 host/outcome_commerce.py project \
  --events revenue/outcome_commerce/examples/commercial_events.json
```

The CLI is standard-library-only, uses `Decimal`, deduplicates exact event IDs,
refuses conflicting duplicates and mixed-currency statements, applies explicit
reversals and prepaid credits, and never claims payment.

`event.schema.json` is the canonical DIO-linked commercial transition envelope.
It preserves `correlation_id`, chains predecessor events, and binds retries to a
stable `idempotency_key`. A crash after an external call enters
`UNKNOWN_EFFECT`; the projector refuses a blind retry and accepts only an
explicit provider reconciliation to `RUNNING` (effect absent) or `SUBMITTED`
(effect completed). `metering-event.schema.json` is the charge-calculation
adjunct. Neither schema moves money, contacts a buyer, or invokes a provider.

Schemas use JSON Schema draft 2020-12. Example data is synthetic and does not
represent a buyer, invoice, settlement, or collected cash.
