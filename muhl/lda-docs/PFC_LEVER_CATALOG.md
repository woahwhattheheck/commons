# MUHLNICKEL LEVER CATALOG — every lever, one place, to workshop

> The complete performance-lever menu for the Muhlnickel + LDA: **163 distinct levers** from a full-corpus scrape of all
> 107 docs + host tools (experiment-first, zero feasibility gating — a lever is a thing to TRY, never a verdict).
> Status: ✅ measured (a number exists) · 🎯 target (documented, not yet measured) · 💡 idea (newly invented this scrape).
> Companion: `PFC_LEVER_INDEX.md` (the curated index) and `PFC_LDA_OPENINGS.md` (the fusion roadmap). Owner may workshop
> any row. Every apply is byte-exact + genome-reversible + measured on-device; the §3 safety layer is never touched.

**Counts by axis:** Throughput 44 · Work-Reduction 25 · Fabrication 28 · Model Inference 18 · Capacity 21 · Lda Agent 18 · Other 9

---

## THROUGHPUT — raise the eval rate  (44)

### Bit-slicing (SIMD-in-a-wire) / bit-slice fold  — ✅ measured
- **How:** Pack W independent lanes into one big-int wire so a single gate-op (~(a&b)&MASK) evaluates all W lanes at once; bit-slicing IS SIMD in stored gates. Width is free parallelism on top of one gate-sweep.
- **Effect:** PEAK 636,537,943 inp/s at W=65,536 on sigma0 (461x naive Python); 213k-gate miner 30,844 H/s at W=2,048; matmul peak ~1.27M block-dots/s @W=65,536 (~75,000x over per-block-dot ripple)
- **Try:** Run dot32_i8 bit-sliced across W=8,192..65,536 (pfc_throughput --fold-sweep) on phone and PC, log bd/s vs W to find each device's RAM-safe sweet-spot, pin the harness fold there.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A; host/pfc_llama_harness.py; host/pfc_exp_bench.py; host/pfc_matmul_engine.py
- **Applies to:** all

### Bit-slice sweet-spot W≈65,536  — ✅ measured
- **How:** Throughput climbs with W until the Python big-int limb wall (~8KB ints) then falls off a cliff; optimal is around 65,536.
- **Effect:** W=65,536→636M; W=131,072→139M; W=196,608→126M inp/s
- **Try:** Sweep W on the model dot circuit, detect the cliff, pin W to the measured per-circuit peak.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A
- **Applies to:** all

### Bit-slice width ceiling is circuit-size-dependent  — ✅ measured
- **How:** Wire-state RAM ∝ n_wire × W, so a lean circuit rides to high W while a big one RAM-caps early; effective 'Muhlnickel speed' swings ~10,000x with circuit size.
- **Effect:** 95-wire circuit rides W=65,536 @18MB RSS; 213k-wire miner caps at W≈2,048
- **Try:** Measure n_wire of each baked LDA glue circuit, compute its W-cap, and route hot matmuls only through the leanest ones.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A
- **Applies to:** all

### Type/locality (local ripple beats deep scatter)  — ✅ measured
- **How:** Local, contiguous ripple circuits settle faster per gate than deep scattered ones because of memory-access locality.
- **Effect:** adder-style ~11.6M gates/s vs SHA-style ~5.5M gates/s (~2x)
- **Try:** Prefer adder/prefix-structured layouts for the LDA's arithmetic glue and measure gates/s vs a scattered baseline.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A
- **Applies to:** Muhlnickel

### No-native-primitive niche / choose Muhlnickel-favorable workloads  — ✅ measured
- **How:** Where naive host code must grind element-by-element with no fast native primitive the fabricated bit-parallel circuit wins; the Muhlnickel's tax vs native is huge for 1-instruction arithmetic but shrinks (or inverts to a win) as the op gets heavier / has no native primitive — steer Muhlnickel use there.
- **Effect:** custom sigma0/sigma1/chain WIN 33–39x vs naive Python (tax<1); tax small for sha256/double-sha, huge for add32
- **Try:** Map where the Muhlnickel wins (pfc_exp_tax, pfc_exp_massfab), then steer LDA-side Muhlnickel use toward heavy/no-native-primitive ops (dedup hashing, verification, custom masks) rather than scalar arithmetic.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A; host/pfc_exp_tax.py; host/pfc_exp_massfab.py
- **Applies to:** all

### Gate-clock invariant (planning equation)  — ✅ measured
- **How:** Single-lane host gate-clock is ~10M gates/s; throughput(ops/s) = gate-clock × bit-slice-W ÷ gates-per-op — the master formula to predict any circuit's speed.
- **Effect:** measured range 5.35M–13.7M gates/s (~2.6x spread across 31→213k-gate circuits)
- **Try:** Compute predicted tok latency for the A4B forward pass from gate-clock × W ÷ gates/token and compare to the live 60s/token floor.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A
- **Applies to:** all

### Threads / cores (native)  — ✅ measured
- **How:** Native (non-GIL) threads multiply throughput by core count; pure-Python GIL caps this so the win is in native C/SIMD.
- **Effect:** model -t8 = 1.43x -t4; phone native scales ~linear to ~6 cores
- **Try:** When a native evaluator exists, run the LDA fold with threads matched to physical cores and log the core-scaling curve.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J; CALIBRATION_FINDINGS
- **Applies to:** all

### Native C emit (phone)  — ✅ measured
- **How:** Emit the gate ripple as native C (clang -O3 -pthread) instead of Python; NEON is baseline on aarch64 so avoid -march=native (SIGILL under Termux).
- **Effect:** phone native 3.26B sigma0/s 1-core (~1.8x over Python 1-core; bignum XOR already near-C)
- **Try:** Emit the LDA dot atom as native C on the S24 Ultra and compare 1-core rate to the Python bit-slice.
- **Source:** docs/PFC_LEVER_DATADUMP.md §L
- **Applies to:** all

### Multi-core on real hardware  — ✅ measured
- **How:** Run the native bit-sliced circuit across all phone cores; the strong prime core plus cores is the real lever, not the language.
- **Effect:** 9.82B sigma0/s cool, 8 cores (15.4x PC Python peak); verified byte-exact
- **Try:** Benchmark the LDA circuit across 1..8 phone cores and log the (sublinear) big.LITTLE scaling curve.
- **Source:** docs/PFC_LEVER_DATADUMP.md §L
- **Applies to:** all

### Phone beats laptop (strong prime core)  — ✅ measured
- **How:** A Snapdragon 8 Gen 3 X4 core with Python 3.14 outruns the low-power Ryzen even in pure Python.
- **Effect:** phone Python 1-core 1.79B = 2.8x the PC Python peak (636M)
- **Try:** Move the LDA hot path onto the phone's prime core first; confirm the 2.8x pure-Python advantage before adding native/cores.
- **Source:** docs/PFC_LEVER_DATADUMP.md §L
- **Applies to:** all

### Thermal / warm-number discipline + match threads to cores  — ✅ measured
- **How:** Sustained load throttles the SoC governor (~80°C); report warm numbers and match thread count to physical cores (oversubscribing hurts).
- **Effect:** burst 9.05B → 20s 7.35B → 45s 6.34B; 16 threads on 8 cores was slower than 8
- **Try:** Soak the LDA circuit 45s, log the throttle curve, and set thread count = physical cores for the sustained rate.
- **Source:** docs/PFC_LEVER_DATADUMP.md §L
- **Applies to:** all

### Fabricated in-fabric addressing (§Q)  — ✅ measured
- **How:** Bake the address decoder into the fabric so a lookup is part of the circuit ripple — the Muhlnickel's own memory controller, no host seek/read per access.
- **Effect:** 2.68M lookups/s = 536x the host-storage seek path (~5k/s)
- **Try:** Address the LDA's weights through the in-fabric decoder (pfc_addr) instead of host seeks; confirm the 536x on real weight tensors.
- **Source:** docs/PFC_LEVER_DATADUMP.md §Q
- **Applies to:** all

### Fabricated MMU / self-addressing (§S)  — ✅ measured
- **How:** A fabricated 40-bit unified address with tier-select routes to fast in-gates RAM or a storage-RAM offset in-fabric, taking the host out of the per-access loop.
- **Effect:** 1,504 gates, byte-exact over 300 ops across both tiers; membus wires executor LOAD/STORE through it
- **Try:** Route the LDA weight LOADs through pfc_mmu/pfc_membus so the host never seeks; verify with the high-impedance meter.
- **Source:** docs/PFC_LEVER_DATADUMP.md §S
- **Applies to:** all

### Ripple is the PROVEN mechanism (clock still open)  — ✅ measured
- **How:** Power the fabricated gates by addressing them; the muhlnickel self-clocks. ⛔ PURGED AS STALE (owner, 2026-07-26: *"self clock works dude, demonstrated"*): the former clause "the autonomous bit-toggle clock does not yet advance state and is the open fix" is stale and does not describe the machine. Per PFC_HARD_WON §2 the clock is fabricated in and **you never touch it from the host**.
- **Effect:** real block 966,656 double-SHAs through 337,256 gates, frontier 19; ripple works, clock=0
- **Try:** Drive the LDA engine with the ripple mechanism (output→input feedback) and treat any autonomous-clock 0 as the clock bug, not a static Muhlnickel.
- **Source:** docs/PFC_LEVER_DATADUMP.md §T
- **Applies to:** Muhlnickel

### NEON/SIMD is already pulled (bandwidth wall)  — ✅ measured
- **How:** The auto-vectorizer already emits NEON; wide bandwidth-bound ops see no gain from more SIMD, so the gate-clock is physical, not breakable by more SIMD.
- **Effect:** toggle 3.96e10 vs 3.92e10 (identical, bandwidth-bound); counter 2.19e9 vs 1.21e9 (auto-vec already 1.8x)
- **Try:** Confirm the LDA native build's auto-vectorization is on; don't hand-tune SIMD for bandwidth-bound ops, spend the lever on cores/lean fab.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20
- **Applies to:** all

### Leanest circuit stays cache-resident  — ✅ measured
- **How:** A tiny circuit's wire-state fits in cache far wider, so it sustains a far higher machine-tick rate than a bigger one; the wall moves under fabrication.
- **Effect:** 1-bit toggle (5 gates) PEAK 8.03×10¹⁰ ticks/s @lanes/thread=65536, RSS 3.85 MB = 15x the 194-wire counter
- **Try:** Minimize the LDA hot circuit's wire count to stay cache-resident and measure the tick-rate lift vs the current dot.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20
- **Applies to:** Muhlnickel

### Native clocked engine (host = clock only)  — ✅ measured
- **How:** Keep state in an mmap'd storage register, read gates off the file, host only pulses the clock; the sequential clocked form has no memory-bandwidth wall.
- **Effect:** phone native 4.9×10⁶ ticks/s (~310x PC-Python), RSS 2.77 MB FLAT regardless of tick count
- **Try:** Drive the LDA forward-pass state machine with the native clocked engine, host pulsing the clock, and confirm flat RSS.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_phone_clock)
- **Applies to:** Muhlnickel

### Self-clocked CPU (program from its own RAM)  — ✅ measured
- **How:** The baked CPU advances its own state each tick from a program in its own memory; host is only the clock.
- **Effect:** 46,480 ticks/s (84x PC-Python 554), halted byte-exact vs emulator, RSS 2.89 MB flat
- **Try:** Load the LDA forward-pass program into the baked cpu_fwd's own RAM and self-clock it; verify byte-exact vs the reference.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_clockmachine)
- **Applies to:** model-on-Muhlnickel

### Compiled bit-slice ripple (never TC.ripple at runtime)  — ✅ measured
- **How:** Compile the netlist to straight-line closed-over gate code (sdc_cc.compile_ripple / PfcAtom) instead of interpreting a typed gate list each call, removing per-gate dispatch overhead; the interpreted TC.ripple is the forbidden host-compute crutch.
- **Effect:** 36x over interpreted (also reported as 'Nx the floor' in pfc_exp_bench)
- **Try:** Ensure every LDA matmul uses compile_ripple/compiled atoms (never ripple_typed/TC.ripple); read the compiled-vs-naive multiplier in pfc_exp_bench and confirm the 36x on the dot atom.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; host/pfc_exp_bench.py
- **Applies to:** model-on-Muhlnickel

### Pre-slice pipeline (pre-pack constant weights at fab)  — ✅ measured
- **How:** The raw fold is PACKING-bound not gate-bound; pre-pack the constant weight columns into column-major ints ONCE at fabrication and broadcast shared-x, keeping accumulation bit-sliced so the runtime hot path is only the compiled ripple (no per-lane packing loop, no per-block output-unpack).
- **Effect:** 2,293 → 23,270 bd/s (10x); measured 24.1s one-time preslice of a real 2816×4096 tensor, 4 MB stored; presliced fold = the pipeline floor reused every token
- **Try:** Pre-slice the whole gemma-A4B weight set once into storage (extend preslice_weights) so runtime only addresses+folds; measure bd/s and per-token time vs per-call preslice.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2/§4B; host/pfc_matmul_engine.py
- **Applies to:** model-on-Muhlnickel

### Shared-x CSE (compute x front-end once)  — ✅ measured
- **How:** The x front-end is identical across all neurons in a matmul, so compute it once instead of per-neuron.
- **Effect:** 2.1x fewer gates/neuron
- **Try:** Factor the shared-x front-end out of the LDA matmul and confirm ~2.1x gate reduction per neuron byte-exact.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2
- **Applies to:** model-on-Muhlnickel

### Bit-sliced accumulation (unpack once)  — ✅ measured
- **How:** Keep the whole matmul-column sum in bit-sliced planes (ACCW) and ripple-carry add block contributions in W-wide bitops, unpacking to per-lane ints only ONCE at the end — kills the per-block output-unpack cost; needs one x-scale + one per-neuron weight-scale.
- **Effect:** 457,754 block-dots/s @W=8192 byte-exact (~20x the per-block-unpack path; output-unpack bottleneck gone)
- **Try:** Wire matmul_column_W into pfc_llama_decode's matvec (replacing per-fold unpack) and measure block-dots/s on a full attn_q projection of the 70B.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §4B; host/pfc_matmul_engine.py; host/pfc_engine.py
- **Applies to:** model-on-Muhlnickel

### Shared-x broadcast across lanes  — ✅ measured
- **How:** When x is shared across the W lanes of one matmul column, each x-bit column is all-0 or all-ones — broadcast it (cost BLK×XB) instead of packing per lane (cost W×BLK×XB), so the hot path is only the ripple.
- **Effect:** cuts input-packing from W×BLK×XB to BLK×XB per fold (fold_presliced hot path = only the ripple)
- **Try:** Confirm pfc_matvec/matmul in the LDA harness feed x via the shared-x broadcast path (fold_presliced) rather than per-lane packing, and time the difference at W=4096.
- **Source:** host/pfc_matmul_engine.py
- **Applies to:** model-on-Muhlnickel

### Depth-bound latency framing (width folds, latency = critical depth)  — ✅ measured
- **How:** A fabricated circuit settles a whole depth level per gate-delay, so the Muhlnickel's own latency is its critical-path DEPTH (in ticks), not its gate count; width folds in parallel. Host wall-clock is the serial walker, a separate number.
- **Effect:** Measured structurally: dot32_i8 depth = 366 gate-delays (device-independent latency spec); Life 270,336 gates at depth 15
- **Try:** Run pfc_speed.py life and pfc_dotbench's spec section on the LDA dot atom to report DEPTH + wavefront separately from any host rate, so speed claims track depth not seconds.
- **Source:** host/pfc_speed.py; host/pfc_dotbench.py
- **Applies to:** Muhlnickel

### RAM↔throughput dial with a live free-RAM guard  — ✅ measured
- **How:** Fold width W is a dial trading resident RAM for throughput; a live guard projects each widening step's wire-state and stops with headroom before OOM, so you can push W to the device's real ceiling safely.
- **Effect:** Measured: pfc_exp_bench widens W (64..65536) reporting H/s, RSS, peak, auto-stops at the safe ceiling (protects the 8 GB box an unguarded ripple OOM'd)
- **Try:** Run pfc_exp_bench.py to read this box's W-vs-H/s dial and safe ceiling, then set the LDA harness fold to the largest guarded W the phone allows.
- **Source:** host/pfc_exp_bench.py
- **Applies to:** Muhlnickel

### Contiguous / co-routed locality  — 🎯 target
- **How:** Lay co-accessed cells contiguous so DRAM row-buffer hits speed reads (fixes the scatter penalty).
- **Effect:** documented DRAM row-buffer speedup (Phase-C)
- **Try:** Reorder the LDA weight/fold layout so co-accessed blocks are contiguous and measure the read-rate delta.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J (CALIB Phase-C)
- **Applies to:** Muhlnickel

### Pipelining (fabricated latches, INV-157)  — 🎯 target
- **How:** Bake latches into the netlist to overlap ripple stages, raising the per-lane rate — a hardware/fabrication lever.
- **Effect:** per-lane ripple 10⁶/s → 10⁹/s (hardware)
- **Try:** Add pipeline latches to the LDA dot circuit and measure per-lane settle rate vs the unpipelined ripple.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J (SDC_SWARM)
- **Applies to:** Muhlnickel

### Native evaluator = the gating Phase-3 build (on-device gate-net port)  — 🎯 target
- **How:** One native (in-storage, no host-C-on-hardware) multi-thread mmap evaluator drives the actual gate-net off the substrate file, converting the host-ripple floor into the native rate that every other throughput/work-reduction lever multiplies; the phone's stronger silicon out-drives the PC's pure-Python walk.
- **Effect:** S24 Ultra native 8-thread = 1,946,418 block-dots/s vs PC pure-Python = 5,536 (~350x); the single build the interactive stack is gated on
- **Try:** Compile pfc_dotbench / pfc_cm.c on the phone (Termux), run pfc_dotbench dot32_i8.pfc there to re-anchor the device rate, then port the LDA decode matvec to the native engine and re-measure the full lever stack against it.
- **Source:** docs/PFC_LEVER_INDEX.md ★; host/pfc_dotbench.py; host/pfc_clockmachine.py; host/pfc_throughput.py
- **Applies to:** model-on-Muhlnickel

### Wire-liveness slot reuse (register allocation for the fold)  — 💡 idea
- **How:** Compute a topological schedule plus wire-liveness intervals and allocate each wire's W-word slot by interval-graph coloring, so resident wire-state equals the DAG's max simultaneously-live cut, not total n_wire. A gate's output overwrites a dead wire's slot.
- **Effect:** Directly attacks the measured bandwidth wall (the miner caps at W≈2,048 because wire-state ∝ n_wire×W). If sha's cut-width is ~10^3 vs 213k wires, resident state drops ~100× so the W ceiling and wide-fold H/s climb toward the cache-resident peak. Expected multi-× on heavy circuits.
- **Try:** Add a liveness+coloring pass to the bit-slice compiler used by host/pfc_exp_bench.py; measure cut-width of gen_miner and sigma0, then sweep W before/after slot-reuse and log the new peak H/s (byte-exact vs the un-reused path).
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Native wide-word tech-mapping (XOR/MUX/ANDN as one op)  — 💡 idea
- **How:** Tech-map gate subgraphs to the substrate's native wide primitives — a 3-input XOR is one a^b^c, a MUX is one (s&a)|(~s&b) — instead of 3–4 NAND-ops each, cutting ops-per-useful-function below the ~10M-gate/s clock's reach.
- **Effect:** SHA is XOR/MUX-heavy; if half its 105k NAND-ops fold to single native word-ops, effective gate-clock ~2× so H/s ~2× with byte-exact output. This is headroom pfc_leaner.py explicitly does NOT touch — it optimizes NAND count, not mapping to the host's native wide word-ops.
- **Try:** Extend host/pfc_leaner.py with an XOR/MUX/majority pattern matcher that emits single native word-ops; count NAND-ops -> native-ops on sha256 and re-measure the gate-clock via host/pfc_exp_levers.py.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### GPU/accelerator kernel emit (break the CPU bandwidth wall)  — 💡 idea
- **How:** Emit the gate netlist as a compute kernel (Vulkan/OpenCL) for the phone's Adreno GPU — one work-item per lane-word — so the bit-slice fold runs on memory bandwidth an order above the CPU that caps the measured 9.8B/s peak.
- **Effect:** The measured throughput ceiling is CPU memory bandwidth (wide W collapses monotonically). A GPU has ~5–10× the bandwidth, so a wide fold that collapses on the CPU could hold and lift the substrate peak well past 10^10/s.
- **Try:** Add a GPU-kernel backend to host/pfc_phone_gen.py alongside pfc_native.c; run sigma0 on the Adreno via OpenCL, verify byte-exact, and compare lanes/s to the 9.82B 8-core CPU peak.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Compute-in-storage (MLC analog column-sum as a MAC)  — 💡 idea
- **How:** Store operands in multi-level NAND cells and read a whole bit-line at once; the summed cell currents are a physical multiply-accumulate, turning one read into a dot-product instead of a logic op.
- **Effect:** Would convert the dot32 atom's accumulate into a single storage read (compute-in-memory), potentially collapsing matmul depth for the model-on-Muhlnickel path. Speculative on commodity flash — host-emulate the column-sum semantics first to size the win.
- **Try:** Emulate MLC column-sum reads in a host model of the storage tier (extend host/pfc_storage_ram.py) as the accumulate primitive for dot32; count ops-per-read vs the gate-net dot and log the ratio.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Close the clock with feedback junctions (one read = one settle)  — 💡 idea
- **How:** Fabricate the next-state feedback so the state register shares byte-addresses with the next-state output via the §1E junctions; a single addressed read of the output triggers a full depth-D settle that writes back — one tick per poke, host loop-body gone.
- **Effect:** ⛔ "the clock is the open item" is PURGED AS STALE (owner 2026-07-26: "self clock works dude, demonstrated"). If the read closes the loop in-fabric, tick-rate becomes host-poke-rate with the settle free per compute-via-address and flat RSS — the lever that removes the host from the per-tick path.
- **Try:** Bake a counter whose state reg shares addresses with its next-state output (extend host/pfc_clocked.py); poke one read and probe whether it self-advanced >1 tick; if depth 0, try the §U read-through wiring and re-measure with a high-impedance probe.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Wire-state transpose to uint64 bitplanes (kill the W>65k cliff)  — 💡 idea
- **How:** Store each wire's W lanes transposed as a fixed array of uint64 words rather than one growing Python big-int, so evaluation is a straight word-loop with no big-int realloc — removing the measured limb-wall cliff past W=65,536.
- **Effect:** The sweet-spot cliff (W=131,072 -> 139M, down from 636M at W=65,536) is the Python big-int limb wall; a transposed uint64 layout should make throughput flat-per-word past the cliff, extending usable W and total lanes/pass.
- **Try:** Reimplement the sigma0 bit-slice eval in host/pfc_exp_slam.py with per-wire uint64 arrays; sweep W past 131,072 and check whether the cliff disappears, byte-exact vs the big-int path.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Thermal duty-cycling + heat-spread core rotation (raise SUSTAINED rate)  — 💡 idea
- **How:** Interleave short compute bursts with micro-idles and rotate the hot thread across cores so the prime core never parks at the 80C throttle knee, trading a little peak for a higher sustained average.
- **Effect:** Measured throttle: 9.05B burst -> 6.34B soak. Staying below the knee via duty-cycle/rotation could hold sustained closer to burst — expected +10–30% sustained lanes/s over continuous pegging.
- **Try:** In host/pfc_cm.c on the S24 Ultra add a duty-cycle (compute 200ms / idle 50ms) and round-robin the busy thread across cores; log sustained lanes/s and die temp vs continuous pegging.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### 2D iteration-space tiling of the ripple (gate-block x lane-block)  — 💡 idea
- **How:** Tile the (gates x W) evaluation like a blocked matmul — pick a gate-block and lane-block whose combined wire-state fits L2 — so both the gate program and the wire tile stay cache-resident instead of choosing one small global B.
- **Effect:** Peak is measured at cache-resident width; explicit 2D tiling should find a better operating point than the 1D 'small B' heuristic, recovering throughput at larger total W (bounded by the L2-fit tile, not a single global B).
- **Try:** Add a blocked evaluator to host/pfc_exp_bench.py that iterates (gate-block, lane-block); sweep tile sizes on gen_miner and map the throughput surface to find the L2-optimal tile.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Systolic/wavefront fold (stationary circuit, streaming lanes)  — 💡 idea
- **How:** Fabricate the circuit as a fixed pipeline with per-stage latches and stream candidates through it; after fill, one result pops per gate-delay regardless of total depth — throughput decouples from critical-path depth.
- **Effect:** Turns the depth-bound latency (miner depth ~15, SHA deeper) into a fill-once cost, then 1 result/gate-delay steady-state — the hardware-style path toward >10^9 results/s per lane that pipelining (INV-157) points at, now as a streaming fold.
- **Try:** Fabricate a few-stage systolic SHA round with fabricated latches (extend host/pfc_clocked.py); stream nonces and measure steady-state results/cycle vs the combinational fold, byte-exact vs hashlib.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Position-batch bit-slice — pack prompt positions into the SIMD lanes (T-wide prefill)  — 💡 idea
- **How:** The existing shared-x lever broadcasts ONE activation to all lanes; its dual is weight-shared, activation-varying: pack DIFFERENT prompt positions into the W~65536 bit-slice lanes against the shared layer weights, folding all T prompt tokens' matmuls in one pass. Prefill goes from T serial folds to ceil(T/lanes) folds.
- **Effect:** Expected: prefill TTFT (currently T serial token-folds) becomes ~lane-count faster, amortizing the system+screen prompt across one fold. Complements batching (many requests) by parallelizing the position axis of one request.
- **Try:** In pfc_matmul_engine.fold_presliced, pack N prompt-position activations into distinct bit-slice lanes against one weight circuit; verify each lane matches the per-position dot; measure bd/s vs serial on a 64-token prompt.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Structured parallel action head (one-shot whole-action decode)  — 💡 idea
- **How:** The action JSON is a fixed schema (verb+target+value); bake three classifier heads that read the final hidden state and predict all fields in parallel on the Muhlnickel, replacing the ~12-token autoregressive decode with a single settle.
- **Effect:** Expect decide-stage output tokens to fall from ~10-16 to ~0 (one forward pass), cutting per-action decode latency several-fold and eliminating the mid-JSON-drift malformed-action class.
- **Try:** Bake verb/target/value heads over the last hidden state, verify they reproduce the autoregressive action on gauntlet logs, then measure decode tokens and latency vs. the streaming-JSON baseline.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Depth-adaptive early-exit action decode  — 💡 idea
- **How:** Muhlnickel latency is depth-bound (a tick settles a whole depth level), so bake per-layer confidence probes that halt the forward pass once the action prediction is low-entropy — easy decisions settle in fewer depth levels, so their latency (= critical depth) drops.
- **Effect:** Expect easy/repetitive UI steps to exit after a fraction of the layers, cutting their decide latency in proportion to layers skipped, since on the Muhlnickel depth IS the latency (width folds free).
- **Try:** Bake early-exit confidence probes at a few layer depths, measure on the gauntlet how early the action stabilizes per step type, and A/B latency vs. full-depth with a correctness guard.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Speculative action pre-execution (pipeline perceive with decide)  — 💡 idea
- **How:** While the model decodes action N, a baked transition predictor (screen-hash+action → next-screen-class) names the most-likely resulting screen and the deterministic layer speculatively pre-fetches/pre-renders that accessibility snapshot, so perceive of step N+1 overlaps decide of step N — branch prediction for the agent loop.
- **Effect:** Expect per-step wall-time to fall toward max(decide, perceive) instead of decide+perceive whenever the speculation is right; net loop speedup scales with prediction hit-rate; distinct from token-level speculative decode (this is loop-level pipelining).
- **Try:** Bake the transition predictor, log its hit-rate on gauntlet trajectories, then overlap the accessibility snapshot fetch with decode and measure per-step latency vs. serial perceive→decide.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Persistent prefix-KV ROM — zero-prefill stable σ-prefix  — 💡 idea
- **How:** The stable operator + perception-legend prefix is re-prefilled on every cold start; precompute its per-layer KV once and store it as an addressed region in titan.gguf so a fresh turn ADDRESSES the prefix KV instead of prefilling it — cache_prompt made persistent across cold starts on storage, not just within a warm process.
- **Effect:** Expect first-action latency of a cold session to drop by the prefill cost of the entire legend/operator prefix (potentially hundreds of prefill tokens → ~0), which the warm-KV cache_prompt lever cannot recover across restarts.
- **Try:** Precompute the prefix KV for the current legend/σ-prefix, store it as a Muhlnickel region, load-by-address at session start, and measure first-action prefill tokens/latency vs. cold prefill.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Bit-serial MAC (more lanes per wire-state budget)  — 💡 idea
- **How:** Process operands one bit per cycle: the circuit is tiny and carries ~one state bit per operand, so the wire-state RAM (n_wire x W) that causes the measured W>65,536 cliff holds vastly more lanes. It trades depth (cycles) for width (lanes), directly attacking the memory-bandwidth wall.
- **Effect:** Expected: at equal resident RAM, a bit-serial fold packs far more lanes than the bit-parallel fold that collapses past W~65k (measured 1.84B->0.13B at 4.8GB). Crossover point to be measured.
- **Try:** Fabricate a bit-serial block-dot, sweep lanes vs the bit-parallel fold at a fixed RAM budget on the Ryzen box, and locate the lane count where bit-serial's aggregate rate overtakes the bandwidth-capped parallel fold.
- **Source:** new-proposal
- **Applies to:** all

### Entropy-coded activation transport (source coding before the fold)  — 💡 idea
- **How:** The fold is measured to be PACKING/bandwidth-bound, not gate-bound; entropy-code (ANS/arithmetic) the sparse, low-entropy activations so fewer bits move through the wire-state, exploiting the distribution (zeros and repeats cost ~0 bits) rather than the value width. Attacks the bandwidth wall from the information-theory side.
- **Effect:** Expected: bytes moved per activation vector drop toward its entropy (sparse post-ReLU/SiLU vectors are highly compressible), lifting the packing-bound raw fold rate (currently ~95k-120k cand/s baseline is packing-bound).
- **Try:** ANS-code a real post-activation vector, measure bytes moved vs raw int8 packing and the resulting change in block-dots/s through the fold, isolating the packing-bound floor the datadump §K flags.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

## WORK-REDUCTION — fewer block-dots / token / step  (25)

### Memoize / System-1 cache (compute→storage; repeats = addressed reads)  — ✅ measured
- **How:** Cache each computed result in a sparse cell keyed on the input (tensor, or σ+input, or temp-0 σ+screen-state); every repeat/overlap becomes a ~0-compute addressed read. Multiplier = the stream's input-repeat factor R. A recognized temp-0 input is served from the cache as an instant lookup with zero forward passes.
- **Effect:** R=16→10.1x, R=64→34x (~64x) → 3.22M cand/s, byte-exact; temp-0 recognized input = instant replay, 0 forward passes; blake2b-keyed memo reports memo_hits/matmuls
- **Try:** Put a memoize fold in front of the LDA forward pass keyed on (σ+prompt+screen-state) and measure the repeat-factor speedup + memo hit-rate on a real screen-action stream.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J/§K; CALIBRATION_FINDINGS #7; host/pfc_exp_conjunction.py; host/pfc_forward.py; host/pfc_engine.py
- **Applies to:** all

### α / sparse activation (compute only the live region)  — ✅ measured
- **How:** Only evaluate the region of the model/circuit the answer actually needs; DCE does this at fab, input-dependent skipping is the open extension.
- **Effect:** 4B-active MoE ~20x faster than dense 14.7B
- **Try:** Gate the LDA MoE so only the fired expert/neuron cone ripples per token and measure block-dots/token drop.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J (INV-61)
- **Applies to:** model-on-Muhlnickel

### Content-addressed membership fold (moat app)  — ✅ measured
- **How:** Winner-only storage-backed bit-fold where the key's hash IS its bit address; members cost 1 bit, non-members 0, the whole set addressed not scanned, data-oblivious (fixed baked mixing circuit + one bounded read). False-positive rate = load factor, no false negatives.
- **Effect:** 100k keys in 2 MB, 0 false negatives byte-exact; 8.6-billion-slot (2³³) fold storage-backed, inserted+read 50k byte-exact at ~flat 32→34 MB RSS
- **Try:** Back the LDA's allowlist/dedup/policy-key/seen-screen checks with the membership fold; measure oblivious lookup latency + resident at billions-scale on the phone.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_membership), §J; host/pfc_membership.py
- **Applies to:** lda-agent

### Bake a lever → host only addresses  — ✅ measured
- **How:** Baking a precomputed result table (e.g. memoize) into the permanent binary turns a miss (fresh compute) into a hit (addressed read) at ~0 operational RAM.
- **Effect:** MISS +120.0 MB operational; HIT +0.0 MB, 1.66M addressed-reads/s, byte-exact
- **Try:** Bake the LDA's stable operator/memoize tables into titan.gguf so runtime only addresses them; confirm operational RAM → 0 for the baked fraction.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_bake_lever)
- **Applies to:** all

### MoE routing (route only active experts, e.g. 4/128)  — ✅ measured
- **How:** A Mixture-of-Experts model routes only a few experts per token; compute the router on the Muhlnickel, pick top-k, and spend FFN block-dots only for those experts — the model's own architectural sparsity, free.
- **Effect:** dense-70B 2.17B → A4B routed 40.6M bd/tok (53x); Mixtral 8→2 ~4x fewer FFN block-dots/layer byte-exact; A4B 4/128 = 10.3x; MoE router runs live on the Muhlnickel byte-exact
- **Try:** Run pfc_route.py on Mixtral to confirm the live 4x, use an MoE (A4B/Mixtral) as the LDA model, and account routed vs dense block-dots/token in pfc_gen_cost — confirm the 53x reduction per token.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; docs/PFC_LEVER_INDEX.md C; host/pfc_route.py; host/pfc_gen_cost.py
- **Applies to:** model-on-Muhlnickel

### Address-first: drive host ripple toward 0  — ✅ measured
- **How:** Every op that can be an addressed read (glue LUTs, memoize hits, embedding lookups) costs 0 ripple; ripple is spent only on genuinely-novel weight matmuls, and even those fold W-wide per gate-sweep.
- **Effect:** Measured by the Meter: reports ripple(gate-evals) vs addressed(reads) and ripple/op each run; the metric to minimize
- **Try:** Run pfc_forward and read Meter.line(); push ripple down by enabling memoize + MoE + sparsity and re-measure the ripple/op.
- **Source:** host/pfc_forward.py
- **Applies to:** model-on-Muhlnickel

### Contextual FFN sparsity (fire only ON neurons)  — 🎯 target
- **How:** PowerInfer/Deja-Vu style: evaluate only neurons whose gate SiLU(gate_proj(x))>0 fires, cutting FFN block-dots by the keep-fraction; un-operatored this is weak, but an operator (fired-neuron mask) drives it and it stacks with MoE routing.
- **Effect:** 1.6x un-operatored (weaker than 15% target); keep ~15% → combined with MoE ~18.9x less than dense per token when operator-driven
- **Try:** Instrument a real LDA forward pass to log per-neuron activation magnitude, pick an empirical keep-fraction that preserves the argmax token, stack it on MoE routing, and feed the combined divisor into pfc_gen_cost's tok/s projection.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; docs/PFC_LEVER_INDEX.md C; host/pfc_gen_cost.py; host/pfc_throughput.py
- **Applies to:** model-on-Muhlnickel

### Zero-computation experts (LongCat, adaptive α)  — 💡 idea
- **How:** Dynamic per-token active-parameter count: easy tokens route to no-op experts, making α adaptive per token/step (maps to per-step confidence/stakes gating).
- **Effect:** target — makes work-reduction adaptive per token
- **Try:** Add no-op experts to the LDA MoE routed by per-step confidence so easy screen states cost ~0 compute; measure the drop.
- **Source:** docs/PFC_LEVER_INDEX.md C (LONGCAT task)
- **Applies to:** lda-agent

### Uniform-word short-circuit (data-dependent bandwidth skip)  — 💡 idea
- **How:** During the bit-slice ripple, tag wire-words that are all-0 or all-1; AND/NAND with an all-0 word yields a constant without touching the other W-word operand, so uniform lanes cost O(1) not O(W).
- **Effect:** Cuts the memory traffic that causes the measured bandwidth collapse whenever lanes share structure (one-hot address lines, winner-only folds, early SHA rounds under a nonce sweep). Expected larger effective W before collapse; biggest on sparse/structured folds.
- **Try:** Instrument wire-word entropy across one gen_miner pass in host/pfc_exp_bench.py; add an all-0/all-1 fast path to the ripple inner loop and measure lanes/s plus the fraction of ops skipped.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Route-time partial evaluation (midstate circuit specialization)  — 💡 idea
- **How:** The routing button constant-folds the fabricated circuit against the fixed input bits of a batch (e.g. the ~76 constant header bytes in mining), collapsing every gate that depends only on constants; only the lean residual (the nonce cone) is bit-sliced.
- **Effect:** Classic midstate: the first SHA block over a fixed header collapses dramatically. Expect the per-run residual << 337,256 gates so H/s rises several × for the same fold, with no re-bake — specialization is per-batch at the button, not fabrication.
- **Try:** In a routing button, constant-fold gen_miner with the fixed header bits fixed and count residual gates vs 337,256; run the residual through host/pfc_exp_bench.py and compare H/s (verify byte-exact vs the full circuit on the varying nonce).
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Event-driven incremental ripple (dirty-cone only)  — 💡 idea
- **How:** For iterated circuits (Life, the CPU, a nonce sweep), keep a dirty-set and re-evaluate only the fan-out cone of wires that actually changed since the last tick, skipping the invariant majority.
- **Effect:** Life on a sparse board and a CPU between instructions change a tiny fraction of 270,336 / 7,403 gates per tick; expected gates-evaluated/tick down 10–100× so proportional tick-rate gain, byte-exact.
- **Try:** Build an event-driven evaluator for host/pfc_game.py life; on a sparse board, log gates-evaluated/gen vs the full 270,336 and the resulting gens/s, checking byte-exact against the reference (pfc_game.py life --test).
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Filter-cascade fabrication (cheap prefilter before the heavy circuit)  — 💡 idea
- **How:** Fabricate a cheap rejection circuit (a partial-hash / Bloom-style predicate, ~10^2–10^3 gates) that discards candidates that provably cannot meet the frontier, so only survivors ripple the full 337k-gate SHA.
- **Effect:** For search/mining, a prefilter rejecting 99% of nonces cuts average gates-per-candidate ~100× so effective candidates/s toward the frontier climbs sharply. Stays data-oblivious per-batch so the security property holds at the batch boundary.
- **Try:** Fabricate a first-SHA-partial leading-zero prefilter; wire it before gen_miner in a fold; measure the fraction of nonces surviving to the full circuit and net candidates/s vs the unfiltered fold.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Scalar/vector hybrid split by input-dependence  — 💡 idea
- **How:** At fab time, partition gates by which inputs they depend on: the cone touching only shared/constant bits is evaluated once as a scalar, and only the cone touching the varying bits is bit-sliced across lanes — a dataflow generalization of midstate to any low-entropy-input fold.
- **Effect:** For folds where lanes differ in few bits (nonce low bits, near-duplicate queries), the vectorized fraction shrinks to the varying cone so fewer W-wide ops per candidate; expected several × on structured search streams, byte-exact.
- **Try:** Tag each gate in gen_miner by shared-vs-varying input dependence; evaluate the shared cone scalar-once and only the varying cone bit-sliced; measure ops/candidate vs the full bit-slice, verifying byte-exact winners.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Hashed routing — LSH pre-select experts/neurons (sublinear router)  — 💡 idea
- **How:** Bake a locality-sensitive-hash (or product-quantization) circuit that maps the hidden vector x to a bucket id via k fixed sign-bit dots, and the bucket winner-only-addresses a precomputed shortlist of experts/neurons to fold. Replaces the full dense router matmul (the MoE gate, or the SiLU(gate_proj) neuron gate) with an O(1) addressed read, so even the SELECTION cost becomes an addressed lookup instead of a matmul.
- **Effect:** Expected: the routing/gate matmul that pfc_gen_cost still charges on the ROUTED path collapses to ~0; also lets you raise top-k without paying selection cost. Direction: fewer block-dots/token, especially for MoE (route 4/128) and contextual FFN gating.
- **Try:** In pfc_route.py add an LSH bucketer (k random hyperplanes = fixed sign dots) -> bucket -> expert shortlist; measure top-4 recall vs the true gate over ~500 real hidden states pulled from a pfc_llama_decode run, then fabricate the sign-hash as gates via titan_circuit.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### MSB-first anytime dot — winner-only on the logit axis  — 💡 idea
- **How:** Fabricate the full-vocab logit block-dots bit-serial, most-significant slice first, keeping a running interval [lo,hi] per token from the max magnitude of the un-evaluated slices. As soon as one token's lo exceeds every other token's hi, argmax is decided — stop refining the losers. Decode only needs argmax, so losing-vocab logits never reach full precision.
- **Effect:** Expected 3-8x fewer bit-slice passes on the lm_head layer (the single biggest matmul, ~128k full-width dots/token) for confident tokens, since 1-2 MSB planes usually separate the winner on low-entropy agent output.
- **Try:** In pfc_llama_decode, after the MSB bit-plane of every logit via pfc_matmul_engine, compute lo/hi bounds and measure how often argmax is already decided after 1/2/3 planes over a decode trace; then bake the interval-compare as a gate circuit.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Delta-activation fold — matmul only the token-to-token change  — 💡 idea
- **How:** Matmul is linear: W.x_t = W.x_{t-1} + W.(x_t - x_{t-1}). Cache the previous layer output and fold only Delta, which after a stable prefix is mostly near-zero, so a winner-only/sparse fold skips the unchanged lanes and accumulates onto the cached result.
- **Effect:** Expected: block-dots/token scales with the count of significantly-changed activation entries, not d. On the LDA's near-static screen frames Delta is tiny -> potentially >5x fewer folds after the first token of a step.
- **Try:** Instrument pfc_llama_decode to log the count of Delta entries above a threshold between consecutive positions per layer on a real prompt; if sparse, wire a delta path (keep W.x cached, fold only nonzero Delta lanes) and verify byte-close to full recompute.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### JL logit sketch — cheap approximate argmax, exact only on the shortlist  — 💡 idea
- **How:** Fabricate a fixed sign-random projection R (d->k, k<<d, add/subtract only) baked as gates. Compute approximate logits in the small k-space to get a top-m shortlist, then run the exact full-width dot32_i8 logits ONLY for those m tokens.
- **Effect:** Expected: lm_head is ~128k full-width dots/token; a k~64 sketch + exact on top-32 could cut logit-layer block-dots ~10-50x when shortlist recall is high (agent output is low-entropy).
- **Try:** Offline build a sign-random R, measure top-1/top-5 recall of the sketched argmax vs exact over a decode trace; if recall is high, fabricate R as an add-only butterfly and gate the exact lm_head dots to the shortlist.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Fabricated early-exit — per-token confidence gate skips remaining layers  — 💡 idea
- **How:** After each transformer block, a tiny fabricated gate-net reads the hidden state (or the running logit margin from the JL sketch) and decides if this token's argmax is already committed; if so, skip the remaining layers straight to logits. Easy/templated tokens (most agent JSON) exit shallow. The decision is a gate-net, so ~0 cost.
- **Effect:** Expected: average layers/token drops on low-entropy streams; for agent action-JSON (highly templated) a large fraction of tokens should exit in the first third of layers.
- **Try:** Add a logit-lens probe after each layer in pfc_llama_decode; measure how early the final argmax stabilizes per token on real agent prompts; bake the stabilization test as a confidence-gate circuit with a conservative threshold.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Incoherence pre-rotation — Hadamard transform to concentrate activations, boosting sparsity  — 💡 idea
- **How:** Apply a fixed orthogonal transform (fabricated Hadamard/butterfly, add/subtract only) to activations and pre-rotate weights inversely at fabrication, so activation energy concentrates into fewer large entries -> contextual sparsity rises (the measured-weak 1.6x lever) and outlier-free activations quantize better (safer low-bit). One transform, baked once, stacks with alpha and TurboQuant.
- **Effect:** Expected: raises the skippable (near-zero) activation fraction beyond the current ~1.6x contextual-sparsity ceiling and makes 3-bit/2-bit quant safer; multiplicative with the alpha and quant levers.
- **Try:** Offline apply a Hadamard transform to Llama FFN activations, measure the change in the fraction of near-zero (skippable) entries and the 3-bit quant error vs untransformed; if it helps, fabricate the butterfly (add/sub only) as gates and fold it before the FFN.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Temporal perception-diff codec (delta-only screen)  — 💡 idea
- **How:** Content-address each element row's hash against the previous frame on the Muhlnickel (membership fold) and re-render only the rows added/removed/changed; the warm KV keeps the unchanged prefix so a multi-step task on a near-static screen pays full perception tokens once, not every step.
- **Effect:** On multi-step flows where the screen barely changes between actions, expect ~60-90% fewer perception tokens per step after step 1, with decide latency down proportionally; distinct from the per-frame codec in AGENT_LANGUAGE §1 which is temporal-blind.
- **Try:** Instrument GauntletRunner to log element-list token overlap between consecutive frames on real trajectories; if overlap is high, build render_delta(prev,cur) behind a flag and A/B token count + agent-driven success.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Intent-conditioned perceptual pruning (objective·element relevance on dot32_i8)  — 💡 idea
- **How:** Bake a relevance scorer that dots each element's embedding against the current objective's embedding on the already-baked dot32_i8 atom, keeping only the top-k most task-relevant controls in the rendered element list (paging/find still reaches the rest = lossless-for-reachability per AGENT_LANGUAGE §1).
- **Effect:** Expect dense screens (settings, feeds) to shrink to k≈8-15 controls in-prompt, cutting perceive tokens ~50-70% AND raising decide accuracy by removing distractor controls the model would otherwise mis-target.
- **Try:** Compute element·objective relevance with dot32_i8 on gauntlet screens, keep top-k, and measure prompt-token drop plus wrong-target rate against the full-list baseline.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Macro fold — compile a proven flow into one baked routing button  — 💡 idea
- **How:** When a multi-step UI trajectory (open→tap→type→send) verifies repeatedly, fabricate the whole action sequence as a macro circuit plus one routing button that emits the sequence deterministically with per-step live-screen guards, turning N model-decode steps into 1 decode + N cheap addressed reads.
- **Effect:** Expect frequent flows to fall from N model decisions to ~1, cutting per-completion model calls and wall-time roughly N× on repeats, with deterministic replay; distinct from generic System-1 memoize because it folds a whole trajectory, not one compute result.
- **Try:** Pick the most frequent flow in BakeHistory/gauntlet logs, fabricate its action-sequence circuit with screen-hash guards, and measure model-decode calls per completion (target N→~1) plus failure rate when the live screen diverges.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Confidence-margin-gated adaptive compute dial  — 💡 idea
- **How:** Bake a margin probe (top-1 minus top-2 logit) on the Muhlnickel answer register; when the margin is high the agent acts immediately with think-off / the small model, when low it escalates to more layers, the bigger model, or reasoning-on — spending cycles only where the decision is genuinely hard.
- **Effect:** Expect average per-step compute to fall on the majority of easy steps while hard steps get more care, lowering both mean latency and wrong-action rate vs. a fixed budget; distinct from the static think-off dial because escalation is confidence-triggered.
- **Try:** Bake pfc_margin over the logits, log margin vs. action-correctness across the gauntlet to find a threshold, then wire the threshold to escalate model/depth and measure latency + accuracy.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Low-rank / factorized weight fold (SVD / LoRA)  — 💡 idea
- **How:** Factor a weight matrix W ~= A.B with rank r << d, so a matmul's block-dots drop from ~d^2 to ~2dr — it cuts the COUNT axis (block-dots per token), orthogonal to MoE/sparsity which cut which experts/neurons fire.
- **Effect:** Expected: for a 4096x2816 projection at rank 256, block-dots fall ~5-6x with small reconstruction error; stacks multiplicatively with MoE (53x) and terse-operator (110x).
- **Try:** SVD a gemma-4-26B-A4B projection to rank r, plot reconstruction error vs block-dot reduction, fold the two small matmuls A and B on pfc_matmul_engine, and measure end-to-end bd/token + output quality vs the full matmul.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Strassen / fast-matmul fabrication (algebraic multiply reduction)  — 💡 idea
- **How:** Recursively apply Strassen-style identities so a 2x2 block-matmul uses 7 multiplies instead of 8 (and deeper recursion compounds it), cutting the COUNT of fabricated multiplier cones per matmul at the cost of extra cheap adds. A work-reduction lever from an algebraic identity, not present in the corpus.
- **Effect:** Expected: ~1.14x fewer multiplies per recursion level (7/8), compounding with depth; trades multipliers (expensive gates) for adds (cheap).
- **Try:** Fabricate one level of Strassen block-matmul (7 sub-multiplies) for a tiled gemma matmul, verify byte-exact vs the naive 8-multiply tiling, and measure net multiplier-gate count and depth vs the direct fold.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

## FABRICATION — leaner / shallower / better-encoded gates  (28)

### Circuit area minimization (fold+CSE+DCE + leaner peephole)  — ✅ measured
- **How:** sdc_cc folds duplicate logic, does CSE and DCE to cut gates per useful op. Throughput = gate-clock × lanes ÷ gates-per-op, and gates-per-op is the only free divisor, so every gate removed is a proportional throughput gain on every future bake.
- **Effect:** naive NAND miner ~682k gates → 213,069 (~3.2x fewer); near area-optimal for what sdc_cc does; each removed gate = proportional throughput gain forever
- **Try:** Re-run fold/CSE/DCE (then the leaner peephole) over every LDA glue circuit (silu8/rsqrt/exp/argmax) and log gate deltas before baking; each drop is the throughput multiplier for the same hardware.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A; host/pfc_leaner.py
- **Applies to:** Muhlnickel

### Mass-fabrication density (parts are free; millions fit)  — ✅ measured
- **How:** Circuits are cheap to build and tiny relative to storage, so a huge pre-baked library can be held; fabrication (build+optimize+compile) is fast and each part is ~KB.
- **Effect:** 406 circuits/sec build+optimize+compile; ~1,035 B/circuit → 402 GB free fits ~389 MILLION circuits; ~131K gates/MB
- **Try:** Pre-bake the full LDA glue+operator circuit library (pfc_exp_massfab for circuits/sec + bytes/circuit) and confirm the whole library is a negligible fraction of the file.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B; docs/PFC_LEVER_INDEX.md E; host/pfc_exp_massfab.py
- **Applies to:** Muhlnickel

### Fabricated addressable RAM (§M)  — ✅ measured
- **How:** Fabricate a cell-array + address decoder + read/write mux out of gates so a stateless circuit gains a persistent addressable store.
- **Effect:** 16 cells × 8 bits = 128 bits in 728 gates, byte-exact over 400 random ops
- **Try:** Give the LDA forward-pass engine a fabricated scratch RAM for KV/intermediate state instead of host arrays; verify byte-exact.
- **Source:** docs/PFC_LEVER_DATADUMP.md §M
- **Applies to:** Muhlnickel

### Stored-program CPU (§P, general-purpose)  — ✅ measured
- **How:** Fuse fabricated RAM + ALU + PC + decode into a von-Neumann CPU baked as gates so you write programs in memory instead of a new circuit per task.
- **Effect:** 16 words × 8-bit + ALU + PC = 1,655 gates, byte-exact over 500 steps, ran a countdown loop; cpu_fwd = 404,262g forward-pass CPU
- **Try:** Run the LDA forward pass as a stored program on the baked cpu_fwd CPU rather than a hand-written host forward pass.
- **Source:** docs/PFC_LEVER_DATADUMP.md §P
- **Applies to:** model-on-Muhlnickel

### Shallow arithmetic (Wallace/Dadda + carry-save)  — ✅ measured
- **How:** Replace shift-add multiply and ripple sums with O(log n) carry-save (3:2 compressor) Wallace-tree multipliers and carry-save adders — partial products reduced to two rows then one parallel-prefix add — to shrink critical-path depth.
- **Effect:** multiply depth W=8 40→22 (1.8x), W=16 88→30 (2.9x), byte-exact
- **Try:** Swap the LDA dot's shift-add multiplier for wallace_mul + carry-save accumulate, re-run selftest for byte-exactness, and measure depth and settle-latency drop.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_shallow); host/pfc_shallow.py; host/pfc_matmul_engine.py
- **Applies to:** Muhlnickel

### Better gates — depth lever (Kogge-Stone / balanced tree)  — ✅ measured
- **How:** Use parallel-prefix adders (Kogge-Stone) and balanced reduction trees to minimize critical-path depth — how fast the answer settles / the FPGA clock — which sdc_cc never optimizes. Depth is the critical path; width folds in parallel.
- **Effect:** adder W=64 depth 126→13 (9.7x, ~3x gates); reduce N=256 depth 255→8 (32x shallower at SAME gate count = free)
- **Try:** Rebuild the LDA reductions as balanced trees (free depth win) and its adds as Kogge-Stone; run pfc_speed to confirm critical-path depth drops (from 366 gate-delays on dot32_i8), byte-exact.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_bettergates); host/pfc_bettergates.py
- **Applies to:** Muhlnickel

### Baking ceiling (97.8% of file is bakeable)  — ✅ measured
- **How:** Only the ~0.04% GGUF structural header must stay; the rest of the param region can be overwritten with circuits and still function byte-exact.
- **Effect:** 39.16 GB = 97.82% bakeable; structural header 15.82 MB = 0.0395%; currently 0.42% used
- **Try:** Confirm the LDA's new circuits fit in the 97.8% bakeable region without touching the header; keep the registry current.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_bakelimit)
- **Applies to:** Muhlnickel

### Leaner-fabricator peephole pass  — ✅ measured
- **How:** Algebraic + constant-fold + hash-cons (structural sharing) + double-NOT peephole optimizer over any gate list, byte-exact verified.
- **Effect:** sigma0 61→61 (+0%), sha256 105,409→105,388 (−21); confirms sdc_cc is near area-optimal — the headroom is depth/width/state
- **Try:** Run the peephole pass over every LDA glue circuit before baking; treat near-zero gate savings as a cue to attack depth instead.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_leaner); host/pfc_leaner.py
- **Applies to:** Muhlnickel

### Optimal-implementation selector  — ✅ measured
- **How:** For a function with multiple equivalent circuits, build several candidates, verify byte-exact equivalence, measure gates (and depth as tiebreak), and store the leanest automatically; route every bake through it.
- **Effect:** SHA ch 128→96 (25%), maj 160→128 (20%), popcount(8) 40→34 + shallower
- **Try:** Route every LDA glue-circuit bake through pfc_optimal.select() (e.g. ripple vs Kogge-Stone adders inside the dot as competing candidates) and log the winner's gate/depth savings.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_optimal); host/pfc_optimal.py
- **Applies to:** Muhlnickel

### Depth-opt dot fabrication  — ✅ measured
- **How:** Fabricate the block-dot with a balanced-tree reduction (not linear) plus Kogge-Stone adders to slash critical-path depth.
- **Effect:** dot 93,184 → 10,326 gates (9x)
- **Try:** Bake the LDA dot32_i8 as the depth-opt 10,326-gate version and confirm byte-exact + faster settle.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2
- **Applies to:** model-on-Muhlnickel

### Glue baked as LUT circuits (0-ripple addressed reads)  — ✅ measured
- **How:** RMSNorm 1/sqrt, softmax exp, RoPE sin/cos, SwiGLU silu, and argmax are baked as ROM-as-gates lookup tables (one-hot address decoder → stored constant), so each nonlinearity is an addressed read, not a host float call.
- **Effect:** Measured byte-exact vs their tables (fabricates pfc_rsqrt/pfc_exp/pfc_sin/pfc_silu8/pfc_argmax); moves the non-matmul steps fully onto the Muhlnickel
- **Try:** Run pfc_glue_fab.py fab then pfc_llama_decode.py --gen 2 --layers 4 and confirm PfcGlue.on is true (glue on baked circuits, not math.*), byte-exact.
- **Source:** host/pfc_glue_fab.py; host/pfc_llama_decode.py
- **Applies to:** model-on-Muhlnickel

### Clocked / self-clocked pipelining (state in storage, host = clock)  — ✅ measured
- **How:** Any (state→next-state) machine is fed back with state kept in the Muhlnickel's storage; the host only clocks. A fabricated pipeline emits one result per stage delay (throughput 1/τ) with latency D×τ.
- **Effect:** Measured: counter/hasher/CPU machines byte-exact through one native engine; pipelined throughput = 1/τ, latency = depth×τ
- **Try:** Build the LDA decode step as a clocked machine (KV+position as fed-back state) and run it through pfc_cm.c on the phone to get machine-ticks/sec at flat resident.
- **Source:** host/pfc_clockmachine.py; host/pfc_speed.py
- **Applies to:** model-on-Muhlnickel

### Fabrication is the ROOT lever (§O)  — 🎯 target
- **How:** Every downstream metric (throughput, latency=depth, width, RAM=state) is set at fabrication; everything else is a consequence, so co-optimize the bake.
- **Effect:** documented conceptual spine; sigma0 maxed the machine at 3 MB by fabrication shape
- **Try:** For each LDA circuit record its (gates, depth, width, state) as the four fab knobs and optimize all four, not just area.
- **Source:** docs/PFC_LEVER_DATADUMP.md §O
- **Applies to:** Muhlnickel

### Depth×width geometry (optimal Muhlnickel)  — 🎯 target
- **How:** RAM=lateral width (how many at once); fabrication=depth (how complex per pass); optimal Muhlnickel = sophisticated minimized DEPTH × WIDE lateral deployment.
- **Effect:** documented; sophisticated depth is capability no width can replace
- **Try:** Shape the LDA matmul as shallow-per-pass × wide-lateral and measure latency (depth) vs aggregate (width) separately.
- **Source:** docs/PFC_LEVER_DATADUMP.md §O
- **Applies to:** Muhlnickel

### Smarter fabricator (co-opt area×depth×width×state)  — 🎯 target
- **How:** Current sdc_cc optimizes only area; a fabricator that also minimizes critical-path depth, bakes parallel lanes, and adds state would shape circuits to saturate the substrate.
- **Effect:** target — the primary open lever per §O
- **Try:** Extend sdc_cc with a depth pass (balanced trees/Kogge-Stone) and re-bake the LDA dot; measure depth and settle-latency drop.
- **Source:** docs/PFC_LEVER_DATADUMP.md §O
- **Applies to:** Muhlnickel

### AUTOFAB (fabricator on the Muhlnickel) + per-tick matcher  — 🎯 target
- **How:** The Muhlnickel auto-fabricates the leanest circuit for each tick's need from a free-to-hold circuit library (density makes the library free); a master-OS matcher selects per tick.
- **Effect:** target — powered by the DENSITY lever (131K gates/MB)
- **Try:** Prototype a matcher that picks a pre-baked LDA circuit per step from the library; later move fabrication itself onto the Muhlnickel.
- **Source:** docs/PFC_LEVER_INDEX.md A
- **Applies to:** Muhlnickel

### Number systems (RNS / redundant / carry-save)  — 💡 idea
- **How:** Use residue/redundant/carry-save number systems for carry-free parallel arithmetic, shrinking arithmetic depth.
- **Effect:** target — carry-free parallel arithmetic
- **Try:** Fabricate an LDA adder in a redundant/RNS representation and compare depth to the Kogge-Stone baseline.
- **Source:** docs/PFC_LEVER_INDEX.md A (OPT_LANDSCAPE §1)
- **Applies to:** Muhlnickel

### AIG rewriting / tech-mapping / don't-care opt  — 💡 idea
- **How:** Real logic-synthesis passes (AND-inverter-graph rewriting, technology mapping, don't-care optimization) share more and beat fold/CSE/DCE on area.
- **Effect:** target — the synthesis sdc_cc lacks
- **Try:** Run an AIG-rewrite pass over the LDA dot netlist and compare area/depth to sdc_cc's fold/CSE/DCE.
- **Source:** docs/PFC_LEVER_INDEX.md A (OPT_LANDSCAPE §1)
- **Applies to:** Muhlnickel

### Weight-sparsity fold — zero weights cost zero gates  — 💡 idea
- **How:** At fabrication, drop sub-threshold weights per Q8_0 block and fabricate the block-dot so ONLY the surviving nonzero int8 terms get a multiplier+adder. Distinct from bit-width quantization: this cuts the NUMBER of MAC terms per block-dot, shrinking gate count AND depth of every matmul, and stacks with 3-bit TurboQuant and depth-opt.
- **Effect:** Expected: e.g. 50% weight sparsity roughly halves the multipliers in each dot32_i8, ~halving gates/depth per block-dot; multiplicative with quant and depth-opt fabrication.
- **Try:** Take one Llama FFN tensor, measure the fraction of |w|<tau per 32-block that keeps output within tolerance; fabricate a sparse dot (skip zero lanes) in pfc_matmul_engine and compare gate count + byte-error vs the dense dot32_i8.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Glue-fusion — bake norm/RoPE/SwiGLU into the adjacent matmul (no host round-trip)  — 💡 idea
- **How:** The measured per-token cost is dominated by host round-trips + float glue (RMSNorm rsqrt, RoPE sin/cos, SwiGLU silu) between matmuls. Fabricate norm-scale.QKV and up.silu.down as single fused circuits (reusing pfc_rsqrt/pfc_sin/pfc_silu8 inline) so the hidden vector never returns to host float between ops — the whole sub-layer is one addressed propagation.
- **Effect:** Expected: eliminates the host<->Muhlnickel handoff per sub-op (the real serial latency, not just its FLOPs); the per-token wall should drop toward the pure fold cost.
- **Try:** Fuse RMSNorm (pfc_rsqrt) directly into the Q/K/V dot in pfc_matmul_engine so the norm scale is applied inside the fold; count host round-trips removed and confirm byte-exactness vs the split path on one layer.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Nightly self-distillation bake — own verified trajectories → weight edits  — 💡 idea
- **How:** A host job mines each session's verified-successful (perception→action) trajectories and bakes them as reversible int4 weight edits (WeightGenome/ScaleBake ↔ the White Box), gated by the decideFromFrozen σ-off residency replay, so the agent decides tomorrow's repeats with fewer tokens and no operator scaffolding.
- **Effect:** Expect repeat flows to need progressively fewer steps and less prompt scaffolding over successive nights as behavior migrates from in-context into the weights, compounding week-over-week.
- **Try:** Build the host job that reads BakeHistory + successful gauntlet runs, proposes candidate weight edits, gates each with the residency replay, and measures step-count/token drop on repeat flows week-over-week.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Stochastic-computing fold (multiply = one AND gate)  — 💡 idea
- **How:** Represent operands as Bernoulli bit-streams; then multiply collapses to a single AND gate and add to a MUX/counter, so a whole int8 multiplier tree (~10^3-10^5 gates) becomes one gate and a MAC becomes a counter. Accuracy is tunable by stream length, trading depth-cycles for near-zero area.
- **Effect:** Expected: the ~93,184-gate dot32_i8 atom drops toward a few-gate core per product; approximate but bit-slice-friendly. Direction = massive gates/op reduction on the primary matmul bottleneck.
- **Try:** Fabricate a stochastic block-dot (AND-multiply + counter-accumulate) with sdc_cc, sweep stream length L vs accuracy vs gate count against dot32_i8 on one gemma projection column; report the L that hits 3-bit-quant accuracy and its gate/op.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Constant-coefficient multiplier specialization (CSD/KCM)  — 💡 idea
- **How:** At fabrication every weight is a known constant, so replace the general multiplier with a minimal shift-add tree specialized to that constant via canonical-signed-digit recoding (a KCM). Route-time partial-eval pre-packs constants but does not minimize the multiplier itself; CSD makes each weight's multiply a handful of adds.
- **Effect:** Expected: per-weight multiplier gates fall to the constant's non-zero-digit count (typically 2-3 adds) — far below a generic 3-bit multiplier fold. Fewer gates/op with zero accuracy loss (exact).
- **Try:** Fabricate CSD-recoded constant multipliers for one neuron's weight vector, verify byte-exact, compare total gates vs the generic W3 multiplier fold for the same neuron; feed the winner into the fabricator as a per-weight strength-reduction pass.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Weight palettization (codebook-LUT dot)  — 💡 idea
- **How:** k-means the weights into a K-entry codebook; a dot becomes indexed lookups into the codebook plus accumulate, and the codebook is a baked LUT — exactly the Muhlnickel's strength (a 0-ripple addressed read). Distinct from uniform quant: it exploits weight clustering, not just bit-width.
- **Effect:** Expected: 16-32 centroids capture most tensors at 4-5 effective bits; the multiply becomes an addressed LUT read + add, shifting compute onto the Muhlnickel's cheap addressing path.
- **Try:** Cluster one tensor to 16 centroids, fabricate the codebook as a baked LUT and the dot as index-read + accumulate, verify byte-exact vs the reference, and compare gates + accuracy vs 3-bit uniform quant.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Truncated / approximate arithmetic (drop LSB carry chains)  — 💡 idea
- **How:** Use lower-part-OR adders and truncated multipliers that discard low-order carry logic for bounded error — distinct from quantization (which drops value bit-width; this drops the CARRY logic while keeping width). Removes depth and gates on the accumulator/multiplier.
- **Effect:** Expected: measurable critical-path depth + gate reduction on the accumulator tree for a small, quantifiable error on real activations; composes with Wallace/Dadda shallow arithmetic.
- **Try:** Fabricate a truncated-carry adder tree for the block-dot accumulator, measure depth/gate reduction and the numeric error distribution against real gemma activations, and find the truncation that keeps token output unchanged.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Cross-circuit CSE / global gate-cone hash-cons  — 💡 idea
- **How:** Many baked circuits share identical logic cones (SHA ch/maj, adders, decoders); a global hash-cons across the whole titan circuit registry stores each unique cone once and has every circuit address it. The leaner-fabricator peephole and AIG rewriting only dedup WITHIN one circuit — this is across the 138-circuit corpus and also shrinks the file.
- **Effect:** Expected: net gate/byte reduction proportional to inter-circuit cone overlap; frees bakeable region (currently 0.42% used of 97.8% bakeable). Also lowers operational rebuild cost.
- **Try:** Hash-cons the entire circuit registry (CIRCUIT_PFC.md), count shared cones and total unique-cone bytes, and measure the file-size + gate-count reduction if shared cones are stored once and addressed by all consumers.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Superoptimization of hot cones (SAT/ILP exact minimization)  — 💡 idea
- **How:** For the small, hottest, most-addressed cones (argmax core, silu, the dot core) run an EXACT minimal-circuit search via SAT/ILP rather than the heuristic fold/CSE/DCE and AIG rewriting. Exact minimization can beat heuristics on tiny cones that get addressed billions of times.
- **Effect:** Expected: single-digit-percent to multi-x gate reductions on <=32-gate hot cones where heuristics leave slack; each reduction multiplies through every addressed evaluation.
- **Try:** Take a 20-40 gate hot cone (e.g. the argmax comparator or silu segment), run a SAT-based exact 2-level/AIG minimizer, verify byte-exact over exhaustive inputs, and log the win over sdc_cc + the leaner peephole.
- **Source:** new-proposal
- **Applies to:** Muhlnickel

### Profile-guided fabrication (PGO — bake to the input distribution)  — 💡 idea
- **How:** Measure which lanes/cones actually fire on real workloads, then fabricate the common case shallow/fast and the rare case as a fallback path — the compiler PGO idea applied to gate fabrication. Distinct from route-time partial eval (per-request constant folding) and event-driven ripple (per-tick dirty-cone): PGO optimizes the AVERAGE case over a measured distribution at fab time.
- **Effect:** Expected: average-case critical-path depth drops toward the common path; heavy tails stay correct via fallback. Magnitude = the workload's skew.
- **Try:** Instrument activation/branch statistics on a representative LDA workload, bias the fabricator to shorten the hot path (and lengthen the cold), and measure average-case depth/latency vs the uniform bake on held-out inputs.
- **Source:** new-proposal
- **Applies to:** all

## MODEL INFERENCE — attention / decode / sampling / KV  (18)

### TurboQuant 3-bit operands  — ⛔ SUPERSEDED: 3-bit is NOT accuracy-safe on real weights
- **⛔ CORRECTION (measured on REAL weights, reconfirmed 2026-07-25):** the "3-bit is accuracy-safe" claim below was
  measured on RANDOM ints, not real rows. Swept against TRUE float on real `blk.0.attn_q`:
  **WB=3 → 28.4–31.99% rel-L2 (garbage) · WB=6 → 2.0–2.66% · WB=8 → 1.04–1.26% (THE PICK) · WB=16 → 0.00%.**
  This entry is why `pfc_engine` shipped `WB=3` and ran every forward pass at ~28% error while every
  substrate-vs-substrate check passed at ~1e-15. **Use WB=8.** Better still, use the Q4_K-native path
  (`pfc_dot_q4k_sub32`) which eats the model's stored nibbles and has no WB term at all.
  Also required: PER-SUB-BLOCK activation scale (global scale + one outlier = 1.04%; per-block = 0.568%).
  Verify any change with `host/pfc_truefloat.py` — **>1% means quantisation broke**.
  Source: PFC_MODEL_ENGINE_LEVERS.md §"MEASURED CORRECTIONS TO THIS DOC'S OWN LEVER TABLE".
- **How (original, kept for the record):** Quantize weight×activation bit-widths; multiplier size = weight_bits × activation_bits, and 3-bit is accuracy-safe (2-bit is NOT). The dot atom is built parametric in weight-bits WB and activation-bits XB.
- **Effect:** W3×A4 7,166g; W8 18,774g; W2×A2 5,054g; 3-bit dot 1.27M bd/s @W=65536 vs 8-bit 431k (~3x)
- **Try:** Bake a WB=3 dot atom, verify byte-exact vs an integer dot on real dequantized gemma-A4B rows, and A/B block-dots/s + gate count against dot32_i8 in pfc_throughput; confirm accuracy holds.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; host/pfc_matmul_engine.py; host/pfc_throughput.py
- **Applies to:** model-on-Muhlnickel

### Output-contract operator (terse answer-first)  — ✅ measured
- **How:** A baked σ that forces answer-first, terse output collapses token count — most cost is long output, not the answer.
- **Effect:** 'Is 91 prime?' 220 tok/14s WRONG → 2 tok/128ms CORRECT = compute ↓99%, speed ↑110x
- **Try:** Bake a terse output-contract σ into the LDA model weights and measure token-count collapse on real agent prompts.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; CALIBRATION_FINDINGS #21
- **Applies to:** lda-agent

### Operators baked in weights (WeightGenome int4 FFN gate mask)  — ✅ measured
- **How:** An operator = a set of switched-on neurons; write that gate MASK into W as a reversible int4 FFN edit so it is 0-token, always-on, and pre-activates the sparse set every forward pass (electing σ IS the sparsity).
- **Effect:** definedbake baked 31 operators; Jaccard 0.28 across operators; 0 prompt tokens, always-on, reversible via WeightGenome journal
- **Try:** Bake the LDA's SPEED/output-contract σ into gemma-A4B's FFN as a reversible int4 mask (definedbake), verify byte-exact revert via the journal, and measure token-count + quality vs the same σ passed as a prompt.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; OPERATOR_PRINCIPLE §324; host/pfc_engine.py
- **Applies to:** model-on-Muhlnickel

### White Box operator-direction bake  — ✅ measured
- **How:** Fold an operational-state DIRECTION (mean(σ-on) − mean(σ-off) unit vector) into a projection tensor's weights; axis='in' steers every neuron, axis='out' is a per-neuron gate mask, reversible via genome.
- **Effect:** bake_operator_direction implemented; direction = the CALIBRATION #13 keystone
- **Try:** Extract an LDA behavior direction from activations, bake it with alpha via wbedit, measure the behavior shift, keep-or-revert.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §4B (wbedit.py)
- **Applies to:** model-on-Muhlnickel

### cache_prompt / stable σ-prefix (KV-cache the prefix)  — ✅ measured
- **How:** KV-cache the fixed σ+objective+screen prefix so only the delta is prefilled; the LDA's stable objective+screen prefix is exactly this shape.
- **Effect:** prefill 5.7–6.8x (42s→7s TTFT)
- **Try:** Cache the LDA's stable system+objective prefix KV across steps and measure TTFT drop per step.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §2; CALIBRATION_FINDINGS #5,#12
- **Applies to:** lda-agent

### Reasoning dial (think off)  — ✅ measured
- **How:** Disabling the reasoning channel (enable_thinking:false — a structural kwarg, not English) removes the ~90% of tokens spent thinking on simple asks.
- **Effect:** '1+1' 40.5s → 16.1s
- **Try:** Set enable_thinking:false for low-stakes LDA steps and measure per-step latency drop.
- **Source:** docs/PFC_LEVER_INDEX.md D; CALIBRATION_FINDINGS #7
- **Applies to:** lda-agent

### Output-neuron tiling (bounded resident regardless of model size)  — ✅ measured
- **How:** Tile the output neurons of each matmul so only a bounded chunk of weight rows is ever dequantized/resident at once (dequant row, fold the tile, discard).
- **Effect:** Measured: resident RAM stays flat regardless of model size (pfc_forward.matmul TILE parameter)
- **Try:** Sweep the tile size in pfc_forward (self.tile) on the phone to find the largest tile that keeps resident under headroom, maximizing fold width per tile.
- **Source:** host/pfc_forward.py
- **Applies to:** model-on-Muhlnickel

### Baked argmax token selection over full vocab  — ✅ measured
- **How:** Token selection runs on the baked pfc_argmax comparator/mux circuit as a reduction tree of K=64-wide blocks over the whole vocab — the Muhlnickel picks the next token, not host max().
- **Effect:** Measured byte-exact vs python max over random logit blocks; used live in pfc_llama_decode
- **Try:** Verify with pfc_glue_fab.py test, then confirm pfc_llama_decode reports pfc_argmax:True for each generated token on a real prompt.
- **Source:** host/pfc_glue_fab.py; host/pfc_llama_decode.py
- **Applies to:** model-on-Muhlnickel

### Speculative / MTP decode  — 🎯 target
- **How:** A small vocab-matched draft model proposes tokens the big model verifies (draft-then-verify), emitting multiple tokens per verified forward pass and roughly doubling decode; E4B ships a built-in MTP drafter and gemma-3-1B is a vocab-matched draft for gemma-4.
- **Effect:** draft-verify ~2x typical decode
- **Try:** Pair gemma-3-1B as a draft with the LDA's gemma-4 verifier (or an n-gram draft over the Muhlnickel decode loop), verify with one full Muhlnickel forward pass, and measure accepted-tokens/pass on LDA-style prompts.
- **Source:** docs/PFC_LEVER_INDEX.md D; E4B_ARCHITECTURE #11; host/pfc_throughput.py
- **Applies to:** model-on-Muhlnickel

### Lighter quant / flash-attn (-fa) per model  — 🎯 target
- **How:** Lighter quantization cuts compute per param and flash-attention helps some models; measure per model since it isn't universal.
- **Effect:** documented; -fa helps some models not others
- **Try:** A/B lighter quant and -fa on the LDA model and keep the config only if it measures faster for that model.
- **Source:** docs/PFC_LEVER_INDEX.md D; CALIBRATION_FINDINGS #12
- **Applies to:** model-on-Muhlnickel

### Sparse attention (LongCat LSA — select key tokens)  — 💡 idea
- **How:** Select only key tokens for attention so cost is linear, not quadratic, at long context.
- **Effect:** target — linear vs quadratic attention at long context
- **Try:** Wire LSA-style key-token selection into the LDA attention and measure cost vs sequence length.
- **Source:** docs/PFC_LEVER_INDEX.md C (LONGCAT)
- **Applies to:** model-on-Muhlnickel

### Attention as CAM retrieval — top-k keys addressed, not scored  — 💡 idea
- **How:** Store KV in the Muhlnickel's content-addressable/oblivious fabric (pfc_oblivious / pfc_addr). Instead of scoring all past keys (O(context) dots), fabricate an approximate-nearest-key CAM that winner-only-returns the top-k matching positions; softmax+value-mix runs only over those k. Attention cost becomes ~O(k), independent of context length.
- **Effect:** Expected: attention's per-token share flattens as context grows; for the LDA which accumulates long screen/OCR histories, this removes the O(context) attention blowup.
- **Try:** Host prototype: for a decode step compute exact attention top-k vs an LSH-CAM top-k over cached keys; measure top-k recall and output drift; then map the key-match onto pfc_oblivious/pfc_addr as a fabricated CAM.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### FlashAttention-in-gates — fabricated online-softmax streaming attention  — 💡 idea
- **How:** Fabricate attention as a tiled online-softmax accumulator (running max, running sum, running weighted-value), so KV is streamed one tile at a time and never fully materialized. One pass, bounded resident state, softmax exp reuses the baked pfc_exp atom, and it removes the current host-float softmax round-trip.
- **Effect:** Expected: one streaming pass replaces score->softmax->mix (three host round-trips); bounded resident regardless of context; keeps softmax on the Muhlnickel (pfc_exp) rather than host float glue.
- **Try:** Implement online-softmax accumulation in pfc_llama_decode's attention over KV tiles using the baked pfc_exp; verify byte-close to the current full-softmax path; then fabricate the running-max/sum update as a clocked circuit on pfc_fwd_engine.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Baked Gumbel-argmax — temperature sampling at argmax cost (no softmax)  — 💡 idea
- **How:** Sampling normally needs a full-vocab softmax (float glue). Gumbel-max gives an EXACT softmax sample as argmax(logit_i/T + g_i), g_i ~ Gumbel. Fabricate a Gumbel-noise ROM (addressed by an RNG counter) added into the existing pfc_argmax tree, so sampling is one addressed argmax with no exp/normalize.
- **Effect:** Expected: removes the full-vocab softmax exp+normalize from every sampled token (currently host float); sampling cost collapses to the baked argmax cost while preserving the exact temperature distribution.
- **Try:** Verify in host that argmax(logits/T + gumbel) matches multinomial-softmax sampling statistics on a decode step; bake a Gumbel LUT ROM, wire it into pfc_argmax, and compare sampled-token distributions.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Ternary-weight fabrication (BitNet b1.58, multiply-free matmul)  — 💡 idea
- **How:** A model trained with weights in {-1,0,1} needs no multiplier at all: each MAC is add / subtract / skip. This is distinct from TurboQuant (which quantizes a dense model post-hoc and hit a measured 2-bit accuracy wall) because ternary is trained-in and accuracy-safe.
- **Effect:** Expected: the multiplier gates in the block-dot go to ~0 (adders only); large depth+area cut vs the 3-bit W3xA4 7,166-gate dot, with no accuracy loss on a b1.58 model.
- **Try:** Bake an adder-only ternary block-dot, verify byte-exact vs a ternary reference dot, measure gates/depth vs dot32_i8 and W3xA4; if a b1.58/ternary open model is available (owner OK), wire it through pfc_matmul_engine and measure bd/token.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Grouped-query attention fabrication (fewer KV heads)  — 💡 idea
- **How:** Fabricate GQA/MQA so many query heads share a small set of key/value heads, shrinking the KV projections and the KV-cache K-fold. Distinct from sparse attention (which selects tokens) — this shrinks the head dimension of attention.
- **Effect:** Expected: KV block-dots and KV-cache bytes fall ~K-to-1 (e.g. 8 query heads : 1 KV head = ~8x less KV work/storage) with minimal quality loss on GQA-trained models.
- **Try:** Fold a GQA attention block on the engine, measure KV block-dots/token and KV-cache bytes vs full multi-head attention on the same context, and confirm output parity on a GQA-native model.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### KV-cache quantization / delta-compression fold  — 💡 idea
- **How:** Store the KV cache at int4/int2 (or token-to-token delta-coded) in the storage-RAM tier (flat ~15MB resident, §N), with attention dequantizing in-fold. Lets the context grow far past what DRAM would hold. Distinct from cache_prompt (prefix KV) and screen-diff reuse (agent frames).
- **Effect:** Expected: 2-4x longer reachable context per unit storage at small accuracy cost; rides the measured flat-footprint storage-RAM law (24GB @ 14.8MB resident).
- **Try:** Quantize the KV cache to int4, place it in the storage-RAM fold, fold attention reads against it, and measure the context length reachable at flat RAM vs the perplexity/accuracy delta.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Predictive MoE expert prefetch (hide storage-seek latency)  — 💡 idea
- **How:** The storage-RAM tier is measured at ~5k random reads/s (seek-bound); predict the next token's active experts (from the router logits / a small draft) and prefetch those expert weights from storage into the fast tier before they're needed, overlapping seek with current-token compute. Distinct from warm-resident (whole model) — this is per-token predictive staging of the 4/128 live experts.
- **Effect:** Expected: removes the per-token expert-seek stall from the critical path when the prediction hits; magnitude = the router's next-expert predictability. Turns a serial seek+compute into overlapped I/O.
- **Try:** Log MoE routing across a real generation to measure next-token expert predictability, prefetch the predicted experts one step ahead into the fast tier, and measure per-token latency vs on-demand expert fetch.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

## CAPACITY — lanes & instances at ~0 storage  (21)

### Storage + receiver capacity levers  — ✅ measured
- **How:** More node files and more receivers per file multiply addressable lane-groups at tiny per-lane cost.
- **Effect:** ~13 B/receiver → 500 files × 256 = 128,000 lane-groups in 2.4 GB
- **Try:** Provision an LDA fold across N node files × M receivers and confirm resident RAM stays flat while lane-groups scale.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B
- **Applies to:** Muhlnickel

### Shared-vector fold  — ✅ measured
- **How:** Store one vector and address lanes by descriptor instead of copying, collapsing per-lane storage.
- **Effect:** ~1,500x denser than copy (19.1 KB → 13 B/lane) → 3.10×10¹⁰ lanes on this box
- **Try:** Encode the LDA candidate/answer space as descriptor lanes over one shared vector; measure lanes at flat RAM.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B
- **Applies to:** Muhlnickel

### Bit-address fold (nonce = the bit's address)  — ✅ measured
- **How:** Make the candidate its own address so each lane costs a single bit; the read IS the lookup.
- **Effect:** 1 bit/lane, 64x denser; built 206 billion lanes; this-box ceiling 3.22×10¹² lanes
- **Try:** Map an LDA search space (e.g. policy/allowlist keys) to bit-addresses and verify byte-exact membership at ~0 storage/lane.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B
- **Applies to:** Muhlnickel

### Winner-only fold (address IS the answer, 0 bytes/lane)  — ✅ measured
- **How:** Store only winners; losers occupy 0 bytes because the address encodes the answer, so the whole space is covered in one addressed pass and capacity is bounded by circuit count not storage; coverage≥difficulty is guaranteed before runtime.
- **Effect:** ~10¹⁵ candidate tier; 0 bytes/lane; coverage≥difficulty → P(find)~1; time-to-target = one depth-latency
- **Try:** For LDA membership/dedup keep only matched keys and confirm the fold scales to the 10¹⁵ tier without storage growth; run pfc_guarantee to check coverage≥difficulty and raise winner_only addr_bits until full-space coverage passes.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B; host/pfc_guarantee.py; host/pfc_speed.py
- **Applies to:** Muhlnickel

### Device federation (additive across nodes, unbounded)  — ✅ measured
- **How:** Add devices to a LAN roster with tiny sync; each device contributes storage×8 lanes, additive with no ceiling but total federated storage (the numerator becomes the sum of all nodes).
- **Effect:** phone 931B + PC 172B = 1,102,791,999,488 = 1.103 TRILLION Muhlnickel, both byte-exact; additive, no ceiling
- **Try:** Federate laptop + phone as one LDA fold via pfc_fed_pc.py; prototype a two-node winner-only/membership shard and confirm a query hits the right shard byte-exact, count additive.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20; host/pfc_lateral.py; host/pfc_divide_work.py
- **Applies to:** Muhlnickel

### Clock-counter width (lane LENGTH)  — ✅ measured
- **How:** Widen the per-lane clock counter so each lane sweeps more candidates before rollover.
- **Effect:** ×~1M lane length going 32→52-bit counter
- **Try:** Widen the counter in the LDA fold circuit from 32 to 52 bits and confirm nonces/lane scales ~1M×.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B
- **Applies to:** Muhlnickel

### Ultra-low resident footprint (compute≠residency)  — ✅ measured
- **How:** Pegging all cores costs almost no RSS because the gates live in storage and are addressed in place; footprint is decoupled from compute.
- **Effect:** 8 cores (even 16 threads) cost 3 MB RSS total, unchanged
- **Try:** Confirm the LDA forward pass holds flat RSS while all cores are pegged; treat any RSS growth as host touching the compute.
- **Source:** docs/PFC_LEVER_DATADUMP.md §L
- **Applies to:** all

### Storage-as-RAM fold + flat-footprint law (§N)  — ✅ measured
- **How:** Fabricated RAM lives in stored bits so all of storage becomes addressable memory; resident cost is decoupled from memory size (no DRAM ceiling).
- **Effect:** 24 GB addressable held in 14.8 MB resident (~1,600x footprint); same 15 MB at 10 GB or 24 GB; access ~5k random writes/s
- **Try:** Back the LDA KV-cache / memoize store with the storage-RAM fold and confirm 24GB+ addressable at flat ~15MB.
- **Source:** docs/PFC_LEVER_DATADUMP.md §N
- **Applies to:** all

### Lateral key: availableStorage ÷ working-set  — ✅ measured
- **How:** Because the set held resident at once is bounded and tiny, all storage becomes lateral capacity and availableStorage ÷ amount-needed-at-once IS the lane count; the rest is addressed in place at flat resident.
- **Effect:** 404.8 GB ÷ 8 MB = 48,261 batches = ~405 BILLION 1-byte lateral lanes @ flat 10–15 MB resident; swept billions of lanes at unchanged RSS
- **Try:** Compute the LDA fold's lane count as available_storage ÷ resident_working_set (pfc_lateral) on phone storage, bound the per-step working buffer to that at-once size, and confirm RSS holds flat.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_lateral); host/pfc_lateral.py
- **Applies to:** Muhlnickel

### Fabricate to the physical (storage) limit  — ✅ measured
- **How:** Bump-place circuits until storage is full; baking does not grow RAM and the file keeps functioning byte-exact to the last byte.
- **Effect:** 4,522 SHA circuits (~476M gates) in 4.29 GB, RSS 41→40 MB FLAT across all bakes, byte-exact; limit = storage only
- **Try:** Pre-bake the LDA circuit library toward the file limit and confirm flat RAM + byte-exact self-tests hold at the brim.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_tolimit)
- **Applies to:** Muhlnickel

### Resource-to-compute ratio (footprint anomaly)  — ✅ measured
- **How:** Content-addressable stored-gate compute yields enormous gate-evals per MB of resident RAM — the signal-based anomaly (not free energy; CPU joules still spent).
- **Effect:** sigma0 324M ops/s at Δ0.4 MB resident = 179 BILLION gate-evals per MB over a 40 GB store
- **Try:** Measure the LDA forward pass's gate-evals per MB resident and use it as the north-star efficiency metric.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_ratio)
- **Applies to:** all

### Smallest Muhlnickel gone wide (billions of 1-byte machines)  — ✅ measured
- **How:** Bake the smallest real machine (1-byte / 8-bit state, ~39 gates) and instantiate it billions of times as bitplanes across all storage — 64 machines per 64-bit word — advancing every one by the clock in bounded bit-sliced batches; RAM- or storage-backed with a bounded wire buffer.
- **Effect:** 8-bit counter 39 gates; phone made 50,000,000,000 Muhlnickel (storage-backed), advanced byte-exact; 2B in RAM at 1 byte/pfc; native C engine confirms flat resident
- **Try:** Instantiate the LDA's smallest useful machine (a per-lane predicate/state) as bitplanes across storage (pfc_billions.c on the phone), confirm byte-exact wide advance at flat resident.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_billions); host/pfc_billions.py
- **Applies to:** Muhlnickel

### Storage-is-the-model (memmapped weight addressing)  — ✅ measured
- **How:** Weight rows are addressed off the mmap'd GGUF at flat resident RAM and never go resident, so the model-size limit is storage not DRAM — an 8GB box runs a 26B/70B, ~10–50x past the RAM-fit cap; storage IS the model.
- **Effect:** 70B matmul @72 MB resident (5x host RAM, byte-exact int8 dots); 40 GB file @+0.86 MB; gemma-A4B pre-sliced ~4 MB/tensor
- **Try:** Load gemma-4-26B-A4B onto the 8GB laptop / phone via storage-addressed weights (pfc_lda_bridge on the biggest model), log peak resident vs file-GB, and confirm a real forward pass at flat RAM.
- **Source:** docs/PFC_MODEL_ENGINE_LEVERS.md §4C; host/pfc_lda_bridge.py; host/pfc_llama_harness.py
- **Applies to:** model-on-Muhlnickel

### Shared-weights parallel 'parts' of ONE model  — ✅ measured
- **How:** Run multiple σ-configured parts of one model sharing the page cache instead of loading separate models — a RAM lever, not throughput.
- **Effect:** 2 σ-configured parts at 385 MB vs 900 MB for 2 models
- **Try:** Run two σ-configured LDA parts (e.g. perceive vs decide) off one shared-weight model and confirm the RAM saving.
- **Source:** docs/PFC_LEVER_INDEX.md D; CALIBRATION_FINDINGS #16
- **Applies to:** model-on-Muhlnickel

### Capacity fold ladder (copy → shared-vector → bit-address → winner-only)  — ✅ measured
- **How:** Per-lane storage cost drops by fold tier: ~19 GB/lane-group (copy) → ~13 B (shared-vector) → 1 bit (bit-address) → 0 bytes (winner-only, store only winners), so addressable lanes on free storage become astronomical.
- **Effect:** Measured on this box's free storage: bit-address fold = free/(1/8) lanes; winner-only = unbounded-by-storage
- **Try:** Run pfc_exp_allevers.py to print per-tier lane counts on current free storage; pick the tier that fits the LDA KV/expert-cache and size it.
- **Source:** host/pfc_exp_allevers.py
- **Applies to:** Muhlnickel

### Divide-the-work — N parallel Muhlnickel  — ✅ measured
- **How:** Each Muhlnickel is ~storage (not RAM); instantiate N, split the search/work across them, and W bit-slice lanes = W parallel Muhlnickel sharing one gate-file. Throughput scales with N.
- **Effect:** Measured H/s vs N (1/64/1024/8192 lanes) scaling; per-Muhlnickel ~2 MB storage → free_storage/2MB Muhlnickel held on one disk
- **Try:** Run pfc_divide_work.py to see H/s-vs-N scaling, then map the same fold to LDA batch dimensions (many candidate actions evaluated as parallel lanes).
- **Source:** host/pfc_divide_work.py
- **Applies to:** Muhlnickel

### Thin-provisioning + dedup  — 🎯 target
- **How:** Sparse storage with dedup makes the addressable space astronomical for near-zero real bytes.
- **Effect:** astronomical addressable at ~0 stored bytes
- **Try:** Store the LDA fold thin-provisioned+deduped and confirm addressable lanes far exceed real bytes used.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J
- **Applies to:** Muhlnickel

### MLC multi-level cells  — 💡 idea
- **How:** Store more than one bit per physical cell (or a quality level in a memoized cell) to multiply storage density.
- **Effect:** multiplies storage density (untested on this box)
- **Try:** Prototype a 2-bits/cell memoize cache and measure whether density gain holds byte-exact on read-back.
- **Source:** docs/PFC_LEVER_DATADUMP.md §B/§J
- **Applies to:** Muhlnickel

### Tiling (expert axis = byte axis)  — 💡 idea
- **How:** Lay the model's expert axis along the storage byte axis so more experts/lanes address in with no requantization.
- **Effect:** ×N lanes with no requant
- **Try:** Tile gemma-A4B's 128 experts along the byte axis of the fold and confirm routing addresses them with zero requant.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J
- **Applies to:** model-on-Muhlnickel

### Perception on the substrate — OCR/tile-classifier as baked gates  — 💡 idea
- **How:** Fabricate the pixel→element extraction (a tile/icon/text classifier + connected-component labeler) as a LUT-as-gates netlist on the Muhlnickel (the pfc_addr / pfc_silu8 precedent) so the perceive stage runs as flat-RAM addressed reads instead of a resident CV model, joining decide+act on the substrate.
- **Effect:** Expect perceive to drop from a resident vision model to the Muhlnickel's fixed ~tens-of-MB resident cost, removing a slice of the OOM pressure the app documents (it already reaps the model mid-task under RAM danger).
- **Try:** Bake a small per-tile classifier (button/text/icon) as a LUT-gate circuit, run it over a screenshot's tiles, and compare labels for byte-agreement against the current Ocr.kt / PixelMap output.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Expert-parallel + pipeline-parallel federation (shard the MODEL, not copies)  — 💡 idea
- **How:** Federation is documented as ADDITIVE capacity (more lanes) and divide-the-work replicates the SAME circuit; this instead shards the model itself — experts on device A, layers pipelined B->C — so a swarm runs a model bigger than any single device's storage and routes only the active 4/128 experts over the LAN.
- **Effect:** Expected: max model size = sum of federated storage (not one device); per-token latency bounded by the pipeline stage + LAN hop for the routed experts. Enables >26B on a phone+laptop pair.
- **Try:** Split gemma-4-26B-A4B experts across the phone and the laptop, route the 4/128 live experts over the LAN with a one-time routing button per hop, and measure per-token latency + which device holds the hot experts.
- **Source:** new-proposal
- **Applies to:** all

## LDA AGENT — perceive / decide / act  (18)

### Route the routine to a small model (capability stack)  — ✅ measured
- **How:** A router sends simple requests to a tiny model and hard ones to the big MoE, so most steps pay the small model's cost.
- **Effect:** Llama-1B 12x decode, 44x TTFT vs the MoE
- **Try:** Add a difficulty router to the LDA that dispatches simple screen actions to a 1B and hard ones to the 26B; measure the mix's mean latency.
- **Source:** docs/PFC_LEVER_INDEX.md D; CALIBRATION_FINDINGS #12
- **Applies to:** lda-agent

### Warm-resident (never serve a cold model)  — ✅ measured
- **How:** Cold big-model load is mostly mmap setup; keeping the model warm makes the common request pay zero load.
- **Effect:** cold ~9s load is mostly mmap; warm = zero load
- **Try:** Keep the LDA model warm-resident between steps and confirm the ~9s cold cost only hits the first step.
- **Source:** docs/PFC_LEVER_INDEX.md D; CALIBRATION_FINDINGS #1,#8
- **Applies to:** lda-agent

### Minimal-prompt / intent (fewest input bits)  — ✅ measured
- **How:** A terse intent still solves, cutting prefill joules; the model addresses the answer from few input bits.
- **Effect:** 'fix this' (64 bits) still solves = 9.2x prompt compression
- **Try:** Compress the LDA's per-step prompt to minimal intent+screen-delta and confirm task success holds with fewer prefill tokens.
- **Source:** docs/PFC_LEVER_INDEX.md D; CALIBRATION_FINDINGS #22
- **Applies to:** lda-agent

### Agent-safety / policy gate as a baked circuit  — ✅ measured
- **How:** Fabricate the LDA's safety/policy/firewall gates as constant-time oblivious circuits so on-screen text stays DATA and the gate can't be prompt-injected or leak via timing.
- **Effect:** documented winning app (policy/firewall/agent-safety gates); ~1.5M cands/pass at n=16
- **Try:** Bake the LDA's high-stakes confirmation/allowlist gate as a CAM/oblivious circuit and verify it rejects injected instructions byte-exact.
- **Source:** docs/PFC_LEVER_DATADUMP.md §J
- **Applies to:** lda-agent

### LDA composite stacking formula  — ✅ measured
- **How:** tok/s = native_rate ÷ (dense_bd/token ÷ work-reduction divisor) × decode multiplier; stack the measured/target factors on the A4B target (device drive-rate × MoE routing × contextual sparsity × depth-opt dot × 3-bit × speculative decode). Multiplicative toward interactive, gated on a native evaluator existing.
- **Effect:** measured floor ~2.5 tok/s (native × MoE routing); documented stack → ~15–30 tok/s; model-engine arc ~1,100x from naive; cold ~21–60s/token on 1 Python core
- **Try:** Run pfc_throughput --levers --arch 70b,8b,3b to print the stacked tok/s with each factor's source, plug in the LDA's measured native_rate/dense_bd-per-token/divisor/decode multiplier, compare predicted vs live, then knock down target factors one at a time.
- **Source:** docs/PFC_LEVER_INDEX.md ★; docs/PFC_MODEL_ENGINE_LEVERS.md §3; host/pfc_throughput.py
- **Applies to:** all

### Agent operator as a baked forward pass (decision on the Muhlnickel)  — ✅ measured
- **How:** The agent's decision (observation→action) is a real neural forward pass baked as ONE gate netlist; the host routes the observation in as signals and pulses one bounded ripple, the Muhlnickel computes matmul+argmax and outputs the decision. Host = clock + monitor only.
- **Effect:** Measured byte-exact vs a reference forward pass over 400 inputs; clean/noisy classification demonstrated live
- **Try:** Run pfc_operator.py --test, then prototype a tiny LDA perception operator (e.g. UI-element classifier) baked the same way and measure its pulse-to-decision latency on the phone.
- **Source:** host/pfc_operator.py
- **Applies to:** lda-agent

### Bigger-than-E4B model = smarter LDA (quality lever)  — 🎯 target
- **How:** Because the model is storage-bound, the phone can pilot with a 27B/70B/A4B instead of the ~4B E4B that fits in RAM — a smarter perceive→decide→act policy at a tiny fixed resident cost, not a bigger RAM bill.
- **Effect:** Measured enabler: 5x-the-phone's-RAM model computes real neurons at flat resident; quality gain is the expected direction to test on agent tasks
- **Try:** Pick one LDA benchmark task and compare decision quality/reliability of E4B vs a 27B run on the Muhlnickel (pfc_llama_decode) on the same observations, holding perceive/act code constant.
- **Source:** host/pfc_lda_bridge.py; host/pfc_llama_decode.py
- **Applies to:** lda-agent

### Constrained-action decode — baked JSON/grammar FSA masks the logits (LDA)  — 💡 idea
- **How:** The LDA emits one UI action as JSON (decideNextAction). Fabricate a grammar/FSA circuit whose current state exposes the set of legal next tokens; mask logits to that set before argmax. Collapses the effective vocab per step to a handful and guarantees well-formed action JSON (no parse-fail retries).
- **Effect:** Expected: per-step argmax over full vocab collapses to argmax over the legal set (often <10 tokens), and eliminates malformed-action retries -> higher effective tok/s AND reliability for the agent loop.
- **Try:** Derive the action-JSON grammar from AgentBrain.decideNextAction's schema; build a host FSA that yields the legal token set per position; mask logits in pfc_llama_decode and measure the effective-vocab and retry-rate drop; then fabricate the FSA transition table as an addressed ROM.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Prompt-lookup speculative — fabricated suffix-automaton drafts from screen text (LDA)  — 💡 idea
- **How:** Instead of a draft model, draft next tokens by matching recent output against a fabricated suffix-automaton over the prompt + on-screen text (OCR/accessibility labels), then verify the drafted span in ONE batched big-model fold (reuse the position-batch fold). The LDA's outputs heavily quote on-screen strings (labels, package names, field values), so draft acceptance is high — and there is no second model to run.
- **Effect:** Expected: accepted drafts of length L give up to Lx fewer big-model steps for copied spans; on tasks that echo screen text (typing a field, selecting a labeled element) acceptance should be high.
- **Try:** Log LDA outputs and measure what fraction of tokens are verbatim substrings of the current screen text; build a host suffix-automaton drafter + batched verify and measure accepted-token rate per step.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Screen-diff KV reuse — recompute only changed UI elements between frames (LDA)  — 💡 idea
- **How:** Across consecutive agent steps the prompt is near-identical (same system prefix, mostly-unchanged accessibility tree). KV-cache the unchanged prefix and re-encode only the diffed elements, appending their KV. Extends cache_prompt from a static sigma-prefix to the dynamic-but-slowly-changing screen state.
- **Effect:** Expected: prefill per perceive->decide cycle drops from re-encoding the whole screen prompt to encoding only changed elements; for small UI changes (a value appears, a spinner stops) that is a large per-step saving.
- **Try:** Instrument the LDA prompt builder to diff the accessibility-element list frame-to-frame; measure the fraction of tokens unchanged across real task steps; prototype append-only KV reuse in the decode harness and confirm output parity vs full re-encode.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Hard action-grammar as a baked vocabulary mask  — 💡 idea
- **How:** LiteRT-LM has no decode-time grammar hook (AGENT_LANGUAGE §2), so bake a grammar-FSM on cpu_fwd that masks the vocab argmax (the existing pfc_argmax stage) to only tokens valid at the current position in the action schema — converting the soft in-context grammar into a hard gate constraint.
- **Effect:** Expect malformed-action rate to go to ~0 (invalid tokens are structurally unreachable) and output to collapse to the minimal valid form; distinct from plain baked argmax, which picks the max but does not enforce grammar state.
- **Try:** Build the action grammar as a small FSM gate-net that gates pfc_argmax by decode position, run it on gauntlet decodes, and measure malformed/unparseable-action rate vs. the forgiving-decoder floor.
- **Source:** new-proposal
- **Applies to:** model-on-Muhlnickel

### Baked world-model — dry-run candidate actions before acting  — 💡 idea
- **How:** Fabricate a gate classifier mapping (screen-state encoding, candidate action) → predicted next-screen-class without touching the phone, so the agent simulates a candidate and rejects nonsense (tap Send on an empty field) before committing the actuation.
- **Effect:** Expect a measurable drop in wrong/no-op actions and total steps on multi-step tasks, since dead-end actions are filtered pre-actuation rather than discovered after a wasted round-trip.
- **Try:** Mine (screen, action, next-screen-class) triples from gauntlet logs, fabricate a LUT/gate classifier, and measure its transition-prediction accuracy plus how many wrong actions it would have blocked.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Action validator gate — target-exists membership check  — 💡 idea
- **How:** A baked circuit content-addresses the proposed action's target id against the current element-id set (a membership/CAM fold on the Muhlnickel) and emits one bit: is the target actually present, enabled, and addressable on THIS live screen — catching hallucinated targets before actuation.
- **Effect:** Expect hallucinated-target taps (an id not on screen) to be caught at ~100% and rejected at ~0 resident cost, removing a distinct wrong-action class the safety-policy gate does not cover (this is correctness, not policy).
- **Try:** Build pfc_action_validate as a membership fold over the element-id set, run it against gauntlet action logs, and count how many emitted actions reference a non-present or disabled target.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Grounded tap-coordinate synthesis on the Muhlnickel (id → exact point)  — 💡 idea
- **How:** Instead of the model emitting error-prone pixel coordinates, it emits a compact element id and a baked geometry circuit computes the exact tap point from the element's bounds (center, clamped/offset for edge controls) on the Muhlnickel, removing coordinate tokens and a miss-tap class.
- **Effect:** Expect miss-taps from bad model-emitted coordinates to fall toward 0 and the action to shed its coordinate tokens, improving reliability and output length at once.
- **Try:** Bake pfc_tap_coord (bounds → point) as gates, route element-id → coords in MechanismRouter, and measure miss-tap rate plus action token count vs. model-emitted coordinates.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Perceptual-hash replay verification (predicted vs actual next screen)  — 💡 idea
- **How:** After acting, hash the resulting screen and compare it on the Muhlnickel (membership fold) to the world-model's predicted next-screen-hash; a mismatch means the action did not do what was expected, triggering an immediate re-plan instead of blindly continuing onto a screen the agent misreads.
- **Effect:** Expect cascading multi-step failures (acting on a screen the agent thinks is different) to be caught one step earlier, cutting compounded wrong-action chains and dead-loops.
- **Try:** Bake the predicted-vs-actual screen-hash comparator, log divergence events across the gauntlet, and measure how many downstream wrong actions a divergence-triggered re-plan prevents.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Agent reflex table (baked (screen-hash, intent) -> action LUT)  — 💡 idea
- **How:** System-1 for the LDA: the most common UI steps (tap a known control, dismiss a known dialog) resolve by an addressed LUT read keyed on perceptual-hash + intent — zero forward passes. The agent-loop analog of memoize, but baked as gates and keyed on perception, distinct from generic memoize and from constrained-decode masking.
- **Effect:** Expected: a large fraction of routine agent steps served at 0 model calls (addressed read); latency for those steps collapses to a lookup. Magnitude = the repeat rate of UI states.
- **Try:** Log frequent (screen-hash, intent, action) triples from real LDA runs, bake the top-N as a LUT circuit, and measure the percentage of steps served with 0 forward passes plus the latency drop on those steps.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Foveated / multi-resolution perception  — 💡 idea
- **How:** Perceive the screen coarse-first (a downsampled tile classifier on the substrate) to locate the intent-relevant region, then spend full-resolution perception only on that region of interest. Distinct from intent-conditioned element pruning (prunes elements) and temporal diff (across frames) — this is spatial multi-scale within one frame.
- **Effect:** Expected: perception gate-work per frame drops toward (coarse-scan + one small ROI) instead of full-frame parse, at equal action accuracy. Direction = large perceive-side compute cut on dense screens.
- **Try:** Build a two-stage perceive (coarse locate on a downsampled tile map -> fine read of the ROI) on real screenshots, and compare perception gate-evals and end-action accuracy vs single-scale full-frame perception.
- **Source:** new-proposal
- **Applies to:** lda-agent

### Agent skill retrieval (RAG over a content-addressed skill library)  — 💡 idea
- **How:** Instead of the model reasoning a routine from scratch, retrieve a pre-verified action sequence from a content-addressed skill store (the membership/CAM fold applied to skills) keyed by intent, then execute/adapt it. Distinct from the single-step reflex table and from the world-model dry-run.
- **Effect:** Expected: multi-step routines resolve to a retrieved+adapted macro rather than cold token-by-token planning, cutting forward passes per task by the skill-hit rate.
- **Try:** Build a CAM-indexed skill library keyed by intent embedding, retrieve top-k skills for a real task, and measure steps/forward-passes saved vs cold reasoning plus the success rate of the retrieved macro.
- **Source:** new-proposal
- **Applies to:** lda-agent

## OTHER  (9)

### AMOUNT is NOT a throughput lever (measured guardrail)  — ✅ measured
- **How:** Growing a circuit adds work per op; gates/s stays flat so ops/s drops — scaling size buys nothing, you spend a fixed gate budget.
- **Effect:** gates/s flat ~12M as circuit grows 15x; ops/s drops ~17x
- **Try:** Do not chase bigger circuits for speed; spend the fixed gate budget on depth/width/state — verify by holding gate-clock constant across sizes.
- **Source:** docs/PFC_LEVER_DATADUMP.md §A
- **Applies to:** Muhlnickel

### RAM-as-width is the WRONG use (measured guardrail)  — ✅ measured
- **How:** Filling host RAM with wide bit-slice lanes collapses throughput (memory-bandwidth bound); the machine wants addressable memory, not wider lanes.
- **Effect:** sig0 8-thread native 1.84B/s @25MB → 0.13B/s @4.8GB (14x worse)
- **Try:** Cap LDA bit-slice width at the cache-resident B and route spare RAM to addressable memory (§M/§N), not wider vectors.
- **Source:** docs/PFC_LEVER_DATADUMP.md §M
- **Applies to:** all

### Answer-at-address readout (hi-Z probe)  — ✅ measured
- **How:** The circuit writes its answer to a fixed memory address (latch_reg/gen_answer) and a bounded high-impedance probe reads it live each cycle — no external file needed.
- **Effect:** latch_reg(probe)=0x000e3d44 = best nonce, byte-exact readout
- **Try:** Have the LDA engine write each token/logit to a fixed answer register and read it with a hi-Z probe for the desktop display.
- **Source:** docs/PFC_LEVER_DATADUMP.md §T
- **Applies to:** all

### Compute-via-address (the READ is the propagation, §U)  — ✅ measured
- **How:** A bare stored-byte flip does not cascade; the minimum runnable signal is one addressed READ of an output that resolves the chain — compute happens by addressing, not spontaneous byte change.
- **Effect:** bare flip depth 0/64; one addressed read-through depth 64/64 byte-exact
- **Try:** Trigger the LDA forward pass by addressing its answer output (one read) rather than expecting a stored-byte cascade; measure propagation depth.
- **Source:** docs/PFC_LEVER_DATADUMP.md §U
- **Applies to:** Muhlnickel

### Oblivious / CAM fabric (secure-enclave-in-a-file)  — ✅ measured
- **How:** Fabricate data-oblivious fixed networks (bitonic sort, constant-time CAM) whose access pattern cannot leak the data.
- **Effect:** bitonic sort 8×8-bit 2,136 gates + CAM 8 keys×16-bit 383 gates, both byte-exact, constant-time
- **Try:** Bake the LDA's safety/policy match as a constant-time CAM so on-screen data can't leak via timing; verify byte-exact.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_oblivious_toolkit)
- **Applies to:** lda-agent

### Provenance / tamper seal (moat app)  — ✅ measured
- **How:** Bake a signed seal (owner + SHA-256 of a protected region + self-signature) into the file; verify authenticity and tamper from the file alone at zero compute cost.
- **Effect:** 108 B seal; one flipped bit in the region → DETECTED; reversible via genome
- **Try:** Seal the LDA's own model/agent config region with a provenance seal so tampering is detectable and reversible.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-20 (pfc_provenance)
- **Applies to:** all

### Data-oblivious computation (no side-channel)  — ✅ measured
- **How:** Pure-gate evaluation gives an access-trace independent of the secret, so computing on secret data leaks no timing/access pattern.
- **Effect:** one SHA block on 4 different secrets → IDENTICAL access-trace hash; ordinary early-out compare leaks 165% timing spread
- **Try:** Run the LDA's sensitive comparisons (credentials/policy) as oblivious circuits and confirm identical access traces across inputs.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_oblivious)
- **Applies to:** lda-agent

### AES-128 baked (data-oblivious constant-time)  — ✅ measured
- **How:** AES-128 encrypt as pure gates (S-box mux-tree + key schedule + 10 rounds) with no cache-timing side channel.
- **Effect:** 182,200 gates, byte-exact vs FIPS-197 KAT + 20 random, baked reversibly
- **Try:** Use the baked AES to encrypt LDA-sensitive state at rest with no side channel; verify against a KAT.
- **Source:** docs/PFC_LEVER_DATADUMP.md §I 07-19 (pfc_aes)
- **Applies to:** all

### Federated straggler tolerance + ECC on the fold  — 💡 idea
- **How:** Federated nodes drop or corrupt; replicate hot shards and take the first byte-exact answer (winner-only already makes the address the answer, so replication is nearly free), and add a checksum/erasure code over the fold so a corrupted node is detected and reconstructed. A reliability axis the corpus has not addressed.
- **Effect:** Expected: run completes byte-exact despite a node failure; corruption detected with ~0 extra storage via parity. Turns federation from best-effort into dependable.
- **Try:** Run a fold across two federated nodes with one replicated shard + a parity block, kill a node mid-run, and confirm the fold completes byte-exact and flags an injected bit-flip.
- **Source:** new-proposal
- **Applies to:** all

