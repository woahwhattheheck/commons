# V5 S2 milk-shop-gated sheep swap

Status: **default-OFF current-ABI candidate; not promoted**.

This directory carries exactly one recovered S2 donor into the V5 candidate tree. The donor blob is byte-identical to Git blob `84b025aa9ead6bf362445ad9c3e97598c175c5fd`, recovered by commit `a04e0f0a0f2cb466f33ae89fd84bfbb6165c396e`. The current adapter consumes the existing `FrozenSelected` controller tape and the already-selected action; it does not call a producer or mint a sibling controller.

The preserved admission is intentionally narrow: the current town must contain a `YARN_STORE`, contain no milk-consuming shop, and have `WOOL >= MILK`. The donor also requires the standard engine shape, a bounded day-3..15 window, no same-day future purchase conflict, no live animal cargo/stock collision, confirmed purchase receipts before redirecting linked pickup/place actions, and no late two-YARN overlap. It may only rewrite a selected COW buy/pickup/place to SHEEP and may only top up an already-existing WOOL sale with physically harvested credited wool.

The adapter adds current-V5 fail-closed boundaries: non-frozen or terminal routes are rejected, only the current controller route is accepted, selected market queues longer than the engine-executable ten-row prefix are rejected rather than truncated, and any donor delta outside the authenticated COW→SHEEP / existing-WOOL-top-up grammar is rolled back together with candidate state.

Historical causal evidence motivating the port: the milk-shop-gated S2 variant was positive in the 88-game V4 bench audit (+395.9 mean margin/game), while the relaxed/ungated sheep variant regressed (-821.6/game). Therefore **do not relax the milk-shop or WOOL>=MILK gates**. Fresh CURRENT-V5 natural-engagement and official-engine matched economics are still required before any runtime/default activation.

Focused source checks live at `test_v5_s2_sheep_swap.py` in the lab root. The historical donor test is retained beside the donor as custody, not as promotion evidence.
