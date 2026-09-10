# Titan V3 frozen-seller active-prefix funding repair

Operation: `titan-v3-frozen-active-prefix-funding-20260909-01`
Carrier: `SOL-ANVIL`
Base commit: `c63a7e0d64d300b390b46bcc5b5c4e1331c264b5`
Base `frozen_selected.py` blob: `fc7baf5c179818a55037f6a61d92984d81d1a21c`

## Defect

`fund_same_turn_acquisition` inspected the complete inherited market list even though the pinned engine constructs each queue as `q[:max_orders]`. A failing fixed acquisition outside that executable prefix could become the modeled target, and a still-later sale could be moved into an earlier executable empty slot. The emitted action then executed the sale while the acquisition it allegedly funded remained truncated. A live acquisition could likewise consume a sale source that was not part of the inherited executable queue.

## Repair

The helper now derives one `active_end` from `maxMarketOrdersPerTurn`, evaluates only that prefix, and limits candidate sale sources to it. Invalid/nonpositive limits fail closed without mutating the inherited action. Within-prefix sale funding behavior and total-sale preservation are unchanged.

## Verification

The one-shot workflow required the new four-test regression to fail against the predecessor before applying the patch, then pass afterward. Cases cover an off-prefix target, an off-prefix source, a positive within-prefix control, and a direct assertion against the pinned engine's `queues.append(q[:max_orders])` truncation.

This is an engine-semantics repair only. It makes no leaderboard, matchup, or playing-strength claim and does not alter any canonical archive, export, default flag, provider action, route, seed, or opponent logic.
