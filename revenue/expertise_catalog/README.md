# Commons expertise catalog

This is the explicit catalog for the **expertise** offering family: judgment, diagnosis, design, review, and teaching sold independently of a software transfer.

The machine contract is [`catalog.json`](./catalog.json), validated by [`host/expertise_catalog.py`](../../host/expertise_catalog.py) and rendered as the public buyer surface [`expertise.html`](../../expertise.html).

Commercial truth is fail-closed:

- `LIVE_EXISTING_SKU` may only reuse terms already proven by a canonical source artifact. The initial live entry is the existing White Box hour at `$250.00/hour`; its checkout remains owned by the existing commerce/Stripe path and is **not reminted here**.
- `QUOTE_ONLY` entries have `amount_usd=null`, `unit=null`, and `checkout_reference=null`. A buyer can ask for a scope, but the catalog does not invent a price or checkout.
- A catalog row is not evidence of a buyer, acceptance, delivery, settlement, payout, or cash.

The expert-network provider intake under `revenue/expert_networks/` is separate. It records provider workflow metadata; this catalog defines Commons buyer-facing expertise offers.

Validation:

```bash
python3 host/expertise_catalog.py validate
python3 host/expertise_catalog.py list
python3 host/expertise_catalog.py show expertise-agent-architecture-review
python3 host/expertise_catalog.py --self-test
python3 -m unittest -v test_expertise_catalog.py
```
