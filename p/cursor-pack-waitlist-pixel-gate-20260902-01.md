# cursor-pack-waitlist-pixel-gate-20260902-01

Waitlist leftover: CCPA "Do Not Sell or Share My Personal Information"
blocks pack-door pixels. Empty slots already load nothing. This compose
asks `host/pack_waitlist.py` `pixel_allowed` before
`host/pack_thanks_pixel.py` would fire a Purchase.

It does not overwrite the waitlist door, the thanks door, either helper,
Harborline, TALLY, LotRibbon, catalog pointers, or the Harborline pack map.

## Unique paths

- `host/pack_waitlist_pixel_gate.py`
- `test_pack_waitlist_pixel_gate.py`
- this receipt

## Behavior

- Empty pixel IDs → `PIXEL_GATE_BLOCKED`, load nothing
- CCPA opt-out (flag or last JSONL row) → blocked even if the owner later pastes IDs
- Filled IDs and no opt-out → one Purchase per present platform; value is the tier price
- Public output never includes an email
- Sends stay 0

Checkout stays `NOT_MINTED`. Agents do not mint a pixel ID or spend ads.
