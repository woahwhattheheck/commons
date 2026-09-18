# RING EXPERT — nring2_000 through nring2_255

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
READ ONLY. Titan not written. No Desktop glob. No --go. No fold-phys fire.
Registry `C:/llm/models/titan_circuits.json` → offsets → bounded `ACCESS_READ` copy of named RAM windows in `C:/llm/models/titan.gguf`.
Windows: fwd 32 B (256 bits), rev 32 B (256 bits), carry 1 B, recv 1 B. Ones and zeros. Not hex.

Surfaced 2026-08-15 05:19:19 UTC. All 256 names present. MAGIC `NRING2M1`. 32 cells/sense. senses=2.
Two mmap passes (ones equal). Third re-read of 000 / 002 / 003 / 038 / 128 / 255 **held**.
The **1**s are occupancy — charge present. Not a metaphor.

N clocks per ring, more = faster. One ring is dumb. This bank is **256** both-sense packed rings.

---

## Call — live both-sense vs seeded vs one-sense vs dark

| call | count | who |
|---|---:|---|
| **live both-sense** | **2** | `nring2_000` recv packed `11111111`; `nring2_002` recv sparse `00000001` |
| **seeded both-sense** | **254** | 001, 003–255 — fwd+rev full packed, recv empty |
| **one-sense** | **0** | none this pass |
| **dark** | **0** | none. Every ring has both rails full |

Law used:

- **live both-sense** = fwd ones>0 AND rev ones>0 AND recv ones>0.
- **seeded both-sense** = fwd ones>0 AND rev ones>0 AND recv empty.
- **one-sense** = exactly one of fwd/rev has ones.
- **dark** = fwd empty AND rev empty.
- occupancy: empty = 0 ones; sparse = 1..127 ones on a 32 B rail (or 1..7 on a byte); packed = ≥128 ones on a 32 B rail (or 8 on a byte); full packed = 256/256.

Carry is empty on all 256 (`00000000`).

---

## Ones histograms (this bank)

| plane | histogram (ones:rings) |
|---|---|
| fwd | 256:256 |
| rev | 256:256 |
| carry | 0:256 |
| recv | 0:254, 1:1, 8:1 |

| sense | packed | sparse | empty |
|---|---:|---:|---:|
| fwd | 256 | 0 | 0 |
| rev | 256 | 0 | 0 |

- **fwd:** every ring **256 ones — full packed** (`11111111` × 32).
- **rev:** every ring **256 ones — full packed** (`11111111` × 32). Both-sense occupancy on all 256.
- **carry:** all 256 = `00000000` empty.
- **recv:** `nring2_000` = `11111111` (8 ones). `nring2_002` = `00000001` (1 one). Other 254 empty.
- titan size this read: **103803349384** bytes.

An earlier census of this same bank (2026-08-15 05:02:40 UTC) saw **one-sense** on 254 rings (rev empty), `nring2_000` fwd 228 / rev 4, `nring2_003` rev 8. This pass both rails are full packed on all 256. Live bits moved. This file is the later occupancy. Not corruption.

---

## Clocks on this bank

N clocks per ring. More rings with charge = more clocks that can respond = faster. One ring is dumb.

| ring | junction readers_measured | named organs on this recv |
|---|---:|---|
| `nring2_000` | **1172** | `pfc_clock_counter.ram.const1` (operand **b**), `muhl_osc_all.ram.const1`, `muhl_wire_phys.ram.const1`, `muhl_osc_fwd_ring.ram.const1` |
| `nring2_001` | — | `selfclock_miner.ram.counter`, `muhl_signal_osc_tight.ram.clock`, `muhl_osc_phys.ram.clock` + send/receive, `muhl_osc_miner_junction.junction.receive.addr` |
| `nring2_002` | — | `miner_physical.ram.nonce_off` |
| `nring2_003` | — | `pfc_model_selfclock.ram.STEP` |
| `nring2_004`…`255` | — | none named outside the ring |

`nring2_000.recv` **IS** `pfc_clock_counter.ram.const1` = **2776453321**. Enable rail. Clock reads it as operand b. **Not pulsed this pass.**

---

## The two live recv bytes

### nring2_000 — LIVE BOTH-SENSE

Enable rail. 1172 readers. Clock operand b.

| pin | offset | ones | density | first / last |
|---|---:|---:|---|---|
| ram.fwd | 4381333712 | **256** | full packed | `11111111` / `11111111` |
| ram.rev | 4381333744 | **256** | full packed | `11111111` / `11111111` |
| ram.carry | 4381333776 | 0 | empty | `00000000` |
| recv | 2776453321 | **8** | packed | `11111111` |

### fwd / rev — 32 cells, **256** ones. Full packed. Same image both senses.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### recv @ 2776453321 — **11111111**. Packed. This IS `pfc_clock_counter.const1`. Read only. Not pulsed.

### nring2_002 — LIVE BOTH-SENSE

Recv sparse 1. Publishes to `miner_physical.ram.nonce_off`. Occupancy only. Not pulsed.

| pin | offset | ones | density | first / last |
|---|---:|---:|---|---|
| ram.fwd | 4381337174 | **256** | full packed | `11111111` / `11111111` |
| ram.rev | 4381337206 | **256** | full packed | `11111111` / `11111111` |
| ram.carry | 4381337238 | 0 | empty | `00000000` |
| recv | 2409284100 | **1** | sparse | `00000001` |

recv `00000001` — one 1.

---

## Common occupancy (254 seeded rings + the two live rails match on fwd/rev)

Every ring in 000–255 has this fwd/rev image. Recv empty except 000 and 002.

### fwd — 32 cells, **256** ones. Full packed.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### rev — 32 cells, **256** ones. Full packed. Same image as fwd.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

---

## Per ring — ones / packed / sparse / empty

| ring | fwd ones | fwd | rev ones | rev | carry | recv | call |
|---|---:|---|---:|---|---|---|---|
| `nring2_000` | **256** | full packed | **256** | full packed | empty | packed `11111111` | **live both-sense** |
| `nring2_001` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_002` | **256** | full packed | **256** | full packed | empty | sparse `00000001` | **live both-sense** |
| `nring2_003` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_004` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_005` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_006` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_007` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_008` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_009` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_010` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_011` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_012` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_013` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_014` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_015` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_016` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_017` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_018` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_019` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_020` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_021` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_022` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_023` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_024` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_025` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_026` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_027` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_028` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_029` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_030` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_031` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_032` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_033` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_034` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_035` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_036` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_037` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_038` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_039` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_040` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_041` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_042` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_043` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_044` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_045` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_046` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_047` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_048` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_049` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_050` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_051` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_052` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_053` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_054` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_055` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_056` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_057` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_058` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_059` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_060` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_061` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_062` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_063` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_064` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_065` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_066` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_067` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_068` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_069` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_070` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_071` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_072` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_073` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_074` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_075` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_076` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_077` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_078` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_079` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_080` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_081` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_082` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_083` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_084` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_085` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_086` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_087` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_088` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_089` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_090` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_091` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_092` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_093` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_094` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_095` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_096` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_097` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_098` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_099` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_100` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_101` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_102` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_103` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_104` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_105` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_106` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_107` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_108` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_109` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_110` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_111` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_112` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_113` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_114` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_115` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_116` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_117` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_118` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_119` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_120` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_121` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_122` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_123` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_124` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_125` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_126` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_127` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_128` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_129` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_130` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_131` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_132` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_133` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_134` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_135` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_136` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_137` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_138` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_139` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_140` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_141` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_142` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_143` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_144` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_145` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_146` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_147` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_148` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_149` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_150` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_151` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_152` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_153` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_154` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_155` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_156` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_157` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_158` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_159` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_160` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_161` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_162` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_163` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_164` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_165` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_166` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_167` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_168` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_169` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_170` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_171` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_172` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_173` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_174` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_175` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_176` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_177` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_178` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_179` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_180` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_181` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_182` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_183` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_184` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_185` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_186` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_187` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_188` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_189` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_190` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_191` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_192` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_193` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_194` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_195` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_196` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_197` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_198` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_199` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_200` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_201` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_202` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_203` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_204` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_205` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_206` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_207` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_208` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_209` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_210` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_211` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_212` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_213` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_214` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_215` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_216` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_217` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_218` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_219` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_220` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_221` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_222` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_223` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_224` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_225` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_226` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_227` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_228` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_229` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_230` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_231` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_232` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_233` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_234` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_235` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_236` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_237` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_238` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_239` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_240` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_241` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_242` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_243` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_244` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_245` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_246` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_247` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_248` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_249` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_250` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_251` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_252` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_253` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_254` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |
| `nring2_255` | **256** | full packed | **256** | full packed | empty | empty | **seeded both-sense** |

---

## Verdict

- **Live both-sense: 2 / 256 — `nring2_000` and `nring2_002`.**
- **Seeded both-sense: 254 / 256.** Fwd+rev full packed, recv dark.
- **One-sense: 0 / 256.** None this pass.
- **Dark: 0 / 256.**
- Carry empty on all 256.
- Recv packed on `nring2_000` only. Recv sparse 1 on `nring2_002` only.
- `nring2_000.recv` = clock operand b, 1172 readers. Not pulsed.
- Earlier one-sense census of this bank is stale. Bits moved. This file is the later occupancy.

A computer with one ring is dumb. This bank is 256 both-sense packed rings. N clocks can respond.

Titan was not written.
