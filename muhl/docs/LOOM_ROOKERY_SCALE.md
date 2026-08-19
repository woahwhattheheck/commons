# LOOM_ROOKERY_SCALE — grow `loom.mno` and `ROOKERY0.mno`

**Inventor:** Bryce Muhlnickel  
**Date:** 2026-08-15  
**Scope:** only  
`C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno` and  
`C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\ROOKERY0.mno`.  
Circuits live in those binaries. No titan write. No git. No `--go`. No grow file this turn.

Two containers. Two magics. Two size laws. Do not mix opcode tables. Do not overwrite either sealed dest.

GitHub is a **private archive SIZE gate**, not a distribution gate. This file is the grow map.

---

## 1. What already exists (exact)

### LOOM — same header math as DISTRO, different net / tick count

Shipped folder. Runtime does not fabricate.

| path | role | measured size |
|---|---|---:|
| `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno` | the computer (netlist + ring + planes) | **140,454 B** |
| `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\run_muhlnickel.py` | reader: shoot both senses, then surface | 7,609 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\MANIFEST.sha256` | tamper digest; `.mno` listed as `sha256-machine` | 1,095 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\README.md` | product doc | 3,538 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\Muhlnickel.bat` | one click | 183 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\INDEX.md` | breadcrumb | 1,913 B |

Fabricator (stay on this machine; **do not run to grow** — `OUT_DIR` is this LOOM folder):

| path | role |
|---|---|
| `C:\llm\muhl_builds\muhl_fab_loom.py` | one-and-done fab. `CELLS,SENSES,TICKS = 32,2,32768`. Magic `LOOMPKG1`. Reads titan **only at fab**. Rebuilds this package. |

**Do not run `muhl_fab_loom.py` to grow.** It would overwrite the sealed 140,454 B machine. Growth = **new file**, new dest. Seed the grow from **this** `.mno`, not titan.

### ROOKERY — different container class (no resident planes)

| path | role | measured size |
|---|---|---:|
| `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\ROOKERY0.mno` | the computer (11 rings + clock bank + records) | **586,918 B** |
| `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_fab_rookery.py` | one-and-done fab. Magic `ROOKERY0`. Genome → records. No titan. | 13,570 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_rookery_verify.py` | independent reader; only this promotes | 4,612 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_rookery_fire.py` | two host verbs: shoot both senses, surface clocks | 4,569 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\RESUME.md` | session card | 3,447 B |

**Do not run `muhl_fab_rookery.py` to grow.** `CONTAINER` is this `ROOKERY0.mno`. Growth = **new file**, new dest.

Sidecars (not the computer): `rookery_probes.json` 1,245,847 B · `rookery_genome.jsonl` 7,043,424 B.

---

## 2. Headers (measured 2026-08-15 off the two files)

### 2a. `loom.mno` — magic `LOOMPKG1`

Header **224** bytes. Little-endian. Addresses are **inside this file**. Same field map as DISTRO (`MUHLPKG1`).

| off | type | field | live value |
|---:|---|---|---|
| 0 | 8s | magic | `LOOMPKG1` |
| 8 | I | `n_in` | **16** (operand bits) |
| 12 | I | `n_wire` | **369** (= 84 + 285) |
| 16 | I | `n_gate` | **283** |
| 20 | I | `n_out` | **8** |
| 24 | I | `ring_gates` | **66** |
| 28 | I | `cells` | **32** |
| 32 | I | `senses` | **2** |
| 36 | I | `ticks` | **32768** |
| 40 | Q | `wire` | **288** |
| 48 | Q | `wire_len` | **84** |
| 56 | Q | `ring` | **657** |
| 64 | Q | `ring_len` | **1650** (= 66 × 25) |
| 72 | Q | `net` | **2307** |
| 80 | Q | `net_len` | **7075** (= 283 × 25) |
| 88 | Q | `netwire` | **372** |
| 96 | Q | `netwire_len` | **285** (= 2 + 283) |
| 104 | Q | `ans` | **9382** |
| 112 | Q | `pubplane` | **74918** |
| 120 | Q | `lanes` | **65536** |
| 128 | Q | `outs_off` | **224** |
| 136 | Q | `fwd` | **288** |
| 144 | Q | `rev` | **320** |
| 152 | Q | `carry` | **352** |
| 160 | Q | `pub` | **353** |
| 168 | Q | `opnd` | **354** |
| 176 | Q | `sel` | **370** |
| 184 | Q | `total` | **140454** |
| 192 | 32s | machine digest | `278d190728ce0124a485d86360f6dca14745d41b610a46c531922999fa8a691d` |

Layout after header (this file):

```
224    outs[n_out * 8]
288    wire: fwd[CELLS] rev[CELLS] carry[1] pub[1] opnd[NOPND] sel[2]
372    netwire[2 + n_gate]     const0, const1, one byte per gate
657    ring[ring_gates * 25]   record = <BQQQ> opcode, a, b, out
2307   net[n_gate * 25]        same record
9382   ans[lanes]
74918  pubplane[lanes]
140454 end
```

`sha256-machine` hashes header[0:192] + body with the state-wire region zeroed. Matches MANIFEST and the digest field. State wires are the input register; every shot writes them.

Magic bits @0: `01001100 01001111 01001111 01001101 01010000 01001011 01000111 00110001`

### 2b. `ROOKERY0.mno` — magic `ROOKERY0`

Header **256** bytes. Different class. No answer plane. No DISTRO/LOOM net.

| off | type | field | live value |
|---:|---|---|---|
| 0 | 8s | magic | `ROOKERY0` |
| 8 | 32s | seal | `9af6e3a1020e1b8a289e3bf66be669f7de581aacd74829c588f5ba0f5633eb38` |
| 40 | Q | `n_records` | **22563** |
| 48 | Q | `n_clocks` | **24** |
| 56 | Q | `n_rings` | **11** |
| 64 | Q | `n_cells` | **1024** |
| 72 | Q | `body_off` | **22843** |
| 80 | Q | `state_base` | **288** |
| 88 | 8B | pad | all `00000000` |
| 96 | 32s | genome digest | `75fcab01d9b847bd69d992bc148b594fc9e59d3cd1c0de71a1ed2e6d363f753f` |
| 128–255 | — | rest of header | all `00000000` |

Seal recomputes: `sha256(MAGIC + genome_hex_ascii + <QQQQ> n_records, n_clocks, n_rings, n_cells)`. Matches live bytes.

Layout (this file):

```
256    clock bank [n_clocks]     receive bytes; one writer per clock
280    pad 8
288    state  [11 × (2×1024 + 1)] = 22539 B   fwd + rev + carry per ring
22827  gap 16
22843  records [22563 × 25]
586918 end
```

Clock bank @256..279: **24 zeros**. Pad @280..287: zeros. Gap @22827..22842: zeros.

Magic bits @0: `01010010 01001111 01001111 01001011 01000101 01010010 01011001 00110000`

Live file sha256: `1cf1a9f3c1649b82d19fc78440d468483d5d4bd3bff49a3da1cc0179a3f4911d`.  
`RESUME.md` / registry still print an older digest. Size, header fields, and the closed form still match. Those two ones in state (below) are a fired electron, not a broken header. Do not revert the container because the hash moved.

Ring organs already in this binary (clock primes are the genome bank, not invented):

| ring | organ | clocks | wire_base | carry | recv |
|---:|---|---|---:|---:|---|
| 0 | sense | 11, 13 | 288 | 2336 | 256, 257 |
| 1 | sense | 11, 13 | 2337 | 4385 | 258, 259 |
| 2 | memory | 11, 13, 17 | 4386 | 6434 | 260–262 |
| 3 | tension | 11, 13 | 6435 | 8483 | 263, 264 |
| 4 | imagination | 11, 13, 17 | 8484 | 10532 | 265–267 |
| 5 | value | 11, 13 | 10533 | 12581 | 268, 269 |
| 6 | value | 11, 13 | 12582 | 14630 | 270, 271 |
| 7 | value | 11, 13 | 14631 | 16679 | 272, 273 |
| 8 | value | 11, 13 | 16680 | 18728 | 274, 275 |
| 9 | action | 11, 13, 17 | 18729 | 20777 | 276–278 |
| 10 | witness | 11 | 20778 | 22826 | 279 |

---

## 3. Opcodes — THIS package (not invented)

Record stride **25**. `struct "<BQQQ"` = opcode, addr_a, addr_b, addr_out. All three addresses are file offsets.

### LOOM (same codes as DISTRO)

| opcode byte | name | measured in `loom.mno` |
|---:|---|---|
| `00000000` = 0 | XOR | `ring[0]` @657: XOR(319, 352) → 288  (fwd rotate) |
| `00000001` = 1 | AND | `ring[64]` @657+1600: AND(288, 320) → 352  (**both senses or nothing**) |
| `00000010` = 2 | NAND | net body (AND/NAND only) |
| `00000011` = 3 | OR | `ring[65]`: OR(353, 352) → 353  (publish latch) |

Ring opcode counts: XOR **64**, AND **1**, OR **1**.  
Net opcode counts: AND **79**, NAND **204**. No XOR/OR in the net.

`net[0]` @2307: AND(354, 353) → 374 — drive gate 0 is `AND(opnd[0], PUB)`. Shared bit. Dark ring → dead datapath.

Eight outputs (predicate bits, not the DISTRO adder sums), addresses measured:  
`468, 652, 656, 489, 496, 524, 564, 525`.

### ROOKERY (different table — do not reuse 0=XOR)

| opcode byte | name | measured in `ROOKERY0.mno` |
|---:|---|---|
| `00000000` = 0 | NAND | rotate: `rec[0]` @22843: NAND(1311, 2336) → 288 |
| `00000001` = 1 | AND | contact + junctions |

Record opcode counts: NAND **22528** (= 11 × 2048), AND **35** (= 11 contacts + 24 junctions).

```
rec[0]      NAND(fwd[1023]=1311, carry=2336) → fwd[0]=288
rec[2048]   AND(fwd[0]=288, rev[0]=1312) → carry=2336
rec[2049]   AND(2336, 2336) → recv 256
rec[2050]   AND(2336, 2336) → recv 257
rec[last]   AND(22826, 22826) → recv 279   (witness junction)
```

Ring formula already in the binary (do not invent a new topology):

```
for i in 0..C-1:  NAND(fwd[(i-1)%C], carry) → fwd[i]
for i in 0..C-1:  NAND(rev[(i+1)%C], carry) → rev[i]
AND(fwd[0], rev[0]) → carry
for each clock recv: AND(carry, carry) → recv     # OUT IS the receive byte
```

---

## 4. Bits before any modify (BINARY, these files, 2026-08-15)

Reason if a later write happens: grow a **new** container. Preserve these two. Must not wipe header, ring/net/records, or (loom) planes. Must not zero a live fire because a digest moved.

### loom.mno

**fwd @288 (32 B). 22 ones. 234 zeros.**

```
00000001 00000000 00000000 00000000 00000001 00000000 00000000 00000000
00000001 00000000 00000001 00000001 00000001 00000000 00000000 00000000
00000001 00000001 00000001 00000001 00000001 00000001 00000001 00000001
00000001 00000001 00000001 00000001 00000001 00000001 00000001 00000001
```

**rev @320 (32 B). 22 ones. 234 zeros.** Same pattern as fwd (last shot wrote both senses).

**carry @352:** `00000000`  
**pub @353:** `00000000`  
**opnd @354 (16 B):** matches fwd[0:16] (operand bits of last shot).  
**sel @370 (2 B):** `00010001 00011101` = 7441 little-endian — last select address.

**ans[0:8] @9382** (lane = a + 256*b; first eight a=0..7, b=0). Eight predicate bits per lane, not DISTRO sums:

```
11000001 10100100 10100100 10000100 10100100 10000100 10000100 10100100
```

Whole answer plane: **176,962 ones**, 65,536 nonzero bytes.  
**pubplane[0:8] @74918:** `00000001` × 8. Whole plane: **65,536 ones** (every lane published).

### ROOKERY0.mno

Clock bank @256 (24 B): all `00000000`.  
State @288 first 32 B: all `00000000`. Carry r0 @2336: `00000000`. Last state @22826: `00000000`.

Whole state 288..22826: **2 ones**. Those two bits:

```
@15456  00000001    ring 7 cell 825 fwd   (seed ROOKERY-0, both senses)
@16480  00000001    ring 7 cell 825 rev
```

That is a fired electron. Do not wipe it to chase the older RESUME digest.

---

## 5. Scale knobs (what to change)

### LOOM

All knobs are in `muhl_fab_loom.py` **or** (preferred, no titan) decoded from this `.mno` and rebuilt to a **new** path.

| knob | where today | live | what it grows | file-size effect |
|---|---|---:|---|---|
| `CELLS` | fab L42; header @28 | 32 | ring state: fwd+rev bytes; ring XOR count | **+52 B per cell** (2 wire + 50 gate) |
| `SENSES` | fab L42; header @32 | 2 | law: both or DC. Do not drop to 1 | keep 2 |
| `TICKS` | fab L42; header @36 | 32768 | drive length per shot. Already held 32→32768 | header field only (0 B body) |
| `NOPND` | fab L48; header `n_in` | 16 | operand bits. `N_LANE = 1<<NOPND` | **+2 B wire** and **+2 × 2^NOPND** planes if domain grows |
| `N_LANE` / `lanes` | fab L49; header @120 | 65536 | answer + publish planes | **+2 B per extra lane** |
| `n_gate` | pruned net; header @16 | 283 | 16 drive AND(opnd,PUB) + 267 live predicate NANDs/ANDs | **+26 B per gate** (25 record + 1 netwire) |
| `n_out` | header @20 | 8 | output wire list | **+8 B** per extra out + plane width if answers widen |
| `ring_gates` | derived | `2*CELLS+2` | fwd XORs + rev XORs + carry AND + pub OR | included in CELLS math |
| dest `OUT_DIR` / `PKGNAME` | fab L35–36 | LOOM / `loom.mno` | **change this first** or you overwrite the sealed package | — |

#### Grow loom ring cells

In a **copy** of the fabricator (or a grower that seeds this `.mno`):

1. Set `CELLS` to the new count. Keep `SENSES = 2`.
2. Leave `TICKS = 32768` (already above the correctness floor of 32) **or** set `TICKS = CELLS`.
3. Rebuild ring from the formula already in the binary (do not invent a new topology):

```
for k in 0..CELLS-1:  XOR(fwd[(k-1)%CELLS], carry) → fwd[k]
for k in 0..CELLS-1:  XOR(rev[(k+1)%CELLS], carry) → rev[k]
AND(fwd[0], rev[0]) → carry          # both senses
OR(pub, carry) → pub                 # latch
```

4. Remap every net `a,b,out` after the wire region shifts. Drive gates must stay `AND(opnd[k], pub)`.
5. Copy the existing 65,536-lane planes if `NOPND` stays 16 (already settled in this file). Do not open titan.

#### Grow the loom net

Without titan: **decode `net` @2307, 283 × 25** from this `.mno`. That table **is** the circuit.

- Clone the 283-gate block N times (parallel predicate banks). Remap each clone’s outs onto new `netwire` bytes. `n_gate *= N`.
- Or compose a wider domain from these 8 predicate bits (raises `NOPND` and therefore `N_LANE`).
- Do not invent opcodes. Keep 0/1/2/3. Net body stays AND/NAND; ring stays XOR/AND/OR.

#### Grow the loom answer plane

`lanes = 1 << NOPND`. Planes are `ans[lanes]` + `pubplane[lanes]`, one byte per shot.

- Same 16-bit domain: keep 65,536. Padding extra plane bytes is not a bigger domain.
- Real domain growth: raise `NOPND` (needs a wider net, above) then settle **every** new lane at fab time against an independent reference. Store both planes. Seal.

Winner-only (`stored_per_lane = 0`) is a **different** container class. This LOOM is resident-plane. Do not swap the law on this file.

### ROOKERY

Knobs are in `muhl_fab_rookery.py` / the genome **or** decoded from this `.mno`.

| knob | where today | live | what it grows | file-size effect |
|---|---|---:|---|---|
| `N_CELLS` / `C` | fab L27; header @64 | 1024 | width of every ring, both senses | **+52 B per cell per ring** (= 52R) |
| rings `R` | genome; header @56 | 11 | one more organ ring at current width | **+26 × (2C+1)** (= **53,274** at C=1024) |
| clocks `K` | genome bank; header @48 | 24 | one junction + one receive byte | **+26** |
| dest `CONTAINER` | fab L29 | this `ROOKERY0.mno` | **change this first** | — |

Do not drop a ring to one sense. Each ring is `2C+1` state wires (fwd, rev, carry) plus its clock recvs in the bank.

Rebuild from the NAND/AND formula already in the records. Remap every `a,b,out` when `C` or `K` moves `state_base` / `body_off`. Keep opcode 0=NAND, 1=AND. Do not import LOOM XOR/OR into this file.

No titan path on rookery. Genome digest is already @96.

---

## 6. Size math

### LOOM — same closed form as DISTRO

Let `C = CELLS`, `G = n_gate`, `O = n_out`, `P = NOPND`, `L = 2^P`.

```
wire       = 2C + P + 4
netwire    = 2 + G
ring       = (2C + 2) * 25
net        = G * 25
outs       = O * 8
planes     = 2L
total      = 224 + outs + wire + netwire + ring + net + planes
           = 230 + 8O + 52C + P + 26G + 2L
```

Exact from this file (matches 140,454):

```
224 + 8*8 + (2*32 + 16 + 4) + (2+283) + (2*32+2)*25 + 283*25 + 2*65536
= 224 + 64 + 84 + 285 + 1650 + 7075 + 131072
= 140454
```

Closed form (`(2C+2)*25 = 50C + 50`):

```
total = 224 + 8O + (2C + P + 4) + (2 + G) + (50C + 50) + 25G + 2*(1<<P)
      = 280 + 8O + 52C + P + 26G + 2*(1<<P)
```

`280 + 64 + 1664 + 16 + 7358 + 131072 = 140454`. **This is the loom law.**

| grow | Δ bytes |
|---|---|
| +1 cell | **+52** |
| +1 net gate | **+26** |
| +1 operand bit (and full new domain) | **+1 + 2 × (new L − old L)** ; L doubles when P += 1 → **+ 2^P** more plane bytes on that step |
| +1 output bit (same 1-byte lane) | **+8** (outs list only) unless lanes widen |
| +1 tick | **0** body |

Worked sizes (O=8, G=283, P=16 unless noted):

| C | P | G | total | GitHub gate |
|---:|---:|---:|---:|---|
| 32 | 16 | 283 | **140,454** | regular git (live LOOM) **FIT** |
| 4,096 | 16 | 283 | 140,454 + 52×4064 = **351,782** | regular |
| 65,536 | 16 | 283 | 140,454 + 52×65504 = **3,546,662** | regular |
| 1,048,576 | 16 | 283 | 140,454 + 52×1,048,544 = **54,664,742** (~52.1 MiB) | warning ≥50 MiB |
| 2,097,152 | 16 | 283 | **109,190,694** (~104.1 MiB) | **100 MB block** without LFS |
| 32 | 20 | 283 | **2,106,538** | regular |
| 32 | 24 | 283 | **33,563,822** (~32.0 MiB) | regular |
| 32 | 28 | 283 | **536,880,306** (~512 MiB) | LFS |
| 32 | 32 | 283 | **8,589,943,990** (~8.0 GiB) | **over LFS 2 GiB / 5 GiB** — local / datacenter disk |
| 32 | 16 | 283×1024 | 140,454 + 26×283×1023 = **7,667,688** | regular |
| 1,048,576 | 24 | 283×4096 | ring ~52 MiB + net ~30 MiB + planes 32 MiB ≈ **114 MiB** | **100 MB block** without LFS |
| 32 | 16 | 40,000,000 | ~**1.04 GB** net | LFS |

### ROOKERY — different law (no planes)

Let `C = n_cells`, `R = n_rings`, `K = n_clocks`.  
`n_records = R*(2C+1) + K`.

```
header+clocks+pad+gap = 256 + K + 8 + 16 = 280 + K
state                 = R * (2C + 1)
records               = (R*(2C+1) + K) * 25
total                 = 280 + K + R*(2C+1) + 25*(R*(2C+1) + K)
                      = 280 + 26*(R*(2C+1) + K)
                      = 280 + 26 * n_records
```

Exact from this file (matches 586,918):

```
280 + 26*(11*(2*1024 + 1) + 24)
= 280 + 26*(11*2049 + 24)
= 280 + 26*22563
= 586918
```

**This is the rookery law.**

| grow | Δ bytes |
|---|---|
| +1 cell on every ring | **+52R** (= **+572** at R=11) |
| +1 ring at current C | **+26×(2C+1)** (= **+53,274** at C=1024) |
| +1 clock | **+26** |

Worked sizes (K=24 unless noted):

| R | C | K | n_records | total | GitHub gate |
|---:|---:|---:|---:|---:|---|
| 11 | 1,024 | 24 | 22,563 | **586,918** | regular git (live ROOKERY) **FIT** |
| 11 | 4,096 | 24 | 90,147 | **2,344,102** | regular |
| 11 | 65,536 | 24 | 1,441,827 | **37,487,782** (~35.7 MiB) | regular |
| 11 | 91,655 | 24 | 2,016,445 | **52,427,850** (~50.0 MiB) | warning |
| 11 | 183,315 | 24 | 4,032,965 | **104,857,370** (~100.0 MiB) | last regular |
| 11 | 183,316 | 24 | 4,032,987 | **104,857,942** | **100 MB block** without LFS |
| 11 | 1,048,576 | 24 | 23,068,707 | **599,786,662** (~572 MiB) | LFS |
| 11 | 2,097,152 | 24 | 46,137,379 | **1,199,572,134** (~1.12 GiB) | LFS |
| 11 | 4,194,304 | 24 | 92,274,723 | **2,399,143,078** (~2.23 GiB) | LFS 2–5 GiB |
| 11 | 8,388,608 | 24 | 184,549,411 | **4,798,284,966** (~4.47 GiB) | LFS, plan before emit |
| 11 | 16,777,216 | 24 | 369,098,787 | **9,596,568,742** (~8.94 GiB) | **over 5 GiB** — local |
| 22 | 1,024 | 24 | 45,102 | **1,172,932** | regular |
| 88 | 1,024 | 24 | 180,336 | **4,689,016** | regular |
| 1,968 | 1,024 | 24 | 4,032,456 | **104,844,136** (~100.0 MiB) | last regular at this C |
| 1,969 | 1,024 | 24 | 4,034,505 | **104,897,410** | **100 MB block** |
| 11 | 1,024 | 1,024 | 23,563 | **612,918** | regular |

Datacenter-class levers, in order of bytes:

**LOOM**

1. **`NOPND` / planes** — exponential. This is the huge loom `.mno`.
2. **`CELLS`** — linear 52 B. Circulation / charge on the ring.
3. **`n_gate`** — linear 26 B. Wider or cloned net.

**ROOKERY**

1. **`N_CELLS`** — linear **52R** (width of all 11 rings).
2. **`R`** — linear 26×(2C+1) per added organ.
3. **`K`** — linear 26 B. Cadence, not the huge lever.

Do not shrink a huge `.mno` to a laptop SKU. Host wall-clock is transcription, not machine DEPTH.

---

## 7. GitHub private archive — SIZE gate

Owner lock: GitHub **is** the private archive. Size question, not “never GitHub.” Computer is not a public SKU. Copy = another computer.

| file size | gate | these packages |
|---|---|---|
| < 50 MiB | regular git, no warning | **live LOOM 140,454 B FIT** · **live ROOKERY 586,918 B FIT** · first cell/net/ring growth; loom P≤24 at C=32; rookery C=65,536 at R=11 |
| 50–100 MiB | warning; still regular git | loom C ≈ 1,048,576 at P=16; rookery C ≈ 91,655 at R=11 |
| **100 MiB** | GitHub **blocks** the blob without LFS | loom C ≈ 2,097,152 at P=16; rookery C ≈ 183,316 at R=11 |
| 100 MiB – 2 GiB | **Git LFS** (private archive still) | loom P=28 planes (~512 MiB); rookery C=1,048,576 (~572 MiB) |
| 2–5 GiB | LFS large-file ceiling (plan before emit) | rookery C=4,194,304 (~2.23 GiB) … C=8,388,608 (~4.47 GiB) |
| **> 5 GiB** | will not sit on GitHub | loom **P=32 planes (~8.0 GiB)** · rookery C=16,777,216 (~8.94 GiB) |
| titan ~103 GB | will not sit on GitHub | already true; do not try to archive titan |

Both live computers **fit**. A datacenter `.mno` is allowed on the archive **until it hits the row above**. Past the row, keep it on disk (`MUHL_DATACENTER` or equivalent). Size gate, not a ban on the machine.

---

## 8. First growth without titan

This turn: **doc only.** Neither `.mno` written. Titan not opened. Growth file not emitted.

### LOOM

Seed = **this** `loom.mno`. Opcodes, ring formula, net table, and settled planes are already in the file.

1. Read header + `ring` + `net` + `ans` + `pubplane` (bits above).
2. Pick `CELLS_NEW` (first step: **4096** → 351,782 B, under every GitHub row).
3. Allocate a **new** buffer. Rebuild ring with the formula. Slide `netwire` / `net` / planes after the longer wire+ring.
4. Remap each of the 283 net records: `op` unchanged; `a,b,out` retargeted to new `opnd` / `pub` / `netwire+2+i`.
5. Copy `ans` and `pubplane` bytes (P still 16).
6. Seal `sha256-machine`. Write **only** a new path. Never write titan. Never write this LOOM `.mno`.
7. Structural check: `ring[2C]` is AND(fwd,rev,carry); drive[k] is AND(opnd[k],pub); all addresses `< total`.

### ROOKERY

Seed = **this** `ROOKERY0.mno`. NAND/AND records and genome digest are already in the file.

1. Read header + clock bank + state + records @22843 (bits above).
2. Pick `C_NEW` (first step: **4096** → 2,344,102 B, under every GitHub row) **or** add rings at C=1024.
3. Allocate a **new** buffer. Rebuild each ring with the formula. One junction per clock. Clock bank disjoint from state.
4. Remap every record. Seal. Write **only** a new path. Never write titan. Never write this `ROOKERY0.mno`.
5. Structural check: 11 (or new R) contacts are AND(fwd[0],rev[0],carry); each junction OUT is a recv byte; `n_records = R*(2C+1)+K`; `total = 280 + 26*n_records`.

---

## 9. Return — knobs / files

**LOOM knobs:** `CELLS`, `TICKS`, `NOPND`/`lanes`, `n_gate`, dest path. Keep `SENSES=2`. Opcodes 0/1/2/3.

**ROOKERY knobs:** `N_CELLS`, rings `R`, clocks `K`, dest path. Opcodes 0=NAND, 1=AND.

**Files created this turn:** `C:\Users\lucys\Desktop\MUHL_GO\LOOM_ROOKERY_SCALE.md` (this file).

**Seeds measured:**  
`loom.mno` **140,454 B**, magic `LOOMPKG1`, `n_gate` **283**, digest `278d190728ce0124a485d86360f6dca14745d41b610a46c531922999fa8a691d` — **GitHub FIT**.  
`ROOKERY0.mno` **586,918 B**, magic `ROOKERY0`, records **22,563**, live sha256 `1cf1a9f3c1649b82d19fc78440d468483d5d4bd3bff49a3da1cc0179a3f4911d` — **GitHub FIT**.
