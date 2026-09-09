# muhl_fold_surface_add — fold SURFACE routing button

**Inventor:** Bryce Muhlnickel  
**Status:** additive. New files only. Does not edit `muhl_fold_tick_add.py`, `muhl_fold_header_add.py`, `pfc_fire.py`, or titan.

This button **surfaces**. It never injects. It never pulses tick. Default `--dry` is a bounded read of `win_off` + `latch_off` from live registry `muhl_fold_phys`. It prints the winner bit and latch bytes — what a submit would need — and does **not** broadcast to a pool.

`--submit` exists and defaults **OFF**. Do not pass `--submit` unless Bryce says so. `--go` is refused.

The file is the computer. This button does not SHA as the mine.

## Offsets (fail closed)

Read only from live `titan_circuits.json`:

| Name | Required fields |
|------|-----------------|
| `muhl_fold_phys` | `ram.win_off` (1 byte), `ram.latch_off` (32 bit-bytes) |

Missing name/fields → **FAIL CLOSED**, no guessed constants, no inject, no tick, no broadcast.

Named but not used by this button: `header_off`, `target_off`, `tick_off` (IS `nring2_1023.recv`), `nonce_off`. Those belong to the header fetch and the tick button.

## Usage

```text
python host/muhl_fold_surface_add.py
python host/muhl_fold_surface_add.py --dry
```

Default is dry: bounded SURFACE, print winner bit + latch bytes + the `mining.submit` params a broadcast would need (`wallet`, `job_id`, `en2`, `ntime`, nonce from latch). No network unless `--submit`.

`--submit` stays OFF unless the owner passes it **and** `--job` `--ntime` `--en2` from the header-fetch handshake **and** `winner_bit=1`. `--dry` wins over `--submit`.

## Non-goals

- No inject (header/target)
- No tick / no mmap of the receiver
- No pfc_fire (packed-76 path)
- No host-eval SHA as the mine
- No numpy
- No autofab
- No guessed offsets
- No `--go`
- No pool broadcast on the default run

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html)
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
