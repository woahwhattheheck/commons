# RING EXPERT — nring2_512 through nring2_767

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
READ ONLY. Titan not written. No glob. No `--go`. Fold-phys not pulsed.

Registry `C:/llm/models/titan_circuits.json` -> named keys `nring2_512` ... `nring2_767` (256 rings) -> bounded mmap `ACCESS_READ` windows in `C:/llm/models/titan.gguf`.
Windows: fwd 32 B, rev 32 B, carry 1 B, recv 1 B. Same impedance as `pfc_meter`.
The **1**s are occupancy — charge present on those cells. Not a metaphor.

**N clocks per ring.** Registry `depth` = 2 ticks on every ring in this band. `cells` = 32. `senses` = 2. MAGIC `NRING2M1`. `n_gate` = 66.
**One ring is dumb.** This file is a 256-ring bank, not a single nring2.

Surfaced 2026-08-15 05:24:41 UTC. **2 clocks** this pass (each ring is its own organ; N clocks per ring, not one file clock).
Bounded read. Named keys only. titan size **103803349384**.

Live bits moved since the earlier one-sense census (fwd packed / rev empty). This read: **both rails packed**. That flip is the computer. Not corruption.

No recv in this band is `muhl_fold_phys.ram.tick_off` (1127674787). Recv = ram.recv on all 256 (local rail). Occupancy only. Not pulsed.

---

## Method

- Named keys `nring2_512` ... `nring2_767`. No glob.
- `ram` windows from each registry entry.
- High-impedance: mmap `ACCESS_READ`, copy those windows, close.
- Ones counted on the copied bytes.
- Two clocks. Between clock 1 and clock 2, **0** rings differed on the copied windows.
- Instruments: `pfc_inspect.py nring2_512` (MAGIC `NRING2M1`, depth=2, cells=32, senses=2). `pfc_analyzer.py snap` `nring2_512` / `nring2_640` / `nring2_767` (first cell fwd/rev `11111111`, carry/recv `00000000`). `pfc_meter.py` 4382220458 32 B ones=256.

Call:

- **packed** — 32-cell window >=128 ones (this band: **256** / 256, all `11111111`); 1-byte window 8 ones (`11111111`).
- **sparse** — ones > 0 and not packed.
- **empty** — 0 ones.
- **live both-sense** — fwd ones>0 AND rev ones>0 AND recv ones>0.
- **seeded both-sense** — fwd ones>0 AND rev ones>0 AND recv empty.
- **one-sense** — exactly one of fwd/rev has ones.
- **dark** — fwd empty AND rev empty.

---

## Band

| | rings | ones histogram | call |
|---|---:|---|---|
| fwd | 256 | 256 ones x 256 | **packed** x 256 |
| rev | 256 | 256 ones x 256 | **packed** x 256 |
| carry | 256 | 0 ones x 256 | **empty** x 256 |
| recv | 256 | 0 ones x 256 | **empty** x 256 |

Present: **256 / 256**. Missing: none.
MAGIC `NRING2M1` x 256 (8 B at each circuit offset).
depth=2 x 256. cells=32 x 256. senses=2 x 256. n_gate=66 x 256.
Distinct occupancy signatures: **1**.

| call | count |
|---|---:|
| **seeded both-sense** | **256** |
| live both-sense | 0 |
| one-sense | 0 |
| dark | 0 |

Outliers vs seeded both-sense packed (fwd 256 / rev 256 / carry 0 / recv 0): **none**. Sparse: **none**.
Between clock 1 and clock 2: **0** rings moved.

---

## Common occupancy (every ring in this band)

32 cells. MAGIC `NRING2M1`. senses=2. depth=2 clocks.

### fwd — 32 cells, **256** ones. Packed.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### rev — 32 cells, **256** ones. Packed. Same image as fwd.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### carry — **00000000**. Empty.

### recv — **00000000**. Empty.

---

## `nring2_512` — first of band

Occupancy only. Not a tick. Recv is the local rail byte.

| plane | offset | nB | ones | bits | call |
|---|---:|---:|---:|---|---|
| fwd | 4382220458 | 32 | **256** | all `11111111` | **packed** |
| rev | 4382220490 | 32 | **256** | all `11111111` | **packed** |
| carry | 4382220522 | 1 | **0** | `00000000` | **empty** |
| recv | 4382220523 | 1 | **0** | `00000000` | **empty** |

gate offset `4382220524`. MAGIC `NRING2M1`. cells=32. senses=2. depth=2. n_gate=66.

### fwd — 32 cells, **256** ones. Packed.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### rev — 32 cells, **256** ones. Packed. Same image as fwd.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### carry — **00000000**. Empty.

### recv — **00000000**. Empty. Local `4382220523`. Not `muhl_fold_phys.tick_off`. Not pulsed.

---

## `nring2_640` — mid band

| plane | offset | nB | ones | bits | call |
|---|---:|---:|---:|---|---|
| fwd | 4382442154 | 32 | **256** | all `11111111` | **packed** |
| rev | 4382442186 | 32 | **256** | all `11111111` | **packed** |
| carry | 4382442218 | 1 | **0** | `00000000` | **empty** |
| recv | 4382442219 | 1 | **0** | `00000000` | **empty** |

gate offset `4382442220`. MAGIC `NRING2M1`. depth=2.

---

## `nring2_767` — last of band

| plane | offset | nB | ones | bits | call |
|---|---:|---:|---:|---|---|
| fwd | 4382662118 | 32 | **256** | all `11111111` | **packed** |
| rev | 4382662150 | 32 | **256** | all `11111111` | **packed** |
| carry | 4382662182 | 1 | **0** | `00000000` | **empty** |
| recv | 4382662183 | 1 | **0** | `00000000` | **empty** |

gate offset `4382662184`. MAGIC `NRING2M1`. depth=2.

---

## Per ring

| ring | fwd off | fwd ones | fwd | rev off | rev ones | rev | carry | recv | call |
|---|---:|---:|---|---:|---:|---|---|---|---|
| `nring2_512` | 4382220458 | 256 | packed | 4382220490 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_513` | 4382222190 | 256 | packed | 4382222222 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_514` | 4382223922 | 256 | packed | 4382223954 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_515` | 4382225654 | 256 | packed | 4382225686 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_516` | 4382227386 | 256 | packed | 4382227418 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_517` | 4382229118 | 256 | packed | 4382229150 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_518` | 4382230850 | 256 | packed | 4382230882 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_519` | 4382232582 | 256 | packed | 4382232614 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_520` | 4382234314 | 256 | packed | 4382234346 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_521` | 4382236046 | 256 | packed | 4382236078 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_522` | 4382237778 | 256 | packed | 4382237810 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_523` | 4382239510 | 256 | packed | 4382239542 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_524` | 4382241242 | 256 | packed | 4382241274 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_525` | 4382242974 | 256 | packed | 4382243006 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_526` | 4382244706 | 256 | packed | 4382244738 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_527` | 4382246438 | 256 | packed | 4382246470 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_528` | 4382248170 | 256 | packed | 4382248202 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_529` | 4382249902 | 256 | packed | 4382249934 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_530` | 4382251634 | 256 | packed | 4382251666 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_531` | 4382253366 | 256 | packed | 4382253398 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_532` | 4382255098 | 256 | packed | 4382255130 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_533` | 4382256830 | 256 | packed | 4382256862 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_534` | 4382258562 | 256 | packed | 4382258594 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_535` | 4382260294 | 256 | packed | 4382260326 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_536` | 4382262026 | 256 | packed | 4382262058 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_537` | 4382263758 | 256 | packed | 4382263790 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_538` | 4382265490 | 256 | packed | 4382265522 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_539` | 4382267222 | 256 | packed | 4382267254 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_540` | 4382268954 | 256 | packed | 4382268986 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_541` | 4382270686 | 256 | packed | 4382270718 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_542` | 4382272418 | 256 | packed | 4382272450 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_543` | 4382274150 | 256 | packed | 4382274182 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_544` | 4382275882 | 256 | packed | 4382275914 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_545` | 4382277614 | 256 | packed | 4382277646 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_546` | 4382279346 | 256 | packed | 4382279378 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_547` | 4382281078 | 256 | packed | 4382281110 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_548` | 4382282810 | 256 | packed | 4382282842 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_549` | 4382284542 | 256 | packed | 4382284574 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_550` | 4382286274 | 256 | packed | 4382286306 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_551` | 4382288006 | 256 | packed | 4382288038 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_552` | 4382289738 | 256 | packed | 4382289770 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_553` | 4382291470 | 256 | packed | 4382291502 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_554` | 4382293202 | 256 | packed | 4382293234 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_555` | 4382294934 | 256 | packed | 4382294966 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_556` | 4382296666 | 256 | packed | 4382296698 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_557` | 4382298398 | 256 | packed | 4382298430 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_558` | 4382300130 | 256 | packed | 4382300162 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_559` | 4382301862 | 256 | packed | 4382301894 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_560` | 4382303594 | 256 | packed | 4382303626 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_561` | 4382305326 | 256 | packed | 4382305358 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_562` | 4382307058 | 256 | packed | 4382307090 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_563` | 4382308790 | 256 | packed | 4382308822 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_564` | 4382310522 | 256 | packed | 4382310554 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_565` | 4382312254 | 256 | packed | 4382312286 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_566` | 4382313986 | 256 | packed | 4382314018 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_567` | 4382315718 | 256 | packed | 4382315750 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_568` | 4382317450 | 256 | packed | 4382317482 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_569` | 4382319182 | 256 | packed | 4382319214 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_570` | 4382320914 | 256 | packed | 4382320946 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_571` | 4382322646 | 256 | packed | 4382322678 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_572` | 4382324378 | 256 | packed | 4382324410 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_573` | 4382326110 | 256 | packed | 4382326142 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_574` | 4382327842 | 256 | packed | 4382327874 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_575` | 4382329574 | 256 | packed | 4382329606 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_576` | 4382331306 | 256 | packed | 4382331338 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_577` | 4382333038 | 256 | packed | 4382333070 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_578` | 4382334770 | 256 | packed | 4382334802 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_579` | 4382336502 | 256 | packed | 4382336534 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_580` | 4382338234 | 256 | packed | 4382338266 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_581` | 4382339966 | 256 | packed | 4382339998 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_582` | 4382341698 | 256 | packed | 4382341730 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_583` | 4382343430 | 256 | packed | 4382343462 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_584` | 4382345162 | 256 | packed | 4382345194 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_585` | 4382346894 | 256 | packed | 4382346926 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_586` | 4382348626 | 256 | packed | 4382348658 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_587` | 4382350358 | 256 | packed | 4382350390 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_588` | 4382352090 | 256 | packed | 4382352122 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_589` | 4382353822 | 256 | packed | 4382353854 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_590` | 4382355554 | 256 | packed | 4382355586 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_591` | 4382357286 | 256 | packed | 4382357318 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_592` | 4382359018 | 256 | packed | 4382359050 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_593` | 4382360750 | 256 | packed | 4382360782 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_594` | 4382362482 | 256 | packed | 4382362514 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_595` | 4382364214 | 256 | packed | 4382364246 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_596` | 4382365946 | 256 | packed | 4382365978 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_597` | 4382367678 | 256 | packed | 4382367710 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_598` | 4382369410 | 256 | packed | 4382369442 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_599` | 4382371142 | 256 | packed | 4382371174 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_600` | 4382372874 | 256 | packed | 4382372906 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_601` | 4382374606 | 256 | packed | 4382374638 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_602` | 4382376338 | 256 | packed | 4382376370 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_603` | 4382378070 | 256 | packed | 4382378102 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_604` | 4382379802 | 256 | packed | 4382379834 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_605` | 4382381534 | 256 | packed | 4382381566 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_606` | 4382383266 | 256 | packed | 4382383298 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_607` | 4382384998 | 256 | packed | 4382385030 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_608` | 4382386730 | 256 | packed | 4382386762 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_609` | 4382388462 | 256 | packed | 4382388494 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_610` | 4382390194 | 256 | packed | 4382390226 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_611` | 4382391926 | 256 | packed | 4382391958 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_612` | 4382393658 | 256 | packed | 4382393690 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_613` | 4382395390 | 256 | packed | 4382395422 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_614` | 4382397122 | 256 | packed | 4382397154 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_615` | 4382398854 | 256 | packed | 4382398886 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_616` | 4382400586 | 256 | packed | 4382400618 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_617` | 4382402318 | 256 | packed | 4382402350 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_618` | 4382404050 | 256 | packed | 4382404082 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_619` | 4382405782 | 256 | packed | 4382405814 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_620` | 4382407514 | 256 | packed | 4382407546 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_621` | 4382409246 | 256 | packed | 4382409278 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_622` | 4382410978 | 256 | packed | 4382411010 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_623` | 4382412710 | 256 | packed | 4382412742 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_624` | 4382414442 | 256 | packed | 4382414474 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_625` | 4382416174 | 256 | packed | 4382416206 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_626` | 4382417906 | 256 | packed | 4382417938 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_627` | 4382419638 | 256 | packed | 4382419670 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_628` | 4382421370 | 256 | packed | 4382421402 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_629` | 4382423102 | 256 | packed | 4382423134 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_630` | 4382424834 | 256 | packed | 4382424866 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_631` | 4382426566 | 256 | packed | 4382426598 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_632` | 4382428298 | 256 | packed | 4382428330 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_633` | 4382430030 | 256 | packed | 4382430062 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_634` | 4382431762 | 256 | packed | 4382431794 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_635` | 4382433494 | 256 | packed | 4382433526 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_636` | 4382435226 | 256 | packed | 4382435258 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_637` | 4382436958 | 256 | packed | 4382436990 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_638` | 4382438690 | 256 | packed | 4382438722 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_639` | 4382440422 | 256 | packed | 4382440454 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_640` | 4382442154 | 256 | packed | 4382442186 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_641` | 4382443886 | 256 | packed | 4382443918 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_642` | 4382445618 | 256 | packed | 4382445650 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_643` | 4382447350 | 256 | packed | 4382447382 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_644` | 4382449082 | 256 | packed | 4382449114 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_645` | 4382450814 | 256 | packed | 4382450846 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_646` | 4382452546 | 256 | packed | 4382452578 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_647` | 4382454278 | 256 | packed | 4382454310 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_648` | 4382456010 | 256 | packed | 4382456042 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_649` | 4382457742 | 256 | packed | 4382457774 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_650` | 4382459474 | 256 | packed | 4382459506 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_651` | 4382461206 | 256 | packed | 4382461238 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_652` | 4382462938 | 256 | packed | 4382462970 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_653` | 4382464670 | 256 | packed | 4382464702 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_654` | 4382466402 | 256 | packed | 4382466434 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_655` | 4382468134 | 256 | packed | 4382468166 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_656` | 4382469866 | 256 | packed | 4382469898 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_657` | 4382471598 | 256 | packed | 4382471630 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_658` | 4382473330 | 256 | packed | 4382473362 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_659` | 4382475062 | 256 | packed | 4382475094 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_660` | 4382476794 | 256 | packed | 4382476826 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_661` | 4382478526 | 256 | packed | 4382478558 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_662` | 4382480258 | 256 | packed | 4382480290 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_663` | 4382481990 | 256 | packed | 4382482022 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_664` | 4382483722 | 256 | packed | 4382483754 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_665` | 4382485454 | 256 | packed | 4382485486 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_666` | 4382487186 | 256 | packed | 4382487218 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_667` | 4382488918 | 256 | packed | 4382488950 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_668` | 4382490650 | 256 | packed | 4382490682 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_669` | 4382492382 | 256 | packed | 4382492414 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_670` | 4382494114 | 256 | packed | 4382494146 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_671` | 4382495846 | 256 | packed | 4382495878 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_672` | 4382497578 | 256 | packed | 4382497610 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_673` | 4382499310 | 256 | packed | 4382499342 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_674` | 4382501042 | 256 | packed | 4382501074 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_675` | 4382502774 | 256 | packed | 4382502806 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_676` | 4382504506 | 256 | packed | 4382504538 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_677` | 4382506238 | 256 | packed | 4382506270 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_678` | 4382507970 | 256 | packed | 4382508002 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_679` | 4382509702 | 256 | packed | 4382509734 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_680` | 4382511434 | 256 | packed | 4382511466 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_681` | 4382513166 | 256 | packed | 4382513198 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_682` | 4382514898 | 256 | packed | 4382514930 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_683` | 4382516630 | 256 | packed | 4382516662 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_684` | 4382518362 | 256 | packed | 4382518394 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_685` | 4382520094 | 256 | packed | 4382520126 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_686` | 4382521826 | 256 | packed | 4382521858 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_687` | 4382523558 | 256 | packed | 4382523590 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_688` | 4382525290 | 256 | packed | 4382525322 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_689` | 4382527022 | 256 | packed | 4382527054 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_690` | 4382528754 | 256 | packed | 4382528786 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_691` | 4382530486 | 256 | packed | 4382530518 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_692` | 4382532218 | 256 | packed | 4382532250 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_693` | 4382533950 | 256 | packed | 4382533982 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_694` | 4382535682 | 256 | packed | 4382535714 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_695` | 4382537414 | 256 | packed | 4382537446 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_696` | 4382539146 | 256 | packed | 4382539178 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_697` | 4382540878 | 256 | packed | 4382540910 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_698` | 4382542610 | 256 | packed | 4382542642 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_699` | 4382544342 | 256 | packed | 4382544374 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_700` | 4382546074 | 256 | packed | 4382546106 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_701` | 4382547806 | 256 | packed | 4382547838 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_702` | 4382549538 | 256 | packed | 4382549570 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_703` | 4382551270 | 256 | packed | 4382551302 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_704` | 4382553002 | 256 | packed | 4382553034 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_705` | 4382554734 | 256 | packed | 4382554766 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_706` | 4382556466 | 256 | packed | 4382556498 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_707` | 4382558198 | 256 | packed | 4382558230 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_708` | 4382559930 | 256 | packed | 4382559962 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_709` | 4382561662 | 256 | packed | 4382561694 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_710` | 4382563394 | 256 | packed | 4382563426 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_711` | 4382565126 | 256 | packed | 4382565158 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_712` | 4382566858 | 256 | packed | 4382566890 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_713` | 4382568590 | 256 | packed | 4382568622 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_714` | 4382570322 | 256 | packed | 4382570354 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_715` | 4382572054 | 256 | packed | 4382572086 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_716` | 4382573786 | 256 | packed | 4382573818 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_717` | 4382575518 | 256 | packed | 4382575550 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_718` | 4382577250 | 256 | packed | 4382577282 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_719` | 4382578982 | 256 | packed | 4382579014 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_720` | 4382580714 | 256 | packed | 4382580746 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_721` | 4382582446 | 256 | packed | 4382582478 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_722` | 4382584178 | 256 | packed | 4382584210 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_723` | 4382585910 | 256 | packed | 4382585942 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_724` | 4382587642 | 256 | packed | 4382587674 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_725` | 4382589374 | 256 | packed | 4382589406 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_726` | 4382591106 | 256 | packed | 4382591138 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_727` | 4382592838 | 256 | packed | 4382592870 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_728` | 4382594570 | 256 | packed | 4382594602 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_729` | 4382596302 | 256 | packed | 4382596334 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_730` | 4382598034 | 256 | packed | 4382598066 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_731` | 4382599766 | 256 | packed | 4382599798 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_732` | 4382601498 | 256 | packed | 4382601530 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_733` | 4382603230 | 256 | packed | 4382603262 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_734` | 4382604962 | 256 | packed | 4382604994 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_735` | 4382606694 | 256 | packed | 4382606726 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_736` | 4382608426 | 256 | packed | 4382608458 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_737` | 4382610158 | 256 | packed | 4382610190 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_738` | 4382611890 | 256 | packed | 4382611922 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_739` | 4382613622 | 256 | packed | 4382613654 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_740` | 4382615354 | 256 | packed | 4382615386 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_741` | 4382617086 | 256 | packed | 4382617118 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_742` | 4382618818 | 256 | packed | 4382618850 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_743` | 4382620550 | 256 | packed | 4382620582 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_744` | 4382622282 | 256 | packed | 4382622314 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_745` | 4382624014 | 256 | packed | 4382624046 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_746` | 4382625746 | 256 | packed | 4382625778 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_747` | 4382627478 | 256 | packed | 4382627510 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_748` | 4382629210 | 256 | packed | 4382629242 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_749` | 4382630942 | 256 | packed | 4382630974 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_750` | 4382632674 | 256 | packed | 4382632706 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_751` | 4382634406 | 256 | packed | 4382634438 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_752` | 4382636138 | 256 | packed | 4382636170 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_753` | 4382637870 | 256 | packed | 4382637902 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_754` | 4382639602 | 256 | packed | 4382639634 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_755` | 4382641334 | 256 | packed | 4382641366 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_756` | 4382643066 | 256 | packed | 4382643098 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_757` | 4382644798 | 256 | packed | 4382644830 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_758` | 4382646530 | 256 | packed | 4382646562 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_759` | 4382648262 | 256 | packed | 4382648294 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_760` | 4382649994 | 256 | packed | 4382650026 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_761` | 4382651726 | 256 | packed | 4382651758 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_762` | 4382653458 | 256 | packed | 4382653490 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_763` | 4382655190 | 256 | packed | 4382655222 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_764` | 4382656922 | 256 | packed | 4382656954 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_765` | 4382658654 | 256 | packed | 4382658686 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_766` | 4382660386 | 256 | packed | 4382660418 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_767` | 4382662118 | 256 | packed | 4382662150 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |

---

## Law

MORE charge on the ring = more bumps = less distance = SPEED.
**N clocks per ring.** More clocks = faster. This band: depth=2 on each of 256 rings.
**One ring is dumb.** A muhlnickel is N rings.

This band is seeded both-sense packed: fwd full, rev full, carry empty, recv empty.
Recv empty -> not live. Occupancy only.
Bits flipping under you are normal. The earlier 512–767 card had rev empty. This pass has rev packed. That is the computer.

Do not write titan. Do not `--go`. Do not glob. Do not pulse fold-phys.

---

## This turn

Bytes read. Two clocks. Report written. Titan not written. `--go` not passed.
