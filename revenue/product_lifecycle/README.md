# Product lifecycle tombstone

This directory is the machine-readable lifecycle boundary for customer-facing products that can appear on Commons active checkout/storefront surfaces.

`registry.json` is descriptive lifecycle state. It does **not** grant Stripe/provider mutation, payment, refund, invoice, customer-contact, payout, cash, accounting, or revenue-recognition authority.

## States

- `ACTIVE` — the product may appear on active surfaces.
- `RETIRING` — cleanup is in flight. The guard deliberately does not block yet so one retirement carrier can remove the active footprint without making current `main` permanently red.
- `RETIRED` — the recorded checkout identities and catalog sources are forbidden from active surfaces.

A retirement should compose the last active-footprint removal and the `RETIRING -> RETIRED` flip in the same semantic generation. From that point forward, stale branches that try to re-add the checkout fail the retained lifecycle guard.

## Active vs historical

`host/product_lifecycle_guard.py` scans active root `*.html` customer surfaces plus the active payment-capability and outcome-commerce catalog sources. It intentionally does not recursively scan `p/`, `by/`, `d/`, or other append-only evidence trees. Historical receipts remain evidence; retirement is not history deletion.

Checkout URL identity is normalized across scheme/host case, percent-decoding, default HTTPS port, and trailing slashes. Registry entries with query/fragment ambiguity, credentials, unsafe ports, duplicate IDs, duplicate normalized checkout identities, malformed states, or path traversal are rejected fail-closed.

## Local proof

```bash
python -m py_compile host/product_lifecycle_guard.py revenue/product_lifecycle/test_guard.py
python -m unittest -v revenue.product_lifecycle.test_guard
python -O -m unittest -v revenue.product_lifecycle.test_guard
python host/product_lifecycle_guard.py --repo-root .
python -O host/product_lifecycle_guard.py --repo-root .
```

The repository's retained `capability-entrypoints` workflow runs the same contract when lifecycle, active checkout source, or root customer HTML surfaces change.
