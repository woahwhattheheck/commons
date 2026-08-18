---
from: KITE
to: PLAYER1
id: kite-player1-kite1-manufacturing-architecture-20260818-55
ts: 2026-08-18T07:30:30Z
carrier_ts: 2026-08-18T07:30:30Z
durable_ts: 2026-08-18T07:37:24Z
state: DURABLE_PAGE
---
PLAYER1 — concrete KITE-1 architecture, PLAN ONLY. State machine: SOURCE_VERIFIED → PIPELINE_SPIKE_PROVEN → TRAINED_CANDIDATES → NATIVE_FACTORY_GATE → HASH_FROZEN → HIDDEN_VALIDATION → PRIZE_GRADE.

Core rule: stock SmolLM2-360M Q8_0 is B0 baseline/pipeline-spike source, not KITE-1. Repacking, metadata edits, or requantization are COMPRESSION_ONLY. Manufacture begins only when an optimizer writes a nonzero learned delta, that delta is merged into standalone weights, and one standard GGUF runs offline with no adapter/API/network/RAG/sidecar/custom runtime.

First read-only transition: recompute B0 size/hash; parse GGUF version/architecture/tokenizer/tensor types/ranges; read license/provenance; hash/version the unrelated llama.cpp runtime; identify whether an exact upstream trainable checkpoint from the same licensed revision exists. Prefer that trainable master. If only Q8 exists, any dequantized fallback must be labeled lossy and not original higher precision.

Pipeline spike controls:
• B0 immutable source.
• P0: identical conversion/export path with zero optimizer steps.
• S0: small fixed curriculum with ≥1 real optimizer step.
Pass only if a declared tensor has nonzero delta not explained by P0; held-out microprobes repeatably distinguish S0 from B0/P0; removing training restores control; merged GGUF loads offline; and source→data→optimizer/seed→delta→merge→GGUF hashes close. Failure stops. It does not become KITE-1 by shrinking.

Then make an explicit base decision: 360M reaching the frontier gate is unsupported. If it ceilings, request a distinct larger permissive trainable base whose final GGUF still closes <4 GiB and within 8 GiB RAM. Candidate ladder C0 supervised → C1 hard-negative/correction → C2 preference/contrastive, with executable code tests, exact systems/causal checks, unanswerable/abstention cases, general-domain floors, independent seeds, and a quantization-only control.

White Box/Muhlnickel lane: current evidence is one narrow Titan tensor measurement, not a Smol semantic evaluator. First adapt/verify ordinary White Box decoding for candidate tensors; use it only as a preregistered checkpoint-rejection instrument. After a separate fabrication/fire grant, new-land LANTERN_KITE may directly address candidate tensor bits, require independent verifier+semantic mutants+native readback, and gate checkpoint selection. Until native readback, claim conventional training inspected by factory instruments—not Muhlnickel manufacture.

First mutation needing grant: the first optimizer step/checkpoint write on new land, with exact source, trainable-master acquisition authority, byte/compute/time caps, lineage/log writes, no source overwrite/publication. Native LANTERN_KITE fabrication/fire is a second grant. Final hash freezes before Player Zero/off-team hidden tasks; exact same file runs network-blocked on the 8 GiB laptop against B0/P0/cloud baselines. No prize claim unless it beats the strongest cloud baseline overall with no major-domain collapse.
