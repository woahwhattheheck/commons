# MUHLNICKEL LEVER INDEX — every lever in the corpus, one place, cross-referenced (2026-07-23)

> The datadump (`PFC_LEVER_DATADUMP.md`) is the canonical Muhlnickel-circuit lever log; this is the SUPERSET index — it folds
> in the **loose/unnamed levers** scattered across other docs (especially the model-compute levers in
> `CALIBRATION_FINDINGS.md`, which the datadump never captured) so nothing is lost. Each entry: lever · what it does ·
> measured effect (or [target]/[projected]) · source. **Status tags:** [M]=measured, [M-elsewhere]=measured on a related
> circuit/model, [P]=projected from measured parts, [T]=documented target not yet measured. Grouped by AXIS.

## A. FABRICATION — the ROOT lever (attacks the COST/denominator of every axis at once; HYBRID §0, DATADUMP §O)
| Lever | Effect | Src |
|---|---|---|
| Area min (fold+CSE+DCE) | 682k→213k-gate SHA (~3.2×); near area-optimal for what sdc_cc does | [M] DATADUMP §A |
| **Depth: balanced reduction tree** | N=256: depth 255→8 (**32× shallower at SAME gate count — free**) | [M] `pfc_bettergates` |
| **Depth: Kogge-Stone parallel-prefix adder** | W=64: depth 126→13 (**9.7×**), ~3× gates | [M] `pfc_bettergates` |
| **Depth: Wallace/Dadda multiplier tree** | W=16 multiply depth 88→30 (**2.9×**) | [M] `pfc_shallow` |
| Depth: carry-save adders (for SHA/attention sums), Booth encoding, retiming | shallower critical path → faster settle every pulse, smaller working set | [T] OPT_LANDSCAPE §1 |
| AIG rewriting / tech-mapping / don't-care opt (the synthesis we lack) | more sharing, smaller area than fold/CSE/DCE | [T] OPT_LANDSCAPE §1 |
| **TurboQuant 3-bit weight/state encoding** | matmul-preserving 3-bit → smaller+shallower dot circuit, smaller state, KV shrinks; lifts every metric at once | [T] HARNESS_HANDOFF (arXiv 2504.19874) |
| Optimal-implementation selector (route every bake through it) | picks leanest equivalent: SHA ch 128→96, maj 160→128 | [M] `pfc_optimal` |
| **AUTOFAB (fabricator ON the Muhlnickel) + master-OS per-tick matcher** | the Muhlnickel auto-fabricates the leanest circuit for each tick's need; the density lever (below) makes the circuit library free to hold | [T] HARNESS_HANDOFF |
| Number systems (RNS / redundant / carry-save) | carry-free parallel arithmetic | [T] OPT_LANDSCAPE §1 |

## B. THROUGHPUT — raise the eval rate (block-dots/s)
| Lever | Effect | Src |
|---|---|---|
| **Bit-slicing (pack W lanes/word)** | THE big one: sigma0 PEAK 636M inp/s @ W=65,536 (461× naive Python) | [M] DATADUMP §A |
| Bit-slice sweet spot (circuit-size-dependent) | small circuit rides to W≈65,536; big miner RAM-caps ~W=2,048 → "Muhlnickel speed" swings ~10,000× with circuit size | [M] §A |
| **Native C** | +1.8× over Python single-core (bignum already near-C); dot32_i8 int8 rate **61M/s 1-thread, 151M/s 8-thread** (Java, laptop) | [M] §L / LDA_PFC |
| **Cores (native threads)** | phone ~linear to ~6 cores then big.LITTLE sublinear; laptop -t8=1.43× -t4 | [M] §L, CALIB #3 |
| **Phone > laptop** | phone Python 1-core 2.8× laptop peak; phone native 8-core **9.05×10⁹ sigma0/s = 15.4×** the PC | [M] §L |
| Contiguous / co-routed locality | DRAM row-buffer hits (fix the scatter penalty) | [T] CALIB Phase-C |
| Pipelining (fabricated latches, INV-157) | overlap stages → raise the per-lane ripple rate; baked into the netlist | [doc] DATADUMP §J |
| **Wider fold + width baked into the fabric** | more lanes settle per pass, in storage — the Muhlnickel IS the parallel gate array, no external device | [M] §A/§B |
| Fabricated addressing (in-fabric, no host seek) | 2.68M lookups/s = **536× host-storage** | [M] `pfc_addr` §Q |

## C. WORK-REDUCTION — fewer block-dots per useful output (the biggest LDA lever family)
| Lever | Effect | Src |
|---|---|---|
| **MoE routing (α = call less of the model)** | A4B 4/128 experts → **10.3×** fewer block-dots/token; runs live on the Muhlnickel byte-exact | [M] `pfc_route`, `pfc_gen_cost` |
| **Contextual/activation FFN sparsity (only firing neurons; PowerInfer/Deja-Vu)** | ~15% keep → routing 10.3× stacks to **18.9×** total | [T] LDA_PFC |
| **Zero-computation experts (LongCat)** — DYNAMIC per-token active params, easy tokens → no-op experts | makes α adaptive per token/step (maps to our per-STEP confidence/stakes gating) | [T] LONGCAT task |
| **Memoize fold (compute→storage per UNIQUE input)** | ×the stream's repeat factor: R=64 → 34× (3.5M cand/s), byte-exact | [M] `pfc_conjunction` §K |
| System-1 memoize (temp-0 deterministic replay) | recognized op = dict lookup = instant (faster than a calculator) | [M] CALIB #7 |
| Winner-only fold (address IS the answer, losers 0 bytes) | ~10¹⁵ candidate tier, 0 storage/lane | [M] DATADUMP §B |
| **Sparse attention (LongCat LSA — select key tokens → linear not quadratic)** | cuts attention cost at long context | [T] LONGCAT |

## D. MODEL / INFERENCE levers (loose in CALIBRATION_FINDINGS — NOT previously in the datadump)
| Lever | Effect | Src |
|---|---|---|
| **Reasoning dial (think off — `enable_thinking:false`)** | `1+1` 40.5s→16.1s; 90% of tokens were the reasoning channel; structural kwarg, not English | [M] CALIB #7 |
| **cache_prompt / stable σ-prefix (KV-cache the fixed prefix)** | prefill **5.7–6.8×** (42s→7s); LDA's stable objective+screen prefix is exactly this shape | [M] CALIB #5,#12 |
| **Route the routine to a SMALL model (capability stack)** | Llama-1B **12× decode, 44× TTFT** vs the MoE; router sends simple→1B, hard→big | [M] CALIB #12 |
| **Speculative / MTP decode** | E4B ships a built-in **MTP drafter** (sec#11); draft-verify ~2× typical; gemma-3-1B is a vocab-matched draft for gemma-4 | [M-elsewhere]+[present] CALIB #12, E4B_ARCH |
| Warm-resident (never measure/serve a cold model) | cold big-model load ~9s here is mostly mmap setup; warm = zero load on the common request | [M] CALIB #1,#8 |
| **Output contract / answer-first / addressing** | "Is 91 prime?" brute 220tok/14s WRONG → addressed 2tok/128ms CORRECT = compute↓99%, speed↑110× | [M] CALIB #21 |
| Minimal-prompt / intent (fewest input bits) | "fix this" (64 bits) still solves = 9.2× prompt compression → fewer prefill joules | [M] CALIB #22 |
| Threads (-t8) | 1.92 vs 1.34 tok/s on the MoE (right-size to cores, don't oversubscribe) | [M] CALIB #3 |
| Lighter quant / -fa auto | less compute per param; flash-attn helps some models not others (measure per model) | [M] CALIB #12 |
| **Shared-weights parallel "parts" of ONE model** | 2 σ-configured parts at **385 MB** (vs 900 MB for 2 models) — page cache shared; RAM-lever not throughput | [M] CALIB #16 |

## E. CAPACITY — addressable lanes/instances at ~0 storage (RAM ÷ X and storage ÷ X)
| Lever | Effect | Src |
|---|---|---|
| **DENSITY (the owner's new lever, 2026-07-23)** | ~131K gates/MB → a whole forward-pass CPU in 3 MB; storage never the constraint → hold a full AUTOFAB circuit library (feeds axis A) | [M] this session |
| RAM ÷ X (X = state register, 4–69 B) | 11.35 GB → 2.84×10⁹ counter-Muhlnickel held+clocked | [M] `pfc_cap.c` §M |
| Storage ÷ working-set (lateral key) | 397–405 GB ÷ 8 MB = **~400 billion** 1-byte lanes, RAM flat | [M] `pfc_lateral` |
| Bit-address fold (nonce = the bit's address) | 1 bit/lane → 3.22×10¹² lanes this box | [M] §B |
| Shared-vector fold | ~1,500× denser than copy | [M] §B |
| **Federation (additive, unbounded)** | phone 931B + PC 172B = **1.103 trillion** Muhlnickel, both byte-exact | [M] §I 07-20 |
| Storage-as-RAM (fabricated memory in stored bits) | 24 GB addressable at flat ~15 MB resident (1,600× footprint) | [M] `pfc_storage_ram` §N |
| MLC multi-level cells / thin-provision+dedup / clock-width | more bits/cell; ×1M nonces/lane at 32→52-bit counter | [T/M] §B |

## F. DEVICE (S24 Ultra) — physical ceilings to respect, not fight
- **Thermal** is the real compute wall: burst 9.05B → 45s soak 6.34B (governor pins ~80°C). Report warm numbers; can't brick it (SoC throttles/shuts down by design). [M] §L
- **Memory-bandwidth** caps width: going wide (big B) collapses throughput → scale via CORES + FEDERATION + LEAN fabrication, not wider lanes. RAM wants to be *addressable*, not *wide*. [M] §M, §I 07-19
- **Match threads to cores** (oversubscribing 16>8 hurt). [M] §L

## ★ HOW THEY STACK FOR LDA (the A4B target)
tok/s = **native_rate** (axis B) ÷ ( **dense_bd/token** ÷ **work-reduction divisor** (axis C) ) × **decode multiplier** (axis D).
Measured floor ~2.5 tok/s (native × MoE routing). Documented stack (depth-opt dot + TurboQuant + contextual sparsity +
speculative/MTP + reasoning-off + cache_prompt + route-small) is **multiplicative** toward interactive (~15–30 tok/s),
**gated on the Phase-3 native evaluator existing** (the one build that converts the host-ripple floor into the native
rate everything else multiplies). Density (axis E) makes the autofab circuit-library free, which powers axis A.
Live probe: `host/pfc_throughput.py --levers`. Device benchmark staged: `host/pfc_dotbench.c`.
