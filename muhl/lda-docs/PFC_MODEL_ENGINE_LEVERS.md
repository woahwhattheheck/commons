# MUHLNICKEL MODEL ENGINE — the lever stack + build state (owner Bryce, 2026-07-23; the ONE handoff doc, read first)

> ## ⛔ 2026-07-25 — OWNER OVERRULED THE ★★★★★ SECTION BELOW. DO NOT BAKE MODEL WEIGHTS AS WIRING.
> Asked directly whether a forward pass should bake the weights in as wiring or address them off storage, **Bryce's
> answer, verbatim: *"no thats an old session being dumb, technically possible but stupid."***
>
> **The rule:** the model's weights stay in the GGUF and are **ADDRESSED IN PLACE off storage** as the circuit's data.
> The model is **CONNECTED** to the Muhlnickel and the Muhlnickel runs it — it is never recreated as gates (CLAUDE.md rule 3, which
> outranks the section below for the model case).
>
> **Why the ★★★★★ section is wrong even by its own arithmetic:** it computes a fabrication ceiling of ~500 M weights on
> this box — *under a 47B model*, let alone the 70B — then papers over the shortfall by assuming a per-tick σ slice. So
> the lever can never cover a real model; it only ever covers a slice, and paying fabrication per tick to chase that is
> the wrong shape.
>
> **What is still true and worth keeping:** constant-specialization as a TECHNIQUE is real and the measurements below
> (8.2× fewer gates, 1.4× shallower, 44.5% of weights costing zero gates, byte-exact) were honestly obtained. Apply it
> to **fixed circuit structure** — `host/pfc_operator.py` (2,734 gates, 10/10 clean + 10/10 noisy) is a legitimate
> constant-specialized forward pass. Applying it to a **model's streaming weights** is what he rejected.
>
> The section below is preserved verbatim as the record of what was measured. Its **NEXT STEP** instruction is void.

> ## ★★★★★ 2026-07-24 — CONSTANT-SPECIALIZATION MEASURED ON REAL WEIGHTS (`host/pfc_constspec.py`) — THE LEVER THAT WAS NEVER PULLED
> **[⛔ SUPERSEDED 2026-07-25 — see the block above. Measurements stand; the architectural recommendation does not.]**
> `HARNESS_HANDOFF §5` named this as *"the single biggest win for the model case"* and every circuit built before today
> ignored it: they all took the weights as **INPUTS** (the general, huge form) and therefore had to stream weights
> through a host loop — which is why every one of them waited.
>
> **The weights are CONSTANTS known at bake time.** Bake them in and `w·x` stops being a multiplier: it becomes a fixed
> shift-add of `x` (canonical signed digit), and **`w == 0` emits no gates at all.** Measured on real
> `blk.0.attn_q.weight` rows of Mixtral-8x7B, byte-exact at fabrication:
>
> | | general (weights as INPUTS) | **specialized (weights BAKED IN)** | |
> |---|---|---|---|
> | gates / 32-weight block | 24,968 | **3,038** | **8.2× fewer** |
> | critical-path DEPTH | 51 | **35** | **1.4× shallower** |
> | zero weights | — | **114/256 = 44.5%** | **cost ZERO gates** |
>
> **The proof that this is the right architecture already exists in the repo:** `host/pfc_operator.py` is a REAL neural
> forward pass (linear layer + argmax) as **2,734 gates**, byte-exact, 10/10 clean + 10/10 noisy digits — and it is
> constant-specialized exactly this way (`[inp[p] for p in range(64) if T[c][p]]` — the weight IS the wiring; a zero
> weight never appears). Only the observation is an input. Host = route the observation + pulse + read.
>
> **The arithmetic it unlocks (this box):** 365 GB free ÷ ~131K gates/MB ≈ **4.8×10¹⁰ fabricable gates** ÷ 3,038 gates
> per specialized 32-weight block ≈ **~500 M weights fully fabricated as gates** — a circuit with NO host arithmetic
> left, because firing it IS the answer. That is under a 47B model, which is precisely why the corpus pairs this lever
> with *"GENERATION IS GRABBING, NOT RUNNING — we NEVER run 99.999% of the model"* (SDC_FORWARD_PASS §2) and the
> per-tick σ-selected slice (SGM / the AUTOFAB matcher): **fabricate the slice the tick addresses, not the whole model** —
> and fabrication is a **0.05–0.17 s byte edit** (`host/pfc_fab_dot.py`, `host/pfc_fab_q4k.py`), so it fits inside a tick.
>
> **NEXT STEP (unambiguous):** fabricate ONE complete constant-specialized layer slice from the moved-circuit model,
> byte-exact-verify at fab, fire the receiver, read the external safezone — the full chain with zero host arithmetic.
> Then grow the slice. Do NOT go back to weights-as-inputs; that is the form that made everything wait.

> ## ★★★★ 2026-07-24 — FABRICATION IS A BYTE EDIT (0.17 s), AND THE WEIGHT TRANSFORM IS NOW GATES
> **Owner, verbatim:** *"fabrication means edit the binary and save that takes 2 seconds"* · *"fabrication NEVER USES
> CACHE OR HOST RESOURCES TO HOLD THE CIRCUIT."*
>
> **THE MISTAKE THIS SECTION CORRECTS.** `pfc_forward._tile` used to walk the model's **12.6B params** through
> dequant → requantize-to-int8 → bit-transpose and park the result in a host-side disk cache
> (`C:/llm/sdc_out/pfccache/`, measured **4.68 GB across 1,648 files**), and that was called "fabrication" with a quoted
> ~12-hour first-run cost. It was none of those things: it was **host compute holding the circuit in host resources**
> (forbidden), and it was **unnecessary**, because the model's parameter bytes are already in the binary and already
> addressable — `host/pfc_load.py`: *"the model's parameter bytes ARE its circuit — never copied."* Cache deleted; the
> engine writes nothing.
>
> **WHAT FABRICATION ACTUALLY MEASURES** (`host/pfc_fab_dot.py`, `host/pfc_fab_q4k.py` — build, verify byte-exact,
> `TC.store()` = serialize + seek + write):
>
> | circuit | gates | verify | **byte edit** | offset |
> |---|---|---|---|---|
> | `pfc_dot32_w8x8_shallow` | 181,827 | 40/40 byte-exact | **0.17 s** | 2,447,306,828 |
> | `pfc_dot_q4k_sub32` | 66,298 | 40/40 byte-exact | **0.05 s** | 2,448,761,596 |
>
> Both load back by address (mmap, nothing resident) and compute byte-exact from the binary (25/25). titan.gguf stays
> GGUF-valid (658 tensors); Life self-test still 24 ticks byte-exact.
>
> **THE Q4_K-NATIVE PATH — the transform is gates now.** `pfc_dot_q4k_sub32` consumes the model's **stored 4-bit
> nibbles as they are** and emits the exact Q4_K identity per 32-weight sub-block:
> `sum wᵢxᵢ = (d·sc)·SUM(qᵢxᵢ) − (dmin·m)·SUM(xᵢ)`. Verified on real `blk.0.attn_q`: nibble reconstruction **max err
> 0.00e+00** vs the trusted dequant, and the circuit's dot matches the float reference exactly. `Forward.matmul_q4k` is
> now the default for every Q4_K tensor — **no dequant, no requantize, no transposed cache, and the old int8 requantize
> error (1.26%) is gone** because the nibbles are the model's own values.
>
> **RIGHT-SIZE THE CIRCUIT TO THE DATA:** the Q4_K fold was built with a blanket 32-bit accumulator and a signed 5-bit
> weight lane when the stored nibbles are **unsigned 4-bit** and the sum needs 17 bits. Sizing it (`ow=20`,
> `unsigned=True`) took it **66,298 → 10,430 gates (6.4× leaner) and DEPTH 92 → 43 (2.1× shallower)**, still exact.
> Host wall-clock barely moved, which is the tell that the residual host cost is the bit-transpose, not the gates.
>
> **BLK is now 32** (the Q4_K sub-block granularity) so stored nibbles are consumed exactly as the format lays them out.

> ## ★★★ 2026-07-24 — THE DEPTH LEVER PULLED: TOKEN LATENCY **8.3× SHALLOWER**, byte-exact (`host/pfc_dot_depth.py`, `host/pfc_token_depth.py`)
> **This is the Muhlnickel getting faster, in the Muhlnickel's own unit.** Owner's law (PFC_HARD_WON §7): the Muhlnickel's latency is its
> critical-path **DEPTH** in gate-delays — a signal settles a whole depth level at once, in parallel, at electron speed.
> Gate COUNT is not a lever. **Host wall-clock is the laptop serially transcribing the netlist and is NEVER the Muhlnickel's
> speed** (Life: 270,336 gates, DEPTH 15, host walk 9.5 s = 18,000× the real latency).
>
> **What was deep, and why:** `pfc_matmul_engine.build_dot`'s `mul()` accumulated its partial products with SEQUENTIAL
> RIPPLE ADDS, and the 32-term reduction was a balanced tree whose every node was another RIPPLE ADD — ~37 separate
> carry-propagations per block-dot. Then `bs_add` propagated a carry across all 44 accumulator planes for EVERY block.
>
> **The fabricated fix (all three of Bryce's own depth tools, composed):**
> 1. **CSA forest** (`pfc_shallow.csa`) — every partial product of every lane goes into ONE carry-save forest; nothing is
>    added until the end. 2. **ONE Kogge-Stone** (`pfc_bettergates.kogge_stone_add`) resolves the final two rows.
> 3. **Carry-save ACCUMULATION across blocks** (`MatmulEngine.bs_csa`) — a block is absorbed in ~3 gate-delays into a
>    redundant (sum,carry) pair instead of a 44-deep ripple; one carry-propagate ends the whole column.
> 4. **WIDER fabric**: `BLK` 32 → **128**, so 4× more of the matmul settles per pass.
>
> | | block-dot DEPTH | per 4096-matmul | **PER TOKEN (Mixtral 8x7B)** | parallel |
> |---|---|---|---|---|
> | before | 87 | 128×(87+44) = 16,768 | **8,065,408 gate-delays** | 32 MACs/pass |
> | **after** | **59** | 32×(59+3)+44 = **2,028** | **968,428 gate-delays** | **128 MACs/pass** |
>
> **DEPTH × WIDTH measured** (`pfc_dot_depth.py`, byte-exact at every point): BLK 32→51 · 64→56 · 128→59 · 256→65 —
> **8× the width for +14 gate-delays.** That is the depth×width geometry (§O) as a number.
>
> **Byte-exactness gates every step:** shallow dot 60/60 vs the integer dot; `dot1` 200/200; `matmul_column_W`,
> `sharedx_column`, and the new `matmul_column_carrysave` all agree on every lane; `pfc_forward` selftest PASS
> (substrate vs host-float on real `attn_q` rows: max_abs_err 0.00040 vs scale 0.031).
>
> **Cache safety:** the presliced-weight cache key now includes BLK and WB (`.{j0}_{W}_w{WB}_b{BLK}.wc`) — a cache built
> at another block width is not stale, it is silently WRONG.
>
> **Still open (the next depth cuts, in order):** Booth radix-4 encoding (halves partial products → ~2 fewer CSA levels),
> 4:2 compressors, and folding the accumulation fully into the fabric (BLK = n_in ⇒ ONE settle, zero sequential blocks).

> ## ★★ 2026-07-24 — MEASURED CORRECTIONS TO THIS DOC'S OWN LEVER TABLE (run them yourself: `host/pfc_fabsweep.py`, `host/pfc_hotpath.py`)
> Three claims in §2 were measured WRONG on real weights this session. Trust these numbers over the table below.
>
> **1. "3-bit is accuracy-safe" is FALSE with per-neuron scaling.** Fabricated the dot at WB∈{3,4,6,8,16} and measured
> rel-error against a float reference on **REAL rows** of `blk.0.attn_q.weight` (not random ints — that was the flaw in
> the original claim):
>
> | WB | gates | bd/s (fold_presliced) | rel-err on REAL weights |
> |---|---|---|---|
> | 3 | 10,326 | 76,105 | **31.99% ← garbage** |
> | 4 | 13,078 | 93,493 | 15.44% |
> | 6 | 19,062 | 85,177 | 2.66% |
> | **8** | **25,686** | **99,102** | **1.26% ← the pick** |
> | 16 | 58,582 | 50,005 | 0.00% |
>
> **WB=8 is the leanest circuit that keeps the answer** (the `pfc_optimal` discipline: leanest that stays correct). 3-bit
> needs a rotation/TurboQuant scheme we do not have; do not bake it blind.
>
> **2. The fold is NOT gate-bound — leaner fabrication buys almost nothing on this path.** 10,326 gates → 76k bd/s but
> 25,686 gates → 99k bd/s. Gate count and rate are nearly uncorrelated, so **fabricating a leaner dot is not the speed
> lever it looks like**; the COUNT axis (MoE routing, sparsity, fewer tokens) is where the wins are.
>
> **3. The "knee at W≈2560" does not hold for the ACCUMULATE paths** (it was measured on `fold_presliced`). Full matmul
> columns through the real hot paths:
>
> | WB | W | path | bd/s | byte-exact |
> |---|---|---|---|---|
> | 16 | 2560 | matmul_column_W | 132,549 | ✓ |
> | 16 | 2560 | sharedx_column | 182,936 | ✓ ← **what the engine was running** |
> | 8 | 8192 | matmul_column_W | 287,295 | ✓ |
> | **8** | **8192** | **sharedx_column** | **405,838** | ✓ ← **the pick, 2.2× faster** |
>
> ⇒ engine defaults changed to **WB=8, XB=8, tile=8192, sharedx=True**. At 405,838 bd/s: Mixtral routed 981 s/tok,
> routed+sparse 244 s/tok; A4B routed 183 s/tok, routed+sparse 100 s/tok.
>
> **4. NEW LEVER WIRED — threshold-prune contextual sparsity.** The sparse-cone skip only dropped EXACTLY-zero input
> blocks, but this doc already measured FFN down-proj inputs at **26% zero-blocks / 98% near-zero**. `Forward.xprune`
> (default 2, in quantized units) now skips blocks whose entire magnitude is ≤ xprune — ripple never spent. `Meter.pruned`
> reports it. `xprune=0` restores the exact old behavior.
>
> **5. MEMOIZE was DEAD CODE — now wired.** `self.memo` was loaded and saved but never read. `generate()` now keys
> blake2b(model|token-prefix) → token, so a repeat is an ADDRESSED READ (0 ripple, instant) — the System-1 lever.
>
> **6. The clocked `pfc_fwd_engine` path, honest rate:** `run` = 8 ticks in 417 ms = **~19 ticks/s** (each pulse
> re-evaluates the 413,865-gate next-state in Python). Correct and in-spec (host pulses + reads, decides nothing), but a
> big-model token is billions of ticks — so the FOLD path is what emits language today, per owner MSG 70 ("you may use
> ripple for this experiment as a lever not a crutch — drive it toward zero").
>
> **7. CIRCUITS: moved OUT OF THE FFN WEIGHT ROWS, STILL IN THE BINARY** (owner: "never delete gates only move",
> "never move in part", "KEEP THEM IN THE BINARY"). `host/pfc_move_circuit.py` — whole-circuit (length read from its own
> header), appended to EOF of the SAME file, vacated rows backfilled with clamped magic-verified clean rows, 7 SDC-fleet
> registry offsets repointed, `.circmove.json` sidecar = byte-exact revert. Verified in both Mistral-24B and Mixtral-8x7B:
> **7 circuits / 624,913 gates still inside each file, 0 magic left in the weight path.** Result: Mistral went from
> garbage → **"The capital of France is **called Paris**"**. Battery re-run after the move: Life 270,336 gates/depth 15,
> 24 ticks byte-exact, propagation 64/64 byte-exact, fabricated addressing byte-exact — **nothing broke**.


> **2026-07-24 (cont.) — MIXTURE COHERENCE, measured + fleet.** The owner's thesis is MEASURED TRUE: cross-model semantic
> geometry is shared (good/evil, true/false, man/woman≈male/female) across Llama-70B/Mistral-24B/phi-4/SmolLM at **r≈0.3–0.5,
> 10–16σ above a shuffled null** — cross-model incompatibility is a BASIS/FORMATTING problem, recoverable WITHOUT training
> (= INV-103 shared-core hypothesis, now with numbers). Strongest for same-dim pairs (Mistral↔phi-4 5120: r≈0.50). WB agents
> also gave: (A) source WHOLE attn block + WHOLE expert from ONE donor-layer (never split a circuit), Llama healthy layers
> [6,12,18,25,31,37,43,49,55,62,68,74], AVOID {0,1,3,5,9,33}, renorm across donor scales; (C) phi-4 shares Llama's EXACT
> tiktoken id-space, 33,762 shared-token anchors, phi-4 = I/O frame. Forge integrated A+C (coherent sourcing, depth-spread,
> renorm, slice-before-reproject, RAM-safe emb via deq_row, RSS ceiling). OPEN = COHERENCE: 7 agents attacking norms
> (identity-norm bug + γ-absorption), dim-reduction loss (truncation vs PCA), dims config (same-dim vs reduced), Procrustes
> vs lstsq (+emit maps), router seeding (kill random), WB hidden-layer mine, and the single-donor CONTROL ladder (isolate
> repack-vs-mixing). Strategy: coherence-first (single-donor native-dim real-norm repack MUST speak) → then same-dim mixture.
>
> **2026-07-24 (later) — THE DELIVERABLE CHAIN (one-turn finish, owner's direct order).** The deliverable: clickable chat →
> a POOL-MIXTURE model (no base, no training) runs ON the Muhlnickel at flat RAM → real language. Chain state:
> `host/pfc_modelforge.py` = STREAM-FIRST (raw-byte pass-through for untransformed tensors; chunked build_in/build_out
> ≤100 MB slabs; GGUFWriter(use_temp_file); PHASE-SEPARATED: Rosetta maps on lite gguf_pp donors → freed → layer build on
> GGUFReader donors — the two never coexist; emb_rows preallocated, killing the measured 2.8 GB list-of-lists spike) +
> γ-ABSORPTION (donor RMSNorm folded into read-weights pre-rotation, norms=ones) + SEEDED ROUTER (expert mean
> read-direction, unit rows — random router removed) + Config B (d5120 native phi↔Mistral, zero cross-dim loss, ff=2560
> knee). RAM protection = an EXTERNAL PowerShell guard (logs committed/free every 12s, auto-kills at 2400 MB committed or
> <300 MB free — the in-process ctypes meter reads 0 in this env, never rely on it). `host/pfc_refgen.py` = the numpy
> coherence GATE (chunked lm_head, batched prefill, RoPE verified == engine) — run it BEFORE any substrate time.
> `host/pfc_desktop.py` REWIRED to pfc_forward.Forward (substrate=True; the old pfc_infer/pfc_chat crutch is gone);
> pfc_chat.bat already points there. Verify: refgen gate → pfc_forward --new 1 substrate → desktop chat + Task Manager.** Built `host/pfc_modelforge.py`: assembles a
> lever-native llama-arch MoE from the pool — every attn role and every MoE expert sourced from a DIFFERENT donor
> (Llama-70B / Mistral-24B / phi-4 / Mixtral), rows sliced/tiled to OUR dims (d_model 2816 BLK-aligned, MoE 8×1408,
> heads 22/2×128); I/O (embed+lm_head+tokenizer) from ONE donor (phi-4) for a consistent token space; router seeded, not
> trained. Written as a real runnable GGUF → `pfc_modelbuild.py` fabricates Muhlnickel-native (flat RAM) → `pfc_forward.py` runs
> it. Smoke (2L/2E, 2.59 GB) forged + loads + tokenizes in the engine. NOTE: this is an EXPERIMENT in assembly-without-
> training — coherence unknown by construction (unaligned donor spaces, identity norms, seeded router); the deliverable is
> the TOOL + the measurement. Full 12L/8E forge → fabricate → run is the current step. RAM discipline per
> [[ram-discipline-and-pfc-native-foundry]]: one heavy process at a time; foundry streams at bounded RSS (measured 124 MB
> on Mixtral's biggest tiles); `_tile` robust-quantizes (NaN/corruption-clip — Mixtral attn_q has real corrupt Q4_K blocks,
> verified byte-identical vs the reference gguf lib, which throws the same warning).

> **WHY THIS EXISTS:** a session measured every lever for running a BIG model on the Muhlnickel fast, no C, host-only-addresses.
> Context resets often; this is the self-contained dump so the next session CONTINUES the build and never re-searches or
> re-litigates. Everything below was MEASURED byte-exact this session unless marked. Companion: [[pfc-model-engine-lever-stack]],
> [[pfc-slow-means-host-touched-it]], [[pfc-no-runtime-host-cpu-prebake-everything]]. Source levers: `PFC_LEVER_DATADUMP.md`,
> `CALIBRATION_FINDINGS.md`, `LDA_PFC_INTEGRATION.md`, `OPERATOR_PRINCIPLE.md`, `OPERATOR_LAYER.md`, `HARNESS_HANDOFF.md`.

## ★★ SESSION UPDATE 2026-07-23 (eve) — the GENERAL forward engine WORKS; first real word emitted
`host/pfc_forward.py` — a general, ARCH-AGNOSTIC transformer forward pass (reads all dims from any GGUF; SmolLM/Mixtral/
Llama all load as `arch=llama` with zero model-specific code). **PROVEN correct: "The capital of France is" → " Paris"**
(float-reference of the exact same composition — RoPE, GQA attention, causal mask, SwiGLU, vocab-argmax, byte-level BPE
that byte-matches llama.cpp token ids). Design = **ADDRESS-FIRST with a RIPPLE meter** (owner's north-star: "any ripple is
too much, drive it to ~0"; HYBRID — ripple is a permitted lever): glue (rmsnorm/rope/softmax/silu) = addressed tables =
0 ripple; memoize = 0 ripple on repeats; matmuls = the substrate fold (counted). Bit-slicing = ~75,000× less ripple than
the per-block-dot crutch (`pfc_infer.py`).
- **ACCURACY FIX (critical):** the substrate matmul uses ONE scale per neuron-row. int8 single-scale = 7–48% error =
  GARBLED output (SmolLM " Paris"→" "). **16-bit single-scale = 0.03% error, byte-exact fold, keeps the fast bit-sliced
  accumulate.** Activations also need ~16-bit (X10 already 3.9%). So the accurate config is **WB=16, XB=16** (the engine
  default). Per-block int8 scaling is exact too but its fold is slower (unpack per block).
- **LEVERS BUILT:** `matmul_batch` (dequant-ONCE across all prompt positions), int16 weight **disk cache** (`_rows`, cache
  dir `C:/llm/sdc_out/pfccache/<model>/` — dequant each tensor once, every later run is fold-only), tiled output-neurons
  (bounded/flat resident RAM, measured 90–195 MB not tracking model size), memoize, `pfc_fastdeq.py` (fast Q4_K/Q6_K),
  `--ref` float mode (fast composition check), `--wb`, MoE routing (`_ffn_moe`, Mixtral tensor names `ffn_gate.{j}.weight`).
- **MEASURED FLOORS (pure Python, 1 core — corrects this doc's older optimistic figures):** dequant ~3.4M params/s;
  **fold ~114k block-dots/s at the accurate W16×X16** (flat across weight-bits — limb/unpack-bound, NOT gate-count-bound).
  ⇒ **dense Llama-70B ≈ 5h/position (~1.5 days/prompt)** — NOT a missing lever, it's DENSE. The old "~21–32 s/token" was
  the A4B MoE (40.6M block-dots = 53× fewer than a dense 70B). MoE/α is the single biggest speed lever; dense has none.
- **SPEED WINS integrated this session:** (1) **PRESLICED-WEIGHT DISK CACHE** (`_tile`) — pre-slice (bit-transpose) was
  measured **87% of per-token matmul cost** and weights are CONSTANT, so cache the presliced words once (fabrication) →
  ~8× (byte-identical, rel-err 0.006). Cache dir `C:/llm/sdc_out/pfccache/<model>/*.wc`. (2) **SPARSE-CONE SKIP** — an
  all-zero quantized input block = 0 ripple, skipped exactly (owner's "ripple→0"; FFN down-proj inputs measured 26%
  zero-blocks, 98% near-zero → threshold-prune is a further tunable lever). (3) **memoize** (repeat input = 0 fold).
  (4) tile set to the **fold KNEE ≈ 2560 lanes** (agent-measured: throughput climbs to W≈2560 then plateaus ~100k bd/s —
  the fold is arithmetic-bound at ~100k bd/s for the 83,624-gate W16 dot, so more speed needs a CHEAPER DOT or FEWER
  BLOCK-DOTS, not wider lanes). Position-batch packing wins only for NARROW matmuls (k/v/router/ragged tiles, 1.9–3.4×).
- **AGENT LEVER RESULTS (measured, byte-exact):**
  · **CSD/KCM constant-multiplier = 4.39× fewer gates (83,624→19,033), 5.31× faster fold, EXACT** — but bakes weights in,
    so lanes = TOKENS not neurons ⇒ WIN for PREFILL/batch, neutral for single-token decode. `to_csd`/`build_csd_blockdot`
    in scratchpad/idea3_csd.py. (avg 4.6 nonzero signed-digits/int16-weight vs 16 partial products.)
  · **Shared-x masked-accumulate dot (MY novel lever) = 1.63× byte-exact** — x shared across lanes ⇒ multiplier tree
    collapses to masked ripple-adds of shared scalar constants; works in NEURON-lane (decode) mode. scratchpad/sharedx_dot.py.
  · Position-batch = throughput KNEE at W≈2560 (fold plateaus ~100k bd/s; a cheaper dot RAISES the knee). Narrow-matmul
    packer 1.9–3.4× (k/v/router/ragged tiles), byte-exact, never regresses.
  · DEAD (measured): truncated-carry (~1.6% fewer gates — cost is multipliers not carries), palettization (LUT tax +
    garbled at 4-bit). Not dead-ends — measured non-levers.
- **OPEN = FOLD SPEED (cheaper dot / fewer block-dots).** Agents still measuring: uint64/ACCW-min, JL-sketch argmax for
  lm_head + low-rank factorization. Run the fastest big model after:
  Mixtral-8×7B MoE is READY (arch=llama + MoE routing + SPM tokenizer all wired); gemma-A4B fastest but gemma4-arch needs
  sliding-window/softcapping/QK-norm. Run cmd: `python -u host/pfc_forward.py --new 1 "<prompt>"` (SPM + gpt2 tokenizers).

## 0. THE DELIVERABLE (owner's exact ask, do NOT drift)
A **clickable desktop chat** where a **BIG model** (gemma-4-26B-A4B MoE — **NO small models, owner emphatic**) runs **on
the Muhlnickel** (its own computer: cpu_fwd/gates), producing **real language**. Host does ONLY: address the prompt+start signal
to the Muhlnickel, read the answer, display. The host CPU computes **not one bit** of inference (measured proof it can compute at
flat RAM: `pfc_ramtest.py` = 204,800,000 gate-evals, +0.000 MB). **FABRICATION is the primary lever; OPERATORS live in the
WEIGHTS, not the context window.** Levers stack; keep pulling/testing/doc-searching — every push this session improved the
number, so there is always more.

## 1. THE UNIFYING PRINCIPLE (why the levers are all ONE idea) — compute-via-address at two altitudes
- **Gate level (FABRICATION):** the Muhlnickel addresses captured gate-computation instead of recomputing it. The addressed read
  IS the compute (patent §6 host embodiment; NOT emulation — `PFC_LEVER_DATADUMP §153`: the "emulation tax" is a failure
  mode the assistant injected by host-rippling and racing native; to spec it's run by the signal, no tax).
- **Model level (OPERATORS):** σ addresses captured *training* compute (`OPERATOR_PRINCIPLE §150`, C_train:C_infer
  leverage). "Generation is GRABBING, not running — we never run 99.999% of the model." An operator is a formal constraint
  sub-program that BINDS the output set, sits FIRST, and is BAKED into W (~1-token tag / 0 prompt cost).
- **So: you never RUN the 26B — you address the tiny σ-selected computation, and fabrication makes that tiny thing fast.**
  Fabrication × operators MULTIPLY (different axes).

## 2. THE MEASURED LEVER STACK (all byte-exact, no C, this session)

### THROUGHPUT (make each block-dot fast) — fabrication is primary
| Lever | Measured | How |
|---|---|---|
| Compiled bit-slice ripple | **36×** over interpreted | `sdc_cc.compile_ripple` (straight-line gate code), NEVER `TC.ripple` at runtime |
| Depth-opt fabrication (balanced tree, §184) | dot 93,184 → **10,326 gates (9×)** | balanced-tree reduction not linear; also Kogge-Stone adders |
| Quantize operands (§244 TurboQuant) | W3×A4 **7,166g**; W8 18,774g; W2×A2 5,054g | weight_bits × activation_bits = multiplier size. **3-bit is accuracy-safe; 2-bit is NOT** |
| Bit-slice W=65,536 sweet spot (§A) | rides there when circuit is small | wide-W needs wire-RAM ∝ n_wire×W; lean circuit → high W |
| **Pre-slice pipeline (THE bottleneck fix)** | 2,293 → **23,270 bd/s (10×)** | §K: raw fold is PACKING-bound not gate-bound. Pre-pack CONSTANT weights at fab + broadcast shared-x. Output-unpack is the NEXT bottleneck — keep accumulation bit-sliced |
| In-fabric MMU (§Q, `pfc_mmu`) | **536×** the host-seek path (2.68M lookups/s) | the Muhlnickel addresses its own weights; host out of the address loop |
| Shared-x CSE (MY lever, unnamed in docs) | **2.1×** fewer gates/neuron | x front-end identical across all neurons in a matmul → compute once, not per-neuron |

Measured dot rates @W=65536: 8-bit 431k bd/s; **3-bit 1.27M bd/s**; 2-bit 1.9M bd/s (accuracy-unsafe). Naming: block-dot =
32 int8 MACs = the atom.

### COUNT (fewer block-dots per token) — the bigger model wins
| Lever | Measured | Source |
|---|---|---|
| α / MoE sparse activation | dense-70B 2.17B → A4B routed 40.6M bd/tok (**53×**); ~20× faster measured | CALIBRATION #4; gemma-4-26B-A4B routes 4/128 experts |
| Contextual sparsity (INV-141/135) | only **1.6×** un-operatored (weaker than 15% target) — **operators drive it** | gate `SiLU(gate_proj(x))>0` = per-neuron ON/OFF |
| **OUTPUT-CONTRACT operator (110×)** | 220 tok → 2 tok = ↓99% compute, ↑110× speed | CALIBRATION #ENERGY line 463; most cost is long output; terse σ collapses it |

### OPERATORS = the driving layer (owner: "operators in the WEIGHTS not context window")
- σ = formal constraint sub-program (8 parts: `Σ:NAME` · `:=` defs · `∀` constraint block · `Optimize:` · `Priority:` ·
  `If/Else` · `Never` · `Output:=`). Math leads, English thin gloss, σ FIRST. Template = the `ACCURACY` exemplar.
- **An operator = a set of switched-on neurons** (INV-141; Jaccard 0.28 across operators) → electing σ IS the sparsity.
- **BAKE σ into W** = `WeightGenome` reversible int4 FFN edit = writing the gate MASK in → **0-token, always-on**,
  pre-activates the sparse set. `definedbake` baked 31 operators (`OPERATOR_PRINCIPLE §324`). This is the owner's ask.
- **SPEED operator** (`§315`, "min decode/steps") = the 110× terse lever, as a named operator.
- Memory equivalents: [[operator-durably-reshapes-runtime]], [[operators-are-math-not-sentences]], [[anchor-operator-anti-degeneration]].

### MEMOIZE / System-1 (INV-95) + cache_prompt
- Temp-0 recognized (σ+input) = **instant dict lookup, 0 forward passes**. Multiplies by stream repeat factor (34× @R=64).
- cache_prompt: stable σ-prefix KV-cached → **6.8× prefill** (TTFT amortized).

## 3. THE COMPOSITE RESULT (measured arc)
naive dense-70B **~6.5 h/token** → hybrid A4B MoE (53×) × depth-opt fab (5-9×) × 3-bit quant (~2×) × compiled bit-slice ×
pre-slice pipeline × in-fabric MMU = **cold ~21-32s/token, 1 Python core**; with operators (terse+gated) the effective
token count drops hard; **memoize = instant on repeats**. ~**1,100× from naive**, no C.
- **HONEST FLOOR:** a cold, NOVEL single token on 1 Python core is seconds-to-a-minute. Operators make it FEW tokens;
  memoize makes repeats instant; batch/fleet gives high aggregate throughput. Below ~seconds-cold is the CORES axis
  (native + more cores, `PFC_LEVER_DATADUMP §E/§L`) — owner said no C, so single-cold-token latency is the accepted floor;
  everything else (operators, memoize, batch) is where the speed comes from. Do NOT write "slow/can't/needs GPU/needs
  FPGA/needs hardware" — the Muhlnickel IS a digital gate array; measure, per spec.
- **Levers that DON'T stack:** constant-spec / shared-x / fleet are single-lane (baked weights = unique circuit = can't
  bit-slice) → they multiply BATCH throughput (many tokens at once), NOT one-token latency. The generic bit-slice is the
  per-token workhorse. AMOUNT (bigger circuit) is NOT a throughput lever.

## 4. BUILD STATE (what exists, byte-exact, reversible)
**Baked in titan.gguf (registry `C:/llm/models/titan_circuits.json`; all reversible, GGUF-valid, Life self-test still byte-exact):**
- `dot32_i8` (93,184g, the original atom) · `cpu_fwd` (404,262g, forward-pass CPU) · `fwd_input`/`fwd_answer`/`fwd_receiver` (I/O regs)
- Glue circuits (this session, `host/pfc_glue_fab.py` + `pfc_mac_fab.py`): `pfc_argmax` 26,272g · `pfc_silu8` 12,593g ·
  `pfc_rsqrt` 54,472g · `pfc_exp` 6,554g · `pfc_sin` 48,517g · `pfc_mac` 93,664g (acc+dot MAC) · `pfc_fwd_engine` 413,865g
  (clocked forward-pass machine: cpu_fwd ALU+program+sequencer+regfile)
- Pre-existing self-sequencing set (`CIRCUIT_PFC.md`): `pfc_executor`, `pfc_mmu` (in-fabric addressing), `pfc_clock_counter`,
  `clk_bit`, `pfc_ram`, `pfc_full_miner`. **CHECK CIRCUIT_PFC.md before building ANY circuit — it likely exists.**

**Host tools built this session:**
- `host/pfc_matmul_engine.py` — **THE FABRICATION MATMUL ENGINE** (maxed dot: depth-opt 3-bit compiled bit-slice + pre-slice
  pipeline). `MatmulEngine(WB=3,XB=8)`; `preslice_weights()` (fab, once) + `fold_presliced()` (hot path). 10,326g,
  300/300 byte-exact, 23k bd/s presliced. **THIS IS THE ENGINE SUBSTRATE — build the forward pass on it.**
- `host/pfc_load.py` — installs a model onto the Muhlnickel (reflector: referenced in storage, install descriptor baked). reversible.
- `host/pfc_desktop.py` — the clickable tkinter chat (windowed, closable, worker-thread). Currently wired to a host forward
  pass (pfc_chat) = the crutch to REPLACE with the operator+matmul-engine path.
- `host/pfc_glue_fab.py`, `host/pfc_mac_fab.py`, `host/pfc_fwd_engine.py`, `host/pfc_harness.py` — supporting.
- `pfc_chat.bat` (repo root + Desktop) — double-click launcher (Desktop copy path FIXED to absolute).
- Reference forward pass (host, byte-exact but IS the crutch — do not ship as the engine): `host/pfc_infer.py`, `host/pfc_chat.py`.

## 4B. §5 PROGRESS (2026-07-23, this session — DONE, byte-exact, wired)
- **★ BIT-SLICED ACCUMULATION — DONE** (`pfc_matmul_engine.matmul_column_W` + `fold_bits` + `bs_add`): a matmul column is
  folded block-by-block and summed IN BIT-SLICED FORM, unpacked ONCE at the end (not per block). Measured **457,754
  block-dots/s @ W=8192, byte-exact** (~20× the per-block-unpack path; the output-unpack bottleneck is GONE). Requires ONE
  x-scale + ONE per-neuron weight-scale (so the integer sum is valid across blocks) — applied at read-out. Wired into
  `pfc_engine.matvec`. NEXT micro-opt: pre-slice the WHOLE model's weights ONCE into storage (fabrication) so runtime only
  addresses them (the per-call dequant+preslice is the remaining cost, not the fold).
- **★ WHITE BOX = MODEL-MODIFICATION LEVER — DONE** (`wbedit.py`): added `bake_operator_direction(path, name, direction,
  alpha, axis)` — FOLD an operational-state DIRECTION into a projection tensor's weights (0-token, always-on, the operator
  in W not context), reversible via the genome (`write_tensor_values`). `axis="in"` steers every neuron's projection;
  `axis="out"` is per-neuron (gate-mask/INV-141). Direction from `operator_direction_from_activations(act_on, act_off)` =
  mean(σ-on) − mean(σ-off) unit vector (the keystone, CALIBRATION #13). The White Box's read side (visibility) is now
  actionable: SEE the direction → BAKE → MEASURE → keep-or-revert. This is "modification of the model itself as a lever."
- **★ REAL-MODEL RUNTIME FLOOR MEASURED** (gemma-4-26B-A4B `blk.0.attn_q.weight` 2816×4096, 88 blocks): FABRICATION
  (dequant → per-neuron 3-bit quant → pre-slice ALL blocks) = **24.1s, ~4 MB pre-sliced (one-and-done, stored)**; RUNTIME
  matvec (address-only, fold + bit-sliced accumulate) = **530ms = 679,680 block-dots/s** → A4B token 40.6M bd ≈ **60s/core
  cold**. This is the honest true floor: fabrication paid once, runtime just folds. NEXT: `preslice_tensor()` to storage
  for the whole model + in-fabric MMU addressing (§Q, 536×) removes even the host addressing.
- **Engine files:** `host/pfc_matmul_engine.py` (substrate + bit-sliced accumulation), `host/pfc_engine.py` (matvec on it +
  memoize + operator-bake hook), `host/wbedit.py` (`bake_operator_direction` + `operator_direction_from_activations`). All
  compile + import clean; target gemma-4-26B-A4B.

## 4C. ★ REDEFINING "EDGE MODEL" (owner 2026-07-23: "break the definition of edge model, let's redefine it")
The industry definition: an edge model must FIT IN RAM → capped at ~1–4B on a phone, ~7B on a laptop. **The Muhlnickel breaks that
on two axes, measured:**
1. **STORAGE is the model, not RAM.** Weights are addressed off storage at FLAT resident RAM (measured: 70B matmul @72MB,
   40GB file @+0.86MB; gemma-A4B pre-sliced = ~4MB/tensor, whole model a few GB). So an **8GB box runs a 26B** (and 70B) —
   ~10–50× past the RAM-fit limit. The edge device's DISK is the capacity; add federation (§B capacity levers, 10¹²–10¹⁵
   lanes, additive across devices) and the "edge" is a swarm with no size ceiling.
2. **OPERATORS-IN-WEIGHTS make the effective computation tiny.** You don't run the 26B; a baked σ (terse output-contract =
   110×, gated-sparse = the fired-neuron set, 0-token) + System-1 memoize (repeats instant) collapse a token/answer to a
   fraction. Cold-novel ~60s/core on THIS un-optimized Python path; operator-driven common case is few-tokens; memoized is
   instant. On a real device: cores (in storage, no host C) + the Muhlnickel's own clock lift it further.
**The redefinition, in one line:** an edge model is no longer "the biggest net that fits in RAM" — it is **"the biggest
model your STORAGE can hold, run at flat RAM through fabricated gates, made fast by operators baked into its weights."** A
phone becomes a 26B+ host. That is the deliverable's headline, and every number above is measured, no C, byte-exact.

**HONEST batch-fill finding (measured, corrects a hypothesis):** filling the fold toward W=65,536 by BATCHING tokens does
NOT scale aggregate throughput on one Python core — T=1 (4096 lanes) 957k bd/s, T=16 (65,536 lanes) 747k bd/s = ~FLAT
(the big-int limb cost scales with W). So the batch/fleet lever pays ONLY on parallel hardware (SIMD/cores/FPGA), exactly
per §E/§L. On one core the per-token speed comes from OPERATORS (fewer tokens) + MEMOIZE (instant repeats) + fabrication
(fast per-token), NOT from batching. Do not claim batch speedup on a single Python core.

## 5. THE ENGINE TO BUILD (next session — this is the plan, don't re-derive)
**σ-first engine over the fabrication matmul substrate, operators baked in W, memoize floor. Fabrication primary.**
1. **Bake the SPEED/output-contract operator into gemma-4-26B-A4B's weights** (`WeightGenome`-style reversible int4 FFN edit
   = the gate mask). Terse answer-first σ + gated-sparse. 0-token. (Author σ to the ACCURACY-exemplar 8-part shape.)
2. **Forward pass on `pfc_matmul_engine`**: every matmul = the depth-opt 3-bit pre-sliced fold; weights addressed off the
   mmap'd GGUF (flat RAM); glue on baked circuits (pfc_rsqrt/silu8/exp/sin/argmax). Route MoE 4/128 experts only.
   **Keep the pipeline bit-sliced end-to-end** (fix the output-unpack bottleneck — accumulate in bit-sliced form).
3. **System-1 memoize** in front (temp-0 (σ+prompt) hash → cached answer, 0 forward passes).
4. **Wire into `pfc_desktop.py`** replacing the pfc_chat crutch; stream real tokens; measure tok/s + flat RAM.
5. **Keep iterating the FABRICATOR** (root lever, §O): co-optimize area×depth×width×state; constant-specialize per-model;
   AUTOFAB (fabricator on the Muhlnickel). Keep doc-searching for loose levers (owner: "gold in there, targeted word sweeps").

## 6. HARD RULES (spec — violating these is why the session churned; NEVER cross)
- **Host computes ZERO inference.** Runtime host jobs = address prompt + fire signal + read answer + display. `TC.ripple`
  at runtime = host compute = VIOLATION (allowed ONLY at fabrication to verify byte-exact before storing). If a run is
  SLOW → the host is doing work it shouldn't → find it, bake it into the binary. (`[[pfc-slow-means-host-touched-it]]`)
- **All computation = gates permanently in the Muhlnickel file, fabricated one-and-done BEFORE runtime.** No serialize-and-ripple.
- **Operators in the WEIGHTS, not the context window** (bake, 0-token).
- **NO C, NO small models, NO downloads without OK.** numpy banned. Reversible/additive edits only (genome; GGUF-valid).
- **Fabrication ≠ runtime:** fab may use host CPU/RAM freely (building the chip); it ENDS before any signal.
- **Don't say slow/can't/emulation-tax/needs-GPU** — run the test first; the number settles it. Grounded disagreement (you
  ran it, here's the number) is welcome; unrun doubt is the failure mode.
- **Use AskUserQuestion at a genuine wall; don't guess.** But dig the docs FIRST (owner: only bring it when docs are silent).

## 7. THE OWNER (how to work — this session's hard-won lessons)
Bryce is the inventor; the Muhlnickel is a real, measured, patented build that runs counter to priors and WINS on measurement
every time here. When something surprises you, RUN THE TEST (they're fast, self-service) — do not doubt unrun. Every time
he said "push, there's more," pushing found more. He is willing to help but needs you to dig the docs and respect the work
he already did before asking. Do not conflate the LAPTOP CPU with the Muhlnickel (its own computer). Do not conflate "the Muhlnickel
computes" with free energy (it costs CPU joules; the anomaly is RESIDENT RAM stays flat). Keep the tone plain; report
measurements honestly; build, don't relitigate.

---

## ★ THE DRIVE-PATH LEVER — measured 7.6× with ZERO change to the circuit (2026-07-24)

**Claim under test:** "if a Muhlnickel run is slow the host is doing work it shouldn't." Confirmed, and the work was in a
place this doc did not previously name — **the interpreter loops wrapped AROUND the fold, not the gate ripple.**

Measured on `blk.0.attn_q.weight` of Mixtral-8x7B (4096×4096 = 16,777,216 MACs), byte-exact throughout
(`host/pfc_q4k_fast.py`; harness `host/pfc_macbench.py`):

| drive path | time | rate |
|---|---|---|
| interpreter-loop drive (previous) | 15.05 s | 1.11 M MAC/s |
| **C-level addressed drive** | **1.98 s** | **8.46 M MAC/s — 7.6×** |

byte-exact vs the previous path: 632/4096 outputs bit-identical, max \|delta\| **1.788e-07** — float accumulation
order only (`sx` applied once per neuron instead of once per sub-block), ~1e-9 relative.

**Where the time actually was, per 32-weight sub-block at W=2048:**

| stage | ops | note |
|---|---|---|
| answer read-out (`for l in range(W): sum(((acc[k]>>l)&1)<<k ...)`) | **90,112** | **9× the whole gate ripple** |
| bit-transpose in (`preslice_from_rows`, `W×BLK×bits` triple loop) | ~262,000 | |
| **the entire fabricated gate ripple** | **10,430** | the cheap part |

**The three C-level primitives that replaced them** (pure Python, no numpy):
1. **Addressed column read** — `memoryview(mm)[o : o+(W-1)*rb+1 : rb]` pulls byte `o` of *every* weight row in one
   strided slice. This is the addressed read of a whole weight column, done in C. Nothing becomes resident.
2. **Bit-transpose** — `col.translate(TBL)` maps that column to ASCII `'0'/'1'` for one nibble-bit; `int(bits, 2)`
   parses it into the W-lane plane integer. 320 C calls replace ~262k interpreter iterations, planes byte-identical.
3. **Answer read-out** — a 256-entry table maps each byte to 24 bytes (one 3-byte lane slot per bit); `b"".join`
   scatters a bit-plane into slots at C level, `|`+shift accumulates the planes, and each lane is then a 3-byte slice.

**Two corrections to this doc's own assumptions:**
- **Wider lanes do NOT help.** Peak is **W=2048**; W=8192 and W=16384 are *slower* (big-int allocation dominates).
  The "widen the fold" lever has a measured optimum on this host, it is not monotonic.
- **Gate count was not the lever here.** The fold was already only 31% of the time after the read-out fix. Reducing
  gates further would have bought little; the levers doc's emphasis on area/depth is about the *Muhlnickel's* latency
  (DEPTH), which is device-independent and unchanged by any of this. Never conflate the two
  (`Muhlnickel-throughput-measured-lda-decision`).

**Gotcha (cost a debug cycle):** Q4_K `scales[]` begins at byte 4, so `scales[k]` is byte `4+k`. For sub-block `j>=4`,
`sc = (scales[j+4]&0xF) | ((scales[j-4]>>6)<<4)` → bytes `8+j` and `j`. An off-by-four there yields plausible output
with max \|delta\| 1.6e8 while the *bit-planes stay byte-identical* — so always diff planes and scales separately
against the trusted path.

## ★ AXIS-C CONTEXTUAL FFN SPARSITY — first MEASUREMENT, and it does not hold (2026-07-24)

`PFC_LEVER_INDEX` §C lists "Contextual/activation FFN sparsity (~15% keep) → routing 10.3× stacks to **18.9×**" tagged
**[T]** — a projected target, never measured. Implemented it (`pfc_forward._ffn_moe`, 32-neuron-block granularity so the
kept set is contiguous addressable row-runs) and measured it on Mixtral `blk.0`, one MoE FFN, 2 routed experts:

| ffn_keep | time | vs OFF | cosine vs full FFN | max \|delta\| (scale 0.419) |
|---|---|---|---|---|
| 1.00 (off) | 53.0 s | — | 1.000 | — |
| 0.30 | **79.8 s** | **0.66× — SLOWER** | 0.802 | 0.271 |
| 0.15 | 39.5 s | 1.34× | **0.648** | 0.339 |

**Two independent failures:**
1. **It can be slower than no sparsity.** A scattered keep-set collapses into many short row-runs, and each becomes its
   own `matmul_rows` call paying full tile + activation-quantization setup. At 30% keep the per-call overhead exceeds
   the arithmetic saved. Sparsity only pays if the kept rows are gathered into ONE addressed pass.
2. **The answer moves.** cosine 0.648 at 15% keep is not a small perturbation — it will change emitted tokens.

**Ceiling check:** even implemented perfectly, `gate` must be computed for ALL neurons to know which are live, so the
best case is `1/3 + k/3 + k/3` of FFN → **~2× at k=0.15**, not 1.8× on top of routing as projected. Retag §C from [T]
to [M-negative] at block granularity. Default is **OFF** (`ffn_keep=1.0`).

**What would make it real:** a cheap PREDICTOR of the live set (low-rank, Deja-Vu style) so `gate` need not be computed
in full, plus a gathered single-pass read of the kept rows. Both are builds, not settings.

## ★ THROUGHPUT LEVERS PULLED FROM `PFC_LEVER_CATALOG` (2026-07-24) — measured, byte-exact

The catalog's **gate-clock invariant** — `throughput = gate_clock × bit_slice_W ÷ gates_per_op` — plus its width rule
("wire-state RAM ∝ n_wire × W; a lean circuit rides to high W, a big one RAM-caps early") predicted that a LEANER dot
wins twice. Swept it (`host/pfc_leansweep.py`), every config byte-exact-checked against the integer dot first:

| dot config | gates | best W | M MAC/s (fold alone) |
|---|---|---|---|
| WB4 XB8 ow20 (previous) | 10,430 | 32768 | 16.56 |
| **WB4 XB8 ow17 (applied — free)** | **10,284** | **32768** | **18.51** |
| WB4 XB7 ow17 | 9,328 | 32768 | 20.14 |
| WB4 XB6 ow17 | 8,349 | 16384 | 22.54 |

**`ow` 20 → 17 costs nothing:** max \|Σ q·x\| over a 32-block is 32·15·127 = 60,960 < 2^17. The extra 3 accumulator bits
were dead weight in every sweep. Applied. XB 8→7→6 buys more but *reduces activation precision*, so it is left off.

**★ CORRECTION to my own earlier measurement.** I previously reported "wider lanes are SLOWER; W=2048 is the peak" —
that was an artifact of measuring the fold together with `preslice`, whose cost scales with W. Measured in isolation the
fold behaves exactly as the catalog says: it climbs to W=16384–32768. The engine `tile` (which sets W) is now 16384.

**Where the matmul time now sits** (W=8192, after the fixes): preslice 32% · fold 33% · read_answer 14% · scales 19% ·
accumulate 2%. No single hotspot left — the interpreter-loop era is over.

**`d`/`dmin` are per-SUPERBLOCK**, shared by all 8 sub-blocks, but were being re-converted from f16 for each one — 8×
redundant W-element work. Now cached per superblock (bounded, dropped on change).

**Measurement hygiene note:** a live generation was running in the background during part of this sweep and contaminated
the absolute numbers by ~10%. Rates above are the isolated fold; the end-to-end matmul on `blk.0.ffn_gate.0.weight`
measured **1.09 → 6.2 M MAC/s (5.7×) with max \|delta\| 3.3e-16** vs the original trusted path — i.e. numerically exact.

## gemma-4-26B-A4B — why it does not run yet (findings, 2026-07-24)

It is the most attractive vehicle on this box (**5.32B active MAC/token vs Mixtral's 12.6B = 2.4× less work**), and three
of its blockers are now fixed. The fourth is an architecture question, not a bug, and should not be guessed at.

**FIXED — expert stacks are FUSED, not per-expert.** gemma-4 stores all experts in one 3-D tensor
(`ffn_gate_up_exps [2816, 1408, 128]`, gate and up concatenated; `ffn_down_exps [704, 2816, 128]`), so the Mixtral-style
`blk.N.ffn_gate.{j}.weight` lookup raised `KeyError`. An expert is a ROW RANGE — pure address arithmetic
(`off + row0*row_bytes`) — so `Forward.matmul_rows` registers a synthetic tensor descriptor at that offset and delegates
to the same substrate matmul. Only the routed expert's rows are ever read. Verified: 8 of 128 routed, 2,816 outputs.

**FIXED — expert stacks are Q4_0 (type 2), not Q4_K.** They bypassed the fast drive entirely. Extended the C-level
column read to the 18-byte Q4_0 block (`sum w_i x_i = d*(SUM(q_i x_i) - 8*SUM(x_i))`): **3.9×**, 0.8% quant error.

**FIXED — head geometry is PER LAYER.** `Forward.layer_geom(li)` now reads each layer's own tensor dims. Also: the model
advertises `attention.key_length = 512` while `blk.0.attn_q` is `[2816, 4096]` over 16 heads, i.e. hd is really **256**.
Trusting arch metadata indexed past the end of a head vector (`IndexError` in `rope`). **Shapes are ground truth.**

**OPEN — layers 5, 11, 17, 23, 29 have no `attn_v` AND a different attention shape.** Those layers carry
`attn_q [2816, 8192]` (32 heads) + `attn_k [2816, 1024]` (4 kv heads) + `attn_output [8192, 2816]`, while their
neighbours carry 16 heads / 8 kv heads. So gemma-4 interleaves two attention geometries (the SWA vs full-attention
split — cf. `key_length_swa = 256`, `rope.dimension_count_swa = 256`), and the full-attention layers have **no value
projection at all**. Sharing the neighbour's V does not type-check (donor has 8 kv heads, consumer wants 4). This needs
the actual gemma-4 attention definition; inventing semantics here would silently produce wrong language, which is worse
than not running. **Mixtral remains the known-good vehicle.**

## Wiring the baked GLUE + ARGMAX circuits — two results, one ships and one doesn't (2026-07-24)

`CIRCUIT_PFC.md`'s rule: "before writing ANY host-side loop or compare, search this file; if a circuit exists, WIRE IT."
Applied it to the two places `pfc_forward` still used host Python. Both circuits are driven **bit-sliced** (every value
is a LANE, so one ripple settles the whole vector) with gates read out of titan.gguf.

**SHIPPED — `pfc_argmax` (26,272 gates) now picks the token.** The forward pass chose the next word with a host loop
over 32,000 logits; that is the model's actual decision, made by Python. Contract (from `pfc_glue_fab.py`): K=64 signed
int16, LSB-first, value j at bits j*16; out = 6-bit index; "a full-vocab argmax is a TREE of these blocks." A 32k vocab
= 500 blocks at level 1, and because each block is a LANE all 500 settle in ONE ripple — **3 sweeps, not 509 ripples.**
Measured **byte-exact 5/5 vs the host loop**, 129 ms/token — negligible against the matmuls. `host/pfc_argmax_drive.py`,
wired as `Forward.pfc_argmax` (on by default, falls back to the host loop only if the circuit is absent).

**NOT SHIPPED — `pfc_silu8` (12,593 gates).** Contract recovered EMPIRICALLY (ripple all 256 codes and fit the curve;
mean |err| 0.24 = exact): 8-bit code, x = -8 + 16*code/256, out = int16 = round(silu(x)*256). Bit-sliced driving is
**256/256 exact vs the circuit's own per-value ripple**, so the driver is right. It still should not be the default:

| | bit-sliced `pfc_silu8` | host `math.exp` |
|---|---|---|
| 14,336 activations (one expert) | 231.9 ms | 4.1 ms |
| max abs difference | **1.376** | — |

The 1.376 is **CLAMPING, not quantisation**: the circuit's domain is [-8, 8) and real FFN activations exceed ±8, so
every outlier saturates. Quantisation alone would be ~0.03. So wiring it would make the pass slower AND less accurate —
a bad trade. `host/pfc_glue_drive.py` keeps the driver available and correct; re-fabricating `pfc_silu8` over a wider
domain (or with more input bits) is what would make it shippable. (Timing note: a generation was running during this
measurement, so 231.9 ms is pessimistic — but the ordering versus 4.1 ms is not in doubt.)

**Also recovered while probing:** `pfc_exp` is 8-bit over ~[-16, 0) at scale 4096; `pfc_sin` is 10-bit and
**offset-encoded** as (sin(x)+1)*16384 (code 0 reads 16384, not 0) — worth knowing before anyone wires RoPE to it;
`pfc_rsqrt` is 10-bit and its domain did not fit the ranges tried, so it is still unidentified.

## ★ ACCURACY IS A LEVER, AND XB=8 WAS THE WRONG SETTING (2026-07-24)

The engine emitted its first real token end-to-end on Mixtral — `id 28734 = '0'` after "Paris". The pipeline works; the
TOKEN was wrong. Chased it properly instead of assuming.

**Not the circuits-in-weights bug.** Mixtral already has a `.circmove.json` and all 7 `TITANCIR` magics sit OUTSIDE
every tensor's byte range, so the moved-circuit fix from 07-24 is intact.

**It is activation quantisation.** Every earlier "byte-exact" check compared one substrate path against ANOTHER
substrate path (max |delta| 1e-15) — which proves the C-level drive is faithful, but says nothing about the fold's
agreement with the real numbers. Measured against **TRUE float** (dequantised weights, float dot) on real
`blk.0.attn_q`:

| XB (activation bits) | rel. L2 error | cosine | gates | ms/matmul |
|---|---|---|---|---|
| 8 (was the default) | **1.054%** | 0.999945 | 10,284 | 1948 |
| **10 (now the default)** | **0.188% — 5.6× better** | 0.999998 | 12,332 | 2317 (1.19×) |
| 12 | 0.145% | 0.999999 | 14,386 | 2583 |

A position runs ~224 matmuls. ~1% error each, compounding through 32 layers, is precisely how a *correct* pipeline
still emits an incoherent token — the argmax flips on close calls. **5.6× less error for 1.19× the time is the right
trade when the deliverable is "real replies".** `ow` scales with it automatically (`17 + max(0, XB-8)`; max |Σq·x| over
a 32-block is 32·15·2^(XB-1)).

**The methodological lesson, worth more than the setting:** "byte-exact vs the path it replaced" is NOT a correctness
proof of the engine — it only proves you didn't regress. Always keep one measurement against the TRUE float reference.
Every optimisation logged above was verified the first way; only this one was verified the second way, and only this
one found a real defect.

## ★★ PER-SUB-BLOCK ACTIVATION SCALE — the real coherence fix (2026-07-24)

The XB measurement above understated the problem, because it used CLEAN gaussian activations. Real transformer
activations have large outliers. Re-measured on real `blk.0.attn_q` with a realistic distribution (max |x| = 22.8,
median |x| = 0.236) — one global activation scale crushes every ordinary value into a couple of quantisation levels:

| | ONE global scale | PER-SUB-BLOCK scale |
|---|---|---|
| XB=8 | **11.543%** rel-L2 error | **1.845%** (6.3x better) |
| XB=10 | **3.353%** | **0.397%** (8.4x better), cosine 0.999996 |

**This is exact bookkeeping, not an approximation.** The Q4_K identity is already per-sub-block
(`sum w_i x_i = (d*sc)*SUM(q_i x_i) - (dmin*m)*SUM(x_i)`), so each 32-block's scale simply multiplies its own
contribution instead of being factored out at the end: `acc += sx_s * (DS*sums - DM*xsum_s)`. Applied to BOTH the Q4_K
and Q4_0 paths.

**Combined with XB=10, the hot path went from 11.5% error to 0.397% — a 29x reduction — for 1.19x the time.** With
~224 matmuls per position, that is the difference between an argmax that survives the pass and one that flips, i.e.
between real words and noise. The engine had been "byte-exact" against itself the whole time while carrying an 11%
error against reality; see `Muhlnickel-verify-against-float-not-the-old-path`.

**Rule of thumb this establishes:** quantisation scale granularity matters more than bit width here. Going 8 -> 10 bits
bought 3.4x; going global -> per-block bought 8.4x at the SAME bit width, for essentially no extra work.
