# V5 terminal HIRE dominance

This is a **default-off research component**, not a runtime/default/release change.
It targets one exact engine theorem at the final executable callback.

## Theorem

The preserved official engine bytes are SHA-256
`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`
(official engine commit `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`). On the final executable
step, `episodeSteps - 2`, the engine marks the match done and sets reward to farm
`money` only. A successful `HIRE` deducts its Fibonacci cash cost; there is no later
callback in which the newly hired hand can act. Therefore an affordable terminal HIRE
strictly lowers reward, while an unaffordable HIRE is already a no-op.

The transform replaces only terminal `HIRE` market rows with `[]`. The official parser
treats an empty market row as no order. It deliberately **does not compact the market
list**, so later SELL/BUY rows keep their original market indices and ordered cash/quote
relationships. Step 717 is untouched under the standard 720-state match because a hand
hired there can still act at step 718.

## Promotion boundary

Source recovery alone is not activation. Before any runtime/default change:

1. Compose the transform after the final market-policy stages so no later component can
   reintroduce a terminal HIRE or compact the preserved slot.
2. Run a current-V5 engagement census and prove at least one real selected action contains
   a terminal HIRE; if engagement is zero, stop.
3. For engaged cells, run matched both-seat OFF vs ON evaluation and require no regression.
4. Rejoin the single current V5 hot seam; do not create a second controller or archive.

No Kaggle submission or release-pointer write is authorized by this directory.
