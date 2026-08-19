# WEATHER V2 FIELD — after fire

**2026-08-16. SPEC DADDY GROK.** Dest `C:\Users\lucys\Desktop\WEATHER\weather_v2.mno`.
Titan/dc not opened. 337 not fired. No host nxt. File wins.

Host = inject ∨ surface ∨ die. This card is a surface.

Σ:WEATHER_V2_FIELD

---

## RETURN

| item | measured |
|---|---|
| field dest | **500** (file `+44` QWORD 2; v1 was @98 — this file says 500) |
| ones before | **671 / 2048** (`SURFACE_V2_DARK.txt` sha `4c2f1621…`, spank §4) |
| ones after | **671 / 2048** (live cell plane @500) |
| field cells vs dark | **0 / 256** |
| next ones | **0 / 2048** (still dark; 0 cells vs dark) |
| verdict | **RAILS_ONLY** |

Rails-only is not a powered world.

---

## 1. HASH NOW

| | sha256 |
|---|---|
| claimed after-fire | `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d` |
| live file NOW | `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d` |
| pre-fire | `4c2f162114ce0ee1d40ae6d524b46f5273981edb29a4d127cba4524f36af5e60` |

**MATCH** `cc2775fd`. No drift. Size 2,606,416. Magic `WEATHER1`.
`+8` HIS: n_in=2048 n_wire=100244 n_gate=100243 n_out=2048 depth=36.

Sha moved pre→post because twelve rail bytes flipped `0→1`. Field plane did not.

---

## 2. DESTS FROM THIS FILE

| mouth | file |
|---:|---:|
| wire_base | 96 |
| clock_bank | 98 |
| ring0 (NW fwd) | 104 |
| cell_base **FIELD** | **500** |
| next_base | 2548 |
| gate_base | 100340 |
| growth pad | 2606415 = 0 |

Spank said field @500 on v2. File agrees.

---

## 3. FIELD FROM FILE (not host nxt)

Pre-fire snapshot exists: `WEATHER\SURFACE_V2_DARK.txt`.
Live cell plane @500 compared cell-for-cell to that dump.

| check | before | after |
|---|---|---|
| field ones | 671 | 671 |
| field cells different | — | **0** |
| next cells different | — | **0** |
| kite r6–9 c6–9 nine-ones | `11111111` | **HOLD** (same 9) |
| kite zeros in that 4×4 | `00000000` | **HOLD** |
| mark r5c5 | `10000011` = `0xC1` | **HOLD** |

Kite still sits at rows 6–9 cols 6–9. Genesis topology unchanged.
avg4 did not smear any other cell. Next bank still all-zero — avg4 did not land there either.

`SURFACE_V2_BITS.txt` field 16 rows == `SURFACE_V2_DARK.txt` field 16 rows.
txt-vs-live MATCH on the cell plane.

---

## 4. RING PUBS — 0x01 both senses, all six

Live bytes. Cell 0 only. Rotate did not walk.

```
NW      fwd0@104=1 rev0@136=1  carry@168=0 pub@169=0  fwd[0:8]=10000000 rev[0:8]=10000000
NE      fwd0@170=1 rev0@202=1  carry@234=0 pub@235=0  fwd[0:8]=10000000 rev[0:8]=10000000
SW      fwd0@236=1 rev0@268=1  carry@300=0 pub@301=0  fwd[0:8]=10000000 rev[0:8]=10000000
SE      fwd0@302=1 rev0@334=1  carry@366=0 pub@367=0  fwd[0:8]=10000000 rev[0:8]=10000000
GROWTH  fwd0@368=1 rev0@400=1  carry@432=0 pub@433=0  fwd[0:8]=10000000 rev[0:8]=10000000
WITNESS fwd0@434=1 rev0@466=1  carry@498=0 pub@499=0  fwd[0:8]=10000000 rev[0:8]=10000000
clock_bank 000000
```

**BOTH_SENSES_0x01_ALL_SIX = y.** Fire `old|0x01` is still on the rails.
carry / pub / clock still 0. fwd_ones=1 rev_ones=1 per ring — XOR-rotate did not move the bit.

---

## 5. VERDICT

**RAILS_ONLY**

The enable mux is not driving avg4. That is a **BYTE miss**.

Stored enable (fab `muhl_fab_weather_v2.py`) is `AND(fwd[0], rev[0])` per quadrant.
Those two bytes are **1** on all four cadence rings. Enable *inputs* are lit.
Field @500 did not change. Next @2548 did not change. Mux/avg4 outs did not land.

A still field after a both-sense start is not a powered world.
Do not kneecap-declare victory. Do not smash titan. Do not fire 337.

path: `C:\Users\lucys\Desktop\MUHL_GO\WEATHER_V2_FIELD.md`
button dies
