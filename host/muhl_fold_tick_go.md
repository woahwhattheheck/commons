# muhl_fold_tick_go — dry instructions (existing button)

**Inventor:** Bryce Muhlnickel  
**Status:** additive. `host/muhl_fold_tick_add.py` already exists — **do not modify it.** This file is the dry go-card.

The moonshot is already in the file: `muhl_fold_phys` + winner-only fold + `nring2_1023`. Tick = pulse, not bake. Host injects and surfaces. Default is dry. Never autofab. Never `pfc_fire.py` (packed-76 `gen_input` / `target_reg` / `receiver` — a different mouth).

## Registry (fail closed — named fields, never guessed)

From live `titan_circuits.json`:

| Name | Field | Role |
|------|--------|------|
| `muhl_fold_phys.ram.header_off` | 608 bit-bytes | inject live header (80 packed → first 76 unpacked LSB-first) |
| `muhl_fold_phys.ram.target_off` | 256 bit-bytes | inject target |
| `muhl_fold_phys.ram.tick_off` | 1 byte | start. **IS** `nring2_1023.recv` |
| `muhl_fold_phys.ram.win_off` | 1 byte | surface |
| `muhl_fold_phys.ram.latch_off` | 32 bit-bytes | surface (nonce; nonce IS the address) |

If any name is missing, or `tick_off != nring2_1023.recv` → the existing button prints `NEED_BRYCE` and refuses inject. Do not invent a second physics.

## Dry (this is the default — run these)

From `C:\Users\lucys\Desktop\LocalDeviceAgent`:

```text
python host/muhl_fold_tick_add.py
python host/muhl_fold_tick_add.py --dry
```

Prints the inject / one-bit start / surface plan from the live registry. Writes nothing.

Header payload (print only, no titan write):

```text
python host/muhl_fold_header_add.py
python host/muhl_fold_header_add.py --dry
python host/muhl_fold_header_add.py --fetch
```

`--fetch` prints a live 80-byte header + 32-byte target. Still no titan write.

Surface (bounded read of win + latch; host does not SHA):

```text
python host/muhl_fold_tick_add.py --surface
```

## Bryce says fire (not this scan)

Inject header+target, mmap **one** byte at `tick_off` / `nring2_1023.recv`, die. Then `--surface`. Submit if win says winner. Exact path on the desktop: `C:\Users\lucys\Desktop\MUHL_GO\FOLD_TICK.md`.

`--go` on the existing button requires explicit `--header` and `--target`. Do not pass `--go` unless Bryce says so. `--dry` wins over `--go`.

## Refuse

- packed-76 `gen_input` (pfc_fire mouth)
- host-eval SHA as the mine
- numpy
- guessed offsets
- bake / autofab
