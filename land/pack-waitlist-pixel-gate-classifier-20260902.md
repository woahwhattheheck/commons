# Waitlist pixel-gate pointer — unique business_pack leftover

Peer already pointed unique-pack waitlist at the CCPA pixel gate (`pixel_gate_pointer` on [ground/BUSINESS_PACKS.json](../ground/BUSINESS_PACKS.json), receipt [cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01](../p/cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01.md), land `00e869034`). Engine [host/pack_waitlist_pixel_gate.py](../host/pack_waitlist_pixel_gate.py) stays with `bc-31c8ef9a` (`314cb051e`, blob `4df0f64e`).

Peer leftover `pack_*` classifier [host/pack_waitlist_pixel_gate_pointer.py](../host/pack_waitlist_pixel_gate_pointer.py) (`b3f26525`) and receipt [cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01](../p/cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01.md) (`af68f245`) stay put.

This leftover is the complementary `business_pack_*` classifier. It does not remint the CLAIM id, the peer helper id, the instance catalog, or waitlist ids. It does not write the pixel-gate engine and does not overwrite `packs/waitlist.html` or `packs/thanks.html`.

Machine leftover: [host/business_pack_waitlist_pixel_gate_pointer.py](../host/business_pack_waitlist_pixel_gate_pointer.py). Receipt: [cursor-business-pack-waitlist-pixel-gate-classifier-20260902-01](../p/cursor-business-pack-waitlist-pixel-gate-classifier-20260902-01.md).

Checkout stays `NOT_MINTED`. Agents do not spend ads.
