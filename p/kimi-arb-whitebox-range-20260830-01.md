# First measured arbitrage record — White Box range audit — 2026-08-30

State: `LANDED` only when this file is read from current `main`; a branch copy is a candidate.

Bryce, 2026-08-30 00:53 EDT: "Arbitrage good idea for money." The arbitrage road (#5528) landed with a scout page, a fail-closed schema, and zero records on file. A road with no measured edge on it is infrastructure, not a business. This lane writes the first record.

## What landed

- `revenue/arbitrage/whitebox-range-audit-20260830.json`: the first schema-conformant measured opportunity. Source side: WB-RANGE on current main (`host/wb_range.py` + `host/wb_metrics.py`, PRs #5317/#5318/#5320), measured 2026-08-29 against moonshotai/Kimi-K3 (1.56 TB Safetensors) with KB-scale fetches per operation — fulfillment cost is bandwidth-scale, not storage/compute-scale. Buyer side: the published USD 250 White Box hour SKU (ACTIVE_CHARGEABLE, priced at the cited Aristek senior-specialist floor), canonical Stripe link active with charges and payouts enabled. Unit edge USD 241.45 before tax on a USD 250 engagement. State: `QUOTABLE`.
- `test_arbitrage.py`: new `ArbitrageRecordTests` class — record conforms to the schema's exact key set, enums, side definition, evidence floor (two-sided, public https URLs), economics arithmetic (unit edge = sell − buy − fees − delivery; total = unit × quantity), and the non-execution boundary (no automatic purchase/trade, provider authorization required, no cash claimed, never SETTLED here).

## Truth boundary

A `QUOTABLE` record is not a buyer, an accepted quote, a payment, or cash. Collected cash remains USD 0. Demand is still the binding constraint; this record makes one edge explicit and auditable — it does not manufacture the buyer. No contact, purchase, trade, delivery, settlement, payout, or cash is claimed by this lane.

— KIMI (K3)
