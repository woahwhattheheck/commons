# MNO_N_RINGS — how many rings each file actually has

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Date:** 2026-08-15. Additive. Titan not opened. Titan not written. No Desktop glob. No 2 GB scan.

A muhlnickel with **one ring** is dumb. **N rings**, each a computer organ.

This card is the bit-read of the four named containers. Header fields + cheap cell spans only.

---

## Verdict (measured this turn)

| file | magic | bytes | rings | class | ones on those rings (cheap) |
|---|---|---:|---:|---|---|
| `MUHLNICKEL_DISTRO\muhlnickel.mno` | `MUHLPKG1` | 136,450 | **1** | one-ring | fwd 20 · rev 20 · carry 0 · pub 0 |
| `MUHLNICKEL_LOOM\loom.mno` | `LOOMPKG1` | 140,454 | **1** | one-ring | fwd 22 · rev 22 · carry 0 · pub 0 |
| `MUHLNICKEL_ROOKERY\ROOKERY0.mno` | `ROOKERY0` | 586,918 | **11** | N-ring (11 organs) | **2** (both on ring 7) |
| `MUHL_DATACENTER\muhlnickel_dc.mno` | `MUHLDC01` | 2,147,548,550 | **1,251,485** = 1 control + 1,251,484 factory | N-ring (same organ class, remapped) | control **0** (dark). Factory cells **not scanned**. |

DISTRO and LOOM have **no `n_rings` field**. The header names one ring (`ring_gates` / `cells` / `senses`). That is the dumb shape.

ROOKERY and DC name **N**. ROOKERY: header `n_rings=11`, each ring an organ. DC: fold record `factory n_rings=1,251,484` plus the control nring2. 100 GB grow must stay that N-ring factory, not one fat ring.

---

## 1. DISTRO — one ring

`C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno`

| field | live |
|---|---|
| magic @0 | `MUHLPKG1` |
| size = header total | 136,450 |
| `n_in` / `n_wire` / `n_gate` / `n_out` | 16 / 215 / 129 / 8 |
| ring | **66 gates, 32 cells, 2 senses, 32 ticks** |
| `n_rings` | **absent** |
| wire @288 (84 B) · ring table @503 (1650 B) | both inside file |
| fwd @288 · rev @320 · carry @352 · pub @353 | |

**Rings: 1.** One nring2 (XOR rotate, AND carry both senses, OR publish). One organ. Laptop adder + 65,536-shot plane.

Ones (32+32 cells, cheap):

```
fwd @288  0101000000000000010001000000000001010101010101010101010101010101   20 ones
rev @320  same                                                                 20 ones
carry     00
pub       00
```

Those ones are the last both-sense shot (3 + 5 + sixteen `01` drive cells). Not N organs.

---

## 2. LOOM — one ring

`C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno`

| field | live |
|---|---|
| magic @0 | `LOOMPKG1` |
| size = header total | 140,454 |
| `n_in` / `n_wire` / `n_gate` / `n_out` | 16 / 369 / 283 / 8 |
| ring | **66 gates, 32 cells, 2 senses, 32768 ticks** |
| `n_rings` | **absent** |
| wire @288 (84 B) · ring table @657 (1650 B) | both inside file |
| fwd @288 · rev @320 · carry @352 · pub @353 | |

**Rings: 1.** Same nring2 class as DISTRO. Different net (283 gates). Still one organ.

Ones (cheap):

```
fwd @288  0100000001000000010001010100000001010101010101010101010101010101   22 ones
rev @320  same                                                                 22 ones
carry     00
pub       00
```

Last both-sense shot (17 + 29 + sixteen `01` drive). Same one-ring leftover as DISTRO.

---

## 3. ROOKERY — N rings, each an organ

`C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\ROOKERY0.mno`

Header 256 B. Different class. No answer plane.

| off | field | live |
|---:|---|---|
| 0 | magic | `ROOKERY0` |
| 8 | seal | `9af6e3a1020e1b8a289e3bf66be669f7de581aacd74829c588f5ba0f5633eb38` |
| 40 | `n_records` | 22,563 |
| 48 | `n_clocks` | 24 |
| 56 | **`n_rings`** | **11** |
| 64 | `n_cells` | 1,024 |
| 72 | `body_off` | 22,843 |
| 80 | `state_base` | 288 |
| 96 | genome digest | `75fcab01d9b847bd69d992bc148b594fc9e59d3cd1c0de71a1ed2e6d363f753f` |

**Rings: 11.** Each ring is a computer organ (genome bank, not invented). Width 1024-bit, both senses, own carry, own clock recvs.

| ring | organ | wire_base | carry | ones |
|---:|---|---:|---:|---:|
| 0 | sense | 288 | 2336 | 0 |
| 1 | sense | 2337 | 4385 | 0 |
| 2 | memory | 4386 | 6434 | 0 |
| 3 | tension | 6435 | 8483 | 0 |
| 4 | imagination | 8484 | 10532 | 0 |
| 5 | value | 10533 | 12581 | 0 |
| 6 | value | 12582 | 14630 | 0 |
| 7 | value | 14631 | 16679 | **2** |
| 8 | value | 16680 | 18728 | 0 |
| 9 | action | 18729 | 20777 | 0 |
| 10 | witness | 20778 | 22826 | 0 |

Clock bank @256 (24 B): **0 ones**.  
State @288, length `11 × (2×1024 + 1) = 22,539` B: **2 ones**, 2 nonzero bytes.

```
@15456  00000001    ring 7 cell 825 fwd
@16480  00000001    ring 7 cell 825 rev
```

That is the fired electron already journalled. Do not wipe it. Cheap count — 22,539 B, not a glob.

This is the N-ring shape: eleven organs in one file, not one ring wearing eleven names.

---

## 4. DC — already N rings (bounded header only)

`C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

`DATACENTER_MNO.md` + `dc_info.py` layout. Read: 224 B header, 48 B fold, 84 B control wire, 25 B control g0, 25 B factory g0. **Did not scan 2.000 GiB.**

| field | live |
|---|---|
| magic @0 | `MUHLDC01` |
| disk = header total | **2,147,548,550** (2.000 GiB) |
| digest @192 | `28f4050e2349f7f187a133314724db182fd9139393350336c1ec886e98f956c0` |
| `n_in` / `n_out` / lanes | 0 / 0 / 0 (winner-only) |
| `n_wire` / `n_gate` | 82,598,028 / 82,598,010 |
| control ring | 66 gates, 32 cells, 2 senses, 32 ticks |
| fold @224 | `addr_bits=262144` `winner_only=1` `stored_per_lane=0` senses=2 |
| factory | **1,251,484** rings, stride 1716, wire@2006, gates@82599950 |
| control g0 | XOR a=303 b=336 out=272 (inside file) |
| factory g0 | XOR a=2037 b=2070 out=2006 (inside file) |

**Rings: 1,251,485** = 1 control nring2 + 1,251,484 factory nring2 replicas. Header `ring_gates=66` names the **control** organ only. N lives in the fold factory field.

Control cells (cheap, 64 B):

```
fwd @272  00000000 × 32     0 ones
rev @304  00000000 × 32     0 ones
carry @336  00
pub   @337  00
```

Control is dark. Factory occupancy is **not** claimed this turn — that would be a 2 GB scan. First emit law (`DATACENTER_MNO.md`): started dark; fill later on this file's own cells.

Factory rings are the **same organ class** (nring2, remapped, package-local). That is still N rings. It is not ROOKERY's eleven different organs. Both beat one-ring.

---

## One-ring vs N-ring

| | one-ring (dumb) | N-ring |
|---|---|---|
| who | DISTRO, LOOM | ROOKERY (11 organs), DC (1.25M nring2) |
| header | `ring_gates` / `cells` only | `n_rings` (rookery) or fold `factory n_rings` (DC) |
| what it is | one computer organ | N computer organs in one file |
| grow | fatter cells / fatter plane on the same organ | more rings |

One ring can be correct and powered (DISTRO surfaced `3+5=8`; LOOM surfaced `0x4A`). It is still one organ. A muhlnickel is N organs.

---

## 100 GB grow must be N rings

`DATACENTER_100GB.md` already sizes the factory, not one ring:

```
prefix = 224 + 48 + 84 + 1650 = 2006
REPL   = 66 + 1650 = 1716
n      = (100000000000 - 2006) // 1716 = 58,275,057
total  = 2006 + 58,275,057 * 1716 = 99,999,999,818
```

| | |
|---|---:|
| factory rings | **58,275,057** |
| control | **1** |
| **N** | **58,275,058** |
| gates | 66 × 58,275,058 = **3,846,153,828** |
| emit | **99,999,999,818** B |

That is `n_rings_for(TARGET_BYTES)` in `muhl_fab_dc.py`. Storage lever = more nring2 organs. Speed lever = ones on those cells at emit.

**Refuse as the 100 GB grow:** one ring with huge `cells`, one 100 GB answer plane, DISTRO/LOOM 65,536-plane copy, or a dark 100 GB file that is still `n_rings=1`. That is the dumb muhlnickel at titan-class size.

Titan not opened. Existing DISTRO / LOOM / ROOKERY not written. DC not written this turn.
