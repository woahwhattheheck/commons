# WIRING THE MMU INTO THE FORWARD ENGINE — the last mechanical piece (2026-07-25)

> `pfc_mmu.py`'s own closing line: *"This file only FABRICATES the addressing brain; **wiring it into the pipeline is
> the follow-on.**"* This doc is that follow-on, fully specified. Fabrication only — one-and-done, before runtime.

## Why this is the blocker (measured, not argued)

`pfc_fwd_engine` is a real clocked stored-program machine (413,865 gates, byte-exact) but its ISA is
`ADD·SUB·MUL·SILU·EXP·RSQRT·GT·MOV` — a **full 3-bit opcode field, all 8 used, none of which reads storage.**
Operands come only from the register file or from immediates baked into the ROM at fabrication.

Consequence: **lengthening the program ROM does nothing.** A 256-instruction program still cannot see a single model
weight; it can only recombine the 8 seeded registers and the baked constants. That is why the demo bakes its 4 weights
as immediates — it is the only way this ISA can reach a weight. The binding constraint is the missing **LOAD**, not
`PROGLEN`.

## What is already done (do not redo)

- **Shared-location answer wire — PROVEN.** `pfc_fwd_state` (18 B @ 2461013667, allocated by `TC._alloc`, genome-
  journalled). `fwd_answer` re-pointed 2383480828 → 2461013679 so those 2 bytes **are** `regs[6]`. Verified with
  `pfc_diff`: `fwd_answer 0000 -> 5000` = 0x0050 = 0.3125 in Q8.8, matching the engine's computed `SiLU(w·x)`
  byte-exact. Original kept as `fwd_answer_orig`. The engine's register file now lives in `titan.gguf` (PFC_HARD_WON
  §1, "nothing outside the file") instead of a sandbox side-file.
- **Harness reads the shared location** (`pfc_desktop.py`, 2-byte read).
- **Harness installs any selected model** onto the Muhlnickel before connecting (`pfc_load.load`), so the dropdown is real.
- **Continuous power** on the start bit (PFC_HARD_WON §3) replacing the single-instant fire.
- I/O block untouched and verified: `fwd_input` @ 2383480823 (len 5), `fwd_receiver` @ 2383480831 (len 64).

## The MMU's contract (from the registry — read, not assumed)

```
pfc_mmu @ 2389901824   1,504 gates   typed format
n_in  313   fast_cells:16x16 | addr:40 | we:1 | wdata:16
n_out 313   next_cells:16x16 | fast_read:16 | is_storage:1 | storage_offset:40
addr_bits 40  (2 TB address space — deliberately NOT capped at titan's 40 GB file size)
```

Given a 40-bit address it returns either `fast_read` (the in-gates fast tier) or `is_storage` + `storage_offset`
(the storage-RAM fold). That is exactly the "address in a register → bytes from storage" port the ISA lacks, and it
avoids muxing 26 GB into a netlist.

## The fabrication

1. **Widen the opcode field 3 → 4 bits.** `_microcode()` currently packs
   `op(3) | rA(3)<<3 | useImm(1)<<6 | immB(16)<<7 | rD(3)<<23` = 26 bits. Go to 27 and shift every field above `op` by
   one. `build_engine()` slices these at `mc[0:3] / mc[3:6] / mc[6] / mc[7:23] / mc[23:26]` — all five must move.
2. **Add `LOAD` (opcode 8).** Address = `regA + immB` (the engine's existing `c.add` — address arithmetic is already
   ALU work). Feed the 40-bit address into the MMU, take `fast_read` (16 b) as the result, mux it into the writeback
   path alongside `_alu`'s output on `op == LOAD`.
3. **Compose the MMU's gates into the engine circuit.** THIS IS THE HARD PART AND THE REASON THIS DOC EXISTS:
   `titan_circuit` has **no compose/instantiate API** — `TC.load(name)` returns netlist data and `TC.ripple` evaluates
   it, but nothing re-emits a stored circuit's gates into a new `Circuit` with remapped wire indices. Also note the MMU
   is `typed` format while the engine is pure-NAND `TITANCIR`. Either
   (a) add a `TC.instantiate(name, circ, inputs) -> outputs` that reads the stored netlist and re-emits its gates with
       an index offset (the general fix, useful for every future compose), or
   (b) wire the two circuits **in series in storage** — shared-location, per PFC_HARD_WON §1: the engine's address-out
       bytes ARE the MMU's `addr` input bytes, and the MMU's `fast_read` bytes ARE the engine's load-in bytes. No
       composition needed, no host in the loop. **(b) is more in keeping with the machine and is the recommended path.**
4. **Verify byte-exact at fabrication** against `ref_run()` extended with LOAD, BEFORE storing. Never store an
   unverified circuit.
5. **Store reversibly** (genome; titan stays GGUF-valid).

## Verification (seconds, the bar Bryce set)

```
python host/pfc_diff.py snap
python host/pfc_fwd_engine.py run "<inputs>"        # a program using LOAD
python host/pfc_diff.py                             # fwd_answer must CHANGE and match the reference
```

## Standing constraints this must not violate

- No host forward pass, no host ripple as the runtime, **no host-clocking** (PFC_HARD_WON §2 — the clock is fabricated
  in and self-clocks).
- **Do not bake model weights as wiring** — owner 2026-07-25: *"technically possible but stupid."* Weights are ADDRESSED
  off storage; that is precisely what the MMU is for.
- Anything named `sdc_*` is stale (owner 2026-07-25). `pfc_harness.py` still shells out to `sdc_fwd_sdc.py`; the live
  harness is `pfc_desktop.py`.
- Legibility only through the owner's instruments: `pfc_diff` · `pfc_scope` · `pfc_step` · `pfc_meter` · `pfc_analyzer`
  · `pfc_assert` · `pfc_cascade` · `pfc_inspect` · `pfc_speed`.

## After this lands, the levers apply in tier order

Tier 1 mechanism-correctness is then complete. Only then do Tier 2 (XB=10 + per-sub-block activation scale, 29× less
error) and Tier 3 (MoE α 10.3×, memoize fold, KV/cache_prompt ~100×, output contract 110×) mean anything — they all
multiply a forward pass that must first exist.
