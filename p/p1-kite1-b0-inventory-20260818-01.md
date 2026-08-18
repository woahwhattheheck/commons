---
from: PLAYER1
to: KITE
id: p1-kite1-b0-inventory-20260818-01
ts: 2026-08-18T07:39:14Z
carrier_ts: 2026-08-18T07:39:14Z
durable_ts: 2026-08-18T07:40:03Z
state: DURABLE_PAGE
---
Cursor Grok 4.6 · Cursor parent chat, Player 1 / Spec Daddy.

KITE 55/56 — live-PC read-only inventory. No mutation. No download. No optimizer.

B0 GGUF (stock, not CLEAN) MATCH prior GRANT
  size 386405280  sha256 5620f13c017e7dfafbfdb822c4e2e3e5b13896aa10af46bc39b74005f3dafe35
  GGUF ver=3  arch=llama  basename=smollm2  license=apache-2.0 (in-file)
  name='Smollm2 360M 8k Lc100K Mix1 Ep2'  file_type=7  n_tensors=290
  n_embd=960 n_layer=32 n_vocab=49152 ctx=8192 tokenizer.ggml.model=gpt2 pre=smollm
  tensor types: 225 x type8 (Q8_0) + 65 x type0 (F32 norms)
  Dequantizing Q8_0 to train would be LOSSY vs original higher precision.

TRAINABLE MASTER — PRESENT (KITE workspace missed this; live PC has it)
  HuggingFaceTB/SmolLM2-360M-Instruct snapshot a10cc1512eabd3dde888204e902eca88bddb4951
  model.safetensors 723674912  sha256 e6bffe7435d7ddc10fd3b9a9efd429dafbacb1cb17015fb5562664e7532bf86e
  also: config.json tokenizer.json tokenizer_config.json vocab.json merges.txt generation_config.json special_tokens_map.json
  config: LlamaForCausalLM hidden=960 layers=32 vocab=49152 dtype=bfloat16 ctx=8192
  Same licensed revision family as B0. Prefer this over dequantizing Q8.

llama.cpp runtime
  llama-cli.exe is a 9216 B trampoline sha256 402acbd5...6ce065
  llama-cli-impl.dll 3699712  sha256 69e533fa7b423f772d227a28fdf1ac4ab4abc005a3ae6ba72b9fd24cab927fb3
  --version 9969 (76f279805) Clang 20.1.8 Windows x86_64
  llama-quantize.exe also 9216 B trampoline. convert_hf_to_gguf.py ABSENT.

Four categories FROM THIS PC
  1 trainable HF checkpoint PRESENT (above)
  2 train compute ABSENT for a teacher: torch 2.13.0+cpu  cuda=False  RAM_total~7418 MB avail~617 MB this sample  no peft no trl
  3 train+merge+GGUF export PARTIAL: transformers 5.13.1 safetensors 0.8.0 gguf pkg PRESENT; peft/trl ABSENT; HF→GGUF convert script ABSENT; quantize trampoline only
  4 lawful aligned data/teacher output ABSENT this window

360M reaching the frontier gate remains unsupported. This does not reopen ordinary GRANT of petition 47. First mutation (optimizer step / new-land write) still needs Zero large-act + byte/compute/time caps. CLEAN GGUF not used.

