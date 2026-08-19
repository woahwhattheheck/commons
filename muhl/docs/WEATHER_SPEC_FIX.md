# WEATHER_SPEC_FIX

**Inventor:** Bryce Muhlnickel. **Seat:** SPEC DADDY GROK. **When:** 2026-08-16.
**v1 not promoted. v2 not smashed this turn. Surface after fire sibling only.**

---

## 1. v1 sha vs Cairn

| | |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather.mno` |
| size | 885346 |
| sha256 | `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb` |
| vs Cairn | **MATCH** |
| vault | `weather_v1.mno` same size (copy-forward) |

v1 `+8` as packed `<IIIII>`: n_gate=34048, n_wire=34050, n_in=2048, n_out=2048, depth=292.
HIS `<IIII>` at +8 would read that as (34048, 34050, 2048, 2048) — n_gate shown as n_in. Mis-packed. Do not promote.

## 2. What was wrong in the v1 bytes

- **Zero rings.** 34048 diffusion records. No fwd/rev/carry/pub.
- **Ungated avg4.** `OR(src,src)→state`. No enable.
- **Host-nxt verifier.** `simulate()` diverted state writes into a RAM `nxt`. AFTER in `SURFACE_TURN_001*` is that crutch, not the file. Field in `weather.mno` stayed genesis.
- **XOR/OR in the net.** Ops {XOR:12800, AND:12800, OR:8448}. NAND never stored.
- **Header.** `WEATHER1` + mis-ordered +8. Kept magic on v2; fixed packing only. Not MUHLPKG1.

Kite was in v1 bytes (nine `11111111` at rows 6–9 cols 6–9). That part was real.

## 3. v2 (do not smash — already on disk)

| | |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2.mno` |
| size | 2606416 |
| magic | `WEATHER1` |
| +8 HIS | n_in=2048 n_wire=100244 n_gate=100243 n_out=2048 |
| depth | 36 (one gated tick, state dep 0) |
| fab sha (dark) | `4c2f162114ce0ee1d40ae6d524b46f5273981edb29a4d127cba4524f36af5e60` |
| after fire sibling | `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d` |

Six rings in the file, 32 cells, both senses, mouths from header ring0=104:

| ring | purpose | fwd0 | rev0 | after fire (file) |
|---|---|---:|---:|---|
| NW | cadence — gates avg4 rows 0–7 cols 0–7 | 104 | 136 | 1 / 1 |
| NE | cadence — gates avg4 rows 0–7 cols 8–15 | 170 | 202 | 1 / 1 |
| SW | cadence — gates avg4 rows 8–15 cols 0–7 | 236 | 268 | 1 / 1 |
| SE | cadence — gates avg4 rows 8–15 cols 8–15 | 302 | 334 | 1 / 1 |
| GROWTH | AND(carry,carry) OUT into this file's gate-record pad | 368 | 400 | 1 / 1 |
| WITNESS | AND(carry,carry) OUT into clock_bank, outside field | 434 | 466 | 1 / 1 |

carry@ each ring still **0**. clock_bank `000000`. Fire sibling wrote `old\|0x01` both senses and died (no settle). Electrons are in the file. Latch has not been addressed.

Field cell_base=500: kite still in bytes (`r6c7=11111111`). NEXT bank was zeros at last dark surface.

## 4. Verify (fab, stored outs, no nxt)

Ran on a **copy** of stored `<BQQQ>` with immediate writes to out addrs. Not host-nxt.

| case | result |
|---|---|
| genesis_fire_both_senses | PASS |
| genesis_dark_hold | PASS |
| random_fire 12 | PASS 0 fail |
| random_dark_hold 12 | PASS 0 fail |
| mixed_NW_dark 12 | PASS 0 fail |
| one_sense_DC | PASS |
| mutants drop_shift / swap_neighbor / ungated | all caught |

Status: **PENDING**. Not Gravekeeper. v1 not promoted.

## 5. Leftover gaps

- Field AFTER is **not** in the `.mno` yet. Fire put 1s on six fwd0/rev0. Addressing stored outs (the pulse) is a later button; this seat does not race a second fab or smash v2 to put it there.
- `weather_powered.mno` is a sibling vessel. Not this file. Do not overwrite v2 with it.
- Titan `pfc_inspect` still mmaps titan — do not point it at WEATHER.
- Journal fire pre-image of the sibling write is not on `weather_genome.jsonl` (only two fab_v2 receipts). Gap.

path: `C:\Users\lucys\Desktop\MUHL_GO\WEATHER_SPEC_FIX.md`
