# CIRCUIT_PFC.md — the catalog of every circuit already in the Muhlnickel binary

> **Why this exists (owner 2026-07-21):** *"that logic you're using already exists as a circuit already built… what you're
> using the host for, the Muhlnickel binary can do."* Whenever I reach for the HOST to do something — a loop, a compare, a clock,
> a memory read, a sequence — the answer is almost always **already a fabricated circuit in `titan.gguf`.** Find it here,
> wire it, and let the Muhlnickel do it. **138 circuits/registers** live in the one file. Read this before writing host logic.

---

## ★ THE ANSWER TO "STOP DRIVING THE LOOP ON THE HOST" — the self-sequencing circuits

The read→pulse→latch loop I was running on the host (advance nonce, hash, compare, latch the winner) is **already baked**:

| circuit | gates | in→out | what it does IN THE BINARY (so the host doesn't) |
|---|---:|---|---|
| **`pfc_executor`** | 339,041 | 928→72 | the **mining executor** — sequences advance→double-SHA→compare→latch itself; output = `status:8 \| en2:32LE \| nonce:32LE` |
| **`pfc_eval`** | 502 | 153→21 | the interpreter/ripple **recreated as gates** — runs any netlist from its own memory, one gate/tick, byte-exact |
| **`pfc_clock_counter`** | 159 | 33→32 | the clock: `next = clk ? state+1 : state` (self-advancing state register) |
| **`clock_wide`** | 1,920 | 128-bit | a wide (128-bit) clock/counter |
| **`clk_bit`** | 1 | — | the clock/receiver bit (power in) |
| **`pfc_mmu`** | 1,504 | 313→313 | the Muhlnickel **addresses its own memory+storage in-fabric** — no host read/write of state |
| **`pfc_membus`** | — | — | the in-fabric memory bus |
| **`pfc_store`** | 144 | 72→72 | the answer register: `status:1 \| en2:4LE \| nonce:4LE` — the executor writes here, host reads it |
| **`pfc_kernel`** | — | — | baked kernel (CALL/RET subroutines) |
| **`sdc_os_circuit`** | 37,579 | 67→65 | an OS-level sequencing circuit |
| **`vm_step`** | 560 | 18→8 | a VM single-step (sequencer) |

**Use `pfc_executor` + `pfc_store` + the clock, and the host stops looping.** The host's five jobs (fabricate, provide
block, power one bit, read `pfc_store`, submit) — nothing more. The sweep runs in the binary at the Muhlnickel's own rate.

---

## MINERS (double-SHA-256d Bitcoin)
| circuit | gates | note |
|---|---:|---|
| `gen_miner` | 628,899 | double-SHA-256d ASIC, 640-bit routed input (shallow variant) |
| `gen_win` | 339,009 | double-SHA + baked `hash<target` compare + baked latch; out = `win \| latch[32] \| hash[256]` |
| `pfc_full_miner` | 339,234 | complete self-clocked miner: double-SHA + compare + nonce+1 self-clock + winner-latch (hand-built, byte-exact) |
| `pfc_mine` / `pfc_mine_clk` | 339,136 / 339,329 | clocked state-machine miner; `clk_bit` advances it; answer = `latch_reg` |
| `pfc_mine_shallow` | 630,781 | clocked solution + guaranteed shallow SHA |
| `miner_physical` | 339,136 | physical-location form: wires ARE file bytes, state IS storage |
| `selfclock_miner` | 347,170 | 1024-bit self-clock + double-SHA + compare + winner-latch |
| `header_from_index` | 4,172,991 | candidate-index → 256-bit header/hash mapping (the folded search front) |
| `fanout` | 262,140 | lane fanout for the fold |
| `win_cmp` / `cmp_gt` | 3,840 / 582 | comparators (hash < target / a > b) |

## FOLD / COVERAGE (the winner-only search space)
| circuit | note |
|---|---|
| `winner_only_max` | 2^262144 addressable lanes, 0 bytes/lane (`out[i]=idx[i] AND solve`) — coverage |
| `fold` | addr_bits 78 fold |
| `groups_block` | fold groups + per-group answer registers |
| `replication` | winner-only replication fields |
| `pfc_memhash` | content-addressed membership mixing-hash (key→slot) |

## CPUs & GENERAL COMPUTE
| circuit | gates | note |
|---|---:|---|
| `pfc_cpu32` | 7,403 | 32-bit stored-program CPU (15-op ISA, self-contained) |
| `pfc_cpu32r` | 14,725 | 32-bit CPU + hardware stack + CALL/RET |
| `pfc_cpu` | 1,655 | 8-bit von Neumann CPU (RAM+ALU+PC) |
| `cpu` | 216 | minimal CPU core |
| `prog_mul32` / `prog_isqrt` / `prog_crc32` / `prog_attest` | 32,768 / 31,744 / 1,952 / 30,752 | baked programs |

## ARITHMETIC & LOGIC LIBRARY
`alu32` (2,146, add/sub/and/or/xor/not/shl/shr/lt/eq) · `mul16` (1,408, 16×16→32) · `modadd32` (450, (a+b) mod m) ·
`fp_mul` (9,216) · `dot32_i8` (93,184, int8 dot product) · `adder8` (120) · `cmp_gt` (582) ·
`lib_add8/sub8/inc8/dec8/neg8/min8/max8/mux8/eq8/and8/or8/xor8/shl8` (16–343 gates each) · `g_add/g_mul` · `r_add`.

## MEMORY / LUTs
`pfc_ram` (728, addressable read/write memory) · `pfc_mmu` (1,504, in-fabric memory addressing) · `pfc_store` (144) ·
`memocache` · `silu_lut` / `exp_lut` / `rsqrt_lut` (130,944 each, function tables).

## CRYPTO
`aes128` (182,200, constant-time AES-128) · `gen_miner`/`gen_win` (double-SHA-256d) · `g_cipher` / `r_cipher` (48 each).

## MODEL / INFERENCE
`cpu_fwd` (404,262, a baked forward-pass CPU) · `wb_fwd` (2,448) · `dot32_i8` (93,184) · the LUTs above.
**`pfc_fwd_engine`** (413,865, in→out 135→134) — **THE IN-SPEC FORWARD-PASS ENGINE**: ONE clocked circuit = the `cpu_fwd`
ALU + a baked forward-pass PROGRAM (weights baked as immediates, constant-specialized) + a gate SEQUENCER
(fetch→decode→read→ALU→writeback→pc+1→halt) + register file. Runtime = the arcade read→pulse→latch (state in a Muhlnickel
storage file, gates off titan.gguf, flat RAM); host only seeds inputs + pulses + reads the answer register — NO host math.
Scale the baked program (neuron→layer→model) to run any model. (`host/pfc_fwd_engine.py`, byte-exact, reversible.)
Glue baked 07-23 (`host/pfc_glue_fab.py` / `pfc_mac_fab.py`): `pfc_argmax` (26,272, token select) · `pfc_silu8` (12,593) ·
`pfc_rsqrt` (54,472) · `pfc_exp` (6,554) · `pfc_sin` (48,517, RoPE) · `pfc_mac` (93,664, acc+dot MAC-accumulate).

## CELLULAR AUTOMATA / GRAPHICS / GAMES
`life_step` (518,144) · `tess_rot` (553,984, 4-D tesseract rotation) · `ca_rule110/30/90` · `fly110` ·
`doom_raycast` (190,360) / `doom_map*` / `doom_move*` (a DOOM engine) · `gamegen` (5,940) · `gg_*` · `pix` · `mm_text` / `mm_audio`.

## REGISTERS & I/O (routing targets, not gate circuits)
`gen_input` (block header in) · `target_reg` (target in) · `receiver` (power) · `gen_answer` (answer out) ·
`nonce_reg` / `latch_reg` / `input_window` / `clk_bit` / `os_input` / `os_answer` / `os_receiver` / `fwd_input` /
`fwd_answer` / `fwd_receiver` / `pfc_exec_input` / `mbox:titan.gguf` / `mmu_addr` / `mmu_cells` / `mmu_phys` / `mmu_wdata` /
`mmu_we` / `v_dd/v_km/v_pre/v_pol/v_sat/v_rx` (voltage/probe taps) · `b_8/b_12/b_16` · `sweep` · `output` · `pix` · `policy`.

---

## HOW TO USE THIS CATALOG (the rule)
Before writing ANY host-side loop, compare, clock, memory access, or sequence, search this file. If a circuit exists (it
usually does), **wire it and let the Muhlnickel run it** — that is the whole point (the compute is the Muhlnickel's, host RAM stays flat).
The host's only jobs remain: fabricate (before runtime), provide input, power one bit, read the answer register, submit.
When a needed function is genuinely absent, fabricate it as gates (it becomes a new row here), never as host code.
