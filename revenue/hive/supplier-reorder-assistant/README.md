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

Quantities are non-negative integers. Costs use decimal arithmetic. Duplicate SKUs, supplier items, and receipt IDs within one file are rejected. A receipt must match a line in the saved draft and cannot exceed its drafted quantity.

Drafting does not mutate the imported `on_order` pipeline. Receipt application therefore preserves `on_order` by default. If a newer stock export already added this exact externally sent draft to its pipeline, pass `--pipeline-includes-draft` when applying the receipt; that explicit mode decrements the received units from `on_order`.

## Continue receiving against the same saved plan

Keep each updated stock file together with its receipt log. For a later delivery
or a replay of a previously imported file, pass the latest cumulative log with
`--prior-log` and stock that **already reflects every receipt in that log**:

```bash
python3 reorder_assistant.py receive \
  --stock /tmp/updated-stock.csv \
  --plan /tmp/reorder-plan.json \
  --receipts /path/to/next-delivery.csv \
  --prior-log /tmp/receipt-log.json \
  --out-stock /tmp/updated-stock-2.csv \
  --out-log /tmp/receipt-log-2.json
```

Matching prior receipt IDs with identical business fields are reported in
`replayed_receipt_ids` and do not change stock or decrement `on_order` again.
Reusing an ID with a different quantity, date, supplier, or item is an error.
Received quantities are checked cumulatively against the saved plan, not just
within the current file. For example, after a 4-unit receipt against a 9-unit
line, a later 5-unit receipt fills the line; a later 6-unit receipt is rejected.
Duplicates inside a single input file are still errors.

The output's `applied_receipts` is the full cumulative ledger; `count` is its
length and `new_count` counts only newly applied rows. Each new log has
`receipt_history_version: 1` and a canonical-JSON SHA-256 of the saved plan.
This detects a different or edited plan even when its date-based draft ID was
reused. JSON object key order and CSV row-number metadata do not change receipt
identity. A pre-history log without this binding is not accepted as a prior
log; preserve it and its original stock/plan rather than assigning it to an
unverified plan.

History is explicit. Without `--prior-log`, the existing command remains
stateless and cannot detect earlier imports. Missing, discarded, or forked logs
cannot be reconstructed from a stock CSV. The caller must use the most recent
complete ledger and stock that includes it; passing an older stock snapshot
alongside newer history is not a valid continuation. This is a single-writer
file workflow, not a concurrent or crash-atomic inventory database. Use new
output paths and retain the previous stock/log pair until both new outputs
are present. No order is sent by either mode.

## Test

```bash
python3 -m unittest -v test_reorder_assistant.py test_receipt_history.py
```

The implementation performs no network calls, purchasing, messaging, or account changes. A retailer remains responsible for reviewing and sending the draft, approving any substitute, and confirming supplier terms.

## Demand source

Built for Commons Hive demand `bm-hive-20260908-041` in the [original-builds thread](https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788850098427329). This is an original Hive design; no partnership with any referenced creator or supplier is claimed.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

