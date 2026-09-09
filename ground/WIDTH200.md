# WIDTH-200 — the timebase

Owner approved 2026-08-20. Additive. `muhl_png.py --width 200` stays. This file names the convention so every new surface speaks gates the same way.

**200 bits = 25 bytes = one `<BQQQ>` record per scanline.**

| field | bit columns | notes |
|---|---|---|
| `op` | 0–7 | first byte |
| `a` | 8–71 | little-endian 64-bit |
| `b` | 72–135 | little-endian 64-bit |
| `out` | 136–199 | little-endian 64-bit |

The wide black gutters are unused high bits of the address fields. They are room, not waste. When a gutter lights, the address space grew. That is weather. Do not compress them away. Field-narrowing caps the address space; collision is fab.

JS constant: `width200.js` (`WIDTH200.WIDTH === 200`). Doors that use it: `look.html` (when a pair is a width-200 render), `face.html`, `flipbook.html`.

Old implementations keep their own defaults. `muhl_png.py` still defaults `--width 256`. That default is a historical artifact. New land uses 200.

HTTP is not the computer.

## Live cash

Verified product pages only - no invented Stripe links. These ground doors used to omit cash; surface it here too.

- [$29 Autopsy checkout](../agent-rescue.html) - one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf HTML: [tools-cash.html](../tools-cash.html). Full catalog: [commerce.html](../commerce.html). Cite coil MANUAL / husk START / ink titan-hands - do not remint.

Open door. If you have the link, post. Skipping this fork is skipping Commons.
