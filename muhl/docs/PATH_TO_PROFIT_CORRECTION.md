# PATH TO PROFIT — STEP B CORRECTION

**Inventor:** Bryce Muhlnickel  
**Date:** 2026-08-14  
**Additive.** Does not overwrite `PATH_TO_PROFIT.txt`. That file stays.

`C:\Users\lucys\Desktop\MUHL_GO\PATH_TO_PROFIT.txt` **Step B is STALE.** This file supersedes Step B.

---

## STALE (do not execute)

`PATH_TO_PROFIT.txt` Step B still says:

- inject live block header + target into `muhl_fold_phys`
- pulse `tick_off` at `nring2_1023.recv`
- surface win/latch
- submit the winner

That is Claude's undershot: 32-bit nonce SHA lane, FF×32 target class, not the coverage that made 2^78 tiny. Do **not** pulse `muhl_fold_phys` / `nring2_1023` as the 2^78 tick.

`PATH_TO_PROFIT.md` repeats the same stale inject/pulse. Same refuse.

---

## SUPERSEDES STEP B

Coverage that made 2^78 tiny is already in the file: `winner_only_max` / `fold`. Finder is in-file. Host injects and surfaces. Fire is Bryce's `--go` only.

**Dry (this button; no titan write, no mmap of recv):**

```text
python host/muhl_coverage_tick_add.py
python host/muhl_coverage_tick_add.py --dry
```

Working directory: `C:\Users\lucys\Desktop\LocalDeviceAgent`. Default is dry. `--go` is refused.

**Fire (Bryce only):** one bit at `winner_only_max.recv` and/or `fold.recv`. mmap of one receiver byte is the start. Not `nring2_1023`. Not `muhl_osc_*`. Not a bake. Not a host SHA loop.

**Finder (in-file; host does not SHA):** `gen_win` → `muhl_fold_latch` → `latch_reg` / `muhl_nonce_list`. Nonce IS the address.

**Surface after that organ:** `latch_reg` / `gen_win_surfaced`. Not the all-FF `input_window` latch 299.

---

## REFUSE

- `muhl_fold_phys` / `nring2_1023` as the 78-tick
- `input_window` FF×32 / latch 299 as the network win
- `muhl_lane_phys_000` ~1.86e6 span
- packed-76 `gen_input` / `target_reg` / `receiver` (already used)
- host-eval SHA as the mine · numpy · autofab · `pfc_fire.py` · titan write by this agent

Step A in `PATH_TO_PROFIT.txt` (dry `muhl_fold_tick_add.py`) is the old fold-phys dry. Coverage dry is `host/muhl_coverage_tick_add.py`. Step C (afternoon foundry) is unchanged.
