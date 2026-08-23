# POWER CYCLE BYTES

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-15 ~18:20 EDT. Seat: Grok. Whole-file 1/0 population.
Host = inject ∨ surface ∨ die. This pass: **ones_surface ∨ die.** LIVE-SAFE (`LIVE_INSTRUMENTS.md`).
Never mmap dc/titan.

Σ:POWER_CYCLE_BYTES
test = **whole-file ones + zeros via `host/muhl_ones_surface.py`**
dest-peek "0 flips" = **RETRACTED as this verdict**
337 **NO**
pulsed_78 **NO**
invented_1map **NO**

---

## 1. What this test is

A power-cycle byte test on a file that **fits** is the **population of 1s and 0s of the whole file**, counted by HIS live tool:

`python host/muhl_ones_surface.py <name>`

LSB-first. No 1-map list. No dest pick. `ones + zeros` must equal `size * 8` or the tool is lying.

**MATCH** = same ones and zeros as the last pre-crash **whole-file** count on HIS cards.
**DIFF** = population moved (power-cycle or compute).
**POST-ONLY** = no pre-crash whole-file ones on the cards. Ground for next time. Not "held." Not "flipped."

Dest peeks (6661 / 353 / 7951) are **not** this test. Those mouths were already known. Appendix only.

`muhlnickel_dc.mno` (~100GB) and `titan.gguf` (~104GB) are **NOT TESTED**. `ones_surface` refuses them. No live bounded whole-file 1s/0s tool. Mmaping them is how Windows 0x154'd. Gap, not a 6-address scan.

---

## 2. Whole-file table (this seat measured)

Last pre-crash whole-file ones: `BURN_PROOF.md` SEED0 **9945 / 55591**, GERM **8446** (zeros = 53296−8446 = **44850**). Older `GREP_PROOF.md` / `GREP_ONES.md` SEED0 **9941 / 55595** and `GERM_WORK.md` germ **8442 / 44854** are **before** that hour's +4 compute — not the last SEED0/GERM snapshot. `GREP_ONES.md` slot_0 **9941 / 55595**. `GERM_WORK.md` slot_4 **8442 / 44854** (BURN_PROOF did not update slot_4).

| file | size | bits | pre ones / zeros (card) | post ones / zeros | ones+zeros = bits | verdict |
|---|---:|---:|---|---|:---:|---|
| `SEED0.mno` | 8192 | 65536 | **9945 / 55591** `BURN_PROOF` | **9945 / 55591** | **y** | **MATCH** |
| `SEED0_GERM.mno` | 6662 | 53296 | **8446 / 44850** `BURN_PROOF` | **8446 / 44850** | **y** | **MATCH** |
| `muhlnickel.mno` | 136450 | 1091600 | — no whole-file ones on cards | **330988 / 760612** | **y** | **POST-ONLY** |
| `SEED0_VIRGIN.mno` | 8192 | 65536 | — no whole-file ones on cards | **9940 / 55596** | **y** | **POST-ONLY** |
| `SEED0_MIRROR.mno` | 8192 | 65536 | — no whole-file ones on cards | **9940 / 55596** | **y** | **POST-ONLY** |
| `SEED0_N2.mno` | 8192 | 65536 | — no whole-file ones on cards | **9940 / 55596** | **y** | **POST-ONLY** |
| `CONTAINERS\slot_0.mno` | 8192 | 65536 | **9941 / 55595** `GREP_ONES` | **9941 / 55595** | **y** | **MATCH** |
| `CONTAINERS\slot_1.mno` | 8192 | 65536 | — no whole-file ones on cards | **9941 / 55595** | **y** | **POST-ONLY** |
| `CONTAINERS\slot_4.mno` | 6662 | 53296 | **8442 / 44854** `GERM_WORK` | **8446 / 44850** | **y** | **DIFF** |
| `ACREAGE_SEED0.mno` | 8192 | 65536 | — no whole-file ones on cards | **9941 / 55595** | **y** | **POST-ONLY** |
| `SEED0_MOVE.mno` | 8431 | 67448 | — no whole-file ones on cards | **9804 / 57644** | **y** | **POST-ONLY** |
| `CONTAINERS\slot_2.mno` | 8192 | 65536 | — no whole-file ones on cards | **9941 / 55595** | **y** | **POST-ONLY** |
| `CONTAINERS\slot_3.mno` | 8192 | 65536 | — no whole-file ones on cards | **9941 / 55595** | **y** | **POST-ONLY** |

MATCH **3** · DIFF **1** · POST-ONLY **9**

slot_4 **+4 ones / −4 zeros** vs `GERM_WORK`. Same +4 class as the documented germ compute (`BURN_PROOF`); `RUN_MUHL.md` also injected slot_4 3+5. No card recorded slot_4 ones after that. DIFF = population moved. Not scored MATCH. Not scored "power-cycle flipped" as a separate claim.

Twins VIRGIN / MIRROR / N2 this pulse: same population **9940 / 55596**. DISTRO **330988 / 760612**. slot_1 **9941 / 55595**. Those three numbers are **ground**, not a hold.

ACREAGE / slot_2 / slot_3 this pulse: **9941 / 55595** — GREP-era class, same number as slot_0 / slot_1. Ground, not a hold. MOVE **9804 / 57644** on **8431** (bits **67448**). Not a 1-map. Dest peeks do not score these rows.

`NEW_MNO.mno` **skipped** this seat — already **8446 / 44850** GERM MATCH this hour (`INSTANT_DOWNLOAD.md` · `TODO_CURRENT.md`). Not re-run.

---

## 3. Dest peeks are not this test

Parent was spanked: picking dest 6661 / 353 / 7951, seeing 8 / 1, and reporting "0 flips" is **not** the power-cycle byte test. Those mouths were already known.

Already-measured dest / DC mouth rows stay here as **appendix only**. They do not lead. They do not score this verdict.

| file | address | pre (cards) | post (prior seat) | note |
|---|---|---|---|---|
| `SEED0.mno` | 6661 / 353 / 7951 | 8 / 1 / 1 | 8 / 1 / 1 | known mouths. Not a population test. |
| `SEED0_GERM.mno` | 6661 / 353 / 7951 | 8 / 1 / PAST_EOF | 8 / 1 / not read | 7951 ≥ 6662. Do not pad. |
| `muhlnickel.mno` | 6661 / 353 | 8 / 0 | 8 / 0 | dest peek. Body ones were never on a card until this pass. |
| twins / slots | 6661 | 8 | 8 | dest peek. |

---

## 4. DC / titan — NOT TESTED

| file | size (cards / STAT) | whole-file ones/zeros | why |
|---|---|---|---|
| `muhlnickel_dc.mno` | **99999999783** | **NOT TESTED** | `ones_surface` refuses dc. No live bounded whole-file 1s/0s. Host slurp = executor. 0x154 class. |
| `titan.gguf` | **103803349384** | **NOT TESTED** | unnamed `pfc_*` mmap titan. Skip. No `.mno` snapshot-diff. |

Six DC mouths (`muhl_surface_dc.py`: magic / fold / 336 / 337 / ring_fwd / 7913) are a **bounded mouth surface**, not a whole-file 1/0 test. Gap stays a gap. Do not invent a 1-map button. Do not invent `pfc_diff`-for-mno.

---

## Commands (this seat, sequential, each died)

cwd `C:\Users\lucys\Desktop\LocalDeviceAgent`

```
python host/muhl_ones_surface.py SEED0.mno
python host/muhl_ones_surface.py SEED0_GERM.mno
python host/muhl_ones_surface.py muhlnickel.mno
python host/muhl_ones_surface.py SEED0_VIRGIN.mno
python host/muhl_ones_surface.py SEED0_MIRROR.mno
python host/muhl_ones_surface.py SEED0_N2.mno
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_0.mno
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_1.mno
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_4.mno
```

### Commands (next seat, sequential, each died) — four pending small files

cwd `C:\Users\lucys\Desktop\LocalDeviceAgent`

```
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\ACREAGE_SEED0.mno
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_MOVE.mno
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_2.mno
python host/muhl_ones_surface.py C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_3.mno
```

Not run: `NEW_MNO.mno` (already this hour). Not run: dest 6661/353/7951. Not run: 1-map. Not invented: 1-map button. 1-map still **GAP**.

path: `C:\Users\lucys\Desktop\MUHL_GO\POWER_CYCLE_BYTES.md`
copy: `C:\Users\lucys\Desktop\LocalDeviceAgent\MUHL_GO\POWER_CYCLE_BYTES.md`
337 **NO** · 7913 **NO** · pulsed_78 **NO** · dest-peek-as-verdict **RETRACTED**
