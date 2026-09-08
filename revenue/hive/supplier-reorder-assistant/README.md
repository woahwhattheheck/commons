# Supplier Reorder Assistant

A dependency-free command-line product for specialty retailers and small wholesalers. It turns current stock, user-owned reorder rules, and supplier catalogs into **editable, unsent** purchase-order drafts. It also applies actual receipt files back to stock without losing the source receipt.

The assistant never sends an order. Exact catalog items may enter a draft. Alternatives are always emitted separately as `review_required_no_order_created`, so an unavailable product cannot silently become a substitute.

## Run the included workflow

```bash
cd revenue/hive/supplier-reorder-assistant
python3 reorder_assistant.py plan \
  --stock examples/stock.csv \
  --rules examples/rules.csv \
  --catalog examples/catalog.csv \
  --as-of 2026-09-08 \
  --out /tmp/reorder-plan.json

python3 reorder_assistant.py receive \
  --stock examples/stock.csv \
  --plan /tmp/reorder-plan.json \
  --receipts examples/receipts.csv \
  --out-stock /tmp/updated-stock.csv \
  --out-log /tmp/receipt-log.json
```

For each SKU, inventory position is `on_hand + on_order - allocated`. A rule triggers when position is at or below `reorder_at`; requested quantity restores `target_stock`. Existing pipeline stock is counted once.

Exact offers are allocated in deterministic order: preferred supplier, unit price, lead time, supplier ID, then supplier SKU. A catalog shortage is visible in `exceptions`. The draft contains no suggested substitute and records `orders_sent: 0`.

## Input contracts

- `stock.csv`: `sku,name,on_hand,on_order,allocated,unit`
- `rules.csv`: `sku,reorder_at,target_stock,preferred_supplier`
- `catalog.csv`: `supplier_id,supplier_sku,sku,description,unit_cost,available_qty,lead_days,alternative_for_sku`
- `receipts.csv`: `receipt_id,received_at,supplier_id,supplier_sku,sku,quantity`

Quantities are non-negative integers. Costs use decimal arithmetic. Duplicate SKUs, supplier items, and receipt IDs are rejected. A receipt must match a line in the saved draft and cannot exceed its drafted quantity.

Drafting does not mutate the imported `on_order` pipeline. Receipt application therefore preserves `on_order` by default. If a newer stock export already added this exact externally sent draft to its pipeline, pass `--pipeline-includes-draft` when applying the receipt; that explicit mode decrements the received units from `on_order`.

## Test

```bash
python3 -m unittest -v test_reorder_assistant.py
```

The implementation performs no network calls, purchasing, messaging, or account changes. A retailer remains responsible for reviewing and sending the draft, approving any substitute, and confirming supplier terms.

## Demand source

Built for Commons Hive demand `bm-hive-20260908-041` in the [original-builds thread](https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788850098427329). This is an original Hive design; no partnership with any referenced creator or supplier is claimed.
