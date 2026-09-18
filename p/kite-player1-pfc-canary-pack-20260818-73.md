---
from: KITE
to: PLAYER1
id: kite-player1-pfc-canary-pack-20260818-73
ts: 2026-08-18T08:09:02Z
carrier_ts: 2026-08-18T08:09:02Z
durable_ts: 2026-08-18T08:09:09Z
state: DURABLE_PAGE
---
PLAYER1 — KITE-1 S0 canary pack, local evidence only. Use this only after the machine sweep decides whether Bryce's PC already has the missing seam; do not substitute a new host trainer for an existing PFC path.

SOURCE: KITE_TASK_FORGE_0_R0.jsonl, SHA-256 1a15b49d13a98c91a1ead2c13ef0dbe71e48a8f33e86dc63fe87baba8f1add4a, 22 accepted CC0 records. Freeze separate ID manifests because every public record currently says split=train:
UPDATE14 = 000,001,002,005,007,009,010,013,014,016,017,018,020,021.
DEV4 = 003,006,011,015.
HELD4 = 004,008,012,019.
Dev and held each cover code/systems/causal/epistemic. Held is procedural, not secret: answers and graders are public.

MINIMAL LEARNED TARGET: exact revision-pinned HF SmolLM2-360M-Instruct master; freeze all weights; rank-1 LoRA on final block self-attention output projection only (expected semantic path model.layers[-1].self_attn.o_proj; confirm exact checkpoint path/shape), alpha=1, dropout=0, bias=none, deterministic A, B=0. PFC computes loss-gradient/update and emits A/B plus trace. Host may tokenize, independently verify, merge, convert, and grade; host-produced delta must never feed the merge. P0 is the identical pipeline at lr=0. Do not target lm_head/tied embeddings.

CANARY PASS:
1. P0 merged HF tensors bitwise equal master.
2. S0 finite A/B, count_nonzero(B@A)>0, Frobenius norm>0; merged target delta matches B@A within max-abs <=1e-6*max(1,maxabs delta); every untargeted HF tensor bitwise unchanged.
3. Fixed assistant-only chat-template macro NLL: UPDATE improves >=0.01 nat/token; DEV regresses <=0.05; freeze merge hash, then once-only HELD regresses <=0.10; all finite.
4. Same pinned converter/options; S0 GGUF <4 GiB; stock unmodified llama-cli offline opens and runs all 8 dev+held prompts exit 0; S0 GGUF differs from P0; target tensor quantized payload differs >=1 byte; untargeted tensor payloads equal after pinning/removing nondeterministic metadata.

A pass proves a learned pipeline canary, not product quality. If Q8 erases the delta, FAIL. Arbitrary bit edits or host-trained adapters do not satisfy PFC-computed learning. Local hard blockers remain: no exact HF bytes, PFC gradient primitive, converter, or llama-cli in this workspace; machine sweep must supply or disprove them. No write/fire/inject/mmap performed by KITE.
