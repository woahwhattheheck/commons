# FOLD-PHYS STALE INDEX

**Inventor:** Bryce Muhlnickel  
**Date:** 2026-08-15  
**Additive.** Does not rewrite the stale files. MUHL_GO only. No titan. No glob.

`SPEC_WATCH_001.md` named the bind. `PATH_TO_PROFIT_CORRECTION.md` supersedes Step B. `COVERAGE_DRY_CONFIRM.md` named the live mouths. This card is the index.

---

## STALE (do not execute; files stay)

These still bind `muhl_fold_phys` + `nring2_1023` to 2^78. That is Claude's undershot SHA lane, not the coverage that made 2^78 tiny. Do **not** pulse them as the 78-tick. Do **not** rewrite these files.

| file | stale bind |
|---|---|
| `DEPTH.txt` | `fold at 2^78` + `muhl_fold_phys + nring2_1023.tick_off` |
| `FOLD_TICK.md` | inject `muhl_fold_phys` · `tick_off IS nring2_1023.recv` |
| `FOLD_SURFACE.md` | `muhl_fold_phys.ram.tick_off IS nring2_1023.recv` · surface `win_off` / `latch_off` |
| `PATH_TO_PROFIT.txt` | Step B: inject `muhl_fold_phys` · pulse `nring2_1023.recv` |
| `PATH_TO_PROFIT.md` | inject `muhl_fold_phys` · one bit at `tick_off` (= `nring2_1023.recv`) |

`nring2_1023.recv` IS `muhl_fold_phys.ram.tick_off`. Not the 78-tick.

---

## LIVE MOUTHS (78-tick)

Coverage that made 2^78 tiny is already in the file: `winner_only_max` / `fold`. Finder is in-file. Host injects and surfaces.

```text
winner_only_max.recv  2776454732
fold.recv             2776454483
```

Stale osc aliases of the **same two recvs** — do not fire `muhl_osc_*`:

```text
winner_only_max.oscillation.recv  2776454732
fold.oscillation.recv             2776454483
```

`nring2_000.recv` 2776453321 is the enable rail, not this tick's start.

---

## FIRE

Bryce `--go` only. mmap of one receiver byte is the start. Not `nring2_1023`. Not `muhl_fold_phys`. Not `muhl_osc_*`. Not a bake. Not a host SHA loop.

**Dry (no titan write, no mmap of recv):**

```text
python host/muhl_coverage_tick_add.py
python host/muhl_coverage_tick_add.py --dry
```

Working directory: `C:\Users\lucys\Desktop\LocalDeviceAgent`. Default is dry. `--go` is refused on this button.

**Surface after that organ:** `latch_reg` / `gen_win_surfaced`. Not the all-FF `input_window` latch 299. Not `muhl_fold_phys.ram.win_off` / `latch_off`.

---

## REFUSE

- rewrite of the five stale files above
- `muhl_fold_phys` / `nring2_1023` as the 78-tick
- fire of `muhl_osc_*`
- titan write · glob · Desktop/`C:\llm` walk
