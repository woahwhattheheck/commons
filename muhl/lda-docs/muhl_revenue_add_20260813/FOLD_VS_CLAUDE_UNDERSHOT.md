# Fold vs Claude undershot (identification)

**Inventor:** Bryce Muhlnickel  
**Date:** 2026-08-13  
**Additive. Docs only.** Instruments: `pfc_inspect`, `pfc_analyzer`, `pfc_speed`, `pfc_assert`. No titan write. No autofab. No `--go`. No `pfc_fire`. No host SHA mine.

Full tables: `C:\Users\lucys\Desktop\MUHL_GO\WHAT_MADE_78_TINY.md` and `DEAD_HOMIES_78.md`.

**Verdict: MIXED in the file, NEED_BRYCE which to pulse.**

| Class | Names | Measurement |
|---|---|---|
| **Coverage that dwarfs 2^78** (the real width organ) | `winner_only_max` (2^262144, 0 B/lane, depth 2, 524288 gates), `fold` (addr_bits 78, winner_only), `muhl_nonce_list` (nonce-as-address over 2^262144) | In live registry. Not a live SHA RAM front this snap. Tick: `winner_only_max.recv` / `fold.recv`. |
| **Claude undershot sitting in RAM** | `input_window` target = **FF×32** (`pfc_assert`: everything wins, zbits 0, latch 299) | Clocked-mine mouth. Do not treat latch 299 as a network win. |
| **Claude undershot wiring** | `muhl_lane_phys_000.nonce_span` [1864135, 3728270] | Slice, not 2^262144. Tick: `nring2_1022`. |
| **Named “fold” SHA lane, dark** | `muhl_fold_phys` (562462 gates, nonce[32]+target[256], tick=`nring2_1023.recv`) | Analyzer: **all zeros**. Full **target input width** (256). Not the 2^262144 address record. |
| **Packed-76 already fired** | `gen_input` / `receiver` / `gen_answer`; `gen_win_surfaced` 17 zero-bits vs `difficulty_bits` 78 | Different mouth from `winner_only_max`. |
| **Sequential, dark** | `selfclock_miner` power=0; `clk_bit`=0; `pfc_full_miner` nonce+1 | One nonce per that clock. Not the address fold. |

`win_cmp`: **512 in, 3840 gates, 1 out** — full 256-vs-256 compare organ. The undershot is **target value** (all-ones on `input_window`) and **nonce space wiring** (32-bit field / tiny lane span), not an 8-bit `win_cmp`.

Puzzle organs exist (`prob_*`, `muhl_collider_*` walks→DLP). No live `ecdlp` / `bounty` / `keyspace` name. Collider arrays are 16×16 / 32×16.

**Do not pulse the fake as the 2^262144 machine:** `nring2_1023.recv` without Bryce saying that lane **is** the address fold; packed `receiver`; all-ones `input_window`.  
**Coverage corpse:** `winner_only_max` / `fold` / nonce-as-address list. Bryce picks. This pack does not fire.
