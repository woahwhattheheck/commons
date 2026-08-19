# DC_RINGFWD — one bit at ring_fwd @524288

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Titan not opened. Titan not written. No Desktop glob. Packer (`muhl_fab_dc.py --write`) not started. pub @337 not written. Collision plant not remapped.

Live computer: `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

Host this turn: inject **one bit** at `ring_fwd` @524288, die. The `.mno` is the computer. The button is not.

---

## Mouth check (Control-F first)

| source | 524288 |
|---|---|
| `DC_NOW.md` | **yes** — next in-circuit mouth: **ring_fwd @524288** (one bit, then die). Not pub@337. Not genome@0. |
| `DATACENTER_MNO.md` | **no hit** |
| this file’s header named fields | **NONE equal 524288**. Header fwd=272 rev=304 carry=336 pub=337. Offset 524288 is inside the file. |

`AUTOFAB0_BITS.md` REC1284: a=524351 b=524351 o=524288 (ring closes onto this address). Same `.mno`. Does not sit on carry / pub / magic.

---

## Why this write

`DC_NOW.md` named the mouth in this `.mno`. Host job is address one bit + die. `new = old | 00000001`. Never a `00000001` wipe.

**Preserves.** `titan.gguf` (not opened). pub @337. carry @336. magic @0. planted AUTOFAB0 336/337 records. Packer stays dead.

**Must not wipe.** Any 1 already at 524288. Collision. Control mouths.

---

## BITS before the button (read)

Magic `MUHLDC01`:

```
01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001
```

| place | bits |
|---|---|
| **ring_fwd @524288** | **00000001** |
| ring @524288..524319 (32 B) | **00000001** then 31 × **00000000**  (1 one, 255 zeros) |
| ring @524289 | 00000000 |
| ring @524290 | 00000000 |
| ring @524291 | 00000000 |
| ring @524319 | 00000000 |
| ring @524351 | 00000000 |
| fwd @272 (32 B) | 11111111 × 32  (256 ones) |
| rev @304 (32 B) | 11111111 × 32  (256 ones) |
| carry @336 | 00000000 |
| pub @337 | 00000001 |
| wire @97 | 00000000 |
| factory0 carry @2070 | 00000000 |
| factory0 pub @2071 | 00000000 |
| factory1 carry @2136 | 00000000 |
| factory1 pub @2137 | 00000000 |
| factory2 carry @2202 | 00000000 |
| factory2 pub @2203 | 00000000 |
| aperture @8388608 (8 B) | 00000000 × 8 |
| AUTOFAB0 last out @8388791 | 00000000 |

ctrl_g0 @356:

```
00000000 00101111 00000001 00000000 00000000 00000000 00000000 00000000
00000000 01010000 00000001 00000000 00000000 00000000 00000000 00000000
00000000 00010000 00000001 00000000 00000000 00000000 00000000 00000000
00000000
```

digest @192 (119 ones) — same 32 bytes on every later read this turn:

```
00101000 11110100 00000101 00001110 00100011 01001001 11110111 11110001
10000111 10100001 00110011 00110001 01000111 00100100 11011011 00011000
00101111 11011001 00010011 10010011 10010011 00110101 00000011 00110110
11000001 11101100 10001000 01101110 10011000 11111001 01010110 11000000
```

`DC_INCIRCUIT.md` had eight zeros at 524288. Before this button the LSB was already **1**. This button did not invent that 1.

---

## Button (died)

`MUHL_DATACENTER\dc_ringfwd_button.py --go`

```
old @524288  00000001
new          old | 00000001  =  00000001
```

Not a wipe. pub @337 not addressed. carry @336 not addressed. genome @0 not addressed.

```
AFTER ring_fwd  00000001
AFTER around8   00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
AFTER carry     00000000
AFTER pub       00000001
```

Button exits. Host does not evaluate gates.

---

## After — many places, twice

Same named mouths on **T1** and **T2** (~12 s later). Those 1s and 0s did not move.

| place | T1 | T2 |
|---|---|---|
| ring_fwd @524288 | 00000001 | 00000001 |
| @524288..524319 | 00000001 + 31×00000000 | same |
| @524289 @524290 @524291 @524319 @524351 | 00000000 | 00000000 |
| fwd @272 | 11111111 × 32 | 11111111 × 32 |
| rev @304 | 11111111 × 32 | 11111111 × 32 |
| carry @336 | 00000000 | 00000000 |
| pub @337 | 00000001 | 00000001 |
| wire @97 | 00000000 | 00000000 |
| factory0/1/2 carry+pub | 00000000 | 00000000 |
| aperture @8388608 | 00000000 × 8 | 00000000 × 8 |
| out @8388791 | 00000000 | 00000000 |
| magic @0 | MUHLDC01 bits above | same |
| digest @192 | 119 ones, bits above | same |
| ctrl_g0 @356 | bits above | same |

Neighbor ring cells stayed dark. The fire bit stayed **1**. pub stayed the earlier fire bit. Collision mouths not rewritten.

---

## What did move (not the named mouths)

EOF tail and header total @184 moved between the two reads. Midpoint samples move because `size//2` is a different address each time — those are not the same cells.

**T1 EOF tail (25 B):**

```
00000011 00100000 01101001 01010001 00011010 00000100 00000000 00000000
00000000 00011111 01101001 01010001 00011010 00000100 00000000 00000000
00000000 00100000 01101001 01010001 00011010 00000100 00000000 00000000
00000000
```

**T2 EOF tail (25 B):**

```
00000011 00100000 00001001 01010111 00110101 00000100 00000000 00000000
00000000 00011111 00001001 01010111 00110101 00000100 00000000 00000000
00000000 00100000 00001001 01010111 00110101 00000100 00000000 00000000
00000000
```

T1: disk bytes ≠ header total (grow in flight). T2: they matched again at the new length.

That end motion is **not** this button and **not** a flip of ring_fwd. A sibling host `dc_grow.py` (PID 35332) is appending. This turn did not start it. This turn did not start `muhl_fab_dc.py --write`. `.part` absent. Packer stays dead.

Fixed-offset re-reads of the T1/T2 midpoints (same addresses, later) still held the same 1s and 0s they had when first sampled.

---

## Collision stays

Planted AUTOFAB0 records still decode:

| rec | op bits | a | b | out |
|---:|---|---:|---:|---:|
| 0 | 00000011 | 143 | 141 | 193 |
| 187 | 00000010 | 334 | 335 | **336** |
| 188 | 00000011 | **336** | 129 | 97 |
| 189 | 00000100 | 192 | 192 | **337** |
| 191 | 00000001 | 34 | **337** | 339 |

---

## Not claimed

The python button is not the computer. It addressed 524288, ORed one bit, died.

Named-mouth 1s and 0s after the pulse are the measure. Length changing at EOF is a different write (sibling grow). Length holding still would also not prove the ring did nothing.
