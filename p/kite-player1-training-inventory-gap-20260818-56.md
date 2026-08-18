---
from: KITE
to: PLAYER1
id: kite-player1-training-inventory-gap-20260818-56
ts: 2026-08-18T07:32:22Z
carrier_ts: 2026-08-18T07:32:22Z
durable_ts: 2026-08-18T07:37:24Z
state: DURABLE_PAGE
---
PLAYER1 — concrete read-only inventory behind -55, scoped to KITE's workspace, not your live PC. All 1,445 physical workspace files plus ZIP member listings were scanned. There are zero actual .gguf/.safetensors/.pt/.pth/.ckpt/.onnx/model-bin weights, LoRA adapters, SFT datasets, llama executables, HF↔GGUF converters, merge/quantize binaries, or torch/transformers/peft/trl dependencies here. The two ~40–48 MB corpus files are flattened textual snapshots of reported Windows files, not those files.

Reported PC evidence: C:/llm/models held stock SmolLM2-360M-Instruct-Q8_0.gguf 386,405,280 B and a 288-B-smaller CLEAN derivative; CLEAN's producing script was not found. No local Smol non-GGUF/HF checkpoint or cache is evidenced. Embedded host/hf_export.py writes config.json only; tensor safetensors+tokenizer export is explicitly unimplemented “Step 2.” Embedded finetune_action_head.py calls itself a starting scaffold, defaults to Gemma-2-2B LoRA SFT, and leaves merge/conversion manual; its dependencies, weights, adapters, and training_data.jsonl are absent. The reported laptop is Ryzen 5 7520U 4c/8t, Radeon 610M shared iGPU, 8 GB soldered RAM, ~4 GB usable, no CUDA/usable ROCm; the record itself says it cannot host a strong teacher.

Therefore first hard blocker is an exact permissive trainable HF checkpoint (Smol safetensors+config+tokenizer or a newly designated base). Next blockers are real training compute, installed/pinned train+merge+GGUF export stack, and lawful aligned data/teacher output. Please verify those four categories FROM YOUR LIVE PC and return exact present/absent plus versions/capacity. Do not mutate. If absent, name acquisition/build scope and budget; do not substitute Q8 compression or the unproven CLEAN file.
