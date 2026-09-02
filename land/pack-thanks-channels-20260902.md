# Pack thanks — generic channel slots

Owner added TikTok as a spend channel. The shared thanks door on main is still the peer X-only owner-paste slot (`packs/thanks.html` + `ground/BUSINESS_PACK_THANKS.json`). This compose does not overwrite that door.

Machine law for independent channels: [ground/BUSINESS_PACK_THANKS_CHANNELS.json](../ground/BUSINESS_PACK_THANKS_CHANNELS.json). Helper: [host/pack_thanks_pixel.py](../host/pack_thanks_pixel.py).

When the door owner composes later, each of X / TikTok / Meta stays empty-by-default. Empty independently loads zero third-party scripts. A filled id fires one `Purchase` for that platform only. `?value=` is the pack tier price, not an earnings claim.

Checkout stays `NOT_MINTED`. Agents do not mint pixel IDs and do not spend ads.
