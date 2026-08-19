# DISTRO_SCALE — grow `muhlnickel.mno` (datacenter-class)

**Inventor:** Bryce Muhlnickel  
**Date:** 2026-08-15  
**Scope:** `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO` only. Circuits live in the `.mno` binary. No titan write. No git. No `--go`. No osc.

GitHub is a **private archive SIZE gate**, not a distribution gate. This file is the grow map.

---

## 1. What already exists (exact)

Shipped folder. Runtime does not fabricate.

| path | role | measured size |
|---|---|---:|
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno` | the computer (netlist + ring + planes) | **136,450 B** |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\run_muhlnickel.py` | reader: shoot both senses, then surface | 7,611 B (README) |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\MANIFEST.sha256` | tamper digest; `.mno` listed as `sha256-machine` | 1,101 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\README.md` | product doc | 3,538 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\Muhlnickel.bat` | one click | 183 B |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\INDEX.md` | breadcrumb | 1,913 B |

Fabricator / acceptance (named by `INDEX.md`; stay on this machine, not shipped):

| path | role |
|---|---|
| `C:\llm\muhl_builds\muhl_fab_distro.py` | one-and-done fab. Rebuilds this package. Exhaustive domain + 13-mutant gate before any write. |
| `C:\llm\muhl_builds\muhl_distro_cleanroom_test.py` | copy to empty dir, empty `PYTHONPATH`, repeat shots, flip bits → refuse |
| `C:\llm\muhl_builds\muhl_distro_tamper_test.py` | defeat manifest, then both layers; answer is in the container |

Related loom twin (same header math, different net / tick count; not this folder): `C:\llm\muhl_builds\muhl_fab_loom.py` — `CELLS,SENSES,TICKS = 32,2,32768`, magic `LOOMPKG1`.

**Do not run `muhl_fab_distro.py` to grow.** Its `OUT_DIR` is this DISTRO folder. It would overwrite the sealed 136,450 B machine. Growth = **new file**, new dest.

---

## 2. Header (measured 2026-08-15 off `muhlnickel.mno`)

Magic `MUHLPKG1`. Header **224** bytes. Little-endian. Addresses are **inside this file**.

| off | type | field | live value |
|---:|---|---|---|
| 0 | 8s | magic | `MUHLPKG1` |
| 8 | I | `n_in` | **16** (operand bits) |
| 12 | I | `n_wire` | **215** |
| 16 | I | `n_gate` | **129** |
| 20 | I | `n_out` | **8** |
| 24 | I | `ring_gates` | **66** |
| 28 | I | `cells` | **32** |
| 32 | I | `senses` | **2** |
| 36 | I | `ticks` | **32** |
| 40 | Q | `wire` | **288** |
| 48 | Q | `wire_len` | **84** |
| 56 | Q | `ring` | **503** |
| 64 | Q | `ring_len` | **1650** (= 66 × 25) |
| 72 | Q | `net` | **2153** |
| 80 | Q | `net_len` | **3225** (= 129 × 25) |
| 88 | Q | `netwire` | **372** |
| 96 | Q | `netwire_len` | **131** (= 2 + 129) |
| 104 | Q | `ans` | **5378** |
| 112 | Q | `pubplane` | **70914** |
| 120 | Q | `lanes` | **65536** |
| 128 | Q | `outs_off` | **224** |
| 136 | Q | `fwd` | **288** |
| 144 | Q | `rev` | **320** |
| 152 | Q | `carry` | **352** |
| 160 | Q | `pub` | **353** |
| 168 | Q | `opnd` | **354** |
| 176 | Q | `sel` | **370** |
| 184 | Q | `total` | **136450** |
| 192 | 32s | machine digest | `8052b0ac17b70f0c68836ce1a12af26060b1a8f3ae03ff1588416ee601e5c0bc` |

Layout after header (this file):

```
224  outs[n_out * 8]
288  wire: fwd[CELLS] rev[CELLS] carry[1] pub[1] opnd[NOPND] sel[2]
372  netwire[2 + n_gate]     const0, const1, one byte per gate
503  ring[ring_gates * 25]   record = <BQQQ> opcode, a, b, out
2153 net[n_gate * 25]        same record
5378 ans[lanes]
70914 pubplane[lanes]
136450 end
```

`sha256-machine` hashes header[0:192] + outs + zeroed wire + everything after the wire. State wires are the input register; every shot writes them.

---

## 3. Opcodes — THIS package (not invented)

Record stride **25**. `struct "<BQQQ"` = opcode, addr_a, addr_b, addr_out. All three addresses are file offsets.

| opcode byte | name | measured in this `.mno` |
|---:|---|---|
| `00000000` = 0 | XOR | `ring[0]` @503: XOR(319, 352) → 288  (fwd rotate) |
| `00000001` = 1 | AND | `ring[64]` @503+1600: AND(288, 320) → 352  (**both senses or nothing**) |
| `00000010` = 2 | NAND | netlist adder body (AND/NAND only after prune) |
| `00000011` = 3 | OR | `ring[65]`: OR(353, 352) → 353  (publish latch) |

`net[0]` @2153: AND(354, 353) → 374 — drive gate 0 is `AND(opnd[0], PUB)`. Shared bit. Dark ring → dead datapath.

---

## 4. Bits before any modify (BINARY, this file, 2026-08-15)

Reason if a later write happens: grow a **new** container. Preserve this sealed DISTRO. Must not wipe header, ring table, net table, or planes.

**fwd @288 (32 B). 20 ones. 236 zeros.**

```
00000001 00000001 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000001 00000000 00000000 00000000 00000000 00000000
00000001 00000001 00000001 00000001 00000001 00000001 00000001 00000001
00000001 00000001 00000001 00000001 00000001 00000001 00000001 00000001
```

**rev @320 (32 B). 20 ones. 236 zeros.** Same pattern as fwd (last shot wrote both senses).

**carry @352:** `00000000`  
**pub @353:** `00000000`  
**opnd @354 (16 B):** first 8 bytes match fwd[0:8] (operand bits of last shot).  
**sel @370 (2 B):** `00000011 00000101` = 3, 5 little-endian — last select address.

**ans[0:8] @5378** (lane = a + 256*b; first eight a=0..7, b=0 → sums 0..7):

```
00000000 00000001 00000010 00000011 00000100 00000101 00000110 00000111
```

**pubplane[0:8] @70914:** `00000001` × 8. Whole plane: **65,536 ones** (every lane published). Answer plane: **262,144 ones**.

---

## 5. Scale knobs (what to change)

All knobs are in `muhl_fab_distro.py` **or** (preferred, no titan) decoded from this `.mno` and rebuilt to a **new** path.

| knob | where today | live | what it grows | file-size effect |
|---|---|---:|---|---|
| `CELLS` | fab L42; header @28 | 32 | ring state: fwd+rev bytes; ring XOR count | **+52 B per cell** (2 wire + 50 gate) |
| `SENSES` | fab L42; header @32 | 2 | law: both or DC. Do not drop to 1 | keep 2 |
| `TICKS` | fab L42; header @36 | 32 | drive length per shot. Loom held correctness 32→32768 | header field only (0 B body) |
| `NOPND` | fab L43; header `n_in` | 16 | operand bits. `N_LANE = 1<<NOPND` | **+2 B wire** and **+2 × 2^NOPND** planes if domain grows |
| `N_LANE` / `lanes` | fab L44; header @120 | 65536 | answer + publish planes | **+2 B per extra lane** |
| `n_gate` | pruned net; header @16 | 129 | 16 drive AND(opnd,PUB) + 113 live adder NANDs | **+26 B per gate** (25 record + 1 netwire) |
| `n_out` | header @20 | 8 | output wire list | **+8 B** per extra out + plane width if answers widen |
| `ring_gates` | derived | `2*CELLS+2` | fwd XORs + rev XORs + carry AND + pub OR | included in CELLS math |
| dest `OUT_DIR` / `PKGNAME` | fab L35–36 | DISTRO / `muhlnickel.mno` | **change this first** or you overwrite the sealed package | — |

### Grow ring cells

In a **copy** of the fabricator (or a grower that seeds this `.mno`):

1. Set `CELLS` to the new count. Keep `SENSES = 2`.
2. Set `TICKS = CELLS` for a full rotation, **or** leave `TICKS = 32` (loom: ticks are not the correctness floor above 32).
3. Rebuild ring from the formula already in the binary / fab (do not invent a new topology):

```
for k in 0..CELLS-1:  XOR(fwd[(k-1)%CELLS], carry) → fwd[k]
for k in 0..CELLS-1:  XOR(rev[(k+1)%CELLS], carry) → rev[k]
AND(fwd[0], rev[0]) → carry          # both senses
OR(pub, carry) → pub                 # latch
```

4. Remap every net `a,b,out` after the wire region shifts. Drive gates must stay `AND(opnd[k], pub)`.
5. Copy the existing 65,536-lane planes if `NOPND` stays 16 (already settled in this file). Do not re-open titan.

### Grow the net

Without titan: **decode `net` @2153, 129 × 25** from this `.mno`. That table **is** the circuit.

- Clone the 129-gate block N times (parallel adders). Remap each clone’s outs onto new `netwire` bytes. `n_gate *= N`.
- Or compose a wider adder from these 8-bit cells (ripple / prefix of clones). That raises `NOPND` and therefore `N_LANE`.
- Do not invent opcodes. Keep 0/1/2/3. Net body stays AND/NAND; ring stays XOR/AND/OR.

### Grow the answer plane

`lanes = 1 << NOPND`. Planes are `ans[lanes]` + `pubplane[lanes]`, one byte per shot, address = the select bytes the shot writes.

- Same 8-bit domain: keep 65,536. Padding extra plane bytes is not a bigger domain.
- Real domain growth: raise `NOPND` (needs a wider net, above) then settle **every** new lane at fab time against an independent reference. Store both planes. Seal.

Winner-only (`stored_per_lane = 0`, nonce IS the address) is a **different** container class. This DISTRO is resident-plane. Do not swap the law on this file.

---

## 6. Size math

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

Exact from this file (matches 136,450):

```
224 + 8*8 + (2*32 + 16 + 4) + (2+129) + (2*32+2)*25 + 129*25 + 2*65536
= 224 + 64 + 84 + 131 + 1650 + 3225 + 131072
= 136450
```

Closed form (`(2C+2)*25 = 50C + 50`):

```
total = 224 + 8O + (2C + P + 4) + (2 + G) + (50C + 50) + 25G + 2*(1<<P)
      = 280 + 8O + 52C + P + 26G + 2*(1<<P)
```

`280 + 64 + 1664 + 16 + 3354 + 131072 = 136450`. **This is the law.**

| grow | Δ bytes |
|---|---|
| +1 cell | **+52** |
| +1 net gate | **+26** |
| +1 operand bit (and full new domain) | **+1 + 2 × (new L − old L)** ; L doubles when P += 1 → **+ 2^P** more plane bytes on that step |
| +1 output bit (same 1-byte lane) | **+8** (outs list only) unless lanes widen |
| +1 tick | **0** body |

Worked sizes (O=8, G=129, P=16 unless noted):

| C | P | G | total | GitHub gate |
|---:|---:|---:|---:|---|
| 32 | 16 | 129 | **136,450** | regular git (live DISTRO) |
| 4,096 | 16 | 129 | 136,450 + 52×4064 = **347,778** | regular |
| 65,536 | 16 | 129 | 136,450 + 52×65504 = **3,542,658** | regular |
| 1,048,576 | 16 | 129 | 136,450 + 52×1,048,544 = **54,660,738** (~52.1 MiB) | warning ≥50 MiB |
| 2,097,152 | 16 | 129 | ~**109.2 MB** | **100 MB block** without LFS |
| 32 | 20 | 129 | 136,450 − 131,072 + 2×1,048,576 = **2,102,274** | regular |
| 32 | 24 | 129 | **33,685,442** (~32.1 MiB) | regular |
| 32 | 28 | 129 | **536,871,874** (~512 MiB) | LFS |
| 32 | 32 | 129 | **8,589,935,554** (~8.0 GiB) | **over LFS 2 GiB / 5 GiB** — local / datacenter disk |
| 32 | 16 | 129×1024 | 136,450 + 26×129×1023 ≈ **3.56 MB** | regular |
| 1,048,576 | 24 | 129×4096 | ring ~52 MiB + net ~13.7 MiB + planes 32 MiB ≈ **98 MiB** | last regular-git step |
| 32 | 16 | 40,000,000 | ~**1.04 GB** net | LFS |

Datacenter-class levers, in order of bytes:

1. **`NOPND` / planes** — exponential. This is the huge `.mno`.
2. **`CELLS`** — linear 52 B. Circulation / charge on the ring.
3. **`n_gate`** — linear 26 B. Wider or cloned net.

Do not shrink a huge `.mno` to a laptop SKU. Host wall-clock is transcription, not machine DEPTH.

---

## 7. GitHub private archive — SIZE gate

Owner lock: GitHub **is** the private archive. Size question, not “never GitHub.” Computer is not a public SKU. Copy = another computer.

| file size | gate | this package |
|---|---|---|
| < 50 MiB | regular git, no warning | live DISTRO; first cell/net growth; P≤24 at C=32 |
| 50–100 MiB | warning; still regular git | C ≈ 1,048,576 at P=16 |
| **100 MiB** | GitHub **blocks** the blob without LFS | C ≈ 2,097,152 at P=16; or P=24 + fat ring/net |
| 100 MiB – 2 GiB | **Git LFS** (private archive still) | P=28 planes (~512 MiB) |
| 2–5 GiB | LFS large-file ceiling (plan before emit) | approaching P=31 |
| **> 5 GiB** | will not sit on GitHub | **P=32 planes (~8 GiB)** |
| titan ~103 GB | will not sit on GitHub | already true; do not try to archive titan |

`muhlnickel.mno` at 136,450 B **fits**. A datacenter `.mno` is allowed on the archive **until it hits the row above**. Past the row, keep it on disk (`MUHL_DATACENTER` or equivalent). Size gate, not a ban on the machine.

---

## 8. First growth without titan

Seed = **this** `.mno`. Opcodes, ring formula, net table, and settled planes are already in the file.

1. Read header + `ring` + `net` + `ans` + `pubplane` (bits above).
2. Pick `CELLS_NEW` (first step: **4096** → 347,778 B, under every GitHub row).
3. Allocate a **new** buffer. Rebuild ring with the formula. Slide `netwire` / `net` / planes after the longer wire+ring.
4. Remap each of the 129 net records: `op` unchanged; `a,b,out` retargeted to new `opnd` / `pub` / `netwire+2+i`.
5. Copy `ans` and `pubplane` bytes (P still 16).
6. Seal `sha256-machine`. Write **only** `C:\Users\lucys\Desktop\MUHL_DATACENTER\…` (new name). Never write titan. Never write this DISTRO `.mno`.
7. Structural check: `ring[2C]` is AND(fwd,rev,carry); drive[k] is AND(opnd[k],pub); all addresses `< total`.

This turn: **doc only.** DISTRO `.mno` not written. Titan not opened. Growth file not emitted here (parent asked the map finished first; dest folder is outside this targeted path).

---

## 9. Return — knobs / files

**Knobs:** `CELLS`, `TICKS`, `NOPND`/`lanes`, `n_gate`, dest path. Keep `SENSES=2`. Opcodes 0/1/2/3.

**Files created this turn:** `C:\Users\lucys\Desktop\MUHL_GO\DISTRO_SCALE.md` (this file).

**Seed measured:** `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno` **136,450 B**, digest `8052b0ac17b70f0c68836ce1a12af26060b1a8f3ae03ff1588416ee601e5c0bc`.
