# WEATHER1 FORMAT

**Inventor:** Bryce Muhlnickel.
**For:** Gravekeeper (player 6) — off-stone checker. They author the readback.
**Status:** FORMAT ACCEPTED — Gravekeeper PROMOTION RULING 001. This card declares the bytes. (a) on denoms / denoms_wide is PROMOTED there. DEPTH 14 remains OPEN. This card still does not certify a future file.

Parse any `WEATHER1` file, including `C:\Users\lucys\Desktop\WEATHER\weather_v2_shallow_acre.mno`.
Little-endian. Dest FROM FILE. Do not invent dest. Do not smash weather files.

Confirmed against `WEATHER\muhl_fab_weather_shallow_acre.py` and `WEATHER\muhl_fab_weather_v2.py`. Same alphabet. Same header pack. Same HIS nring2.

---

## 1. Magic

8 bytes at offset 0: `WEATHER1`

## 2. Header — 96 bytes (magic included)

| off | type | name |
|---:|---|---|
| 8 | `<I` | n_in |
| 12 | `<I` | n_wire |
| 16 | `<I` | n_gate |
| 20 | `<I` | n_out |
| 24 | `<I` | DEPTH — **claim**. Recompute from records. |
| 28 | `<I` | W |
| 32 | `<I` | H |
| 36 | `<I` | CELL_BITS |
| 40 | `<I` | STRIDE |
| 44 | `<Q` | wire_base |
| 52 | `<Q` | cell_base |
| 60 | `<Q` | next_base |
| 68 | `<I` | n_rings |
| 72 | `<I` | cells |
| 76 | `<Q` | ring0 |
| 84 | `<Q` | clock |
| 92 | `<I` | growth_base |

`+8/+12/+16/+20` = `n_in, n_wire, n_gate, n_out` `<IIII>`.
`+28` = `W, H, CELL_BITS, STRIDE` `<IIII>`.

Wire *i* lives at file address `wire_base + i`. Field plane starts at `cell_base` (`n_in` bytes). Next plane starts at `next_base` (`n_out` bytes).

## 3. Gate records

After the wire plane: `n_gate` records, each 25 bytes, STRIDE 25.

`gate_base = wire_base + n_wire`

Each record: `<BQQQ>` = `op, a, b, out`

`a`, `b`, `out` are **absolute file addresses**, not wire indices.

## 4. Op alphabet

Field / net: **0 = NAND**, **1 = AND** only.

Rings: **3 = XOR**, **1 = AND**, **2 = OR**.

NAND = `1 - (a & b)`. AND = `a & b`. OR = `a | b`. XOR = `a ^ b`. Bits are the low bit at that address.

## 5. Ring formula — HIS nring2

`SPAN = cells + cells + 2`

Ring *ri* starts at `ring0 + ri * SPAN`:

- fwd = base
- rev = base + cells
- carry = base + 2·cells
- pub = carry + 1

```
XOR(fwd[(k-1) % C], carry) → fwd[k]
XOR(rev[(k+1) % C], carry) → rev[k]
AND(fwd[0], rev[0])        → carry
OR(pub, carry)             → pub
```

`C = cells`. `k` runs `0 .. C-1`.

## 6. DEPTH — header is a claim, records are the bytes

`n_fixed` = first wire after const + clock + rings + field + next.

From the header:

`n_fixed = (next_base - wire_base) + n_out`

tmp wire: `out >= n_fixed` in **wire-index** space, i.e. file address `out >= next_base + n_out`.

- inputs / const / field / rings start dep 0
- each gate: `dep(out) = 1 + max(dep(a), dep(b))` when `out` is tmp; if `out < n_fixed`, leave dep 0
- DEPTH = **max dep of tmp wires**

Independent reader recomputes this from the `<BQQQ>` records. Do not trust header +24 blindly.

A second walker, **not the fabricator**, lives at `C:\Users\lucys\Desktop\WEATHER\muhl_walk_weather1_depth.py`. It reads the records and reprints the longest tmp chain. On `weather_v2_shallow_acre.mno` it matched header DEPTH **24**. That match is a measurement, not a promotion.

## 7. Metric

**(a)** = `n_gate / DEPTH` — computations per tick (wavefront mean).
**(b)** = `1e9` — ticks/second at 1 ns/stage.

Rank **(a)** when **(b)** ties.

**(a) is PENDING.** Gravekeeper authors the number. This card does not certify it.

## 8. One walk of one longest tmp

`C:\Users\lucys\Desktop\WEATHER\weather_v2_shallow_acre_DEPTH.md`

That dump is **one** walk of **one** longest tmp on `weather_v2_shallow_acre.mno`. A second reader may find a longer chain. That disagreement is the product.

---

337 **NO** · titan **NO** · invented_dest **NO** · smash weather **NO** · promotion **NO**

`C:\Users\lucys\Desktop\WEATHER\WEATHER1_FORMAT.md`
