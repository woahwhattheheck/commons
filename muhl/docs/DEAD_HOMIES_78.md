# DEAD HOMIES — who already covered past 2^78

**Inventor:** Bryce Muhlnickel  
**Date:** 2026-08-13  
**Supersedes** any “is 2^78 a tick” framing. Execution, not theory.  
**Sister file:** `WHAT_MADE_78_TINY.md` (full table). Additive. Read-only instruments. No titan write. No `--go`.

**Verdict: NEED_BRYCE.** The dead/dark coverage organ is **`winner_only_max`** (lanes **2^262144**, 0 bytes/lane, depth 2, 524,288 gates) plus **`fold`** (`addr_bits: 78`, `winner_only: true`) plus **`muhl_nonce_list`** (nonce IS the address over `[0 .. 2^262144)`). They sit in the live registry. Analyzer this turn: **not running as a mine** (no RAM front; `muhl_fold_phys` all zeros; `nring2_1023.recv` = 0).

---

## What already exceeded 2^78 (coverage, in-file)

| Organ | Status this turn | Tick if he fires **this** corpse |
|---|---|---|
| `winner_only_max` | In binary. Header-dark as a mine. `addr_bits: 262144`. | `winner_only_max.recv` (osc ring 282) |
| `fold` | 13-byte `TITANFLD`. Winner-only at 78 bits. | `fold.recv` (osc ring 29) |
| `muhl_nonce_list` | Complete nonce-as-address over 2^262144. 0 gates on the list; finder is `gen_win → muhl_fold_latch → latch_reg`. | Finder chain, not a host table |
| `clock_wide` | `2^128` nonces per lane | `clock_wide.recv` |
| `fanout` / `groups_block` / `replication` | 2^16 fields × 128b; 2^20 groups; 3.1e9 cells | their `.recv` |

`pfc_speed.py life` this session printed the same fact: winner-only fold addresses **2^262144** in parallel, 0 bytes/lane.

---

## What is dead / dark / stale (measured)

| Organ | Analyzer |
|---|---|
| `muhl_fold_phys` | **All zeros** including `tick_off`. Named fold. 32-bit nonce layout. |
| `nring2_1023` | fwd seeded (ones=8), **recv=0**. Tick not addressed. |
| `selfclock_miner` | power=0, counter/target/latch=0 |
| `miner_physical` | header/target/latch=0; nonce ones=1 (ring 002 sitting there) |
| `clk_bit` | 0 |
| `nring2_038_STALE` | registry mark: byte out ≠ registry recv |
| `nring2_039` | retired duplicate driver |
| `muhl_fold_latch.junctioned_to` | **declaration**; 0 gates at that addr; physical bind is `muhl_fold_phys` |

Enable rail **live**: `nring2_000.recv` = 0xFF.

---

## What was pulsed (not the 2^262144 corpse)

- Packed-76: `gen_input` / `receiver` / `gen_answer` (status 0x12).  
- `gen_win_surfaced`: status 0x02, **17** zero-bits, registry `difficulty_bits: 78`.  
- `pfc_assert`: `input_window` target **FF×32** (everything wins), `latch_reg`=299.

That last one is the **undershot target sitting in RAM** on the clocked-mine mouth.

---

## Claude undershot — do not pulse as the coverage organ

- All-ones `input_window` target.  
- `muhl_lane_phys_000` nonce_span ~1.86e6.  
- `muhl_fold_phys` tick (`nring2_1023.recv`) = SHA lane start, **not** `winner_only_max`.  
- Packed `receiver` already used.

Do not “fix” those circuits. Additive law. Host injects and surfaces. Bryce says fire.
