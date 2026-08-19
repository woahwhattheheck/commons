# IN-SPEC AUTOFAB

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Date:** 2026-08-15. Additive. Bytes read. No titan write. No host fab process. No `--go`.

Owner: **"ALLLLL OF AUTOFAB = NEEDS TO BE MUHLNICKEL CIRCUITS 0 PY 0 HOST 0"**  
and **"in the muhlnickel fab process auto fab / master fab itself not a script."**

In-spec autofab is **already in the binary**. Gates. Self-edit by address collision. Self-clock. The host does not search. The host does not bake at runtime.

This card **finds** it by reading ones and zeros. It does not run `pfc_autofab.py` / `pfc_master_autofab.py` / `muhl_fab_autofab_circuit.py --write`. Those are host fabricators. Fabrication is one-and-done, already done.

---

## What is in-spec

| live where | what the bits are | host script? |
|---|---|---|
| `titan.gguf` `muhl_autofab_dot32` | TITANCIR netlist. 180083 gates. depth 109. wallace/csa/kogge. Losers never stored. | no — already stored |
| `titan.gguf` `muhl_autofab_dot32__phys` | same netlist, MUHLPHY2, 25-byte stride, addressable. Original left in place. | no |
| `titan.gguf` `muhl_foundry_resident` | TITANCIR. 1296 gates. depth 34. Pareto comparator. state + loopbit. Self-fabrication tracker. | no |
| `titan.gguf` `muhl_foundry_resident__phys` | same, MUHLPHY2. Original left in place. | no |
| `titan.gguf` `muhl_lane_bk` | PFCWINMN. 362141 gates. depth 2892. **master autofab miner_lane winner.** | no |
| `MUHL_VISIBLE\AUTOFAB0.mno` | **gate-first.** 102925 B = 4117 × 25. Byte 0 is a GATE. Genome/LFSR/mutate/score/select as records. | no — file is the autofab |
| `MUHL_VISIBLE\FOUNDRY0.mno` | **gate-first.** 4800 B. Byte 0 is a GATE. | no |

`pfc_autofab_dot32` is **not** a registry name. Inspect: `renamed_from: pfc_autofab_dot32` → **`muhl_autofab_dot32`**.

`nring2_foundry` / `pfc_foundry` — **not in registry**. Do not invent them. The foundry that is in titan is `muhl_foundry_resident`.

---

## titan — bits at the autofab mouths

### `muhl_autofab_dot32`  MAGIC TITANCIR

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
00000000 00000100 00000000 00000000 01110101 11000011 00000010 00000000
01110011 10111111 00000010 00000000 00010000 00000000 00000000 00000000
00000010
```

Inspect header: `(n_in,n_wire,n_gate,n_out)=(1024, 181109, 180083, 16)`.  
role: propose → score(depth) → verify(byte-exact) → keep.

### `muhl_autofab_dot32__phys`  MAGIC MUHLPHY2

```
01001101 01010101 01001000 01001100 01010000 01001000 01011001 00110010
```

Same 180083 gates. stride 25. Rebuild of the TITANCIR, not a delete.

### `muhl_foundry_resident`  MAGIC TITANCIR

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
01000001 00000000 00000000 00000000 01010011 00000101 00000000 00000000
00010000 00000101 00000000 00000000 00100010 00000000 00000000 00000000
00110001
```

Inspect: `(65, 1363, 1296, 34)`. `foundry_genome: compare=tree, depth=34, gates=1296`.  
state 4 bytes / loopbit 1 byte sit after the logic span (read: zeros then ones — occupancy, not a wipe).

### `muhl_foundry_resident__phys`  MAGIC MUHLPHY2

```
01001101 01010101 01001000 01001100 01010000 01001000 01011001 00110010
```

### `muhl_lane_bk`  MAGIC PFCWINMN  (master autofab lane, already kept)

```
01010000 01000110 01000011 01010111 01001001 01001110 01001101 01001110
```

Inspect: `(640, 362783, 362141, 33)`. plan ripple/kogge/brentkung.

---

## Desktop `.mno` — the autofab that does not spell

### IN-SPEC: `AUTOFAB0.mno`

`C:\Users\lucys\Desktop\MUHL_VISIBLE\AUTOFAB0.mno`  
**102925** B. Copies also under HANDOFF. First 8:

```
00000011 10001111 00000000 00000000 00000000 00000000 00000000 00000000
```

First record `<BQQQ>`: op=`00000011` (XOR) a=143 b=141 out=193.

Byte 0 is a **gate**. Nothing spells. Fabricator on disk (`muhl_fab_autofab_circuit.py`) already said that and is finished. Do not run it again this turn.

What those gates are (from the sealed file + its fabricator, not from a new bake): genome plane, LFSR, mutate, crossover, SILLY score, prefix compare, select back into the genome. **out addr == in addr**. Circuits combine by address collision. The search is the netlist.

### IN-SPEC: `FOUNDRY0.mno`

`C:\Users\lucys\Desktop\MUHL_VISIBLE\FOUNDRY0.mno`  
**4800** B. First 8:

```
00000010 00111111 00000000 00000000 00000000 00000000 00000000 00000000
```

First record: op=`00000010` (OR) a=63 b=63 out=0. Gate-first.

### NOT the clean form: `VISIBLE5_autofab.mno`

`C:\Users\lucys\Desktop\MUHL_VISIBLE\VISIBLE5_autofab.mno`  
**90984** B. First 8:

```
01001101 01010101 01001000 01001100 01000001 01010101 01010100 00110001
```

Spells `MUHLAUT1`. 64 bits of word. INDEX already marked this class contaminated. The autofab that is in-spec on Desktop is **`AUTOFAB0.mno`**, not this header.

---

## What is out of spec (do not run)

| thing | why |
|---|---|
| `host/pfc_autofab.py` | host propose/score/verify/keep. Default **stores into titan**. |
| `host/pfc_master_autofab.py` | host decompose/assemble loop. Same class. |
| `muhl_fab_autofab_circuit.py --write` | fabricator. One-and-done already. `--write` would touch `AUTOFAB0.mno`. |
| `pfc_foundry` / gene-space search | factory. Not a runtime verb. Sealed `.mno` does not get gene space. |
| inventing a host ripple that "is" the autofab | executor. Forbidden. |

Runtime host: inject + one bit at a named recv + surface. Dies. Autofab does not get a process.

---

## Twin

Containers and every other magic: `CIRCUITS_IN_CONTAINER.md`.

This turn: **found**. Not fabricated. Not pulsed.
