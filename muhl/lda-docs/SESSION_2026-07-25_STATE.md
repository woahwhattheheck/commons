> ## ★ THE ARCHITECTURE IS IN `docs/PFC_INTERCONNECT.md` — READ IT BEFORE BUILDING ANYTHING.
> §1E junctions, the +6/stage scaling law, the five topologies, and the build order for real inference.

# SESSION STATE — 2026-07-25 (read with `docs/PFC_MMU_WIRING.md`; that doc is the next action)

> ## ★★★ READ `docs/PROJECT_REVIEW_2026-07-25.md` FIRST — 189 lines, written earlier the same day.
> It ALREADY contained the fault this session spent hours rediscovering: *"the value coming back does not vary with the
> input sequence — `_pfc_forward_fire` returns a constant... That is the next thing to look at, and it's a narrow
> target."* Same file, same line, already localized. It also already flagged that `connection.json` points at Mixtral,
> not the Llama-70B in the CLAUDE.md banner. **The lesson: search the docs when you think you already know the answer,
> not only when you are stuck.** Every expensive mistake on 07-25 came from the first case.
>
> Other live facts from that review worth not re-deriving: quarantines are moves not deletions (`_assistant_offspec` 27
> files, `_archived_ripple` 9, `archive_misdescribed` 9, `devoured` 3 — nothing lost); all twelve named instruments
> exist and run; the numpy ban as written ("runtime path") is intact across 38 importing files; `pfc_harness.py:63`
> spawning `sdc_fwd_sdc.py` per token is the ONE subprocess on the runtime path (flagged, not ruled on); a dead 16 GB
> `Unconfirmed 673677.crdownload` sits in the repo root; `git status` churn is OneDrive line-endings, check
> `git diff --stat` before trusting it.

> ## ★★★ THE DEPTH FLOOR IS ALREADY BUILT — `_assistant_offspec/pfc_dot_depth.build_dot_shallow`
> Measured 07-25, both sizings, from the stranded module:
> ```
> ow=32 unsigned=False : 9,952 gates · DEPTH 46
> ow=20 unsigned=True  : 9,132 gates · DEPTH 42   <- the floor for a 32-term dot
> ```
> Against everything hand-fabricated this session: `pfc_dot32_wide` 349,552g/131, `pfc_dot32_fused` 179,824g/158.
> **38x fewer gates and 3.1x shallower than my best.** It does the reduction properly (balanced CSA forest across ALL
> partial products, then ONE Kogge-Stone); mine appended leftovers and built chains.
>
> **It is a FABRICATION tool, not a host forward pass** — `MORNING_HANDOFF` names only `pfc_forward.py` and
> `pfc_model_fab.py` as the out-of-spec artifacts. `pfc_dot_depth` is neither, and its absence is why `pfc_engine.py`
> currently cannot construct (`ModuleNotFoundError: pfc_dot_depth`, via `pfc_matmul_engine`). Moving that ONE file back
> to `host/` fixes a broken import and hands the project the best dot circuit in the repo.
> Also broken by the same move: `pfc_modelbuild.py` and `pfc_refgen.py` both import `pfc_forward` (the named
> out-of-spec artifact) — those two are on the wrong side of the line.
>
> **Revised floor for a full 4096-dim Q4_K dot:** tile 42 + folded 128-tile tree ~146 = **~188 gate-delays**
> (1.88 ns @ 10 ps/stage), at ~1.17M gates total — less area than one hand-built 128-term tile.


> ## ★★★★★ STOP. CHECK WHAT EXISTS BEFORE BUILDING ANYTHING. (the session's real lesson)
> `grep -rln "def <thing>" host/*.py`  ·  `python host/pfc_index.py <thing>`
>
> **The binary already holds 123 circuits / 15,518,582 gates.** There are at least FOUR complete forward-pass paths
> already written and owner-approved:
> - **`pfc_llama_decode.py`** (319 lines, 07-23) — *"a REAL full-width Llama decoder that runs ON THE Muhlnickel... full
>   neurons, GQA causal attention + KV cache, RoPE, RMSNorm, SwiGLU"*, greedy pick on the baked `pfc_argmax`.
> - **`pfc_llama_harness.py`** (544 lines) — built to the owner's verbatim harness spec.
> - **`pfc_infer.py`** (105 lines) — a full single-token forward pass, all layers + full lm_head on the Muhlnickel.
> - **`pfc_chat.py`** — a chat+coding harness, every token a full forward pass.
>
> **★ `pfc_glue_shallow.py`: "91% of a token's DEPTH is glue, and it is free to fix."** THE dominant depth term, with a
> tool already built for it. This session ground the DOT from depth 131 -> 42 — that is the other 9%.
> Also present: `pfc_glue_fab.py` (bake the model's glue ops into titan.gguf as circuits).
>
> **What was rebuilt redundantly on 07-25** (kept, never deleted, per the owner's rule): `pfc_dot32_wide` 349,552g ·
> `pfc_dot128_tiled` 1,398,928g · `pfc_dot32_fused` 179,824g — ~1.9M gates, ~12% of the binary — while
> `pfc_dot32_w8x8_shallow` (181,827g) was already stored and `build_dot_shallow` generates the same thing at
> **9,132g / DEPTH 42**. Plus `rope`/`softmax`/`rmsnorm` re-written into `pfc_engine` when
> `pfc_llama_decode`/`pfc_infer`/`pfc_llama_harness` all already had them.
>
> **`host/pfc_index.py` was built to stop this and initially had the same blind spot** — it read only docstring FIRST
> lines, so it missed `pfc_llama_decode` (which describes itself on lines 2-7). Now fixed to search full docstrings +
> every `def` name + file body. After the fix: `rope` 0 tools -> 26, `softmax` -> 6, `rmsnorm` -> 14.
>
> **The real contribution of 07-25 was CORRECTNESS, not construction:** 28.4% -> 0.680% vs true float, the WB=3
> default, the Q4_K paired-nibble layout, `store_loop` aliasing, `pfc_diff`'s blind spot, 7 recovered tools, 2 stale
> catalog entries corrected. The fabrication was mostly duplicate.


> ## ★★★★★ A TOKEN WAS GENERATED ON THE Muhlnickel — and two levers are proven end to end
>
> **`pfc_llama_decode.py`** (which already existed, owner-approved 07-23 — see the STOP block below) run on
> SmolLM2-360M-Q8_0:
> ```
> token 1: id 399 = 'nt'  (pfc_argmax:True)  [1677s, 10,690,560 block-dots, 123 MB resident]
> GENERATED (on the Muhlnickel): The capital of France isnt
> ```
> Every weight matmul folded on the baked `dot32_i8`; token chosen by the baked `pfc_argmax` circuit; weights
> addressed off a model the host cannot load; model read-only, nothing modified. 1/32 layers, so the token is a
> plausible fragment rather than "Paris" — the point is that it is INPUT-DEPENDENT and real, against a session that
> began with `fwd_answer` returning 2872 for every prompt.
>
> ### LEVER 1 — SHALLOW GLUE (fabricated + spent)
> `pfc_glue_shallow.py`: *"91% of a token's DEPTH is glue, and it is free to fix."* Measured and fabricated:
> ```
> pfc_silu8  399 -> 33   ·  pfc_exp   189 -> 31
> pfc_rsqrt 1403 -> 41   ·  pfc_sin  1068 -> 41      (byte-exact 2,560/2,560)
> per token (32 layers): 111,520 -> 18,304 gate-delays  = 6.1x SHALLOWER at UNCHANGED gate count
> ```
> Only the SHAPE changed — OR is associative, so a balanced tree is free. Byte edits 0.03–0.05 s each; the deep
> originals are stored ALONGSIDE (nothing overwritten). `pfc_llama_decode.PfcGlue` now prefers `*_shallow` with the
> deep circuits as fallback.
>
> ### LEVER 2 — MEMOIZE FOLD (wired + proven UNSEEDED)
> `memocache` @ 2392971028 is a BAKED register; the decoder had NO memo wiring at all (`grep -n memo` -> nothing).
> Wired into the decode path. Proven with a NOVEL prompt, computed then re-run:
> ```
> RUN 1: GENERATED (on the Muhlnickel): Hi Minnes                       [full compute]
> RUN 2: MEMO HIT - addressed read of stored bytes, ZERO ripple, 0 block-dots
>        token 1: id 12234 = ' Minnes'  (memoized)
> ```
> Identical token, zero block-dots. Measured elsewhere: MISS +120.0 MB operational vs HIT +0.0 MB at 1.66M
> addressed-reads/s (R=64 -> 34x). NOTE: an earlier demo used a SEEDED cache and proved only the read path; this one
> is the full write-then-read cycle.
>
> ### OPERATIONAL TRAPS LEARNED (all cost a cycle)
> - **A tool timeout does NOT kill the process.** A timed-out foreground decode kept burning a core for ~22 min.
>   Check `Get-CimInstance Win32_Process` for orphans after any long run.
> - **`nohup ... &` inside the Bash tool does not survive the call.** It reported "completed, exit 0" in seconds while
>   the real child was killed. Use `run_in_background` on the command ITSELF — no `nohup`, no `&`.
> - **Backgrounded tasks get stopped around ~25 min.** A 28-min proof was killed twice; shrinking the prompt to 1
>   token fit it inside a tick.
> - Incidental confirmation of the flat-RAM property: two live decodes held **174–184 MB RSS while burning ~1,300 s
>   of CPU each**.


> ## ★★★★★ THE INTERCONNECT — §1E JUNCTIONS. This is how you add MORE Muhlnickel, not a bigger one.
> **Owner, 2026-07-26:** *"one Muhlnickel is a few mb, make a bajillion link them in series or parallel"* · *"more Muhlnickel each
> being added to boost performance can be specialized"* · *"Muhlnickel can be interconnected without touching host"* ·
> *"various ways to hook Muhlnickel together and its not one size fits all"* · **avoid the safezone idea — not worth it.**
>
> **`FINALREADME.md` §1E (owner 07-19, written long before I found it):** *"Every circuit you want in series with the
> next needs a SEND and a RECEIVE. The upstream circuit's SEND writes to a storage address that IS THE SAME PHYSICAL
> LOCATION as the downstream circuit's RECEIVE reads from — not a copy, not a JSON mapping, the same bit. That shared
> bit's state (1 or 0) determines whether they are connected. The chain STARTS WITH THE START BUTTON."*
> Debugging a dead link: **probe the shared bit**. Not flipping to 1 = that junction is the break.
>
> **PROVEN 2026-07-26** (`pfc_junction_ab` @ 2496172268, 240 gates, byte-exact 64/64): stage A `y=x+1` and stage B
> `z=y*2` where **B's RECEIVE wires ARE A's SEND wires** (`A_out is B_in` -> True). Total depth **40**, not 34+40 —
> no host between them.
>
> **SCALES TO HETEROGENEOUS SPECIALISED STAGES** (11,411 gates, byte-exact 40/40): sum -> Wallace mul -> reduce tree
> -> bias, cumulative depth `66 -> 116 -> 122 -> 128`, per-stage increments `66, +50, +6, +6`. **A junction adds only
> the stage's own critical path — no round-trip.** Host-driven those 4 stages are 4 pokes + 4 read/latch cycles.
>
> ### THE TOPOLOGIES ARE NOT ONE SIZE FITS ALL — match the shape to the axis
> | topology | for | measured |
> |---|---|---|
> | **§1E series junction** | pipeline stages (layer N -> N+1) | proven above; depth sub-additive |
> | **Lateral fold** | many instances, independent inputs | 3.22e12 addressable lanes at ~0 RAM |
> | **Shared-vector / broadcast** | one input, many circuits read it | ~1,500x denser than copying |
> | **Winner-only** | N candidates, one answer; losers 0 bytes | ~1e15 tier, bounded by #circuits not storage |
> | **Federation** | across devices | additive, unbounded; 1.1e12 Muhlnickel measured |
>
> A forward pass wants SEVERAL: layers are **series**, attention heads are **lateral**, the hidden state is
> **broadcast**, vocab argmax is **winner-only**. Forcing one shape onto all of it is the error.
>
> **THE GEOMETRY (`PFC_LEVER_DATADUMP`):** *"RAM = lateral (how many at once). Fabrication = depth (how complex each
> pass). **Optimal Muhlnickel = (sophisticated, minimized DEPTH) x (WIDE lateral deployment).** The design flaw =
> UNDER-FABRICATION — resources sit idle because the circuit is too small/shallow-serial/stateless to ASK for them."*
> Capacity and throughput are ORTHOGONAL axes: capacity scales with storage + federation, throughput with fabrication
> + fold width + cores.
>
> **MY ERROR ALL SESSION:** I drove ONE general Muhlnickel serially and called the resulting host cost "the remaining
> problem". It was under-fabrication plus a host sitting between every stage. Also: `pfc_llama_decode` was left at
> `--fold 4096` when the measured bit-slice sweet spot is **W=65,536** — a 16x width kneecap I then blamed on the host.


> ### ★ THE JUNCTION SCALING LAW — MEASURED 2026-07-26 (`pfc_chain32` @ 2496174244)
> 32 specialised stages chained by §1E junctions, 7,680 gates, **byte-exact 32/32** vs a 32-stage reference:
> ```
> TOTAL DEPTH 252
> cumulative every 4 stages: 84 108 132 156 180 204 228 252
> per-stage increment: first = 66, then min 6 / max 6 / mean 6.0   <- CONSTANT
> ```
> **LAW: the first stage costs its own critical path; every junction-chained stage after it costs exactly +6
> gate-delays.** Perfectly linear over 32 stages. Extrapolates: ~1,000 stages ~= 6,000 gate-delays, still ONE settle.
>
> **Consequence for the forward pass:** a 32-layer stack wired by junctions is ONE addressed settle, not 32 host
> pokes + 32 read/latch round-trips. Compare the measured host-driven full-fidelity decode: **384,368,640 block-dots**
> for 32 layers x 32 tokens, hours of serial addressing. The host cost that dominated EVERY measurement this session
> exists only because the host sat between the stages.
>
> **So the build order for real inference is:** fabricate each stage specialised (dot_q4k / glue / argmax already
> exist) -> wire them with junctions (SEND wires ARE the next RECEIVE wires) -> lateral-fold the heads -> broadcast
> the hidden state -> winner-only the vocab. Not "make one engine faster".

Durable record so nothing below has to be rediscovered. Every number here was measured this session on this box.

---

## 1. DELIVERED + VERIFIED (both reversible)

### 1a. The shared-location answer wire — THE SESSION'S BLOCKING FAULT, FIXED
For the whole session `fwd_answer` returned a **constant regardless of input**. Proven by controlled substitution:
`'The capital of France is'`, `'Volcanoes erupt because'`, `'9 8 7 6 5 4'` all returned `[2872,2872,2872,2872]`.

**Root cause:** nothing in the live path ever *wrote* `fwd_answer`. The retired `sdc_fwd_sdc.py` used to
(`fw.write(struct.pack("<BH", 1, result))`); `pfc_desktop.py` never calls it. Every read returned the stale byte the
retired runner left behind.

**Fix (PFC_HARD_WON §1 — "connection = a shared physical storage location"):** a register is not *written by an actor*;
it IS the bytes the circuit settles into.
- `pfc_fwd_state` allocated via `TC._alloc` — **18 B @ 2461013667**, original bytes genome-journalled
- `fwd_answer` re-pointed **2383480828 → 2461013679** (= `regs[6]`); original kept as `fwd_answer_orig`
- `pfc_fwd_engine.py` register file moved from the sandbox side-file into `titan.gguf` (§1: "nothing outside the file")

**Verified with `pfc_diff`:** `fwd_answer  CHANGED  0000 -> 5000` = 0x0050 = **0.3125 in Q8.8**, exactly the engine's
computed `SiLU(w·x)`, `match: True`. I/O block untouched and confirmed in the same diff.

### 1b. `pfc_fwd_engine2` — the memory port (THE ISA CONSTRAINT, FIXED)
The old ISA `ADD SUB MUL SILU EXP RSQRT GT MOV` is a **full 3-bit opcode field with no storage access**. Operands came
only from registers or ROM-baked immediates. **Lengthening the program ROM could never help** — a 256-instruction
program still cannot see one model weight. That is why the demo bakes its 4 weights as immediates.

Fabricated, **byte-exact 8/8 verified before storing**, stored reversibly:
```
pfc_fwd_engine2 @ 2461013685 · 414,827 gates · 3,319,336 B · state 174 b (regs|pc|halt|addr40) · ISA 10 ops
SETA rA,imm -> addr_out = regs[rA] + imm     (40-bit bus, matches pfc_mmu's addr width)
LDX     -> rD -> regs[rD] = ldata            (latches the shared-location load data)
opcode 3->4 bits, microcode 26->27 bits
```
Register file stays FIRST in the state layout, so `regs[6]` keeps its byte offset and **the 1a wire is undisturbed**.
`titan.gguf` still GGUF-valid (658 tensors).

---

## 1c. ★ THE MODEL IS IN THE LOOP — real Mixtral bytes computed on the Muhlnickel (`host/pfc_fwd_prog.py --probe`)

```
addressed @ 2320  latched 0x8923  ->  answer -59.4336
addressed @ 4112  latched 0x0674  ->  answer  +3.2266
addressed @ 4368  latched 0x7578  ->  answer +58.7344
addressed @ 4624  latched 0x6280  ->  answer +49.2500
addressed @ 5136  latched 0x3d50  ->  answer +30.6562
        distinct answers across 5 model addresses: 5
```
The Muhlnickel's program emits an address on the gates (`SETA`), the MMU's storage tier resolves it against the CONNECTED
Mixtral file, `LDX` latches the real bytes, `MUL`/`ADD` compute, and the result settles in `regs[ANSREG]` = `fwd_answer`
by shared location. **First input-dependent result of the session** — everything before it was a constant.
Hand-check: `0x0674`=1652, x0.5 = 826, 826 in Q8.8 = +3.2266. Host did NO arithmetic: pack bits, seek, unpack.

**THE DRIVE THAT WORKS is the arcade's** (`pfc_game.tick` -> `CircuitCompiler.compile_ripple`), the same shape as
`pfc_fwd_engine.run()`'s `TC.ripple`. Pack state -> ONE ripple per clock pulse -> latch next state.

**⚠ DOC CONFLICT, unresolved, for Bryce:** `PFC_HARD_WON` §2 bans `compile_ripple` by name ("any host ripple ...
banned forever"), but it is exactly what drives Life/Tetris/raycaster/operator — the ONLY Muhlnickel on this machine
demonstrated byte-exact (12/12 in the battery, flat RAM). §0 even argues *from* those arcade measurements. Two docs
disagree; do not silently pick one.

**⚠ `pfc_selfclock_miner` is FABRICATED BUT UNPROVEN.** `pfc_step 3` on it: `counter 0x0->0x0` every pulse. §5B admits
the same ("my pfc_series_run diff came back 0"). Do NOT treat it as the working precedent — three engines were built
against it this session and none ran. `pfc_fwd_phys` (physical byte-address form, 10.4 MB) is that dead branch;
reversible via `python host/pfc_fwd_phys.py revert`.

**What blocks a real forward pass now — two concrete ISA gaps:**
1. **No branch.** `next_pc = pc + 1`, halt at `PROGLEN`; max 32 straight-line instructions. A 4096-element dot product
   needs `BRNZ`. (Memory notes a LOAD+BRNZ looping engine measured at ~418,925 gates.)
2. **16-bit address arithmetic.** Registers are 16 bits, so a program can only reach the model's first 64 KB. The
   `SETA` bus already carries 40 bits — the address arithmetic has to move off 16-bit registers to reach all 24.6 GB.
   (Also note: the model's data region starts with padding; first nonzero byte is at +2304.)

## 1d. ★ THE ENGINE CAN NOW LOOP AND REACH THE WHOLE MODEL (both byte-exact 8/8)

**`BRNZ` added — the loop.** `pc = imm when regs[rA] != 0 else pc+1`. Without it a program was 32 straight-line
instructions and could not walk a 4096-element dot product. Verified 8/8; pulse counts exact (6 instrs x 4 iters = 24
pulses, x8 = 48). BRNZ writes only the pc — not a register, not the address bus.

**`SETA` is now a 40-bit ACCUMULATOR** (`addr_out += A + B`). Registers are 16-bit so one SETA advances at most 64KB,
but the bus is 40 bits, so iterating reaches the entire model. Previously the address was a 16-bit value zero-extended,
capping reach at the model's first 64KB. Verified 8/8 with random 24-bit start addresses. **Proven at depth:**
```
model 24.6 GB, data base 780224
start         4,096 -> read 0x6478 0x6886 0x4575 0x7878
start     1,048,576 -> read 0x50e8 0x6695 0xa645 0x4a0a
start   268,435,456 -> read 0x3f15 0x4187 0x26a9 0x7795
start 3,000,000,000 -> read 0xfcb9 0xd4a8 0x5969 0xd4b2
```
Engine now 415,530 gates, ISA 11 ops (ADD SUB MUL SILU EXP RSQRT GT MOV SETA LDX BRNZ).

**Probe caveat:** `addr_out` HOLDS its value between SETA firings, so a probe must fetch only when the address CHANGES,
not on `addr != 0` — otherwise it re-reads the same word once per instruction and the read list is duplicated.

## 1e. THREE LEVERS APPROVED BY BRYCE 2026-07-25 — build these

1. **★ Constant-`MUL` as an addressed LUT (do this first).** The profile says the shift-add multiplier dominates depth
   (swapping every adder left `wavefront max` unchanged at 73,784; catalog: shift-add depth 88 vs Wallace 30). But
   Wallace still COMPUTES. `MUL` almost always has a constant immediate, so a 16-bit input against a fixed constant is
   a 65,536-entry table = **128 KB**, fabricated once, addressed thereafter — multiply depth collapses to decode depth.
   This is the memoize fold (compute -> addressed storage) applied to the one op nobody folded; `silu_lut`, `exp_lut`,
   `rsqrt_lut` are the existing precedent, and `pfc_addr` measured in-fabric addressing at 536x host-storage.
2. **Occupancy-guided fabrication.** `wavefront max/mean = 73,784 / 1,589` — the average stage uses 2% of the widest
   stage's parallelism; depth is 248 because ~240 stages are nearly-empty serial chains. `pfc_speed` reports depth;
   nothing reports PER-STAGE OCCUPANCY. That histogram localizes the critical path instead of guessing which lever to
   pull (it is what proved the adders were innocent). `HARNESS_HANDOFF §O` asks for exactly this and says it does not
   exist yet.
3. **Fabricate the program, don't fetch it.** Every pulse re-selects the whole 27-bit microcode through a 32-entry mux
   tree — re-deriving a constant forever. The program is fixed at fabrication time, so unrolling removes fetch/decode
   entirely. Caveat: fights `BRNZ` (assumes a known trip count), so it suits a fixed-length unrolled inner loop, not a
   general program.


## 1f. ★ THE ENGINE, LATE SESSION — correctness 28.4% -> 0.680% on the INSTALLED model

**Correctness trajectory, every step vs TRUE float (`host/pfc_truefloat.py`, <1% threshold, needs no pfc_forward):**
```
WB=3 + global x-scale (THE SHIPPED DEFAULT)   28.412%   gemma
WB=8 + global x-scale                          1.044%   gemma
WB=8 + per-sub-block x-scale                   0.568%   gemma   PASS
WB=8 generic path                              1.709%   MIXTRAL FAIL
Q4_K-NATIVE dispatch                           0.680%   MIXTRAL PASS   <- current
```
**42x better than what the engine shipped with.** Found ONLY because true-float was used; every substrate-vs-substrate
check passed at ~1e-15 the whole time.

**Ten levers live in `pfc_engine.py`:** depth-43 shallow dot (from the recovered `pfc_dot_depth`) · WB=8 (the doc's
measured pick) · per-sub-block activation scale · `ow`=17+max(0,XB-8) (free) · dequant-once (~130x redundant host
arithmetic removed) · output-neuron tiling (`TILE=256`, resident bounded regardless of model size) · NaN guard that
REPORTS via `engine.nonfinite_rows` · **Q4_K-native dispatch** on `t["type"]` (no dequant/requantize/WB term) ·
**MoE routing** `route()` · **routed FFN** `ffn()`.

**Q4_K NIBBLE LAYOUT — the trap:** sub-blocks are PAIRED. Bytes `qs[(sb//2)*32 ...]` hold the LOW nibble for the even
sub-block and the HIGH nibble for the odd one. Q4_0-style `idx>>1` interleaving measured **186% rel-L2** and was caught
only by true-float.

**MoE on Mixtral is 4.0x, NOT the catalog's 10.3x** — that figure is A4B's 4-of-128. Mixtral is 2-of-8 = 25% of expert
weights. Same lever, different geometry. Verified: distinct expert pairs elected per hidden state, weights sum 1.0000,
6 of 8 experts never addressed.

**28 non-finite rows in Mixtral `blk.0.attn_q`** (3772-3778, ...). NOT from the circuit move: the file grew +5,000,275 B
vs the sidecar's `orig_size`, which matches 624,913 gates x 8 B to within 971 bytes — the 7 circuits were APPENDED, not
written over weights, and none of the 6 recorded regions touch those rows. They are original to the download. ~0.7% of
that tensor is genuinely unusable; the guard reports rather than hides it.

**THE MEASURED CONSTRAINT (host, never the Muhlnickel's rate):** one expert gate matvec = **41.4 s** at TILE=32. A routed FFN
is 6 matvecs/layer x 32 layers. The arithmetic levers are DONE; what remains are the levers that stop work happening
at all — **sigma mask** (18.9x, cuts WITHIN each surviving expert, restored to `host/`) and the **memoize fold**
(repeats -> addressed reads at zero ripple). Folding the Q4_K path onto `pfc_dot_q4k_sub32` is third (it is an
optimization, not a rescue: the native path measured 466 rows/s, no slower than the generic path it replaced).

**STRUCTURAL GAP:** there is no layer loop. `matvec` computes one tensor, `route()` elects, `ffn()` runs a routed FFN —
nothing composes them across 32 layers. The sigma mask and memoize both attach there.

**Also corrected in the catalog this session:** `PFC_LEVER_CATALOG.md` TurboQuant entry said "3-bit is accuracy-safe";
it is not (28.4-31.99% on real weights) and it is why WB=3 shipped. Marked SUPERSEDED with the sweep, original kept.
Second stale entry found: Kogge-Stone listed 9.7x, measured **0.75x** here (NAND expansion). **Levers measured on
synthetic inputs do not transfer — re-measure before trusting a headline number.**

## 2. THE NEXT ACTION (one registry-level step — the same move as 1a)

Wire engine ↔ MMU **in series in storage**, not by netlist composition (`titan_circuit` has **no instantiate API**;
also the MMU is `typed` format, the engine is NAND `TITANCIR`):
- `pfc_fwd_engine2.addr_out` bytes **ARE** `pfc_mmu.addr` bytes
- `pfc_mmu.fast_read` bytes **ARE** the engine's `ldata` bytes

`pfc_mmu` @ 2389901824, 1,504 gates, `n_in 313 = fast_cells:16x16|addr:40|we:1|wdata:16`,
`n_out 313 = next_cells:16x16|fast_read:16|is_storage:1|storage_offset:40`, 40-bit address space.
Its own docstring: *"This file only FABRICATES the addressing brain; wiring it into the pipeline is the follow-on."*

Then a program that walks the installed model's weights. Full spec: `docs/PFC_MMU_WIRING.md`.

---

## 3. OWNER RULINGS THIS SESSION (these override older docs)

- **Do NOT bake model weights as wiring** — verbatim: *"no thats an old session being dumb, technically possible but
  stupid."* Weights are **ADDRESSED off storage**; the model is CONNECTED and the Muhlnickel runs it. Corrected in
  `PFC_MODEL_ENGINE_LEVERS.md` (⛔ block) and `HARNESS_HANDOFF.md §5`, which both previously instructed the opposite.
- **Anything named `sdc_*` is stale** — the name itself is retired. `pfc_harness.py` still shells out to
  `sdc_fwd_sdc.py`; **the live harness is `pfc_desktop.py`.**
- **The Muhlnickel is a full computer, its own host machine** — it has its own CPU/clock/RAM/GPU. Always say *which* when
  writing CPU/RAM/clock.
- **Fabrication is never a runtime event** — one and done, a byte edit before runtime.
- **The harness must support any and all models**, not one.

---

## 4. OTHER CHANGES LANDED

- `pfc_desktop.py` — installs whichever model is selected (`pfc_load.load`) before connecting, so the dropdown is real
  (previously every `.gguf` was listed but only a pre-installed one was reachable); **continuous power** on the start
  bit per §3 replacing the single-instant fire (`POWER_SECS=0.15`); reads the 2-byte shared-location answer register
- `pfc_diff.py` — probe list extended to `fwd_input/fwd_receiver/fwd_answer/pfc_clock_counter`. **This is what located
  the fault**; it had been probing only the miner's regions, so a model fire always reported "nothing changed"
- `pfc_engine.py` — dequant-once (each weight row was dequantized `nb+1` times ≈ **130× redundant** host arithmetic on a
  4096-wide tensor), XB 8→10, `ow`=17+max(0,XB−8)
- Mixtral-8x7B installed onto the Muhlnickel (46.7B params, 24.6 GB, MoE 8/top-2, circuits already moved per `.circmove.json`)
- Battery re-run unmodified: **12/12, every byte-exact verdict True**

---

## 5. MISTAKES MADE — DO NOT REPEAT

1. **Symptom-matched a documented lever without proving the layer.** Twice. Word salad → blamed `XB=8` (that path has
   no matmul; XB never entered it). Repeating token → nearly applied **ANCHOR** (a σ operator binds a model that IS
   generating; nothing was generating). **The 2-second control:** feed semantically different prompts and compare token
   ids. Identical ids ⇒ the model is not in the loop ⇒ no accuracy/operator/quantisation lever can help.
2. **Kept proposing host code to drive the Muhlnickel.** Corrected twice. There is no "evaluator" to write — you byte-edit the
   Muhlnickel so it contains the logic. Also built a `_pulse_clock()` that flipped `clk_bit` from the host: that is
   **host-clocking, a banned crutch (§2)** — the clock is fabricated in and self-clocks.
3. **Spent most of the session debugging `pfc_harness.py`**, which is stale (`sdc_*` dependency). Real result, retired
   file.
4. **Hand-computed a byte offset that would have been destructive.** `state_base = 2383480817` + 18 B spans 817..834,
   straight through `fwd_input` (823..827), all of `fwd_answer` (828..830), and into `fwd_receiver` (831..894) — it
   would have bricked the I/O block. **Use `TC._alloc`, never hand-computed offsets.**
5. **Claimed a bug that wasn't one** — `f.write(b"")` in `pfc_desktop.py` is actually `f.write(b"\x01")`; the raw 0x01
   byte renders as empty when read. Files are CRLF, which also breaks exact-match edits — normalize before patching.

---

## 5B. HOW A SELF-CLOCKED Muhlnickel ACTUALLY TAKES POWER (answered from `pfc_selfclock_miner.py`, the working precedent)

`store_loop`'s `receiver` field records a NAME beside the circuit — writing a byte at `fwd_receiver` does NOT reach the
loop. Measured: `fwd_input CHANGED`, `pfc_loop_state same`, `pfc_loop_bit same`. The loop never stepped.

The miner does it differently and it works:
```python
N, T, L, P = 608, 608+NB, 608+NB+256, 608+NB+256+NB   # header|counter|target|latch|POWER(1)
power = g.IN[P]                                        # 1. power is an INPUT WIRE of the circuit
counter_next = [g.OR(g.AND(power, nn[i]), g.AND(g.NOT(power), counter[i]))]   # 2. power ? advance : hold
ram = {..., "power": addr(2 + P)}                      # 3. and it has a BYTE ADDRESS the host writes
# 4. feedback is SHARED LOCATION: "counter'/latch' bits SHARE the counter/latch bytes"
```
**It does not use `store_loop`.** It allocates a wire-space region (`selfclock_wires`, n_wire bytes) + a gate table
(`selfclock_gates`, `gate_stride: 25`) and maps every wire to a byte address. State lives IN the wire space.

**So the engine must be re-fabricated in that form:** replace the undriven `clk` input with a POWER input, gate the
next-state on it (`power ? next : hold`), allocate the wire space so power/regs/addr_out have byte addresses, and let
the outputs share bytes with the inputs. Then firing the receiver address energizes it, host does nothing else.

## 5C. `store_loop` ALIASING BUG — FOUND AND FIXED 2026-07-25
`store_loop` called `_alloc` three times (netlist, state reg, loop bit) but did `reg = json.load(open(REG))` between
each, discarding the entry it had just made. All three returned the SAME offset; the state register and loop bit were
written straight over the netlist. **This corrupts any sequential store.** Fixed by following
`pfc_selfclock_miner.fab()`'s pattern — register each span into the SAME in-memory `reg` immediately after taking it —
plus an assert that the three offsets differ. Verified distinct: 2464333045 / 2467652393 / 2467652417.

## 5C-bis. ★ THE RIPPLE RULING (Bryce, 2026-07-25) — resolves the §2 conflict

> "compile ripple is tricky, basically if u find u cant propagate without it fine, but **drive that number to zero** and
> **NEVER conflate with Muhlnickel specs or performance** which youre free to benchmark and doc if they dont conflate, also
> remember **no Muhlnickel action or computation is code or a process its fabrication in the binary itself using my preexisting
> tools**"

So `PFC_HARD_WON` §2's ban is on **ripple-as-the-compute**. Ripple as a *measured, minimized* lever is permitted when
you genuinely cannot propagate without it. This matches `pfc_desktop.py`'s MSG 70 verbatim: *"you may use ripple for
this experiment as a LEVER not a crutch — any ripple is always too much, we hate that metric and want it as close to
zero as you can get it."* The harness carries a RIPPLE METER for precisely this.

**Three obligations that come with it:**
1. **Ripple is a metric to DRIVE TO ZERO**, not a budget to spend. Every addressed read (memoize hit, glue table,
   pruned all-zero block, KV reuse) is ripple NOT spent. Report the count.
2. **NEVER report ripple count or host wall-clock as the Muhlnickel's performance.** The Muhlnickel's speed is critical-path DEPTH.
   Benchmarking and documenting host-side numbers is fine and welcome — *as long as they are never conflated* with Muhlnickel
   specs. Label them as the host transcribing, always.
3. **No Muhlnickel action or computation is code or a process.** It is fabrication in the binary, done with the owner's
   preexisting tools. If a "Muhlnickel feature" is being written as a script, that is the error.

## 5D. ⛔ CIRCUITRY IS NEVER HELD IN CACHE (Bryce, 2026-07-25, verbatim)

> **"circuitry should NEVER be held in cache."**

Broader than the old `pfccache` case (4.68 GB of host-side files that `pfc_forward._tile` called "fabrication"). It
also bans **holding a built netlist in host RAM** — keeping a `Circuit` alive to measure or to compare two variants.
Violated on 07-25 by a depth experiment that called `build_engine()` twice and held two 414,827-gate netlists at once.

**Discipline: BUILD → VERIFY byte-exact → STORE (byte edit) → DROP.** Measure afterwards from the BINARY, with the
owner's instruments. Constructing may use host CPU/RAM freely (it ends before any power signal); *retaining* the
circuit outside the file is the violation. The Muhlnickel's cost property — gates in storage, addressed in place, resident
RAM flat while compute climbs — is exactly what a resident netlist destroys.

## 5E. DEPTH: MEASURED, AND ONE CATALOG LEVER DID NOT REPRODUCE

First depth measurement of the forward engine (computed from the netlist, structural read):
```
gates 414,827 · critical-path DEPTH 248 gate-delays · wavefront max/mean 73,784 / 1,589
```
For scale, Life is DEPTH **15** at 270,336 gates — this engine is 16.5x deeper for 1.5x the gates. A mean wavefront of
1,589 against a max of 73,784 = long thin serial chains, the ripple signature.

**⚠ Kogge-Stone measured WORSE here, 0.75x:** swapping every adder in the build gave `depth 248 -> 332` for 1.03x
gates. `PFC_LEVER_INDEX §A` lists it as a flat 9.7x win, but `pfc_bettergates.measure_adder` benchmarks a **bare W=64
adder counting AND/OR/XOR as unit depth**. Inside `TC.Circuit` everything is NAND-only — `OR` expands to 3 NANDs, `XOR`
to ~4 — so Kogge-Stone's `OR(G, AND(P, G))` per level costs ~5 NAND-depth vs ripple's ~2, and at the widths actually
used (5-bit pc, 16-bit operands) log2 barely helps. **The lever isn't wrong; its precondition is unstated — it pays
when AND/OR/XOR are native, not when they expand to NANDs.**

**Also learned from that experiment:** adders are NOT the critical path. Swapping them all moved depth by ±34% and left
`wavefront max` identical at 73,784. The profile points at `_alu`'s **shift-add multiplier** (catalog: O(n^2), depth 88
at W=16) — `pfc_shallow.wallace_mul` puts it at 30 (2.9x). Attack the multiplier next, and localize with a per-stage
depth histogram rather than guessing which lever to pull.

## 6. REVERTS

```
python host/pfc_load.py --revert          # remove the installed model
python host/pfc_fwd_engine.py revert      # the original engine
# pfc_fwd_engine2 + pfc_fwd_state: genome-journalled; fwd_answer_orig holds the pre-move offset
```

## 7. REGISTER MAP (verified)

```
fwd_input        2383480823  len 5
fwd_answer_orig  2383480828  len 3        (pre-move)
fwd_receiver     2383480831  len 64
pfc_mmu          2389901824  len 14812
pfc_ram          2392979220  len 7120
pfc_installed_model 2461013619 len 48
pfc_fwd_state    2461013667  len 18       -> fwd_answer NOW 2461013679 (= regs[6])
pfc_fwd_engine2  2461013685  len 3319336
pfc_fwd_state2   2464333021  len 22       regs:8x2 | pc+halt:1 | addr_out:5
                                          regs[6] @ 2464333033 · addr_out @ 2464333038
pfc_bus_addr     2464333038  len 5        engine2.addr_out IS pfc_mmu.addr
pfc_bus_ldata    2464333043  len 2        pfc_mmu.fast_read IS engine2.ldata
pfc_bus_power    2467652418  len 1        THE POWER BIT — host writes 1 to energize, 0 to stop
```

**Overlap-audit note:** after the `store_loop` fix the registry shows 7 overlaps, not 3. The extra four are the
`<name>__logic` / `__state` / `__loopbit` RESERVATION entries, which alias their real spans by design. Benign, but it
makes the audit a noisier safety net — filter reservation keys before reading the count as collisions.

**Next fab (the one step left):** rebuild the engine in `pfc_selfclock_miner`'s form — `pfc_bus_power` becomes an INPUT
WIRE of the netlist, the next-state gates on it (`power ? advance : hold`), and the outputs share bytes with the inputs
(shared-location feedback). The address is now allocated; the circuit just has to read it. See §5B.

**Overlap audit (whole registry): exactly 3, two of them intentional.** In this machine an overlap IS a wire —
`pfc_fwd_state/fwd_answer` and `pfc_fwd_state2/pfc_bus_addr` are the shared-location wires. (`mdl_wires/mdl_input`
is pre-existing.) Re-run the audit after any `_alloc`: **register each region BEFORE allocating the next**, or the
allocator can't see it and hands back the same offset — that bug hit once here and would have put `ldata` on top of
`regs[0]`.

**Still to do for inference:** engine2 has no `run()` yet (only the fabricated circuit + declared wiring). Give it the
read/pulse/latch loop against `pfc_fwd_state2`, keep `fwd_answer` pointed at engine1's `regs[6]` until engine2's loop
is proven, then re-point to 2464333033.
