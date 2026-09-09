# Pack waitlist pixel-gate — pointer leftover

The CLAIM pointer
[cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01](../p/cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01.md)
is already on current main. Unique-pack
[ground/BUSINESS_PACKS.json](../ground/BUSINESS_PACKS.json) CLEARs the waitlist
CCPA pixel-gate leftover to `bc-31c8ef9a` (peer SHIP `314cb051e`).

This leftover is the `pack_*` classifier for that pointer. It does not remint
the pointer id, the waitlist pointer, or SCOUT demand
`scout-demand-pack-door-waitlist-20260902-01`. It does not write
`packs/waitlist.html`, `packs/thanks.html`, or
[host/pack_waitlist_pixel_gate.py](../host/pack_waitlist_pixel_gate.py).

Machine leftover:
[ground/BUSINESS_PACK_WAITLIST_PIXEL_GATE_POINTER.json](../ground/BUSINESS_PACK_WAITLIST_PIXEL_GATE_POINTER.json).
Helper: [host/pack_waitlist_pixel_gate_pointer.py](../host/pack_waitlist_pixel_gate_pointer.py).

CCPA opt-out blocks thanks-door pixels. Empty slots load nothing. Sends stay 0.
Checkout stays `NOT_MINTED`. Agents do not mint a pixel ID or spend ads.
