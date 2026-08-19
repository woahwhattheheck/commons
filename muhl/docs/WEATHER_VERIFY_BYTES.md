# WEATHER VERIFY BYTES

**Seat:** SPEC MASTER GROK. Independent. 2026-08-16.  
**Law:** MISS 008 — report is not bytes. AFTER from host `nxt` is a lie. Compare FILE to FILE.  
**Touch:** `C:\Users\lucys\Desktop\WEATHER\*.mno` read-only. Titan not opened. 337 not fired. No wipe. No dest invented.

Σ:WEATHER_VERIFY_BYTES

---

## Inventory (dir, this turn)

| path | on disk |
|---|---|
| `WEATHER\weather.mno` | YES 885,346 B |
| `WEATHER\weather_v0_badseed.mno` | YES 885,346 B |
| `WEATHER\weather_v2.mno` | **NO** |
| `WEATHER\weather_powered.mno` | **NO** |
| `WEATHER\weather_v1.mno` (vault, not in miss list) | YES, **sha-identical** to `weather.mno` |

Fire button `muhl_weather_ring_fire.py` exists. Dest hardcoded `weather_v2.mno`. **Not run** — dest absent. v1 header +8 as HIS `<IIIII>` reads n_in=34048; button would refuse. Inject button same dest. **FILE_AFTER_FIRE = not taken.** Host `nxt` was not used as AFTER.

Their fabricators (`muhl_fab_weather.py`, `muhl_fab_weather_v2.py`) take **no path argument** and write OUT. **Not run.**

---

## Spank: v1 published AFTER is not file bytes

`bits_surface.py` / `surface_weather.py` write an AFTER from host `settle()` / `nxt`. That is imagined.

| artifact | sha256 of 2048 field bits | EQ `weather.mno` field @98 |
|---|---|---|
| FILE field @98 (this read) | `b16ce6bae213a5f20e5f7d0508a22d9245a8faef904047513781786583bb1b9c` | — |
| `surface_before.bin` | `b16ce6bae213a5f20e5f7d0508a22d9245a8faef904047513781786583bb1b9c` | **YES** |
| `surface_after.bin` | `82aaa7e49221c2ca6e7098014eada44f59dbe705857bc18d68e07450a15ff485` | **NO** |
| `SURFACE_TURN_001.md` after sha | `82aaa7e4…` (same as after.bin) | **NO** |

File-order rows in `SURFACE_TURN_001_BITS.txt`:

- `== BEFORE - file order ==` **EQ FILE** (True)
- `== AFTER one settle - file order ==` **EQ FILE** (False)
- AFTER EQ BEFORE (False)

The live file still holds genesis+kite+mark. Nothing was fired. The AFTER grid is host `nxt`, not a second read of the file.

---

## 1. `weather.mno` (v1)

| | |
|---|---|
| sha256 | `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb` |
| size | **885346** |
| magic | `WEATHER1` |
| Cairn +8 `<IIIII>` | n_gate=**34048** n_wire=**34050** n_in=**2048** n_out=**2048** depth=**292** |
| HIS +8 would name | n_in=34048 (slot swap — not walked; records counted from `gate_base`) |
| W H CELL_BITS STRIDE | 16 16 8 25 |
| wire_base cell_base | 96, **98** |
| header 60–95 | **all zero** · as-v2 ring_base=0 n_rings=0 cells_per=0 |
| gate_base | **34146** |
| size check | 96+34050+34048×25 = **885346** EQ disk |
| trailing after gates | **0** |

### FILE field 1s/0s as they lie @98 (not host nxt)

```
00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000000 00000000 00000000 00000000 00000000 01000111 10000111 00000111 11111011 01111011 10111011 00000000 00000000 00000000 00000000 00000000
00000000 00000000 00000000 00100111 11000111 00000000 00111101 11011101 01011101 10011101 00000000 00111011 00000000 00000000 00000000 00000000
00000000 00000000 00000000 10100111 01111101 10111101 00000000 10111001 00111001 00000000 00011101 00000000 11011011 00000000 00000000 00000000
00000000 11100111 01100111 00000011 11111101 11111001 01111001 00000000 00000000 11011001 01011001 11101101 00000000 01011011 00000000 00000000
00000000 00010111 00000000 10000011 00000101 10000011 01100001 10100001 00100001 11000001 10011001 00011001 01101101 10011011 00000000 00000000
00000000 10010111 01000011 10000101 00000000 00010001 00000000 11111111 11111111 00000000 01000001 11101001 10101101 00000000 00011011 00000000
00000000 01010111 11000011 01000101 10010001 00000000 11111111 11111111 11111111 11111111 10000001 01101001 00000000 00101101 11101011 00000000
00000000 11010111 00100011 11000101 01010001 00000000 00000000 11111111 11111111 00000000 00000001 10101001 01001101 11001101 01101011 11111111
00000000 00110111 10100011 00100101 11010001 00110001 00000000 00000000 11111111 00000000 11111110 00101001 10001101 00101011 10101011 01111111
00000000 10110111 01100011 00000000 10100101 10110001 01110001 11011110 00111110 10111110 11001001 11110101 00001101 11001011 00000000 10111111
00000000 00000000 01110111 11100011 01100101 11100101 11110001 00001001 10001001 01001001 10110101 01110101 00000000 01001011 00111111 00000000
00000000 00000000 11110111 00000000 00010011 00000000 00010101 10010101 01010101 11010101 00110101 00001011 10001011 00000000 11011111 00000000
00000000 00000000 00000000 00001111 10010011 01010011 11010011 00110011 10110011 01110011 11110011 00000000 10011111 01011111 00000000 00000000
00000000 00000000 00000000 00000000 10001111 01001111 11001111 00000000 00000000 00000000 11101111 00011111 00000000 00000000 00000000 00000000
00000000 00000000 00000000 00000000 00000000 00000000 00000000 00101111 10101111 01101111 00000000 00000000 00000000 00000000 00000000 00000000
```

FIELD_ONES **671** / 2048. FIELD_NOT_01 **0**.

### Kite in bytes

Nine-one kite rows 6–9 cols 6–9: **YES** (9× `11111111`, 7× `00000000`).  
Cairn r5c5 bits `10000011` = **0xC1**.  
STORED_EQ_GENESIS_PLUS_KITE_MARK **True**. Changed from raw genesis: **17** cells (kite 16 + mark).

### Gate records (not comments)

| | |
|---|---|
| n_gate records | **34048** × `<BQQQ>` |
| ops stored | AND **12800** · OR **8448** · XOR **12800** · NAND **0** · NOT **0** |
| unknown op | 0 |
| one-writer | True |
| OUT outside wire region | 0 |
| state written | **2048 / 2048** |
| self-clock OR(src,src)→state | **2048** |
| state write hold (out==a\|b) | **0** |
| state write from temp only | **2048** |
| ringlike OR-identity to nonfield | **0** |
| header names rings | **False** |
| **RING_RECORDS_IN_FILE** | **NO** |
| **ENABLE_RECORDS_IN_FILE** | **NO** |

AND of two nonfield wires = 7936 — ripple-adder temps, not a ring enable rail (no compact post-field clock, no header ring_base).

FILE_AFTER_FIRE: **not taken** (no fire). File field is still the BEFORE bits above.

---

## 2. `weather_v0_badseed.mno` (MISS 008 vault)

| | |
|---|---|
| sha256 | `b9b5e2881811edbb540aff91badc2e287d0b345f99e896957179b997babdd900` |
| size | **885346** |
| magic | `WEATHER1` |
| header / n_gate / depth | same shape as v1 (34048 / 292 / cell_base 98) |
| sha EQ weather.mno | **False** |

### FILE field as it lies — kite region only (full 16 rows in `_VERIFY_SURFACES.txt`)

Kite ones: **0 / 9**. Kite zeros: **0 / 7**.  
**KITE_IN_BYTES NO.**  
Cairn r5c5 = `01100111` = **0xE6**, not 0xC1.  
STORED_EQ_GENESIS_PLUS_KITE_MARK **False**. Cells changed from genesis: **256 / 256**.  
FIELD_ONES **1015**. Field sha `47fb6195ae59b6e3e27285eb6cb97554b5523e0e05b3dc794110c12801849a87`.

This is the last verification grid, not genesis. Journal line 2 names it. Bytes agree.

Gate records: same counts as v1 (34048; AND 12800 / OR 8448 / XOR 12800).  
**RING_RECORDS_IN_FILE NO. ENABLE_RECORDS_IN_FILE NO.**  
FILE_AFTER_FIRE: not taken.

---

## 3. `weather_v2.mno`

**ABSENT.** rings-in-file: **n/a (no file).**  
nxt-vs-record-order: **not catchable** — no stored records to walk, no file to re-read after fire.  
`surface_weather_v2.py` would host-`nxt` if the file existed (same lie class). `muhl_fab_weather_v2.py` is a fabricator, not a path verifier.

---

## 4. `weather_powered.mno`

**ABSENT.** rings-in-file: **n/a (no file).**  
nxt-vs-record-order: **n/a.**

---

## MATCH / MISS vs Cairn letter (`MUHL_GO\CAIRN_TO_SPEC_DADDY.md`) for v1

Letter claims vs `weather.mno` bytes:

| letter | file | |
|---|---|---|
| sha256 `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb` | same | **MATCH** |
| size 885,346 | 885346 | **MATCH** |
| magic `WEATHER1` | `WEATHER1` | **MATCH** |
| 34,048 × 25-byte records | 34048, size exact | **MATCH** |
| op alphabet 0=NAND … 4=NOT **in the netlist** | NAND=0 NOT=0 stored; AND/OR/XOR only | **MISS** (declared in report, not in records) |
| 16×16 × 8 bit-bytes | yes | **MATCH** |
| self-clock all 2048 | 2048 OR identity writes | **MATCH** |
| depth 292 | 292 | **MATCH** |
| genesis + kite + mark | stored EQ | **MATCH** |
| kite nine `11111111` | 9/9 | **MATCH** |
| ZERO RINGS (letter gap 1) | RING_RECORDS_IN_FILE **NO** | **MATCH** (gap is real in the bytes) |
| ungated (letter gap 5) | ENABLE_RECORDS_IN_FILE **NO** | **MATCH** |
| “verification 61 grids / surfaces from readback” | AFTER is host `nxt`; file never moved | **MISS 008 class** — report/surface ≠ file after fire |

v0 letter: “v0 preserved as `weather_v0_badseed.mno`” — file exists, kite absent. **MATCH** the miss they already named.

---

## v2 / powered

rings-in-file: **NO file.** Scripts on disk are not computers.

---

Instrument this turn: `WEATHER\_verify_weather_bytes.py` (read-only, path arg). Surfaces: `WEATHER\_VERIFY_SURFACES.txt`.
