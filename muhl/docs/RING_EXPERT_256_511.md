# RING EXPERT — nring2_256 through nring2_511

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
READ ONLY. Titan not written. No glob. No `--go`. Fold-phys not pulsed.

Registry `C:/llm/models/titan_circuits.json` -> named keys `nring2_256` ... `nring2_511` (256 rings) -> bounded mmap `ACCESS_READ` windows in `C:/llm/models/titan.gguf`.
Windows: fwd 32 B, rev 32 B, carry 1 B, recv 1 B. Same impedance as `pfc_meter`.
The **1**s are occupancy — charge present on those cells. Not a metaphor.

**N clocks per ring.** Registry `depth` = 2 ticks on every ring in this band. `cells` = 32. `senses` = 2. MAGIC `NRING2M1`.
**One ring is dumb.** This file is a 256-ring bank, not a single nring2.

Surfaced 2026-08-15 05:17:35 UTC. Bounded read. Named keys only. titan size **103803349384**.

Live bits moved since the earlier 05:04:05 UTC one-sense census (fwd packed / rev empty). This read: **both rails packed**. That flip is the computer. Not corruption.

`nring2_511` occupancy only. Not a tick. Not fold-phys. Recv is local `4382218791`, not `muhl_fold_phys.ram.tick_off`.

---

## Method

- Named keys `nring2_256` ... `nring2_511`. No glob.
- `ram` windows from each registry entry.
- High-impedance: mmap `ACCESS_READ`, copy those windows, close.
- Ones counted on the copied bytes.
- Second confirm on `nring2_256`, `nring2_384`, `nring2_510`, `nring2_511` held the same occupancy.

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
MAGIC `NRING2M1` x 256.
Distinct occupancy signatures: **1**.

| call | count |
|---|---:|
| **seeded both-sense** | **256** |
| live both-sense | 0 |
| one-sense | 0 |
| dark | 0 |

Outliers vs seeded both-sense packed (fwd 256 / rev 256 / carry 0 / recv 0): **none**. Sparse: **none**.

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

## `nring2_511` — occupancy only

In this band. Occupancy only. Not a tick. Not fold-phys. Not 78-tick. Recv is the local rail byte.

| plane | offset | nB | ones | bits | call |
|---|---:|---:|---:|---|---|
| fwd | 4382218726 | 32 | **256** | all `11111111` | **packed** |
| rev | 4382218758 | 32 | **256** | all `11111111` | **packed** |
| carry | 4382218790 | 1 | **0** | `00000000` | **empty** |
| recv | 4382218791 | 1 | **0** | `00000000` | **empty** |

gate offset `4382218792`. MAGIC `NRING2M1`. cells=32. senses=2. depth=2. n_gate=66.

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

### recv — **00000000**. Empty. Local `4382218791`. Not `muhl_fold_phys.tick_off`. Not pulsed.

---

## Per ring

| ring | fwd off | fwd ones | fwd | rev off | rev ones | rev | carry | recv | call |
|---|---:|---:|---|---:|---:|---|---|---|---|
| `nring2_256` | 4381777066 | 256 | packed | 4381777098 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_257` | 4381778798 | 256 | packed | 4381778830 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_258` | 4381780530 | 256 | packed | 4381780562 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_259` | 4381782262 | 256 | packed | 4381782294 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_260` | 4381783994 | 256 | packed | 4381784026 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_261` | 4381785726 | 256 | packed | 4381785758 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_262` | 4381787458 | 256 | packed | 4381787490 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_263` | 4381789190 | 256 | packed | 4381789222 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_264` | 4381790922 | 256 | packed | 4381790954 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_265` | 4381792654 | 256 | packed | 4381792686 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_266` | 4381794386 | 256 | packed | 4381794418 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_267` | 4381796118 | 256 | packed | 4381796150 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_268` | 4381797850 | 256 | packed | 4381797882 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_269` | 4381799582 | 256 | packed | 4381799614 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_270` | 4381801314 | 256 | packed | 4381801346 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_271` | 4381803046 | 256 | packed | 4381803078 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_272` | 4381804778 | 256 | packed | 4381804810 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_273` | 4381806510 | 256 | packed | 4381806542 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_274` | 4381808242 | 256 | packed | 4381808274 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_275` | 4381809974 | 256 | packed | 4381810006 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_276` | 4381811706 | 256 | packed | 4381811738 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_277` | 4381813438 | 256 | packed | 4381813470 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_278` | 4381815170 | 256 | packed | 4381815202 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_279` | 4381816902 | 256 | packed | 4381816934 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_280` | 4381818634 | 256 | packed | 4381818666 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_281` | 4381820366 | 256 | packed | 4381820398 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_282` | 4381822098 | 256 | packed | 4381822130 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_283` | 4381823830 | 256 | packed | 4381823862 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_284` | 4381825562 | 256 | packed | 4381825594 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_285` | 4381827294 | 256 | packed | 4381827326 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_286` | 4381829026 | 256 | packed | 4381829058 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_287` | 4381830758 | 256 | packed | 4381830790 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_288` | 4381832490 | 256 | packed | 4381832522 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_289` | 4381834222 | 256 | packed | 4381834254 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_290` | 4381835954 | 256 | packed | 4381835986 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_291` | 4381837686 | 256 | packed | 4381837718 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_292` | 4381839418 | 256 | packed | 4381839450 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_293` | 4381841150 | 256 | packed | 4381841182 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_294` | 4381842882 | 256 | packed | 4381842914 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_295` | 4381844614 | 256 | packed | 4381844646 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_296` | 4381846346 | 256 | packed | 4381846378 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_297` | 4381848078 | 256 | packed | 4381848110 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_298` | 4381849810 | 256 | packed | 4381849842 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_299` | 4381851542 | 256 | packed | 4381851574 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_300` | 4381853274 | 256 | packed | 4381853306 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_301` | 4381855006 | 256 | packed | 4381855038 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_302` | 4381856738 | 256 | packed | 4381856770 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_303` | 4381858470 | 256 | packed | 4381858502 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_304` | 4381860202 | 256 | packed | 4381860234 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_305` | 4381861934 | 256 | packed | 4381861966 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_306` | 4381863666 | 256 | packed | 4381863698 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_307` | 4381865398 | 256 | packed | 4381865430 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_308` | 4381867130 | 256 | packed | 4381867162 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_309` | 4381868862 | 256 | packed | 4381868894 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_310` | 4381870594 | 256 | packed | 4381870626 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_311` | 4381872326 | 256 | packed | 4381872358 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_312` | 4381874058 | 256 | packed | 4381874090 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_313` | 4381875790 | 256 | packed | 4381875822 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_314` | 4381877522 | 256 | packed | 4381877554 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_315` | 4381879254 | 256 | packed | 4381879286 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_316` | 4381880986 | 256 | packed | 4381881018 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_317` | 4381882718 | 256 | packed | 4381882750 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_318` | 4381884450 | 256 | packed | 4381884482 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_319` | 4381886182 | 256 | packed | 4381886214 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_320` | 4381887914 | 256 | packed | 4381887946 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_321` | 4381889646 | 256 | packed | 4381889678 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_322` | 4381891378 | 256 | packed | 4381891410 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_323` | 4381893110 | 256 | packed | 4381893142 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_324` | 4381894842 | 256 | packed | 4381894874 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_325` | 4381896574 | 256 | packed | 4381896606 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_326` | 4381898306 | 256 | packed | 4381898338 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_327` | 4381900038 | 256 | packed | 4381900070 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_328` | 4381901770 | 256 | packed | 4381901802 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_329` | 4381903502 | 256 | packed | 4381903534 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_330` | 4381905234 | 256 | packed | 4381905266 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_331` | 4381906966 | 256 | packed | 4381906998 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_332` | 4381908698 | 256 | packed | 4381908730 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_333` | 4381910430 | 256 | packed | 4381910462 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_334` | 4381912162 | 256 | packed | 4381912194 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_335` | 4381913894 | 256 | packed | 4381913926 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_336` | 4381915626 | 256 | packed | 4381915658 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_337` | 4381917358 | 256 | packed | 4381917390 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_338` | 4381919090 | 256 | packed | 4381919122 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_339` | 4381920822 | 256 | packed | 4381920854 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_340` | 4381922554 | 256 | packed | 4381922586 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_341` | 4381924286 | 256 | packed | 4381924318 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_342` | 4381926018 | 256 | packed | 4381926050 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_343` | 4381927750 | 256 | packed | 4381927782 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_344` | 4381929482 | 256 | packed | 4381929514 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_345` | 4381931214 | 256 | packed | 4381931246 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_346` | 4381932946 | 256 | packed | 4381932978 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_347` | 4381934678 | 256 | packed | 4381934710 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_348` | 4381936410 | 256 | packed | 4381936442 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_349` | 4381938142 | 256 | packed | 4381938174 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_350` | 4381939874 | 256 | packed | 4381939906 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_351` | 4381941606 | 256 | packed | 4381941638 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_352` | 4381943338 | 256 | packed | 4381943370 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_353` | 4381945070 | 256 | packed | 4381945102 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_354` | 4381946802 | 256 | packed | 4381946834 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_355` | 4381948534 | 256 | packed | 4381948566 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_356` | 4381950266 | 256 | packed | 4381950298 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_357` | 4381951998 | 256 | packed | 4381952030 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_358` | 4381953730 | 256 | packed | 4381953762 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_359` | 4381955462 | 256 | packed | 4381955494 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_360` | 4381957194 | 256 | packed | 4381957226 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_361` | 4381958926 | 256 | packed | 4381958958 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_362` | 4381960658 | 256 | packed | 4381960690 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_363` | 4381962390 | 256 | packed | 4381962422 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_364` | 4381964122 | 256 | packed | 4381964154 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_365` | 4381965854 | 256 | packed | 4381965886 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_366` | 4381967586 | 256 | packed | 4381967618 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_367` | 4381969318 | 256 | packed | 4381969350 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_368` | 4381971050 | 256 | packed | 4381971082 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_369` | 4381972782 | 256 | packed | 4381972814 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_370` | 4381974514 | 256 | packed | 4381974546 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_371` | 4381976246 | 256 | packed | 4381976278 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_372` | 4381977978 | 256 | packed | 4381978010 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_373` | 4381979710 | 256 | packed | 4381979742 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_374` | 4381981442 | 256 | packed | 4381981474 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_375` | 4381983174 | 256 | packed | 4381983206 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_376` | 4381984906 | 256 | packed | 4381984938 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_377` | 4381986638 | 256 | packed | 4381986670 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_378` | 4381988370 | 256 | packed | 4381988402 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_379` | 4381990102 | 256 | packed | 4381990134 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_380` | 4381991834 | 256 | packed | 4381991866 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_381` | 4381993566 | 256 | packed | 4381993598 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_382` | 4381995298 | 256 | packed | 4381995330 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_383` | 4381997030 | 256 | packed | 4381997062 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_384` | 4381998762 | 256 | packed | 4381998794 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_385` | 4382000494 | 256 | packed | 4382000526 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_386` | 4382002226 | 256 | packed | 4382002258 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_387` | 4382003958 | 256 | packed | 4382003990 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_388` | 4382005690 | 256 | packed | 4382005722 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_389` | 4382007422 | 256 | packed | 4382007454 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_390` | 4382009154 | 256 | packed | 4382009186 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_391` | 4382010886 | 256 | packed | 4382010918 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_392` | 4382012618 | 256 | packed | 4382012650 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_393` | 4382014350 | 256 | packed | 4382014382 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_394` | 4382016082 | 256 | packed | 4382016114 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_395` | 4382017814 | 256 | packed | 4382017846 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_396` | 4382019546 | 256 | packed | 4382019578 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_397` | 4382021278 | 256 | packed | 4382021310 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_398` | 4382023010 | 256 | packed | 4382023042 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_399` | 4382024742 | 256 | packed | 4382024774 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_400` | 4382026474 | 256 | packed | 4382026506 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_401` | 4382028206 | 256 | packed | 4382028238 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_402` | 4382029938 | 256 | packed | 4382029970 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_403` | 4382031670 | 256 | packed | 4382031702 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_404` | 4382033402 | 256 | packed | 4382033434 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_405` | 4382035134 | 256 | packed | 4382035166 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_406` | 4382036866 | 256 | packed | 4382036898 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_407` | 4382038598 | 256 | packed | 4382038630 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_408` | 4382040330 | 256 | packed | 4382040362 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_409` | 4382042062 | 256 | packed | 4382042094 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_410` | 4382043794 | 256 | packed | 4382043826 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_411` | 4382045526 | 256 | packed | 4382045558 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_412` | 4382047258 | 256 | packed | 4382047290 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_413` | 4382048990 | 256 | packed | 4382049022 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_414` | 4382050722 | 256 | packed | 4382050754 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_415` | 4382052454 | 256 | packed | 4382052486 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_416` | 4382054186 | 256 | packed | 4382054218 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_417` | 4382055918 | 256 | packed | 4382055950 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_418` | 4382057650 | 256 | packed | 4382057682 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_419` | 4382059382 | 256 | packed | 4382059414 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_420` | 4382061114 | 256 | packed | 4382061146 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_421` | 4382062846 | 256 | packed | 4382062878 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_422` | 4382064578 | 256 | packed | 4382064610 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_423` | 4382066310 | 256 | packed | 4382066342 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_424` | 4382068042 | 256 | packed | 4382068074 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_425` | 4382069774 | 256 | packed | 4382069806 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_426` | 4382071506 | 256 | packed | 4382071538 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_427` | 4382073238 | 256 | packed | 4382073270 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_428` | 4382074970 | 256 | packed | 4382075002 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_429` | 4382076702 | 256 | packed | 4382076734 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_430` | 4382078434 | 256 | packed | 4382078466 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_431` | 4382080166 | 256 | packed | 4382080198 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_432` | 4382081898 | 256 | packed | 4382081930 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_433` | 4382083630 | 256 | packed | 4382083662 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_434` | 4382085362 | 256 | packed | 4382085394 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_435` | 4382087094 | 256 | packed | 4382087126 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_436` | 4382088826 | 256 | packed | 4382088858 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_437` | 4382090558 | 256 | packed | 4382090590 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_438` | 4382092290 | 256 | packed | 4382092322 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_439` | 4382094022 | 256 | packed | 4382094054 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_440` | 4382095754 | 256 | packed | 4382095786 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_441` | 4382097486 | 256 | packed | 4382097518 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_442` | 4382099218 | 256 | packed | 4382099250 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_443` | 4382100950 | 256 | packed | 4382100982 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_444` | 4382102682 | 256 | packed | 4382102714 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_445` | 4382104414 | 256 | packed | 4382104446 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_446` | 4382106146 | 256 | packed | 4382106178 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_447` | 4382107878 | 256 | packed | 4382107910 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_448` | 4382109610 | 256 | packed | 4382109642 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_449` | 4382111342 | 256 | packed | 4382111374 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_450` | 4382113074 | 256 | packed | 4382113106 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_451` | 4382114806 | 256 | packed | 4382114838 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_452` | 4382116538 | 256 | packed | 4382116570 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_453` | 4382118270 | 256 | packed | 4382118302 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_454` | 4382120002 | 256 | packed | 4382120034 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_455` | 4382121734 | 256 | packed | 4382121766 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_456` | 4382123466 | 256 | packed | 4382123498 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_457` | 4382125198 | 256 | packed | 4382125230 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_458` | 4382126930 | 256 | packed | 4382126962 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_459` | 4382128662 | 256 | packed | 4382128694 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_460` | 4382130394 | 256 | packed | 4382130426 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_461` | 4382132126 | 256 | packed | 4382132158 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_462` | 4382133858 | 256 | packed | 4382133890 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_463` | 4382135590 | 256 | packed | 4382135622 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_464` | 4382137322 | 256 | packed | 4382137354 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_465` | 4382139054 | 256 | packed | 4382139086 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_466` | 4382140786 | 256 | packed | 4382140818 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_467` | 4382142518 | 256 | packed | 4382142550 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_468` | 4382144250 | 256 | packed | 4382144282 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_469` | 4382145982 | 256 | packed | 4382146014 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_470` | 4382147714 | 256 | packed | 4382147746 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_471` | 4382149446 | 256 | packed | 4382149478 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_472` | 4382151178 | 256 | packed | 4382151210 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_473` | 4382152910 | 256 | packed | 4382152942 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_474` | 4382154642 | 256 | packed | 4382154674 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_475` | 4382156374 | 256 | packed | 4382156406 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_476` | 4382158106 | 256 | packed | 4382158138 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_477` | 4382159838 | 256 | packed | 4382159870 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_478` | 4382161570 | 256 | packed | 4382161602 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_479` | 4382163302 | 256 | packed | 4382163334 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_480` | 4382165034 | 256 | packed | 4382165066 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_481` | 4382166766 | 256 | packed | 4382166798 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_482` | 4382168498 | 256 | packed | 4382168530 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_483` | 4382170230 | 256 | packed | 4382170262 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_484` | 4382171962 | 256 | packed | 4382171994 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_485` | 4382173694 | 256 | packed | 4382173726 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_486` | 4382175426 | 256 | packed | 4382175458 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_487` | 4382177158 | 256 | packed | 4382177190 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_488` | 4382178890 | 256 | packed | 4382178922 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_489` | 4382180622 | 256 | packed | 4382180654 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_490` | 4382182354 | 256 | packed | 4382182386 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_491` | 4382184086 | 256 | packed | 4382184118 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_492` | 4382185818 | 256 | packed | 4382185850 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_493` | 4382187550 | 256 | packed | 4382187582 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_494` | 4382189282 | 256 | packed | 4382189314 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_495` | 4382191014 | 256 | packed | 4382191046 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_496` | 4382192746 | 256 | packed | 4382192778 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_497` | 4382194478 | 256 | packed | 4382194510 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_498` | 4382196210 | 256 | packed | 4382196242 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_499` | 4382197942 | 256 | packed | 4382197974 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_500` | 4382199674 | 256 | packed | 4382199706 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_501` | 4382201406 | 256 | packed | 4382201438 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_502` | 4382203138 | 256 | packed | 4382203170 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_503` | 4382204870 | 256 | packed | 4382204902 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_504` | 4382206602 | 256 | packed | 4382206634 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_505` | 4382208334 | 256 | packed | 4382208366 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_506` | 4382210066 | 256 | packed | 4382210098 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_507` | 4382211798 | 256 | packed | 4382211830 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_508` | 4382213530 | 256 | packed | 4382213562 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_509` | 4382215262 | 256 | packed | 4382215294 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_510` | 4382216994 | 256 | packed | 4382217026 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |
| `nring2_511` | 4382218726 | 256 | packed | 4382218758 | 256 | packed | empty (00000000) | empty (00000000) | seeded both-sense |

---

## Law

MORE charge on the ring = more bumps = less distance = SPEED.
**N clocks per ring.** More clocks = faster. This band: depth=2 on each of 256 rings.
**One ring is dumb.** A muhlnickel is N rings.

This band is seeded both-sense packed: fwd full, rev full, carry empty, recv empty. Including `nring2_511`.
Recv empty -> not live. Occupancy only.

Do not write titan. Do not `--go`. Do not glob. Do not pulse fold-phys. `nring2_511` occupancy only.
