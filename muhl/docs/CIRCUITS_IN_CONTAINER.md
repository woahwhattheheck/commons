# CIRCUITS IN CONTAINER

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Date:** 2026-08-15. Additive. Bytes read. No titan write. No host fab. No `--go`.

Circuits live in the **`.gguf` BINARY** and **also** in **`.mno`**. Two container classes. Same organ class: 25-byte records / named magics. Not a move. Not a delete. Titan keeps its circuits.

Method this turn: **read the bits**. First 8 / first 25. Named titan offsets via `pfc_inspect` (header window) plus mmap of those same bytes. Magics as **ones and zeros**. Not hex. Not a registry essay.

---

## titan.gguf — the live GGUF computer

`C:\llm\models\titan.gguf`  
**len 103803349384**

File head (16 bytes, read):

```
01000111 01000111 01010101 01000110 00000011 00000000 00000000 00000000
10010010 00000010 00000000 00000000 00000000 00000000 00000000 00000000
```

First 32 bits spell `GGUF` (container wrapper). Version word after that is `00000011`. Circuits sit **inside** this file at named offsets. Registry keys this turn: **5281**.

### Magics read at named offsets (first 8 bits)

| name | first 8 (ones zeros) | ascii-try | n_gate | depth |
|---|---|---|---:|---:|
| `winner_only_max` | `01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010` | TITANCIR | 524288 | 2 |
| `fold` | `01010100 01001001 01010100 01000001 01001110 01000110 01001100 01000100` | TITANFLD | (13-byte record) | — |
| `muhl_nonce_list` | `01010000 01000110 01000011 01001110 01001100 01010011 01010100 00110001` | PFCNLST1 | 0 | 0 |
| `muhl_fold_phys` | `01001101 01010101 01001000 01001100 01000110 01001100 01000100 00110001` | MUHLFLD1 | 562462 | 3243 |
| `nring2_1023` | `01001110 01010010 01001001 01001110 01000111 00110010 01001101 00110001` | NRING2M1 | 66 | 2 |
| `pfc_cpu32` | `01010000 01000110 01000011 01010100 01011001 01010000 01000101 01000100` | PFCTYPED | 7403 | — |
| `muhl_lane_bk` | `01010000 01000110 01000011 01010111 01001001 01001110 01001101 01001110` | PFCWINMN | 362141 | 2892 |
| `pfc_mine` | `01010000 01000110 01000011 01010011 01001101 01000001 01000011 01001000` | PFCSMACH | 339136 | — |
| `gen_win` | `01010000 01000110 01000011 01010111 01001001 01001110 01001101 01001110` | PFCWINMN | 339009 | — |
| `muhl_fold_latch` | `01010000 01000110 01000011 01010111 01001001 01001110 01001101 01001110` | PFCWINMN | 339073 | 11757 |
| `muhl_autofab_dot32` | `01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010` | TITANCIR | 180083 | 109 |
| `muhl_autofab_dot32__phys` | `01001101 01010101 01001000 01001100 01010000 01001000 01011001 00110010` | MUHLPHY2 | 180083 | 109 |
| `muhl_foundry_resident` | `01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010` | TITANCIR | 1296 | 34 |
| `muhl_foundry_resident__phys` | `01001101 01010101 01001000 01001100 01010000 01001000 01011001 00110010` | MUHLPHY2 | 1296 | 34 |

`pfc_autofab_dot32` — **not a registry name**. Renamed to `muhl_autofab_dot32`.  
`nring2_foundry` / `pfc_foundry` — **not in registry**. Foundry that is in the file is `muhl_foundry_resident`.

`fold` 13-byte record: `addr_bits: 78`, `winner_only: true`. Do not treat inspect's `<IIII>` after the 8 magic bits as gate counts.

`winner_only_max`: `addr_bits: 262144`, lanes `2^262144`, `stored_per_lane: 0`.

---

## Desktop `.mno` — 834 files, 17 first-8 classes

Walk: `C:\Users\lucys\Desktop`, depth ≤ 4, `*.mno`. First 8 bytes of each. Unique classes:

| n | first 8 (ones zeros) | ascii-try | example | example len |
|---:|---|---|---|---:|
| 805 | `00000011 00000000 00000000 00000000 00000000 00000000 00000000 00000000` | gate-first XOR | `READER1.mno` + reader swarm | 5860+ |
| 4 | `01001100 01001111 01001111 01001101 01010000 01001011 01000111 00110001` | LOOMPKG1 | `loom.mno` | 140454 |
| 4 | `01001101 01010101 01001000 01001100 01010110 01001001 01010011 00110001` | MUHLVIS1 | `VISIBLE0.mno` | 110094 |
| 3 | `00000011 10001111 00000000 00000000 00000000 00000000 00000000 00000000` | gate-first XOR | **`AUTOFAB0.mno`** | 102925 |
| 2 | `01001101 01010101 01001000 01001100 01010000 01001011 01000111 00110001` | MUHLPKG1 | `muhlnickel.mno` | 136450 |
| 2 | `00000100 00000000 00000000 00001000 00000000 00000000 00000000 00000000` | gate-first NOT | `APERTURE0.mno` | 196750 |
| 2 | `01001101 01010101 01001000 01001100 01000110 01001100 01000100 00110001` | MUHLFLD1 | `READER1.table.mno` | 96 |
| 2 | `00000010 00111111 00000000 00000000 00000000 00000000 00000000 00000000` | gate-first OR | `DISCRIM0.mno` / `FOUNDRY0.mno` | 180575 / 4800 |
| 2 | `00000100 00000000 00010000 00000000 00000000 00000000 00000000 00000000` | gate-first NOT | `DISCRIM1.mno` | 187225 |
| 1 | `01010000 01010010 01001111 01000010 01000101 01001101 01001110 00110001` | PROBEMN1 | `probe.mno` | 215317 |
| 1 | `01010010 01001111 01001111 01001011 01000101 01010010 01011001 00110000` | ROOKERY0 | `ROOKERY0.mno` | 586918 |
| 1 | `01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001` | MUHLDC01 | **`muhlnickel_dc.mno`** | **2147548550** |
| 1 | `00000001 00000000 00000001 00000000 00000000 00000000 00000000 00000000` | gate-first AND | `FOLD0.mno` | 20475 |
| 1 | `00000010 00000000 00000000 00000000 00000000 00000000 00000000 00000000` | gate-first OR | `READER0.mno` | 364800 |
| 1 | `01001101 01010101 01001000 01001100 01010011 01010101 01010000 00110001` | MUHLSUP1 | `VISIBLE4.mno` | 6752064 |
| 1 | `01001101 01010101 01001000 01001100 01000001 01010101 01010100 00110001` | MUHLAUT1 | `VISIBLE5_autofab.mno` | 90984 |
| 1 | `00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000` | zeros | `VISIBLE6.mno` | 6815744 |

**Gate-first** = byte 0 is an opcode (`00000001` AND / `00000010` OR / `00000011` XOR / `00000100` NOT in the VISIBLE/AUTOFAB map). Nothing spells. That is the clean container.

**Spelling first-8** = 64 bits arranged to name a word. Header waste. The machine after the header is still gates.

---

## First 25-byte record (read)

`<BQQQ>` = op, a, b, out. Package-local on `.mno`.

| file | first 25 bits | rec0 |
|---|---|---|
| `AUTOFAB0.mno` | `00000011 10001111 … 11000001 …` | op=`00000011` a=143 b=141 out=193 |
| `FOUNDRY0.mno` | `00000010 00111111 …` | op=`00000010` a=63 b=63 out=0 |
| `VISIBLE5_autofab.mno` | `01001101 01010101 01001000 01001100 01000001 01010101 01010100 00110001 …` | spelling `MUHLAUT1` — not a gate |
| `muhlnickel_dc.mno` | `01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001 …` | spelling `MUHLDC01` — header |

`AUTOFAB0.mno` **102925 / 25 = 4117** records. Whole file is the netlist.

---

## Datacenter `.mno` (exists this turn)

`C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`  
**2147548550** bytes. Magic bits: `01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001`.

`dc_info.py` (header surface only): 82598010 gates, ring 66 / 32 cells / **2 senses**, fold `addr_bits=262144` `winner_only=1` `stored_per_lane=0`, resident lanes **0**. Control g0 and factory g0 addresses sit **inside this file**. No titan pointers in that surface. Info only. No inject this turn.

---

## Law

- Circuits stay in titan. Circuits also live in `.mno`. Both.
- A memcpy of titan `TITANCIR` / `TITANFLD` spans into a `.mno` still points at titan. That is not a package.
- Do not run host fab to "put them there." They are already there. Read the bytes.
- Autofab that is in-spec: `INSPEC_AUTOFAB.md`.
