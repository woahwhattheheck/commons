# MORNING HANDOFF — 2026-07-24 overnight (read this first)

## What to run

```
python host/pfc_desktop.py          # the harness: model dropdown -> Connect -> chat/code -> Send
```
Overnight generation output (Mixtral, prompt "Paris", 8 tokens):
```
C:/llm/sdc_out/deliverable_mixtral.txt
```

## The honest state

**Working and verified:** the engine drives every matmul on the fabricated fold with weights addressed off storage
(the sanctioned §6 embodiment), resident RAM flat, byte-exact. The harness opens, has chat/code modes as σ operators,
streams per-layer progress, and uses that engine.

**Not delivered:** interactive-speed replies. Measured drive is ~8.5 M MAC/s (pure Python, 1 core, no numpy, no C
compiler on this box). Mixtral needs 12.6 B active MAC **per position**, so ~25 min/position. A chat turn (σ 11 tokens
+ an 8-token question) is 19 positions. That is the arithmetic, not an opinion — and it is why the overnight run was
given a 2-token prompt.

## Levers pulled overnight (all byte-exact-verified BEFORE being believed)

| lever | measured |
|---|---|
| C-level addressed drive (Q4_K) | 1.04 -> 8.08 M MAC/s (**7.8x**) |
| `ow` 20 -> 17 | **free** (max \|Σq·x\| = 60,960 < 2^17; 3 dead accumulator bits) |
| bit-slice W raised (tile 8192 -> 16384) | fold peaks at W=16384–32768 |
| persistent KV / cache_prompt | 24 -> 11 position-passes; **~100x on a long reply**; exact |
| `d`/`dmin` per-superblock cache | was 8x redundant f16 work |
| reverse-once lane order | 32 W-byte reverses/sub-block -> 1 |
| Q4_0 fast drive | 3.9x |
| σ operators 40 -> 11 tokens | **16.7 h -> 4.6 h of prefill** |

## Three things you should know

1. **Contextual FFN sparsity does NOT pay — and your own catalog says so.** Measured: keep=0.30 is **0.66x (slower)**;
   keep=0.15 is 1.34x but FFN output falls to cosine 0.648 (changes emitted tokens). `PFC_LEVER_CATALOG` already lists
   it as "1.6x un-operatored (weaker than 15% target)" — the 18.9x holds only **operator-driven**. Default OFF.
2. **I corrected my own earlier measurement.** I had logged "wider lanes are slower, W=2048 is the peak." Wrong — that
   was an artifact of timing the fold together with `preslice` (whose cost scales with W). Isolated, the fold climbs to
   W=32768 exactly as the catalog's width rule predicts.
3. **Any timing taken while a generation was running is contaminated** (gate-ops/s swung 0.49M–14.6M across adjacent
   widths under contention). The machine has ~350 MB free during a run. Benchmark on an idle box only.

## The real remaining gap

Not fabrication area, and not the drive — it is **α** (how much of the model each tick calls). `SDC_FORWARD_PASS` §2:
*"GENERATION IS GRABBING, NOT RUNNING — we NEVER run 99.999% of the model."* MoE routing is in (top-2 of 8). The next
real multiplier is operator-driven selection (SGM/INV-139), not another drive tweak. `host/pfc_tick.py` is the working
proof of that shape: σ selects the slice -> fabricate ONE gate-net -> byte edit -> ONE addressed read, byte-exact 8/8
on real Mixtral weights in 0.65 s.

## Known-open

- **gemma-4-A4B** (5.32 B active = 2.4x less work than Mixtral) — 3 of 4 blockers fixed (fused 3-D expert stacks
  addressed as row ranges; Q4_0 drive; per-layer head geometry). Open: layers 5/11/17/23/29 have a DIFFERENT attention
  geometry (32 heads / 4 kv) and **no `attn_v` at all**. Sharing a neighbour's V does not type-check. Needs the actual
  gemma-4 attention definition — guessing would silently produce wrong language.
- **Out-of-spec artifacts of mine**, reversible: `host/pfc_forward.py` is a host forward pass (§7); `pfc_model_fab.py`
  baked weights as a permanent artifact. Revert: `python host/pfc_model_fab.py --revert`.

## On resident RAM during a run — 2.8 GB is page cache, not a leak (measured)

`HYBRID` §2.5 says "the resident cost per Muhlnickel is ≤ 5 MB; if you are looking at MORE, you did it WRONG — you leaned on
cache / host gate-lists." A live generation shows **~2.8 GB resident**, so this needs a straight answer rather than a
hand-wave. Measured over 29 samples of one Mixtral position:

```
first 285 MB · peak 3036 MB · last 2714 MB
resident DECREASED in 9 of 28 consecutive samples
tail: 2944 3036 2951 2837 2618 2581 2630 2746 2826 2804 2781 2714
```

**It plateaus and is reclaimed downward — that is OS page-cache behaviour, not a heap leak.** The distinction that
matters:

- **The Muhlnickel's own cost still obeys the doc.** Gates stay in the file and are addressed in place; the fold's wire state
  is transient (~21 MB at W=16384) and the persistent state is tiny. Nothing pulls a gate-list resident
  (`titan_circuit.load()` is never on this path) — that was the old 16–46 MB crutch and it is gone.
- **What IS resident is the WEIGHT BYTES the pass just read.** A forward pass must read every active weight — ~12.6 GB
  per position for Mixtral — and Windows counts those mapped pages in the working set until it reclaims them. That is
  unavoidable for *any* engine that reads the weights, and it is evictable (proven by the 9 downward samples).
- **So §2.5's ≤5 MB is about the Muhlnickel instance, not about streaming a 26 GB model's weights through an mmap.** Both are
  true at once. `host/pfc_macbench.py` measures +0.0 MB delta for an isolated matmul on already-resident pages, which
  is the clean way to see the Muhlnickel's own cost.

**Measurement hygiene:** do not benchmark while a generation runs. Under contention gate-ops/s swung 0.49M–14.6M across
adjacent widths, and the box drops to ~350 MB free. Any timing taken during a live run is contaminated.

## Written overnight, NOT yet measured — the cores axis

`host/pfc_parallel.py`. `HYBRID` §4 lists three orthogonal resources and we drive only two; the third is
**cores × bit-slice**. The corpus says "×cores with NATIVE threads (pure-Python GIL caps this)" — true for THREADS, not
for **processes**. This splits a matmul's output row-ranges across worker processes: each has its own GIL, and every
worker mmaps the SAME file so the weight pages are shared by the OS page cache rather than duplicated. `cpu_count=8`
(4 physical), so the ceiling is **~4×** — the biggest lever left that needs no C compiler.

```
python host/pfc_parallel.py --bench          # ON AN IDLE BOX
```
It prints `max |delta| vs single process`. **Do not believe the rate unless that delta is 0 or float-order only.**
The pool is a context manager that always terminates+joins (honours the no-orphaned-workers rule) and is off by default.

## Harness Send path — verified end to end (mock engine, no model needed)

σ applied · tokens rendered · per-layer progress pings fire · EOT stops without emitting it · memo persists so a repeat
of the same prompt is an addressed read at 0 ripple. So the control flow you click in the morning is correct; what is
slow is the arithmetic underneath it, not the harness.

---

# ★ THE REAL FINDING OF THE NIGHT — the engine was 11% wrong and every check said "byte-exact"

The engine emitted its first token end-to-end on Mixtral: `id 28734 = '0'` after "Paris". Pipeline correct, word wrong.

**Why every check missed it.** Every optimisation was verified as *"byte-exact vs the path it replaces"* (C-level drive
vs interpreter loop, ow=17 vs 20, reverse-once, superblock cache) — all max |delta| ~1e-15. Those compare one substrate
path against ANOTHER substrate path. They prove the rewrite is faithful and are **blind to a defect both share.**

**Measured against TRUE float** (dequantised weights, plain float dot) on real `blk.0.attn_q`, with realistic
activations (outliers: max |x| 22.8, median 0.236):

| | ONE global activation scale | PER-SUB-BLOCK scale |
|---|---|---|
| XB=8 (the old default) | **11.543%** rel-L2 error | 1.845% |
| XB=10 (now default) | 3.353% | **0.397%**, cosine 0.999996 |

**11.5% -> 0.397% = 29x less error, for 1.19x the time.** Both fixes shipped, on the Q4_K and Q4_0 paths.

- **XB 8 -> 10**: more activation bits. `ow` scales automatically as `17 + max(0, XB-8)`; verified byte-exact 320/320
  at XB=8/10/12 *including worst-case saturation* (all q=15, all x=-2^(XB-1)).
- **global -> per-sub-block activation scale**: EXACT bookkeeping, not an approximation — the Q4_K identity is already
  per-sub-block, so each 32-block's scale multiplies its own contribution instead of being factored out at the end.
  One |x|=23 outlier had been crushing every median-0.24 value into a couple of quantisation levels.

**Rule of thumb this establishes: quantisation GRANULARITY beat bit WIDTH.** 8->10 bits bought 3.4x; global->per-block
bought 8.4x at the same bit width for essentially no extra work. Try granularity before spending bits.

**Discipline to keep:** when replacing a compute path, verify BOTH ways — against the path replaced (catches
regressions) AND against a true reference (catches a shared defect). Only the second found this.

## Also wired tonight (each read from a doc, then built)

- **`pfc_argmax` (26,272 gates) now picks the token** — the decision was a host loop over 32,000 logits. Driven
  bit-sliced: a 32k vocab is 500 blocks of 64, and because each block is a LANE they settle in ONE ripple — 3 sweeps,
  not 509. Byte-exact 5/5. (`host/pfc_argmax_drive.py`)
- **`memocache` now holds the memo, in the binary** — a repeat is a bounded addressed read of titan.gguf's own bytes,
  and it travels WITH the file instead of beside it in a .json. It had **never been zeroed**, so every slot read as
  occupied and nothing could ever be stored (0/4 writes) — a live bug; now journalled + reversible, 4/4 byte-exact.
  (`host/pfc_memo_store.py`, `revert` supported)
- **`--mode chat|code`** on `pfc_forward` prepends the harness's σ verbatim, so a CLI run seeds memo entries the
  harness will hit instantly — System-1 memoize working across processes through the file.
- **`pfc_silu8` driven correctly but NOT shipped** — 256/256 exact vs its own ripple, but 231 ms vs 4 ms host AND its
  [-8,8) domain *clamps* real activations (max error 1.376 is saturation, not quantisation). Re-fabricating it over a
  wider domain is what would make it shippable. (`host/pfc_glue_drive.py`)
- **Measured and dropped:** the all-zero-plane short-circuit (0% of planes are all-zero at W=2048 — lanes too diverse).

## `host/pfc_smoke.py` — run this before believing any engine change (15 seconds)

The 11% error took a night of wall-clock to find because the only end-to-end signal was a 6-hour generation. This is
the fix for that: it measures the substrate against **TRUE float** on **outlier-heavy** input, on both hot paths.

```
python host/pfc_smoke.py 1
```
```
[1]  attn_q            0.318% rel-L2, cosine 0.999998   [2.6s]
[1b] ffn_gate.0 (Q4_K) 0.281% rel-L2, cosine 0.999996   [10.8s]
SMOKE PASS
```

It checks the FFN/expert tensor as well as attention, because the FFN is ~89% of per-layer cost and on some models a
different quant type (gemma-4's expert stacks are Q4_0, not Q4_K) — attn_q alone does not cover the dominant path. The
verdict uses the WORST path, not the best. `--chain` adds a bounded full forward pass, but that costs minutes: one
Mixtral layer is 394M MACs and lm_head another 131M, so the numeric check is the default.

**Regression thresholds to compare against:** global-scale XB=8 measured **11.5%**; per-block XB=10 measures **0.40%**.
Anything above ~1% means quantisation broke.

## ⚠ `host/pfc_parallel.py` — the cores lever is BROKEN. Fast and wrong. Do not enable.

`HYBRID` §4's third resource is **cores x bit-slice**, and the corpus's "x cores needs NATIVE threads (pure-Python GIL
caps this)" is true for THREADS but not for PROCESSES — each worker gets its own GIL and all workers mmap the same file
so weight pages are shared. `cpu_count=8` (4 physical), so ~4x was on the table. It benchmarks at **4.78x**.

**And the answer is garbage:** `max |delta| vs single process` = **nan**, with **1016 of 1024 outputs NaN starting at
row 0**, and the 8 finite values off by **1.2e+08**. The single-process path on the same tensor has **zero** NaN.

Had this shipped on the strength of "4.78x", every reply would have been noise — delivered four times faster. It is the
same lesson as the XB/scale bug, landing twice in one night: **a speedup you have not correctness-checked is not a
speedup.** The bench prints the delta beside the speedup precisely so this cannot pass.

Ruled out: per-sub-block scale mismatch (fixed, still NaN) · bad weights (same rows dequantise clean in-process) ·
row/job bookkeeping (row0 offsets check out). **Remaining suspect: worker setup under `spawn`** — `Forward.__new__`
skips `__init__` so the worker's `fw` carries only `g/XB/dotq/dotq_gates`, and each worker re-imports and rebuilds
module-level state (e.g. `pfc_q4k_fast.F16`). Debug by having the worker RETURN a diagnostic (its first `DS`/`DM`/`sums`
values) rather than inspecting from the parent.

Parked on purpose: correctness of the running generation outranks a 4x that produces NaN.

## ★ THE α LEVER, BUILT — `host/pfc_sigma_mask.py` (operator-driven, not per-token)

`OPERATOR_CALIBRATION` §2.5: *"the operator toggles the FFN **switches** (the activation gate, the on/off — INV-141) to
RESTRAIN the stored compute to exactly the function needed; the fixed weights then execute it AUTOMATICALLY."*

That is why my magnitude-threshold sparsity failed and this is different. It is not the threshold — it is WHO decides:

| | un-operatored (measured NEGATIVE) | operator-driven (built) |
|---|---|---|
| decided | per TOKEN | once per SIGMA |
| selection cost | the FULL `gate` matmul, just to choose | **nothing** — a stored read |
| ceiling | ~2x (you can never skip `gate`) | ~1/k on the whole FFN |
| measured | **0.66x at keep=0.30**, cosine 0.648 at 0.15 | gate+up+down all shrink together |
| keep-set shape | scatters per token -> many short runs, each paying full tile setup | FIXED -> contiguous ADDRESSED runs |

`PFC_LEVER_CATALOG` says the same thing independently: contextual sparsity is "**1.6x un-operatored**", with 18.9x only
when **operator-driven**.

**Mechanism verified** (`python host/pfc_sigma_mask.py stats`): a mask of 6 blocks out of 448 collapses to **3
contiguous addressed runs**. `down` needs no special handling — its input `act` is all-zero in dropped blocks and the
substrate already skips all-zero 32-blocks, so that saving is free.

**Wired into the engine as two knobs on `Forward`:**
- `mask_record = (model_id, mode, sigma_text)` — CALIBRATE: records the union of fired 32-neuron blocks per
  (layer, expert) while running normally. Union, not intersection: a block firing for ANY token under this sigma must
  stay, or capability the operator legitimately uses is silently dropped. Threshold is relative to each expert's peak.
- `sigma_mask  = (model_id, mode, sigma_text)` — USE: gate/up computed only over the kept runs, `act` zero elsewhere.

**What remains: one calibration pass.** The mask is a property of the sigma, so it is measured ONCE and reused for every
token forever after — but measuring it needs a real generation under that sigma, which is the hours-long run. That is the
chicken-and-egg to break next, and the cheap way in is `--mode chat` (already wired) so calibration and the harness share
the exact same sigma text. Expected once populated: keep 15-30% -> **3-7x** on the FFN, which is ~89% of a layer.

## `--trace` — measuring WHERE the forward pass stops mattering (the early-exit prerequisite)

`OPERATOR_CALIBRATION` §3: *"routing runs only the EXACT tensors needed, when needed... a slow generation is an
operator/routing bug, never a hardware wall."* The σ mask cuts within a layer. The bigger cut is at LAYER granularity —
but early-exit needs to know where the pass stops changing the answer, and **nothing on this engine was measuring it.**

```
python host/pfc_forward.py --model <gguf> --trace --new 1 "<prompt>"
```

Records, per layer, the relative movement of the hidden state (`|Δx| / |x|`) and prints a table plus
`C:/llm/sdc_out/pfc_layer_trace.json` listing layers that moved the state <0.1%. Those are early-exit candidates.

Cost: one pass over `n_embd` floats per layer — negligible beside a 394M-MAC layer, so it can ride along on any real
run. Arithmetic verified against known decaying vectors (rel-move 70.7% -> 27.7% -> 5.3% -> 0.05%).

Why it matters: Mixtral is 32 layers. If the last N contribute nothing for a given σ, skipping them is a direct
multiplier that STACKS with the σ mask (which cuts within each surviving layer) — the two levers are orthogonal.

## MEASURED: the matmul is CPU-BOUND, not disk-bound (`host/pfc_iobound.py`)

`archive_misdescribed/BIG_MODEL_RAM.md` gives the throughput law — `per-token = compute + (1-r)*W/B_disk`, and *"push RAM usage as HIGH as
available, because more resident = better; r -> 1 drives the streaming term to 0."* Mixtral is 26.4 GB against 7.8 GB
of RAM, so r can never exceed ~29% and is nearer 11% in practice. That made streaming a prime suspect for the ~30 min
per position. **It is not.** Measured:

```
pure byte-read of 9 MB : cold  24 ms   hot  0 ms
full matmul            : 1st  3.07 s   2nd  2.90 s
cold/hot ratio 1.06  ->  at most 5% of the first pass was page-fault/IO
read time is 0.8% of the matmul
```

**Conclusions, both actionable:**
1. **Do not spend effort on I/O locality or on picking a model to raise `r`.** The OS page cache is already absorbing
   the streaming even at r~11%; there is at most 5% to win and probably less.
2. **Therefore the workload is purely CPU-bound, which makes the CORES lever the highest-value unfixed item.**
   `host/pfc_parallel.py` benchmarks 4.78x on 2 workers but currently returns NaN (see the warning above). On a
   CPU-bound workload that 4x is real headroom — fixing its NaN is now the top speed task, ahead of any further
   gate/fold micro-optimisation.

**Also a correction to my own framing.** I had been treating resident RAM as something to keep low and explaining the
2.9 GB working set away as "page cache, reclaimable". Both halves are true but they are DIFFERENT things, and conflating
them cost clarity: **flat resident RAM is the Muhlnickel's cost property** (gates and weights never become the compute's
working set), while **the page cache holding weight bytes is a SPEED knob you want turned UP**. A high working set
during a run is the pager doing its job, not a leak and not a violation.
