# RING EXPERT 768–1023

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
READ ONLY. Titan not written. No `--go`. No pulse. No glob.
Bounded `ACCESS_READ` of named `nring2` RAM windows in `C:/llm/models/titan.gguf`
via registry `C:/llm/models/titan_circuits.json`. Ones and zeros. Not hex.

Surfaced 2026-08-15 05:20:04 UTC. **2 clocks** this pass (each ring is its own organ; N clocks per ring, not one file clock).
Range: `nring2_768` … `nring2_1023`. **256** rings named. Missing: **0**.
MAGIC `NRING2M1`. 32 cells/sense. senses=2. depth=2 ticks.
The **1**s are occupancy — charge present on those cells.

**`nring2_1023.recv` IS `muhl_fold_phys.ram.tick_off` = `1127674787`.**
That byte starts the MUHLFLD1 SHA lane. **Not the 78-tick. Not pulsed this pass.**
Occupancy of **fwd/rev** is the job.

---

## Census

titan size this read: **103803349384** bytes.
Named keys present: **256 / 256**. Missing: none.

| sense | packed | sparse | empty |
|---|---:|---:|---:|
| fwd | 256 | 0 | 0 |
| rev | 256 | 0 | 0 |
| carry | 0 | 0 | 256 |
| recv | 0 | 0 | 256 |

| ones | fwd rings | rev rings |
|---:|---:|---:|
| 256 | 256 | 256 |

fwd ones histogram: 256 ones × 256

rev ones histogram: 256 ones × 256

| call | count |
|---|---:|
| seeded both-sense | 256 |

Law used:

- **live both-sense** = fwd ones>0 AND rev ones>0 AND recv ones>0.
- **seeded both-sense** = fwd ones>0 AND rev ones>0 AND recv empty.
- **one-sense** = exactly one of fwd/rev has ones.
- **dark** = fwd empty AND rev empty.
- occupancy: empty = 0 ones; sparse = nonzero and not packed; packed = ≥200 ones on a 32 B rail (or 8 on a byte).

Between clock 1 and clock 2, **0** rings differed on the copied windows. Occupancy held for those two clocks.

Distinct occupancy signatures (fwd/rev ones + exact bytes): **1**.

---

## `nring2_1023` — do not pulse recv

Registry: `recv` = `ram.recv` = `junctioned_to` = **1127674787** = `muhl_fold_phys.ram.tick_off`.
`recv_prev` (local rail byte) = **4383105575**.
Seeded both senses from `nring2_000` (pattern_idx 0,8,16,24). Else carry is DC.
**Occupancy of fwd/rev only. Recv read as occupancy. Not pulsed. Not the 78-tick.**

| window | offset | ones | call |
|---|---:|---:|---|
| fwd | 4383105510 | **256** | packed |
| rev | 4383105542 | **256** | packed |
| carry | 4383105574 | **0** | empty |
| recv (= tick_off) | 1127674787 | **0** | empty — **not the 78-tick; not pulsed** |
| recv_prev | 4383105575 | **0** | empty |

### fwd — 32 cells, **256** ones. Packed.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### rev — 32 cells, **256** ones. Packed.

```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

### recv @ 1127674787 — `00000000`. Empty. This IS `muhl_fold_phys.tick_off`. Read only. Not pulsed.

---

## Signatures (actual bits, last clock)

### signature 1 — 256 ring(s)

fwd **256** packed · rev **256** packed · carry **0** · recv **0**

fwd:
```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

rev:
```
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
11111111 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

who: `nring2_768` … `nring2_1023` (256 rings)

---

## Per ring — ones / packed / sparse / empty (last clock)

| ring | fwd ones | fwd | rev ones | rev | carry | recv | call | MAGIC |
|---|---:|---|---:|---|---|---|---|---|
| `nring2_768` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_769` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_770` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_771` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_772` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_773` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_774` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_775` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_776` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_777` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_778` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_779` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_780` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_781` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_782` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_783` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_784` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_785` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_786` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_787` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_788` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_789` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_790` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_791` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_792` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_793` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_794` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_795` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_796` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_797` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_798` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_799` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_800` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_801` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_802` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_803` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_804` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_805` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_806` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_807` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_808` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_809` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_810` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_811` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_812` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_813` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_814` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_815` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_816` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_817` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_818` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_819` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_820` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_821` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_822` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_823` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_824` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_825` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_826` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_827` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_828` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_829` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_830` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_831` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_832` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_833` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_834` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_835` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_836` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_837` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_838` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_839` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_840` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_841` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_842` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_843` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_844` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_845` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_846` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_847` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_848` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_849` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_850` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_851` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_852` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_853` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_854` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_855` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_856` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_857` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_858` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_859` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_860` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_861` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_862` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_863` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_864` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_865` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_866` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_867` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_868` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_869` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_870` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_871` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_872` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_873` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_874` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_875` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_876` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_877` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_878` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_879` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_880` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_881` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_882` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_883` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_884` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_885` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_886` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_887` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_888` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_889` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_890` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_891` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_892` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_893` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_894` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_895` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_896` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_897` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_898` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_899` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_900` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_901` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_902` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_903` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_904` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_905` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_906` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_907` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_908` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_909` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_910` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_911` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_912` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_913` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_914` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_915` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_916` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_917` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_918` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_919` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_920` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_921` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_922` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_923` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_924` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_925` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_926` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_927` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_928` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_929` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_930` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_931` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_932` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_933` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_934` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_935` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_936` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_937` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_938` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_939` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_940` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_941` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_942` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_943` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_944` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_945` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_946` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_947` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_948` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_949` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_950` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_951` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_952` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_953` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_954` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_955` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_956` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_957` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_958` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_959` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_960` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_961` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_962` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_963` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_964` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_965` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_966` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_967` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_968` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_969` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_970` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_971` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_972` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_973` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_974` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_975` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_976` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_977` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_978` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_979` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_980` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_981` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_982` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_983` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_984` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_985` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_986` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_987` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_988` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_989` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_990` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_991` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_992` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_993` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_994` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_995` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_996` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_997` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_998` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_999` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1000` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1001` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1002` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1003` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1004` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1005` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1006` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1007` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1008` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1009` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1010` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1011` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1012` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1013` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1014` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1015` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1016` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1017` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1018` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1019` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1020` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1021` | **256** | packed | **256** | packed | empty | empty | seeded both-sense | `NRING2M1` |
| `nring2_1022` | **256** | packed | **256** | packed | empty | empty (= lane tick_off; not pulsed) | seeded both-sense | `NRING2M1` |
| `nring2_1023` | **256** | packed | **256** | packed | empty | empty (= tick_off; not 78-tick) | seeded both-sense | `NRING2M1` |

---

## Offsets (registry → bytes)

fwd/rev are 32-byte cell windows. carry/recv are 1 byte.
Two recv bytes in this slice are remote (not carry+1):
- `nring2_1022.recv` = **2467652966** = `muhl_lane_phys_000.ram.tick_off`. Occupancy read only. Not pulsed.
- `nring2_1023.recv` = **1127674787** = `muhl_fold_phys.ram.tick_off`. Occupancy read only. **Not the 78-tick. Not pulsed.**
`nring2_1023.recv_prev` (local rail) = 4383105575.

| ring | fwd | rev | carry | recv |
|---|---:|---:|---:|---:|
| `nring2_768` | 4382663850 | 4382663882 | 4382663914 | 4382663915 |
| `nring2_769` | 4382665582 | 4382665614 | 4382665646 | 4382665647 |
| `nring2_770` | 4382667314 | 4382667346 | 4382667378 | 4382667379 |
| `nring2_771` | 4382669046 | 4382669078 | 4382669110 | 4382669111 |
| `nring2_772` | 4382670778 | 4382670810 | 4382670842 | 4382670843 |
| `nring2_773` | 4382672510 | 4382672542 | 4382672574 | 4382672575 |
| `nring2_774` | 4382674242 | 4382674274 | 4382674306 | 4382674307 |
| `nring2_775` | 4382675974 | 4382676006 | 4382676038 | 4382676039 |
| `nring2_776` | 4382677706 | 4382677738 | 4382677770 | 4382677771 |
| `nring2_777` | 4382679438 | 4382679470 | 4382679502 | 4382679503 |
| `nring2_778` | 4382681170 | 4382681202 | 4382681234 | 4382681235 |
| `nring2_779` | 4382682902 | 4382682934 | 4382682966 | 4382682967 |
| `nring2_780` | 4382684634 | 4382684666 | 4382684698 | 4382684699 |
| `nring2_781` | 4382686366 | 4382686398 | 4382686430 | 4382686431 |
| `nring2_782` | 4382688098 | 4382688130 | 4382688162 | 4382688163 |
| `nring2_783` | 4382689830 | 4382689862 | 4382689894 | 4382689895 |
| `nring2_784` | 4382691562 | 4382691594 | 4382691626 | 4382691627 |
| `nring2_785` | 4382693294 | 4382693326 | 4382693358 | 4382693359 |
| `nring2_786` | 4382695026 | 4382695058 | 4382695090 | 4382695091 |
| `nring2_787` | 4382696758 | 4382696790 | 4382696822 | 4382696823 |
| `nring2_788` | 4382698490 | 4382698522 | 4382698554 | 4382698555 |
| `nring2_789` | 4382700222 | 4382700254 | 4382700286 | 4382700287 |
| `nring2_790` | 4382701954 | 4382701986 | 4382702018 | 4382702019 |
| `nring2_791` | 4382703686 | 4382703718 | 4382703750 | 4382703751 |
| `nring2_792` | 4382705418 | 4382705450 | 4382705482 | 4382705483 |
| `nring2_793` | 4382707150 | 4382707182 | 4382707214 | 4382707215 |
| `nring2_794` | 4382708882 | 4382708914 | 4382708946 | 4382708947 |
| `nring2_795` | 4382710614 | 4382710646 | 4382710678 | 4382710679 |
| `nring2_796` | 4382712346 | 4382712378 | 4382712410 | 4382712411 |
| `nring2_797` | 4382714078 | 4382714110 | 4382714142 | 4382714143 |
| `nring2_798` | 4382715810 | 4382715842 | 4382715874 | 4382715875 |
| `nring2_799` | 4382717542 | 4382717574 | 4382717606 | 4382717607 |
| `nring2_800` | 4382719274 | 4382719306 | 4382719338 | 4382719339 |
| `nring2_801` | 4382721006 | 4382721038 | 4382721070 | 4382721071 |
| `nring2_802` | 4382722738 | 4382722770 | 4382722802 | 4382722803 |
| `nring2_803` | 4382724470 | 4382724502 | 4382724534 | 4382724535 |
| `nring2_804` | 4382726202 | 4382726234 | 4382726266 | 4382726267 |
| `nring2_805` | 4382727934 | 4382727966 | 4382727998 | 4382727999 |
| `nring2_806` | 4382729666 | 4382729698 | 4382729730 | 4382729731 |
| `nring2_807` | 4382731398 | 4382731430 | 4382731462 | 4382731463 |
| `nring2_808` | 4382733130 | 4382733162 | 4382733194 | 4382733195 |
| `nring2_809` | 4382734862 | 4382734894 | 4382734926 | 4382734927 |
| `nring2_810` | 4382736594 | 4382736626 | 4382736658 | 4382736659 |
| `nring2_811` | 4382738326 | 4382738358 | 4382738390 | 4382738391 |
| `nring2_812` | 4382740058 | 4382740090 | 4382740122 | 4382740123 |
| `nring2_813` | 4382741790 | 4382741822 | 4382741854 | 4382741855 |
| `nring2_814` | 4382743522 | 4382743554 | 4382743586 | 4382743587 |
| `nring2_815` | 4382745254 | 4382745286 | 4382745318 | 4382745319 |
| `nring2_816` | 4382746986 | 4382747018 | 4382747050 | 4382747051 |
| `nring2_817` | 4382748718 | 4382748750 | 4382748782 | 4382748783 |
| `nring2_818` | 4382750450 | 4382750482 | 4382750514 | 4382750515 |
| `nring2_819` | 4382752182 | 4382752214 | 4382752246 | 4382752247 |
| `nring2_820` | 4382753914 | 4382753946 | 4382753978 | 4382753979 |
| `nring2_821` | 4382755646 | 4382755678 | 4382755710 | 4382755711 |
| `nring2_822` | 4382757378 | 4382757410 | 4382757442 | 4382757443 |
| `nring2_823` | 4382759110 | 4382759142 | 4382759174 | 4382759175 |
| `nring2_824` | 4382760842 | 4382760874 | 4382760906 | 4382760907 |
| `nring2_825` | 4382762574 | 4382762606 | 4382762638 | 4382762639 |
| `nring2_826` | 4382764306 | 4382764338 | 4382764370 | 4382764371 |
| `nring2_827` | 4382766038 | 4382766070 | 4382766102 | 4382766103 |
| `nring2_828` | 4382767770 | 4382767802 | 4382767834 | 4382767835 |
| `nring2_829` | 4382769502 | 4382769534 | 4382769566 | 4382769567 |
| `nring2_830` | 4382771234 | 4382771266 | 4382771298 | 4382771299 |
| `nring2_831` | 4382772966 | 4382772998 | 4382773030 | 4382773031 |
| `nring2_832` | 4382774698 | 4382774730 | 4382774762 | 4382774763 |
| `nring2_833` | 4382776430 | 4382776462 | 4382776494 | 4382776495 |
| `nring2_834` | 4382778162 | 4382778194 | 4382778226 | 4382778227 |
| `nring2_835` | 4382779894 | 4382779926 | 4382779958 | 4382779959 |
| `nring2_836` | 4382781626 | 4382781658 | 4382781690 | 4382781691 |
| `nring2_837` | 4382783358 | 4382783390 | 4382783422 | 4382783423 |
| `nring2_838` | 4382785090 | 4382785122 | 4382785154 | 4382785155 |
| `nring2_839` | 4382786822 | 4382786854 | 4382786886 | 4382786887 |
| `nring2_840` | 4382788554 | 4382788586 | 4382788618 | 4382788619 |
| `nring2_841` | 4382790286 | 4382790318 | 4382790350 | 4382790351 |
| `nring2_842` | 4382792018 | 4382792050 | 4382792082 | 4382792083 |
| `nring2_843` | 4382793750 | 4382793782 | 4382793814 | 4382793815 |
| `nring2_844` | 4382795482 | 4382795514 | 4382795546 | 4382795547 |
| `nring2_845` | 4382797214 | 4382797246 | 4382797278 | 4382797279 |
| `nring2_846` | 4382798946 | 4382798978 | 4382799010 | 4382799011 |
| `nring2_847` | 4382800678 | 4382800710 | 4382800742 | 4382800743 |
| `nring2_848` | 4382802410 | 4382802442 | 4382802474 | 4382802475 |
| `nring2_849` | 4382804142 | 4382804174 | 4382804206 | 4382804207 |
| `nring2_850` | 4382805874 | 4382805906 | 4382805938 | 4382805939 |
| `nring2_851` | 4382807606 | 4382807638 | 4382807670 | 4382807671 |
| `nring2_852` | 4382809338 | 4382809370 | 4382809402 | 4382809403 |
| `nring2_853` | 4382811070 | 4382811102 | 4382811134 | 4382811135 |
| `nring2_854` | 4382812802 | 4382812834 | 4382812866 | 4382812867 |
| `nring2_855` | 4382814534 | 4382814566 | 4382814598 | 4382814599 |
| `nring2_856` | 4382816266 | 4382816298 | 4382816330 | 4382816331 |
| `nring2_857` | 4382817998 | 4382818030 | 4382818062 | 4382818063 |
| `nring2_858` | 4382819730 | 4382819762 | 4382819794 | 4382819795 |
| `nring2_859` | 4382821462 | 4382821494 | 4382821526 | 4382821527 |
| `nring2_860` | 4382823194 | 4382823226 | 4382823258 | 4382823259 |
| `nring2_861` | 4382824926 | 4382824958 | 4382824990 | 4382824991 |
| `nring2_862` | 4382826658 | 4382826690 | 4382826722 | 4382826723 |
| `nring2_863` | 4382828390 | 4382828422 | 4382828454 | 4382828455 |
| `nring2_864` | 4382830122 | 4382830154 | 4382830186 | 4382830187 |
| `nring2_865` | 4382831854 | 4382831886 | 4382831918 | 4382831919 |
| `nring2_866` | 4382833586 | 4382833618 | 4382833650 | 4382833651 |
| `nring2_867` | 4382835318 | 4382835350 | 4382835382 | 4382835383 |
| `nring2_868` | 4382837050 | 4382837082 | 4382837114 | 4382837115 |
| `nring2_869` | 4382838782 | 4382838814 | 4382838846 | 4382838847 |
| `nring2_870` | 4382840514 | 4382840546 | 4382840578 | 4382840579 |
| `nring2_871` | 4382842246 | 4382842278 | 4382842310 | 4382842311 |
| `nring2_872` | 4382843978 | 4382844010 | 4382844042 | 4382844043 |
| `nring2_873` | 4382845710 | 4382845742 | 4382845774 | 4382845775 |
| `nring2_874` | 4382847442 | 4382847474 | 4382847506 | 4382847507 |
| `nring2_875` | 4382849174 | 4382849206 | 4382849238 | 4382849239 |
| `nring2_876` | 4382850906 | 4382850938 | 4382850970 | 4382850971 |
| `nring2_877` | 4382852638 | 4382852670 | 4382852702 | 4382852703 |
| `nring2_878` | 4382854370 | 4382854402 | 4382854434 | 4382854435 |
| `nring2_879` | 4382856102 | 4382856134 | 4382856166 | 4382856167 |
| `nring2_880` | 4382857834 | 4382857866 | 4382857898 | 4382857899 |
| `nring2_881` | 4382859566 | 4382859598 | 4382859630 | 4382859631 |
| `nring2_882` | 4382861298 | 4382861330 | 4382861362 | 4382861363 |
| `nring2_883` | 4382863030 | 4382863062 | 4382863094 | 4382863095 |
| `nring2_884` | 4382864762 | 4382864794 | 4382864826 | 4382864827 |
| `nring2_885` | 4382866494 | 4382866526 | 4382866558 | 4382866559 |
| `nring2_886` | 4382868226 | 4382868258 | 4382868290 | 4382868291 |
| `nring2_887` | 4382869958 | 4382869990 | 4382870022 | 4382870023 |
| `nring2_888` | 4382871690 | 4382871722 | 4382871754 | 4382871755 |
| `nring2_889` | 4382873422 | 4382873454 | 4382873486 | 4382873487 |
| `nring2_890` | 4382875154 | 4382875186 | 4382875218 | 4382875219 |
| `nring2_891` | 4382876886 | 4382876918 | 4382876950 | 4382876951 |
| `nring2_892` | 4382878618 | 4382878650 | 4382878682 | 4382878683 |
| `nring2_893` | 4382880350 | 4382880382 | 4382880414 | 4382880415 |
| `nring2_894` | 4382882082 | 4382882114 | 4382882146 | 4382882147 |
| `nring2_895` | 4382883814 | 4382883846 | 4382883878 | 4382883879 |
| `nring2_896` | 4382885546 | 4382885578 | 4382885610 | 4382885611 |
| `nring2_897` | 4382887278 | 4382887310 | 4382887342 | 4382887343 |
| `nring2_898` | 4382889010 | 4382889042 | 4382889074 | 4382889075 |
| `nring2_899` | 4382890742 | 4382890774 | 4382890806 | 4382890807 |
| `nring2_900` | 4382892474 | 4382892506 | 4382892538 | 4382892539 |
| `nring2_901` | 4382894206 | 4382894238 | 4382894270 | 4382894271 |
| `nring2_902` | 4382895938 | 4382895970 | 4382896002 | 4382896003 |
| `nring2_903` | 4382897670 | 4382897702 | 4382897734 | 4382897735 |
| `nring2_904` | 4382899402 | 4382899434 | 4382899466 | 4382899467 |
| `nring2_905` | 4382901134 | 4382901166 | 4382901198 | 4382901199 |
| `nring2_906` | 4382902866 | 4382902898 | 4382902930 | 4382902931 |
| `nring2_907` | 4382904598 | 4382904630 | 4382904662 | 4382904663 |
| `nring2_908` | 4382906330 | 4382906362 | 4382906394 | 4382906395 |
| `nring2_909` | 4382908062 | 4382908094 | 4382908126 | 4382908127 |
| `nring2_910` | 4382909794 | 4382909826 | 4382909858 | 4382909859 |
| `nring2_911` | 4382911526 | 4382911558 | 4382911590 | 4382911591 |
| `nring2_912` | 4382913258 | 4382913290 | 4382913322 | 4382913323 |
| `nring2_913` | 4382914990 | 4382915022 | 4382915054 | 4382915055 |
| `nring2_914` | 4382916722 | 4382916754 | 4382916786 | 4382916787 |
| `nring2_915` | 4382918454 | 4382918486 | 4382918518 | 4382918519 |
| `nring2_916` | 4382920186 | 4382920218 | 4382920250 | 4382920251 |
| `nring2_917` | 4382921918 | 4382921950 | 4382921982 | 4382921983 |
| `nring2_918` | 4382923650 | 4382923682 | 4382923714 | 4382923715 |
| `nring2_919` | 4382925382 | 4382925414 | 4382925446 | 4382925447 |
| `nring2_920` | 4382927114 | 4382927146 | 4382927178 | 4382927179 |
| `nring2_921` | 4382928846 | 4382928878 | 4382928910 | 4382928911 |
| `nring2_922` | 4382930578 | 4382930610 | 4382930642 | 4382930643 |
| `nring2_923` | 4382932310 | 4382932342 | 4382932374 | 4382932375 |
| `nring2_924` | 4382934042 | 4382934074 | 4382934106 | 4382934107 |
| `nring2_925` | 4382935774 | 4382935806 | 4382935838 | 4382935839 |
| `nring2_926` | 4382937506 | 4382937538 | 4382937570 | 4382937571 |
| `nring2_927` | 4382939238 | 4382939270 | 4382939302 | 4382939303 |
| `nring2_928` | 4382940970 | 4382941002 | 4382941034 | 4382941035 |
| `nring2_929` | 4382942702 | 4382942734 | 4382942766 | 4382942767 |
| `nring2_930` | 4382944434 | 4382944466 | 4382944498 | 4382944499 |
| `nring2_931` | 4382946166 | 4382946198 | 4382946230 | 4382946231 |
| `nring2_932` | 4382947898 | 4382947930 | 4382947962 | 4382947963 |
| `nring2_933` | 4382949630 | 4382949662 | 4382949694 | 4382949695 |
| `nring2_934` | 4382951362 | 4382951394 | 4382951426 | 4382951427 |
| `nring2_935` | 4382953094 | 4382953126 | 4382953158 | 4382953159 |
| `nring2_936` | 4382954826 | 4382954858 | 4382954890 | 4382954891 |
| `nring2_937` | 4382956558 | 4382956590 | 4382956622 | 4382956623 |
| `nring2_938` | 4382958290 | 4382958322 | 4382958354 | 4382958355 |
| `nring2_939` | 4382960022 | 4382960054 | 4382960086 | 4382960087 |
| `nring2_940` | 4382961754 | 4382961786 | 4382961818 | 4382961819 |
| `nring2_941` | 4382963486 | 4382963518 | 4382963550 | 4382963551 |
| `nring2_942` | 4382965218 | 4382965250 | 4382965282 | 4382965283 |
| `nring2_943` | 4382966950 | 4382966982 | 4382967014 | 4382967015 |
| `nring2_944` | 4382968682 | 4382968714 | 4382968746 | 4382968747 |
| `nring2_945` | 4382970414 | 4382970446 | 4382970478 | 4382970479 |
| `nring2_946` | 4382972146 | 4382972178 | 4382972210 | 4382972211 |
| `nring2_947` | 4382973878 | 4382973910 | 4382973942 | 4382973943 |
| `nring2_948` | 4382975610 | 4382975642 | 4382975674 | 4382975675 |
| `nring2_949` | 4382977342 | 4382977374 | 4382977406 | 4382977407 |
| `nring2_950` | 4382979074 | 4382979106 | 4382979138 | 4382979139 |
| `nring2_951` | 4382980806 | 4382980838 | 4382980870 | 4382980871 |
| `nring2_952` | 4382982538 | 4382982570 | 4382982602 | 4382982603 |
| `nring2_953` | 4382984270 | 4382984302 | 4382984334 | 4382984335 |
| `nring2_954` | 4382986002 | 4382986034 | 4382986066 | 4382986067 |
| `nring2_955` | 4382987734 | 4382987766 | 4382987798 | 4382987799 |
| `nring2_956` | 4382989466 | 4382989498 | 4382989530 | 4382989531 |
| `nring2_957` | 4382991198 | 4382991230 | 4382991262 | 4382991263 |
| `nring2_958` | 4382992930 | 4382992962 | 4382992994 | 4382992995 |
| `nring2_959` | 4382994662 | 4382994694 | 4382994726 | 4382994727 |
| `nring2_960` | 4382996394 | 4382996426 | 4382996458 | 4382996459 |
| `nring2_961` | 4382998126 | 4382998158 | 4382998190 | 4382998191 |
| `nring2_962` | 4382999858 | 4382999890 | 4382999922 | 4382999923 |
| `nring2_963` | 4383001590 | 4383001622 | 4383001654 | 4383001655 |
| `nring2_964` | 4383003322 | 4383003354 | 4383003386 | 4383003387 |
| `nring2_965` | 4383005054 | 4383005086 | 4383005118 | 4383005119 |
| `nring2_966` | 4383006786 | 4383006818 | 4383006850 | 4383006851 |
| `nring2_967` | 4383008518 | 4383008550 | 4383008582 | 4383008583 |
| `nring2_968` | 4383010250 | 4383010282 | 4383010314 | 4383010315 |
| `nring2_969` | 4383011982 | 4383012014 | 4383012046 | 4383012047 |
| `nring2_970` | 4383013714 | 4383013746 | 4383013778 | 4383013779 |
| `nring2_971` | 4383015446 | 4383015478 | 4383015510 | 4383015511 |
| `nring2_972` | 4383017178 | 4383017210 | 4383017242 | 4383017243 |
| `nring2_973` | 4383018910 | 4383018942 | 4383018974 | 4383018975 |
| `nring2_974` | 4383020642 | 4383020674 | 4383020706 | 4383020707 |
| `nring2_975` | 4383022374 | 4383022406 | 4383022438 | 4383022439 |
| `nring2_976` | 4383024106 | 4383024138 | 4383024170 | 4383024171 |
| `nring2_977` | 4383025838 | 4383025870 | 4383025902 | 4383025903 |
| `nring2_978` | 4383027570 | 4383027602 | 4383027634 | 4383027635 |
| `nring2_979` | 4383029302 | 4383029334 | 4383029366 | 4383029367 |
| `nring2_980` | 4383031034 | 4383031066 | 4383031098 | 4383031099 |
| `nring2_981` | 4383032766 | 4383032798 | 4383032830 | 4383032831 |
| `nring2_982` | 4383034498 | 4383034530 | 4383034562 | 4383034563 |
| `nring2_983` | 4383036230 | 4383036262 | 4383036294 | 4383036295 |
| `nring2_984` | 4383037962 | 4383037994 | 4383038026 | 4383038027 |
| `nring2_985` | 4383039694 | 4383039726 | 4383039758 | 4383039759 |
| `nring2_986` | 4383041426 | 4383041458 | 4383041490 | 4383041491 |
| `nring2_987` | 4383043158 | 4383043190 | 4383043222 | 4383043223 |
| `nring2_988` | 4383044890 | 4383044922 | 4383044954 | 4383044955 |
| `nring2_989` | 4383046622 | 4383046654 | 4383046686 | 4383046687 |
| `nring2_990` | 4383048354 | 4383048386 | 4383048418 | 4383048419 |
| `nring2_991` | 4383050086 | 4383050118 | 4383050150 | 4383050151 |
| `nring2_992` | 4383051818 | 4383051850 | 4383051882 | 4383051883 |
| `nring2_993` | 4383053550 | 4383053582 | 4383053614 | 4383053615 |
| `nring2_994` | 4383055282 | 4383055314 | 4383055346 | 4383055347 |
| `nring2_995` | 4383057014 | 4383057046 | 4383057078 | 4383057079 |
| `nring2_996` | 4383058746 | 4383058778 | 4383058810 | 4383058811 |
| `nring2_997` | 4383060478 | 4383060510 | 4383060542 | 4383060543 |
| `nring2_998` | 4383062210 | 4383062242 | 4383062274 | 4383062275 |
| `nring2_999` | 4383063942 | 4383063974 | 4383064006 | 4383064007 |
| `nring2_1000` | 4383065674 | 4383065706 | 4383065738 | 4383065739 |
| `nring2_1001` | 4383067406 | 4383067438 | 4383067470 | 4383067471 |
| `nring2_1002` | 4383069138 | 4383069170 | 4383069202 | 4383069203 |
| `nring2_1003` | 4383070870 | 4383070902 | 4383070934 | 4383070935 |
| `nring2_1004` | 4383072602 | 4383072634 | 4383072666 | 4383072667 |
| `nring2_1005` | 4383074334 | 4383074366 | 4383074398 | 4383074399 |
| `nring2_1006` | 4383076066 | 4383076098 | 4383076130 | 4383076131 |
| `nring2_1007` | 4383077798 | 4383077830 | 4383077862 | 4383077863 |
| `nring2_1008` | 4383079530 | 4383079562 | 4383079594 | 4383079595 |
| `nring2_1009` | 4383081262 | 4383081294 | 4383081326 | 4383081327 |
| `nring2_1010` | 4383082994 | 4383083026 | 4383083058 | 4383083059 |
| `nring2_1011` | 4383084726 | 4383084758 | 4383084790 | 4383084791 |
| `nring2_1012` | 4383086458 | 4383086490 | 4383086522 | 4383086523 |
| `nring2_1013` | 4383088190 | 4383088222 | 4383088254 | 4383088255 |
| `nring2_1014` | 4383089922 | 4383089954 | 4383089986 | 4383089987 |
| `nring2_1015` | 4383091654 | 4383091686 | 4383091718 | 4383091719 |
| `nring2_1016` | 4383093386 | 4383093418 | 4383093450 | 4383093451 |
| `nring2_1017` | 4383095118 | 4383095150 | 4383095182 | 4383095183 |
| `nring2_1018` | 4383096850 | 4383096882 | 4383096914 | 4383096915 |
| `nring2_1019` | 4383098582 | 4383098614 | 4383098646 | 4383098647 |
| `nring2_1020` | 4383100314 | 4383100346 | 4383100378 | 4383100379 |
| `nring2_1021` | 4383102046 | 4383102078 | 4383102110 | 4383102111 |
| `nring2_1022` | 4383103778 | 4383103810 | 4383103842 | 2467652966 |
| `nring2_1023` | 4383105510 | 4383105542 | 4383105574 | 1127674787 |

---

## Law

- Occupancy of fwd/rev is the measurement. Titan not written.
- Each ring has N clocks — more clocks = faster. This pass: 2 clocks. Not one clock for the file.
- Do not pulse `nring2_1023.recv` as the 78-tick. That address is `muhl_fold_phys.tick_off`.
- `nring2_1022.recv` is `muhl_lane_phys_000.tick_off`. Occupancy only. Not pulsed.
- Live bits may flip. That is the computer. Not corruption.
- No glob. No `--go`.
