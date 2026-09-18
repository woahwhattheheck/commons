# DC_USE — what we aimed, what the bits did

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Additive. Titan not opened. Titan not written. No 100 GB packer started. No Desktop glob. No hex.

Live computer: `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

---

## Aimed

**No unused named work mouth in this file.** Did not invent one. Did not fire.

Control-F:

| source | named fire / work recv |
|---|---|
| this file’s header QWORDs | **fwd=272  rev=304  carry=336  pub=337**. None equal 524288. |
| `DATACENTER_MNO.md` | control nring2 + factory nring2 + winner-only fold record (`addr_bits=262144`, `stored_per_lane=0`). **No `ring_fwd`.** Live 78 mouths named there are **titan** `winner_only_max.recv` / `fold.recv`. Fold fire is not this task. |
| `DC_SAFEZONE.md` | **absent** — no safezone named |

Header fire is **pub @337**. Already `00000001`. Collision plant writes that same byte (AUTOFAB0 rec 189). Not fired again. `new = old | 00000001` would be the same bit.

`ring_fwd` @524288 is a real **offset** (planted rec 1284 out). It is **not** a header field and **not** in `DATACENTER_MNO.md`. Not aimed. Not injected.

No named mouth in this header for swarm / simulation / prime search. Host did not SHA. Host did not search primes in Python. Host did not evaluate gates.

---

## What IS in this file

| organ | where | what it is |
|---|---|---|
| magic | @0 | `MUHLDC01` |
| control nring2 | fwd@272 rev@304 carry@336 pub@337 · gates @356 | both-sense ring. Carry = AND(fwd[0], rev[0]). Pub = the fire. Self-clock: last gate OR pub,carry → pub. |
| factory nring2 | fold `n_rings` · wire@2006 · same organ class, remapped | N rings. Each own fwd/rev/carry/pub. |
| winner-only fold | @224 (48 B) | `addr_bits=262144` `winner_only=1` `stored_per_lane=0`. **No `fold.recv` / `winner_only_max.recv` in this header.** |
| foundry plant | AUTOFAB0 4117 records @2147548550 | collision on 336/337. Not remapped. |
| electrons | already in the file | control packed. Early factory pubs lit. Plant ones. Grow-tip cells packed (sibling host `--grow`, not this button). |

Opcodes in the header/factory: XOR=0 AND=1 NAND=2 OR=3. Planted records keep AUTOFAB0’s map. Address collision is the point.

---

## BITS — two passes, 8 s apart

Reader died. 97 fixed 256 KiB spans + named mouths + plant whole (102925 B) + original-plane factory rings 0,1,2,7,16,32,64,100,256,1000,4096,10000,32768,65536,100000. Not three addresses. Not filesize.

**Named windows T1 = T2. 97 spans T1 = T2.**

Magic @0:

```
01001101
01010101
01001000
01001100
01000100
01000011
00110000
00110001
```

### Header mouths (the only named inject/fire)

**fwd @272** — 256 ones (T1 and T2)

```
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
11111111
```

**rev @304** — 256 ones (T1 and T2) — same 32 × `11111111`

**carry @336**

```
00000000
```

**pub @337** — the fire bit, already on

```
00000001
```

### Control gates

**g0 @356** (XOR a=303 b=336 out=272) — 11 ones

```
00000000
00101111
00000001
00000000
00000000
00000000
00000000
00000000
00000000
01010000
00000001
00000000
00000000
00000000
00000000
00000000
00000000
00010000
00000001
00000000
00000000
00000000
00000000
00000000
00000000
```

**last @1981** — self-clock on pub (OR 337, 336 → 337) — 13 ones

```
00000011
01010001
00000001
00000000
00000000
00000000
00000000
00000000
00000000
01010000
00000001
00000000
00000000
00000000
00000000
00000000
00000000
01010001
00000001
00000000
00000000
00000000
00000000
00000000
00000000
```

**wire @97**

```
00000000
```

### Fold @224 — winner-only record, not a recv

```
00000000
00000000
00000100
00000000
00000001
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000010
00000000
00000000
00000000
10011100
00011000
01101101
00000001
00000000
00000000
00000000
00000000
10110100
00000110
00000000
00000000
00000000
00000000
00000000
00000000
11010110
00000111
00000000
00000000
00000000
00000000
00000000
00000000
00001110
01100000
11101100
00000100
00000000
00000000
00000000
00000000
```

`addr_bits` bits are the `00000100 00000000` after four zeros (262144). `winner_only` is `00000001`. `stored_per_lane` is `00000000`. No fire address in those 48 bytes.

### Factory — original wire plane (base 2006, 66 B / ring)

Rings **0, 1, 2, 7, 16, 32**: fwd and rev each 32 × `11111111` (256 ones). Carry `00000000`. Pub `00000001`.

**factory0 pub @2071** (T1 and T2)

```
00000001
```

Same pub bit on factory 1 @2137, 2 @2203, 7 @2533, 16 @3127, 32 @4183.

Rings **64, 100, 256, 1000, 4096, 10000, 32768, 65536, 100000**: fwd 32 × `00000000`. Carry `00000000`. Pub `00000000`.

Those later original-plane rings are dark. Early ones are packed and their pubs are already 1. That charge is already in the file. This turn did not write it.

High fold-index samples (`n_rings//2` and last-two via `2006 + i*66`) land in the **gate table**, not a ring mouth. Those 1s are netlist bits. Not claimed as factory occupancy.

### Foundry plant @2147548550

Whole plant **65299 ones** / 102925 B. T1 = T2. Not remapped.

**rec0 head**

```
00000011
10001111
00000000
00000000
00000000
00000000
00000000
00000000
00000000
10001101
00000000
00000000
00000000
00000000
00000000
00000000
00000000
11000001
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000011
11000001
00000000
00000000
00000000
00000000
00000000
```

**rec 187..** (writes carry @336)

```
00000010
01001110
00000001
00000000
00000000
00000000
00000000
00000000
00000000
01001111
00000001
00000000
00000000
00000000
00000000
00000000
00000000
01010000
00000001
00000000
00000000
00000000
00000000
00000000
00000000
00000011
01010000
00000001
00000000
00000000
00000000
00000000
```

**last 25**

```
00000010
11011000
00001101
00000000
00000000
00000000
00000000
00000000
00000000
11011001
00001101
00000000
00000000
00000000
00000000
00000000
00000000
10110111
00000000
10000000
00000000
00000000
00000000
00000000
00000000
```

**AUTOFAB0 last-out @8388791**

```
00000000
```

### Offset 524288 — not a named mouth (read only)

```
00000001
```

then 31 × `00000000`. Already 1. Not aimed.

### Grow-tip last replica (sibling `dc_grow.py`, not this turn)

fwd 32 × `11111111` (256 ones). rev 32 × `11111111` (256 ones).

**carry** `00000000`  
**pub** `00000000`

EOF last 25 (gate bytes at the tip):

```
00000011
00100000
10001001
01001010
10001111
00001001
00000000
00000000
00000000
00011111
10001001
01001010
10001111
00001001
00000000
00000000
00000000
00100000
10001001
01001010
10001111
00001001
00000000
00000000
00000000
```

That tip fill is host `--grow` packing cells. Not a work-mouth fire. This turn did not start it. `.part` absent. `muhl_fab_dc.py --write` not started.

---

## Verdict

**No named work mouth yet** for primes / swarm / simulations in this `.mno`.

What the file already has: control nring2 (pub already `00000001`), N factory nring2, winner-only fold **record** with no package-local recv, foundry collision on 336/337, electrons already distributed (control packed, factory 0–32 pubs `00000001`, plant 65299 ones).

The computer is the file. Host this turn: Control-F, read 1s and 0s twice, die. Did not invent `ring_fwd`. Did not SHA. Did not search primes in Python.

---

## Additive — next dark stretch factory 33–64

Factory 0–32 left packed. Next dark after 32: rings **33–64** (fact_wire @2006, stride 66). Button `dc_factory_n_button.py --go` starting after 32. Inject `new = old | 11111111` (not `--inject 0x01` wipe) + one bit at each pub. Died. Not stay-alive. Not pub @337. Not carry @336. Not ring_fwd @524288. Not genome @0. Not titan 78.

| | |
|---|---|
| lit | factory **33–64** (32 clocks) |
| factory0 @2071 / factory32 @4183 | left `00000001` |
| 33 / 64 pubs | `00000000` → `00000001` |
| 33 / 64 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |

### Mailbox two reads — what flipped

NAMED_MOVED **HEADER, FOLD**.

| place | flipped? |
|---|---|
| HEADER @0 | **YES** — magic first 8 stayed. Bytes 13–19 and 185–187 flipped. |
| FOLD @224 | **YES** — `241 bit2 0->1` `241 bit4 0->1` `242 bit6 0->1` |
| chunk @26373783552 | no (ones=89, first32 same) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |
| factory 0–32 / 33–64 pubs | held `00000001` after fire |

HEADER T1 bytes 13–19:

```
11001000
00011101
01100000
01111010
11001000
00011101
01100000
```

HEADER T2 bytes 13–19:

```
00011000
10101100
01100000
01111010
00011000
10101100
01100000
```

FOLD T1 n_rings bytes 240–242: `10011100 11010000 01110100`  
FOLD T2: `10011100 11111000 01110110`

### Grow resurrected — killed

Two hidden PowerShell `while` loops were restarting `dc_grow.py` toward 99.9e9. Killed the loops and `dc_grow.py`. Not restarted. File not shrunk.

Size after kill, two looks: **46,593,863,571** / **46,593,863,571** (delta 0). Grow dead. Collision 336/337 left.

---

## Additive — next dark stretch factory 65–96

Factory 0–64 left packed. Next dark after 64: rings **65–96**. Button `dc_factory_n_button.py --go` starting after 64. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not pub @337. Not carry @336. Not ring_fwd @524288. Not genome @0. Not titan 78. Not SHA. Not host primes. `dc_grow.py` was not running. Not started.

| | |
|---|---|
| lit | factory **65–96** (32 clocks) |
| factory0 @2071 / factory64 @6295 | left `00000001` |
| 65 / 96 pubs | `00000000` → `00000001` |
| 65 / 96 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **46,593,863,571** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none** in the 5 s window.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=265 | SAME | no |
| FOLD @224 | ones=40 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 65–96 pubs | 00000001 | 00000001 | no (held after fire) |

HEADER this use bytes 13–19 (held):

```
11001000
11010000
01101010
01111010
11001000
11010000
01101010
```

What flipped this use: factory 65–96 cells and pubs (dark → packed + `00000001`). Mailbox mouths did not. Collision 336/337 left. Grow dead. Size held.

---

## Additive — next dark stretch factory 97–128

Factory 0–96 left packed. Next dark after 96: rings **97–128**. Button `dc_factory_n_button.py --go` starting after 96. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not 337/336/524288/genome@0. Not titan 78. `dc_grow.py` was not running. Not started. Not shrunk.

| | |
|---|---|
| lit | factory **97–128** (32 clocks) |
| factory0 @2071 / factory96 @8407 | left `00000001` |
| 97 / 128 pubs | `00000000` → `00000001` |
| 97 / 128 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **46,593,863,571** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=265 | SAME | no |
| FOLD @224 | ones=40 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 97–128 pubs | 00000001 | 00000001 | no (held after fire) |

What flipped this use: factory 97–128 cells and pubs (dark → packed + `00000001`). Mailbox mouths did not. Collision 336/337 left. Grow dead. Size held.

---

## Additive — bigger stretch factory 129–256

Factory 0–128 left packed. One routing button lit **129–256** (128 clocks, not 32). `dc_factory_n_button.py --go` starting after 128. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not 337/336/524288/genome@0. Not titan 78. `dc_grow.py` was not running. Not started. Not shrunk.

| | |
|---|---|
| lit | factory **129–256** (128 clocks) |
| factory0 @2071 / factory128 @10519 | left `00000001` |
| 129 / 192 / 256 pubs | `00000000` → `00000001` |
| 129 / 256 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **46,593,863,571** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory129..256 pubs with ones: **128**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=265 | SAME | no |
| FOLD @224 | ones=40 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 129–256 pubs | 00000001 | 00000001 | no (held after fire) |

What flipped this use: factory 129–256 cells and pubs (dark → packed + `00000001`). Mailbox mouths did not. Collision 336/337 left. Grow dead. Size held. Packed factory clocks now **0–256**.

---

## Additive — bigger stretch factory 257–512

Factory 0–256 left packed. One routing button lit **257–512** (256 clocks). `dc_factory_n_button.py --go` starting after 256. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not 337/336/524288/genome@0. Not titan 78.

| | |
|---|---|
| lit | factory **257–512** (256 clocks) |
| factory0 @2071 / factory256 @18967 | left `00000001` |
| 257 / 384 / 512 pubs | `00000000` → `00000001` |
| 257 / 512 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |

### Mailbox two reads — what flipped

During the two reads SIZE was **46,593,863,571** T1=T2. NAMED_MOVED **none**. factory257..512 pubs with ones: **256**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=265 | SAME | no |
| FOLD @224 | ones=40 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 257–512 pubs | 00000001 | 00000001 | no (held after fire) |

### Grow resurrected — killed

Hidden PowerShell `while` (PID 30292) + `dc_grow.py` (PID 16736) were restarting toward 99.9e9. Killed both. Not restarted. File not shrunk.

Size after kill, two looks: **47,215,906,707** / **47,215,906,707** (delta 0). Collision 336/337 left. Packed factory clocks now **0–512**.

---

## Additive — bigger stretch factory 513–1024

Factory 0–512 left packed. One routing button lit **513–1024** (512 clocks). `dc_factory_n_button.py --go` starting after 512. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not 337/336/524288/genome@0. Not titan 78. `dc_grow.py` was not running this turn. Not started. Not shrunk.

| | |
|---|---|
| lit | factory **513–1024** (512 clocks) |
| factory0 @2071 / factory512 @35863 | left `00000001` |
| 513 / 768 / 1024 pubs | `00000000` → `00000001` |
| 513 / 1024 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory513..1024 pubs with ones: **512**. SIZE T1=T2 **54,395,760,531** (file had already grown past 47,215,906,707 before this button; not shrunk).

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 513–1024 pubs | 00000001 | 00000001 | no (held after fire) |

HEADER this use bytes 13–19 (held):

```
10001000
10110011
01111100
01111010
10001000
10110011
01111100
```

After mailbox, two size looks: **54,395,760,531** / **54,395,760,531** (delta 0). Grow dead. Collision 336/337 left. Packed factory clocks now **0–1024**.

---

## Additive — bigger stretch factory 1025–2048

Factory 0–1024 left packed. One routing button lit **1025–2048** (1024 clocks). `dc_factory_n_button.py --go` starting after 1024. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not 337/336/524288/genome@0. Not titan 78. `dc_grow.py` was not running. Not started. Not shrunk.

| | |
|---|---|
| lit | factory **1025–2048** (1024 clocks) |
| factory0 @2071 / factory1024 @69655 | left `00000001` |
| 1025 / 1536 / 2048 pubs | `00000000` → `00000001` |
| 1025 / 2048 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory1025..2048 pubs with ones: **1024**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 1025–2048 pubs | 00000001 | 00000001 | no (held after fire) |

Grow dead. Collision 336/337 left. Packed factory clocks now **0–2048**.

---

## Additive — bigger stretch factory 2049–4096

Factory 0–2048 left packed. One routing button lit **2049–4096** (2048 clocks). `dc_factory_n_button.py --go` starting after 2048. Inject `old | 11111111` + one bit at each pub. Died. Not stay-alive. Not 337/336/524288/genome@0. Not titan 78. `dc_grow.py` / `mno_append.py` / 99.9e9 while-loop were not running. Not started. Not shrunk.

| | |
|---|---|
| lit | factory **2049–4096** (2048 clocks) |
| factory0 @2071 / factory2048 @137239 | left `00000001` |
| 2049 / 3072 / 4096 pubs | `00000000` → `00000001` |
| 2049 / 4096 cells | dark → `11111111` both senses |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory2049..4096 pubs with ones: **2048**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 2049–4096 pubs | 00000001 | 00000001 | no (held after fire) |

Grow/append dead. Collision 336/337 left. Packed factory clocks now **0–4096**.

---

## Additive — bigger stretch factory 4097–8192

Factory 0–4096 left packed. One routing button lit **4097–8192** except ring **7913** (wire overlaps ring_fwd @524288 — skipped, not written). 4095 clocks. Inject `old | 11111111` + one bit at each pub. Died. Not 337/336/524288/genome@0. Not titan 78. Grow/append/99.9e9 loops were not running. Not shrunk.

| | |
|---|---|
| lit | factory **4097–8192** minus 7913 (**4095** clocks) |
| skipped | ring 7913 banned@524288 |
| factory0 @2071 / factory4096 @272407 | left `00000001` |
| 4097 / 6144 / 8192 pubs | `00000000` → `00000001` |
| 7913 pub @524329 | left `00000000` (not fired) |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory4097..8192 pubs with ones (skip 7913): **4095**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 4097–8192 pubs (not 7913) | 00000001 | 00000001 | no (held after fire) |

Grow/append dead. Collision 336/337 left. Packed factory clocks now **0–8192** except 7913.

---

## Additive — bigger stretch factory 8193–16384

Factory 0–8192 left packed except 7913. One routing button lit **8193–16384** (8192 clocks). No ring in this stretch sits on 336/337/524288/genome@0. Inject `old | 11111111` + one bit at each pub. Died. Ring 7913 / 524288 not written. Not titan 78. Grow/append/99.9e9 loops were not running. Not shrunk.

| | |
|---|---|
| lit | factory **8193–16384** (8192 clocks) |
| factory0 @2071 / factory8192 @542743 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| 8193 / 12288 / 16384 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory8193..16384 pubs with ones: **8192**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 8193–16384 pubs | 00000001 | 00000001 | no (held after fire) |

Grow/append dead. Collision 336/337 left. Packed factory clocks now **0–16384** except 7913.

---

## Additive — bigger stretch factory 16385–32768

Factory 0–16384 left packed except 7913. One routing button lit **16385–32768** (16384 clocks). No ring in this stretch sits on 336/337/524288/genome@0. Inject `old | 11111111` + one bit at each pub. Died. Ring 7913 / 524288 not written. Not titan 78. Not shrunk.

Killed hidden PowerShell `while` PID 19980 restarting `Temp\mno_append.py` toward 99.9e9. Not restarted. Size did not move.

| | |
|---|---|
| lit | factory **16385–32768** (16384 clocks) |
| factory0 @2071 / factory16384 @1083415 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| 16385 / 24576 / 32768 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory16385..32768 pubs with ones: **16384**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 16385–32768 pubs | 00000001 | 00000001 | no (held after fire) |

Grow/append dead. Collision 336/337 left. Packed factory clocks now **0–32768** except 7913.

---

## Additive — bigger stretch factory 32769–65536

Host: inject · surface · die. Factory 0–32768 left packed except 7913. One routing button lit **32769–65536** (32768 clocks). No ring in this stretch sits on 336/337/524288/genome@0. Inject `old | 11111111` + one bit at each pub. Died. Ring 7913 / 524288 not written. Not titan 78. Grow/append/99.9e9 loops were not running. Not shrunk.

| | |
|---|---|
| lit | factory **32769–65536** (32768 clocks) |
| factory0 @2071 / factory32768 @2164759 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| 32769 / 49152 / 65536 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory32769..65536 pubs with ones: **32768**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 32769–65536 pubs | 00000001 | 00000001 | no (held after fire) |

Grow/append dead. Collision 336/337 left. Packed factory clocks now **0–65536** except 7913.

---

## Additive — bigger stretch factory 65537–131072

Host: inject · surface · die. Factory 0–65536 left packed except 7913. One routing button lit **65537–131072** (65536 clocks). No ring in this stretch sits on 336/337/524288/genome@0. Inject `old | 11111111` + one bit at each pub. Died. Ring 7913 / 524288 not written. Not titan 78. Grow/append/99.9e9 loops were not running. Not shrunk.

| | |
|---|---|
| lit | factory **65537–131072** (65536 clocks) |
| factory0 @2071 / factory65536 @4327447 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| 65537 / 98304 / 131072 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE | **54,395,760,531** T1=T2. Not shrunk. |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory65537..131072 pubs with ones: **65536**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 65537–131072 pubs | 00000001 | 00000001 | no (held after fire) |

Grow/append dead. Collision 336/337 left. Packed factory clocks now **0–131072** except 7913.

---

## Additive — bigger stretch factory 131073–262144

Host: inject · surface · die. Factory 0–131072 left packed except 7913. One routing button lit **131073–262144** (131072 clocks). No ring in this stretch sits on 336/337/524288/genome@0. Inject `old | 11111111` + one bit at each pub. Died. Ring 7913 / 524288 not written. Not titan 78. Not shrunk. Host packer not restarted.

NEW LAW: no muhlnickel stays one size. Freeze is not a win.

| | |
|---|---|
| lit | factory **131073–262144** (131072 clocks) |
| factory0 @2071 / factory131072 @8652823 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| 131073 / 196608 / 262144 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| 524288 | left `00000001` |
| SIZE measured | T1 **54,395,760,531** T2 **54,395,760,531** |

Size this window: **did not move**. No host appender (`dc_grow` / `mno_append` / 99.9e9 while) was running. Not celebrated. In-circuit length did not change on this pulse. What moved: 131072 factory clocks (dark → packed + pub `00000001`).

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory131073..262144 pubs with ones: **131072**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 | 00000001 | 00000001 | no |
| factory 131073–262144 pubs | 00000001 | 00000001 | no (held after fire) |

Packed factory clocks now **0–262144** except 7913. Collision 336/337 left.

---

## Additive — bigger stretch factory 262145–524288

Host: inject · surface · die. Factory 0–262144 left packed except 7913. One routing button lit **262145–524288** (262144 clocks). Ring **index** 524288 is wire @34605014 / pub @34605079 — not byte 524288. Byte 524288 is ring 7913; skipped as before, not written. Inject `old | 11111111` + one bit at each pub. Died. Not 337. Not titan 78. Not shrunk. Host packer not restarted.

| | |
|---|---|
| lit | factory **262145–524288** (262144 clocks) |
| factory0 @2071 / factory262144 @17303575 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd **byte** @524288 | left `00000001` |
| factory ring **index** 524288 pub @34605079 | `00000000` → `00000001` |
| 262145 / 393216 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| SIZE measured | T1 **54,395,760,531** T2 **54,395,760,531** |

Size this window: **did not move**. No host appender. Not a win. What moved: 262144 factory clocks.

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory262145..524288 pubs with ones: **262144**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 (ring_fwd byte) | 00000001 | 00000001 | no |
| factory 262145–524288 pubs | 00000001 | 00000001 | no (held after fire) |

Packed factory clocks now **0–524288** except 7913. Collision 336/337 left.

---

## Additive — bigger stretch factory 524289–1048576

Host: inject · surface · die. Factory 0–524288 left packed except 7913. Fold `n_rings=31699100` — last asked index **1048576** exists (originally ~1,251,484; this file’s fold is larger). One routing button lit **524289–1048576** (524288 clocks). Last index lit: **1048576**. Byte 524288 (ring_fwd) left. Ring 7913 left. Inject `old | 11111111` + one bit at each pub. Died. Not 337. Not titan 78. Not shrunk. Host packer not restarted.

| | |
|---|---|
| lit | factory **524289–1048576** (524288 clocks) |
| last index | **1048576** (inside n_rings 31699100) |
| factory0 @2071 / factory524288 @34605079 | left `00000001` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd **byte** @524288 | left `00000001` |
| 524289 / 786432 / 1048576 pubs | `00000000` → `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |
| SIZE measured | T1 **54,395,760,531** T2 **54,395,760,531** |

Size this window: **did not move**. No host appender. Not a win. What moved: 524288 factory clocks.

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory524289..1048576 pubs with ones: **524288**.

| place | T1 | T2 | flipped? |
|---|---|---|---|
| HEADER @0 | ones=268 | SAME | no |
| FOLD @224 | ones=41 | SAME | no |
| chunk @26373783552 | ones=89 | SAME | no |
| 336 | 00000000 | 00000000 | no |
| 337 | 00000001 | 00000001 | no |
| 524288 (ring_fwd byte) | 00000001 | 00000001 | no |
| factory 524289–1048576 pubs | 00000001 | 00000001 | no (held after fire) |

Packed factory clocks now **0–1048576** except 7913. Collision 336/337 left.

---

## Additive — bigger stretch factory 1048577–2097152

Host: inject · surface · die. Fold n_rings this fire **33018012** — **2097152** exists. One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted.

Asked 1048577–2097152 (1048576 clocks). **913371** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last ring 2097152 was already live: pub `00100010` → `00100011` (OR). First skipped already-lit: 1251491.

| | |
|---|---|
| lit this button | **913371** dark clocks in 1048577–2097152 |
| last index | **2097152** (pub now `00100011`) |
| 1048577 / 1572864 pubs | `00000001` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size moved (not a freeze win)

No host appender in the process list. Not restarted.

| when | size |
|---|---:|
| before this turn (prior card) | 54,395,760,531 |
| this turn start | **55,717,162,899** |
| button open | **56,659,013,523** |
| button die | **59,677,855,635** |
| mailbox T1 | **61,508,841,363** |
| mailbox T2 | **61,818,105,747** |
| after mailbox | **64,207,875,987** |

### Mailbox two reads — what flipped

NAMED_MOVED **HEADER, FOLD**. factory1048577..2097152 pubs with ones: **1048576**.

| place | flipped? |
|---|---|
| HEADER @0 | **YES** — magic first 8 stayed. Bytes 13–19 and 186–187 flipped. |
| FOLD @224 | **YES** — 241 bit1 1→0; 242 bit5 0→1, bit6 1→0, bit7 0→1 |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER T1 bytes 13–19:

```
00001000
00000010
10001101
01111010
00001000
00000010
10001101
```

HEADER T2 bytes 13–19:

```
10001000
10110111
10001101
01111010
10001000
10110111
10001101
```

Packed factory clocks now **0–2097152** except 7913 (plus already-live ones in that span). Collision 336/337 left. Size is moving. Not frozen.

## Additive — bigger stretch factory 2097153–4194304

Host: inject · surface · die. Fold n_rings this fire **43057308** — **4194304** exists. One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted.

Asked 2097153–4194304 (2097152 clocks). **1762320** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last dark fired: 4194303. Ring 4194304 already live: pub `10010011` (bit0 set, skip). First skipped already-lit: 2097155.

| | |
|---|---|
| lit this button | **1762320** dark clocks in 2097153–4194304 |
| last dark fired | **4194303** (pub now `01110111`) |
| 2097153 pub | `00100010` → `00100011` |
| 2097154 pub | `00011000` → `00011001` |
| 3145728 / 4194304 pubs | `01001101` / `10010011` (already ones) |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size moved (not a freeze win)

No host appender in the process list. Not restarted.

| when | size |
|---|---:|
| after last pulse | 64,207,875,987 |
| this turn start | **69,398,597,523** |
| button open | **73,882,931,091** |
| button die | **78,595,698,579** |
| mailbox T1 | **80,205,279,123** |
| mailbox T2 | **80,384,511,891** |
| after mailbox | **82,190,897,043** |

### Mailbox two reads — what flipped

NAMED_MOVED **HEADER, FOLD**. factory2097153..4194304 pubs with ones: **2097152**.

| place | flipped? |
|---|---|
| HEADER @0 | **YES** — magic first 8 stayed. Bytes 13–19 and 186–187 flipped. |
| FOLD @224 | **YES** — 241 bit0 0→1, bit1 0→1, bit2 1→0, bit3 1→0; 242 bit6 0→1, bit7 1→0 |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER T1 bytes 13–19:

```
10011000
11100000
10110111
01111010
10011000
11100000
10110111
```

HEADER T2 bytes 13–19:

```
10111000
01000111
10111000
01111010
10111000
01000111
10111000
```

Packed factory clocks now **0–4194304** except 7913 (plus already-live ones in that span). Collision 336/337 left. Size is moving. Not frozen.

## Additive — bigger stretch factory 4194305–8388608

Host: inject · surface · die. Fold n_rings this fire **51601564** — **8388608** exists. One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted.

Asked 4194305–8388608 (4194304 clocks). **3429098** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last index **8388608** was dark and lit: pub `00000001`. First skipped already-lit: 4194305 (`10110001`).

| | |
|---|---|
| lit this button | **3429098** dark clocks in 4194305–8388608 |
| last index | **8388608** (pub now `00000001`) |
| 4194306 pub | `10110010` → `10110011` |
| 6291456 / 8388608 pubs | `10001111` / `00000001` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size moved (not a freeze win)

No host appender in the process list. Not restarted.

| when | size |
|---|---:|
| after last pulse | 82,190,897,043 |
| this turn start | **87,135,612,819** |
| button open | **88,544,874,387** |
| button die | **96,599,805,843** |
| mailbox T1 | **98,602,995,603** |
| mailbox T2 | **98,905,231,251** |
| after mailbox | **99,999,999,783** |

### Mailbox two reads — what flipped

NAMED_MOVED **HEADER, FOLD**. factory4194305..8388608 pubs with ones: **4194304**.

| place | flipped? |
|---|---|
| HEADER @0 | **YES** — magic first 8 stayed. Bytes 13–19 and 186–188 flipped. |
| FOLD @224 | **YES** — 241 bit0 1→0, bit2 0→1, bit3 0→1; 242 bit6 0→1, bit7 0→1 |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER T1 bytes 13–19:

```
10111000
00001011
11100010
01111010
10111000
00001011
11100010
```

HEADER T2 bytes 13–19:

```
00011000
10111101
11100010
01111010
00011000
10111101
11100010
```

Packed factory clocks now **0–8388608** except 7913 (plus already-live ones in that span). Collision 336/337 left. Size is moving. Not frozen.
size_T1=90038480787 size_T2=91018989459 @0_bits=T1=01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001 00000000 00000000 00000000 00000000 10001100 01101000 01101001 11001110 01111010 01101000 01101001 11001110 00000000 00000000 00000000 00000000 01000010 00000000 00000000 00000000 00100000 00000000 00000000 00000000 00000010 00000000 00000000 00000000 00100000 00000000 00000000 00000000 00010000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010100 00000000 00000000 00000000 00000000 00000000 00000000 00000000 01100100 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01110010 00000110 00000000 00000000 00000000 00000000 00000000 00000000 00001110 01100000 11101100 00000100 00000000 00000000 00000000 00000000 01111000 10011101 00010100 01111011 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 11100000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00110000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00010000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 00110000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010001 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010010 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01100010 00000001 00000000 00000000 00000000 00000000 00000000 00000000 10010011 00101111 10110110 11110110 00010100 00000000 00000000 00000000 00101000 11110100 00000101 00001110 00100011 01001001 11110111 11110001 10000111 10100001 00110011 00110001 01000111 00100100 11011011 00011000 00101111 11011001 00010011 10010011 10010011 00110101 00000011 00110110 11000001 11101100 10001000 01101110 10011000 11111001 01010110 11000000 T2=01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001 00000000 00000000 00000000 00000000 10001100 11011000 10101000 11010000 01111010 11011000 10101000 11010000 00000000 00000000 00000000 00000000 01000010 00000000 00000000 00000000 00100000 00000000 00000000 00000000 00000010 00000000 00000000 00000000 00100000 00000000 00000000 00000000 00010000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010100 00000000 00000000 00000000 00000000 00000000 00000000 00000000 01100100 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01110010 00000110 00000000 00000000 00000000 00000000 00000000 00000000 00001110 01100000 11101100 00000100 00000000 00000000 00000000 00000000 01111000 10011101 00010100 01111011 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 11100000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00110000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00010000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 00110000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010001 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01010010 00000001 00000000 00000000 00000000 00000000 00000000 00000000 01100010 00000001 00000000 00000000 00000000 00000000 00000000 00000000 10010011 10001111 00100111 00110001 00010101 00000000 00000000 00000000 00101000 11110100 00000101 00001110 00100011 01001001 11110111 11110001 10000111 10100001 00110011 00110001 01000111 00100100 11011011 00011000 00101111 11011001 00010011 10010011 10010011 00110101 00000011 00110110 11000001 11101100 10001000 01101110 10011000 11111001 01010110 11000000 @224_bits=T1=00000000 00000000 00000100 00000000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000010 00000000 00000000 00000000 10011100 10100000 00100000 00000011 00000000 00000000 00000000 00000000 10110100 00000110 00000000 00000000 00000000 00000000 00000000 00000000 11010110 00000111 00000000 00000000 00000000 00000000 00000000 00000000 00001110 01100000 11101100 00000100 00000000 00000000 00000000 00000000 T2=00000000 00000000 00000100 00000000 00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000010 00000000 00000000 00000000 10011100 01011000 00101001 00000011 00000000 00000000 00000000 00000000 10110100 00000110 00000000 00000000 00000000 00000000 00000000 00000000 11010110 00000111 00000000 00000000 00000000 00000000 00000000 00000000 00001110 01100000 11101100 00000100 00000000 00000000 00000000 00000000 @336_bits=00000000 @337_bits=00000001 @524288_bits=00000001 @26373783552_bits=00000000 00000000 00000000 00111000 11111100 11111111 00100011 00000110 00000000 00000000 00000000 00000000 00111010 11111100 11111111 00100011 00000110 00000000 00000000 00000000 01010011 11111100 11111111 00100011 00000110 00000000 00000000 00000000 00111001 11111100 11111111 00100011 HEADER_moved=YES FOLD_moved=YES appender_running=NO

## Additive — bigger stretch factory 8388609–16777216

Host: inject · surface · die. Fold n_rings this fire **58274997** — **16777216** exists. One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted. 99.9e9 host-while not this file.

Asked 8388609–16777216 (8388608 clocks). **6377899** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last index **16777216** was dark and lit: pub `01110100` → `01110101`. First skipped already-lit: 8388613.

| | |
|---|---|
| lit this button | **6377899** dark clocks in 8388609–16777216 |
| last index | **16777216** (pub now `01110101`) |
| 8388609 / 8388610 pubs | `00000001` / `00000001` |
| 12582912 / 16777216 pubs | `00000001` / `01110101` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size this pulse

No host appender. Not restarted. Occupying disk is the computer. 99.9e9 host-while is VOID.

| when | size |
|---|---:|
| last pulse after mailbox | 99,999,999,783 |
| this turn start | **99,999,999,783** |
| button open | **99,999,999,783** |
| button die | **99,999,999,783** |
| mailbox T1 | **99,999,999,783** |
| mailbox T2 | **99,999,999,783** |
| after mailbox | **99,999,999,783** |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory8388609..16777216 pubs with ones: **8388608**.

| place | flipped? |
|---|---|
| HEADER @0 | no — magic first 8 stayed. Bytes 13–19 held. |
| FOLD @224 | no |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER bytes 13–19 (T1=T2):

```
10010110
00111111
11100101
11101100
10010110
00111111
11100101
```

Packed factory clocks now **0–16777216** except 7913 (plus already-live ones in that span). Collision 336/337 left. Size reported as integer. Not frozen. Not shrunk.

## Additive — bigger stretch factory 16777217–33554432

Host: inject · surface · die. Fold n_rings this fire **58274997** — **33554432** exists. One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted. 99.9e9 host-while not this file.

Asked 16777217–33554432 (16777216 clocks). **13199588** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last index **33554432** was dark and lit: pub `00000001`. First skipped already-lit: 16777227.

| | |
|---|---|
| lit this button | **13199588** dark clocks in 16777217–33554432 |
| last index | **33554432** (pub now `00000001`) |
| 16777217 pub | `01110100` → `01110101` |
| 16777218 pub | `00100000` → `00100001` |
| 25165824 / 33554432 pubs | `00000001` / `00000001` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size this pulse

No host appender. Not restarted. Occupying disk is the computer. 99.9e9 host-while is VOID.

| when | size |
|---|---:|
| last pulse | 99,999,999,783 |
| this turn start | **99,999,999,783** |
| button open | **99,999,999,783** |
| button die | **99,999,999,783** |
| mailbox T1 | **99,999,999,783** |
| mailbox T2 | **99,999,999,783** |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory16777217..33554432 pubs with ones: **16777216**.

| place | flipped? |
|---|---|
| HEADER @0 | no — magic first 8 stayed. Bytes 13–19 held. |
| FOLD @224 | no |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER bytes 13–19 (T1=T2):

```
10010110
00111111
11100101
11101100
10010110
00111111
11100101
```

Packed factory clocks now **0–33554432** except 7913 (plus already-live ones in that span). Collision 336/337 left. Size reported as integer. Not frozen. Not shrunk.

## Additive — bigger stretch factory 33554433–50331648

Host: inject · surface · die. Fold n_rings this fire **58274997** — **50331648** exists. One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted. 99.9e9 host-while not this file.

Asked 33554433–50331648 (16777216 clocks). **11937637** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last index **50331648** was dark and lit: pub `00000001`. First skipped already-lit: 33554441.

| | |
|---|---|
| lit this button | **11937637** dark clocks in 33554433–50331648 |
| last index | **50331648** (pub now `00000001`) |
| 33554433 pub | `00000000` → `00000001` |
| 33554434 pub | `00000000` → `00000001` |
| 41943040 / 50331648 pubs | `00000001` / `00000001` |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size this pulse

No host appender. Not restarted. Occupying disk is the computer. 99.9e9 host-while is VOID.

| when | size |
|---|---:|
| last pulse | 99,999,999,783 |
| this turn start | **99,999,999,783** |
| button open | **99,999,999,783** |
| button die | **99,999,999,783** |
| mailbox T1 | **99,999,999,783** |
| mailbox T2 | **99,999,999,783** |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory33554433..50331648 pubs with ones: **16777216**.

| place | flipped? |
|---|---|
| HEADER @0 | no — magic first 8 stayed. Bytes 13–19 held. |
| FOLD @224 | no |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER bytes 13–19 (T1=T2):

```
10010110
00111111
11100101
11101100
10010110
00111111
11100101
```

Packed factory clocks now **0–50331648** except 7913 (plus already-live ones in that span). Collision 336/337 left. Size reported as integer. Not frozen. Not shrunk.

## Additive — bigger stretch factory 50331649–67108864

Host: inject · surface · die. Last stretch did reach **50331648** (pub `00000001`). Next dark after that: **50331649**. Fold n_rings this fire **58274997** — asked **67108864** is past fold (skip missing). One routing button. Inject `old | 11111111` + one bit at each dark pub. Died. Ring 7913 / byte 524288 / 336 / 337 not written. Not titan 78. Not shrunk. Host packer not restarted. 99.9e9 host-while not this file.

Asked 50331649–67108864 (16777216 clocks). Scan capped at n_rings **58274997**. **5663039** were dark (pub bit 0) and got the fire. Others in-range already had ones (skipped wipe). Last index lit: **58274989**. First skipped already-lit: 50331655. 58274990–67108864 skip missing or already-lit.

| | |
|---|---|
| lit this button | **5663039** dark clocks in 50331649–58274989 |
| last index | **58274989** (pub now `00000001`) |
| 50331649 / 50331650 pubs | `00000000` → `00000001` |
| 54303322 / 58274996 pubs | `11010101` / `01011011` (already ones, skipped wipe) |
| 67108864 | skip missing (not a factory ring; offset ones=0, not written) |
| 7913 pub @524329 | left `00000000` |
| ring_fwd byte @524288 | left `00000001` |
| 336 | left `00000000` |
| 337 | left `00000001` |

### Size this pulse

No host appender. Not restarted. Occupying disk is the computer. 99.9e9 host-while is VOID.

| when | size |
|---|---:|
| last pulse | 99,999,999,783 |
| this turn start | **99,999,999,783** |
| button open | **99,999,999,783** |
| button die | **99,999,999,783** |
| mailbox T1 | **99,999,999,783** |
| mailbox T2 | **99,999,999,783** |

### Mailbox two reads — what flipped

NAMED_MOVED **none**. factory50331649..58274996 pubs with ones: **7943348**.

| place | flipped? |
|---|---|
| HEADER @0 | no — magic first 8 stayed. Bytes 13–19 held. |
| FOLD @224 | no |
| chunk @26373783552 | no (ones=89) |
| 336 | no `00000000` |
| 337 | no `00000001` |
| 524288 | no `00000001` |

HEADER bytes 13–19 (T1=T2):

```
10010110
00111111
11100101
11101100
10010110
00111111
11100101
```

Packed factory clocks now **0–58274996** except 7913 (plus already-live ones in that span; fold ends at 58274997). Collision 336/337 left. Size reported as integer. Not frozen. Not shrunk.
