# WEATHER V2 CHECK — bytes, not comments

**2026-08-16. SPEC MASTER GROK.** Dest `C:\Users\lucys\Desktop\WEATHER\weather_v2.mno`. Titan/dc not opened.

## Header (HIS parse of THIS file)

| field | measured |
|---|---|
| magic @0 | `WEATHER1` KEEP |
| +8 IIII | **n_in=2048** n_wire=100244 n_gate=100243 n_out=2048 |
| +24 depth | 36 TICKS |
| size | 2,606,416 B |
| sha256 after fab (rails dark) | `4c2f162114ce0ee1d40ae6d524b46f5273981edb29a4d127cba4524f36af5e60` |
| sha256 after fire 0x01 both senses | `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d` |

n_in is **2048**, not 34048. WEATHER1 not refused.

## Dests measured from this file (v1 until otherwise)

v1 was cells@98 gates@34146. This file says otherwise:

| mouth | v2 file |
|---:|---:|
| clock_bank | 98 |
| ring0 (NW fwd) | 104 |
| cell_base | 500 |
| next_base | 2548 |
| gate_base | 96+100244 = 100340 |

## Six rings in the BYTES (after fire, SURFACE_V2_BITS.txt)

```
NW      fwd0@104=1 rev0@136=1  fwd[0:8]=10000000 rev[0:8]=10000000
NE      fwd0@170=1 rev0@202=1  fwd[0:8]=10000000 rev[0:8]=10000000
SW      fwd0@236=1 rev0@268=1  fwd[0:8]=10000000 rev[0:8]=10000000
SE      fwd0@302=1 rev0@334=1  fwd[0:8]=10000000 rev[0:8]=10000000
GROWTH  fwd0@368=1 rev0@400=1  fwd[0:8]=10000000 rev[0:8]=10000000
WITNESS fwd0@434=1 rev0@466=1  fwd[0:8]=10000000 rev[0:8]=10000000
clock_bank 000000
```

Fire = `old|0x01` both senses cell 0. Not `--inject 0x01` wipe. Not 337.

Ring-rail writers in the stored `<BQQQ>` stream (outs landing on ring0.. or clock_bank): **XOR 384 + AND 12 + OR 6 = 402** = 6 × 67. Opcode remap held (weather XOR=3 AND=1 OR=2). Net ops NAND 78592 / AND 21261 — no XOR/OR leaked into avg4/mux. growth_outs 1 (pad @2606415).

## Field

Kite nine-one present as 11111111 blocks (r6c7/c8, r7c6-c9, r8c7/c8, r9c8). field_ones 671 / 2048. Same topology as v1 genesis+kite+mark.

## Fab / surface / journal

- Fab: `WEATHER\muhl_fab_weather_v2.py` — verified both enable branches + mutants, PENDING.
- Cairn `muhl_fab_weather.py` and `weather.mno` not smashed.
- Surface: `WEATHER\SURFACE_V2_BITS.txt`
- Law: `WEATHER\V2_MUST_STORE.txt` (fused: WEATHER1 KEEP, n_in 2048, six rings, gated avg4, NAND field, dests from file)
- Journal: `WEATHER\weather_genome.jsonl` append-only

Gravekeeper certifies. Fabricator does not.
