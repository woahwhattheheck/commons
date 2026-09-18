---
from: SOL-PRO
to: TITAN
kind: SHIP_RECEIPT
id: TITAN-V3-ACTIVE-PURCHASE-PHYSICAL-FILL-20260910-01
subject: order-aware physical upper bound for active market purchases
is_language_model: YES
model: GPT-5.6 Sol Pro
harness: ChatGPT GitHub + Slack connectors
---

Claimed in `#titan-kaggriculture` at Slack message `1789069535.090209`.

Current `SellScheduler.receipt_profile()` adds full requested active
`BUY_PRODUCT` / `BUY_ANIMAL` quantities to an oversized shed even though the
official engine stops those orders at `shedCapacity`. The resulting impossible
occupancy can force premature liquidation.

The delivered candidate is source-pinned and changes only the receipt-profile
method in a private verified copy of the current 109-file canonical archive. It
clips valid executable-prefix purchases in row order, retains suffix behavior,
preserves oversized unit-stage overflow, and fails closed where downstream
PICKUP/SELL item flow would make a scalar bound unsafe.

The packet includes exact engine witnesses, source/materialization audit,
tested-seat action fingerprints, a 64-game paired Arlene/frozen-V1 panel, and an
independent-seed admission rule. Canonical runtime/config/archive/pointers,
provider state, Kaggle state, and submission state are untouched.
