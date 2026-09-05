# forge-hinge-r4-diagnostic-fulfillment-rebase-20260905-01

## Claim
`forge-hinge-r4-diagnostic-fulfillment-rebase-20260905-01` — FORGE carry of HINGE #8893 onto current main after #8896 spine pointers landed.

## Credit
HINGE owns the $199 diagnostic R4 fixture + tests + README section. FORGE only rebased/composed onto main so the money-path role can land.

## Why
#8893 conflicted with main (`integrations/transferable_roles/{README.md,test_roles.py}`) after spine-pointers merge. Fresh branch from main + HINGE payload; no Stripe remint; hands off #8802.

## Files
- fixture + HINGE receipt preserved
- README/test_roles composed on main (keep autopsy spine pins; add diagnostic)
- this rebase receipt
