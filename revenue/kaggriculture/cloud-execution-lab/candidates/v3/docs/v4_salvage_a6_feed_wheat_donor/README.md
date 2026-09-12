# A6 feed-WHEAT donor — V4 salvage custody

Source lineage: `riot/v3.1-lane-a6@06cbe819efd49d6d871aec020abcef565c1129d3`.

Exact preserved source blobs in this directory:
- `r04_feed_wheat.py`: `5ef5de8c5d208acc5e1b1f9166bbb4ffb96e1b5e`
- `test_v3_r04_feed_wheat.py`: `6439bf3833d3d421752ad14baa560086d881b287`

The historical lane ships `r04_feed_wheat=false`. It uniquely combines a day-0..2 extra-WHEAT seed front-load, idle-worker grow/water/harvest/place logic, and a later emergency-buy cap. It is **not** equivalent to V4 F2 (hour-15 minimal pre-buy to unlock V217) or H3e (hour-23 dead-action FEED recycle), but those newer lanes share the same feed/funding surface.

This directory is source custody only. Do not copy the old router/apply/config postimages or flip the feature ON. Any V4 consumer must port the module semantics onto the then-current router, reconcile ownership/order with F2/H3e/V217/V226/V234/M1, preserve current executable-market and cash-reserve theorems, and run a fresh current-head economics gate. The old 31-game replay arithmetic is hypothesis evidence, not current V4 promotion authority.
