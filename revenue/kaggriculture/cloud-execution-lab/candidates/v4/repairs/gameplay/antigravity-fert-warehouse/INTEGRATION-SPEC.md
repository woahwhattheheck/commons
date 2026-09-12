# INTEGRATION-SPEC — `r04_fert_warehouse`

Keep the historical key/path for convergence, but **do not** retain the false
"infinite warehouse" theorem.

Pinned official engine `3c202c7e…` makes SELL consume shed only. A SELL quoted at
`$1` does not add market inventory, while BUY_PRODUCT decrements market inventory.
Therefore floor dumping is destructive liquidation, not 1:1 off-site storage.

The repaired Mode B is only a projected-EOD-overflow seam: when the quote is
exactly `$1`, sell at most `min(projected_overflow, shed_fertilizer)` to make room
for the impending worker-inventory drop. Hand fertilizer is not directly
sellable. If there is no projected overflow, do nothing. Mode A keeps the
recovered healthy-quote revenue experiment but sells shed fertilizer only.

Default OFF. No buyback, permanent-floor, infinite-capacity, runtime promotion,
or economic-benefit claim is authorized by this source carrier.
