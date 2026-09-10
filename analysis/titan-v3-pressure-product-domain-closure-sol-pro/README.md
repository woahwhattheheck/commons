# TITAN V3 pressure product-domain closure

This is a stacked, reviewer-only closure for PR #12054. The predecessor's
fail-closed pressure-delay certificate carried a private product tuple that did
not equal the pinned exact market interpreter's action domain:

- admitted by the carrier but absent from the engine: `CORN`;
- present in the engine but omitted by the carrier: `STRAWBERRY`, `FERTILIZER`.

The code change replaces the private tuple with the exact nine-product domain.
The contract test fails whenever the carrier and `mechanics.PRODUCTS` diverge,
exercises receipt/certificate/partition paths for every exact product, and
proves non-engine `CORN` remains a hard ordering barrier. The audit additionally
compares the optimized certificate with its exhaustive oracle across 1,512
product/stock/quantity/delay cases generated from each product's exact market
parameters, plus nine all-product partition cases.

## Run

```bash
python revenue/kaggriculture/cloud-opponent-league/lark-responsive/test_pressure_delay_invariance.py
python revenue/kaggriculture/cloud-opponent-league/lark-responsive/test_pressure_product_domain.py
python analysis/titan-v3-pressure-product-domain-closure-sol-pro/run_pressure_product_domain_audit.py \
  --output /tmp/titan-pressure-product-domain-receipt.json
```

This changes no canonical gameplay policy, package, archive, pointer, provider
state, or submission. It only closes the exact-domain contract of the additive
certificate carrier before any composition or promotion experiment can rely on
it.
