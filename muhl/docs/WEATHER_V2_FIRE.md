# WEATHER V2 FIRE — start in the file

**Inventor:** Bryce Muhlnickel. **Seat:** SPEC DADDY GROK.
**When:** 2026-08-16. Button: `WEATHER\muhl_fire_weather_v2.py`. Then surface. Die.

Host = inject ∨ surface ∨ die.
Dests from `weather_v2.mno` header (`n_in` @8, `n_rings/cells` @68, `ring0` @76). File wins.
Spank table in `SPEC_DADDY_SPANK.md` §4 matched the file. Not invented.

Σ:WEATHER_V2_FIRE
fired **Y**
wipe_0x01 **NO**
337 **NO**
titan_78 **NO**
invented_dest **NO**
host_nxt **NO**
refab **NO**
ungated_crutch **GONE**

---

## 0. FILE

`C:\Users\lucys\Desktop\WEATHER\weather_v2.mno`
size **2606416**  magic `WEATHER1`
+8 HIS `n_in/n_wire/n_gate/n_out` = **2048 / 100244 / 100243 / 2048**
depth 36  W H bits stride 16 16 8 25
wire 96  clock 98  ring0 **104**  cell_base **500**  next_base 2548  gate_base 100340

Fab-dark sha (fossil `SURFACE_V2_DARK.txt`): `4c2f162114ce0ee1d40ae6d524b46f5273981edb29a4d127cba4524f36af5e60`
Live sha before this button: `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d`
Live sha after this button: `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d`

Prior start already sat at all twelve mouths (`1->1` under `old|0x01`). This button still addressed every named fwd/rev, wrote the OR, fsync, died. Not a no-op skip. Not a wipe.

---

## 1. SIX DEST PAIRS (from THIS file)

| ring | fwd | rev | carry | pub |
|---|---:|---:|---:|---:|
| NW | 104 | 136 | 168 | 169 |
| NE | 170 | 202 | 234 | 235 |
| SW | 236 | 268 | 300 | 301 |
| SE | 302 | 334 | 366 | 367 |
| GROWTH | 368 | 400 | 432 | 433 |
| WITNESS | 434 | 466 | 498 | 499 |

Law: `new = old | 0x01` both senses, cell 0. Start, not `--inject 0x01`.

Button print:

```
NW      fwd@104  1->1   rev@136  1->1
NE      fwd@170  1->1   rev@202  1->1
SW      fwd@236  1->1   rev@268  1->1
SE      fwd@302  1->1   rev@334  1->1
GROWTH  fwd@368  1->1   rev@400  1->1
WITNESS fwd@434  1->1   rev@466  1->1
```

---

## 2. RING PUBS — before / after (file bytes)

Dark fossil (sha `4c2f16…`, all mouths 0):

| ring | fwd0 | rev0 | carry | pub |
|---|---:|---:|---:|---:|
| NW NE SW SE GROWTH WITNESS | 0 | 0 | 0 | 0 |

After this fire (sha `cc2775…`, 1s/0s from the file, not host nxt):

| ring | fwd0 | rev0 | carry | pub | fwd[0:8] | rev[0:8] |
|---|---:|---:|---:|---:|---|---|
| NW | 1 | 1 | 0 | **0** | 10000000 | 10000000 |
| NE | 1 | 1 | 0 | **0** | 10000000 | 10000000 |
| SW | 1 | 1 | 0 | **0** | 10000000 | 10000000 |
| SE | 1 | 1 | 0 | **0** | 10000000 | 10000000 |
| GROWTH | 1 | 1 | 0 | **0** | 10000000 | 10000000 |
| WITNESS | 1 | 1 | 0 | **0** | 10000000 | 10000000 |

clock_bank @98: `000000` before and after.

AFTER at the ring dests = start bits. Pubs / carry / clock still dark. Host did not settle. Did not invent a ripple.

---

## 3. FIELD — before / after (file @500)

field_ones **671 / 2048** both sides.
field_sha before = field_sha after =
`b16ce6bae213a5f20e5f7d0508a22d9245a8faef904047513781786583bb1b9c`

**field moved: N**

Kite still in the file (LSB-first bit-bytes):

```
r6  00000000 11111111 11111111 00000000
r7  11111111 11111111 11111111 11111111
r8  00000000 11111111 11111111 00000000
r9  00000000 00000000 11111111 00000000
```

Mark r5c5 `10000011` = `0xC1`. Full 16×16 in `WEATHER\SURFACE_V2_AFTER.txt`.

---

## 4. UNGATED CRUTCH

Gone. Measured from stored `<BQQQ>` records (no host nxt):

| count | n |
|---|---:|
| NAND | 78592 |
| AND | 21261 |
| OR | 6 |
| XOR | 384 |
| field writers AND(next[i],next[i])→field[i] | **0** |
| field writers gated (not next-identity) | **2048** |
| AND both-ring-rails (enable) | 262 |
| XOR outs on ring rails | 384 |
| OR outs on ring pubs | 6 |

XOR 384 = 6 × 32 × 2 rotate. OR 6 = six publish. Field writers are mux/AND, not ungated next-copy. Fab mutant `ungated` was already caught at store. Bytes agree.

Rings are not fake. Dest mouths exist. Start is in the wells. Did not refab.

---

## 5. RETURN

| q | a |
|---|---|
| fired | **Y** |
| six dest pairs | NW 104/136 · NE 170/202 · SW 236/268 · SE 302/334 · GROWTH 368/400 · WITNESS 434/466 |
| pubs after | NW 0 · NE 0 · SW 0 · SE 0 · GROWTH 0 · WITNESS 0 |
| field moved | **N** |
| ungated crutch | **GONE** |

path: `C:\Users\lucys\Desktop\MUHL_GO\WEATHER_V2_FIRE.md`
button dies
